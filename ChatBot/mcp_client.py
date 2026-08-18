"""
MCP HTTP Client Module
Connects to HTTP/POST JSON-RPC MCP servers (such as https://www.emailmd.dev/api/mcp)
and converts tools into LangChain BaseTool instances.
"""

import os
import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import create_model, Field

load_dotenv()

DEFAULT_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://www.emailmd.dev/api/mcp")

class MCPHttpClient:
    def __init__(self, server_url: str = DEFAULT_MCP_SERVER_URL):
        self.server_url = server_url
        self.request_id = 0

    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    async def _post(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.server_url, json=payload, headers=headers)
            resp.raise_for_status()
            text = resp.text.strip()
            
            # Handle SSE response format (event: message\ndata: {...})
            for line in text.split("\n"):
                if line.startswith("data: "):
                    json_str = line[6:].strip()
                    return json.loads(json_str)
            
            # Handle standard JSON response
            return resp.json()

    async def initialize(self) -> Dict[str, Any]:
        return await self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "langchain-mcp-client", "version": "1.0.0"}
        })

    async def list_tools(self) -> List[Dict[str, Any]]:
        res = await self._post("tools/list", {})
        if "result" in res and "tools" in res["result"]:
            return res["result"]["tools"]
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        res = await self._post("tools/call", {
            "name": name,
            "arguments": arguments
        })
        if "error" in res:
            return f"Error executing tool {name}: {res['error']}"
        if "result" in res and "content" in res["result"]:
            contents = res["result"]["content"]
            outputs = []
            for item in contents:
                if item.get("type") == "text":
                    outputs.append(item.get("text", ""))
                else:
                    outputs.append(json.dumps(item))
            return "\n".join(outputs)
        return json.dumps(res.get("result", {}))

def json_schema_to_pydantic_fields(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Converts simple JSON schema properties into Pydantic field definitions."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = {}
    
    type_mapping = {
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": float,
        "object": dict,
        "array": list
    }
    
    for prop_name, prop_info in properties.items():
        prop_type_str = prop_info.get("type", "string")
        py_type = type_mapping.get(prop_type_str, str)
        description = prop_info.get("description", "")
        
        if prop_name in required:
            fields[prop_name] = (py_type, Field(..., description=description))
        else:
            fields[prop_name] = (Optional[py_type], Field(default=None, description=description))
            
    return fields

async def get_mcp_tools(server_url: str = DEFAULT_MCP_SERVER_URL) -> List[BaseTool]:
    """
    Connects to the remote HTTP MCP server and converts tools into LangChain StructuredTools.
    """
    client = MCPHttpClient(server_url)
    await client.initialize()
    raw_tools = await client.list_tools()
    
    langchain_tools = []
    
    for tool_def in raw_tools:
        tool_name = tool_def["name"]
        tool_desc = tool_def.get("description", "")
        input_schema = tool_def.get("inputSchema", {})
        
        fields = json_schema_to_pydantic_fields(input_schema)
        args_schema = create_model(f"{tool_name}_input", **fields)
        
        # Create a closure for tool execution
        def make_executor(t_name: str):
            def _sync_executor(**kwargs) -> str:
                # Filter out None optional values if necessary
                clean_args = {k: v for k, v in kwargs.items() if v is not None}
                return asyncio.run(client.call_tool(t_name, clean_args))
            return _sync_executor

        async def _async_executor(t_name=tool_name, **kwargs) -> str:
            clean_args = {k: v for k, v in kwargs.items() if v is not None}
            return await client.call_tool(t_name, clean_args)
            
        tool = StructuredTool.from_function(
            func=make_executor(tool_name),
            coroutine=_async_executor,
            name=tool_name,
            description=tool_desc,
            args_schema=args_schema
        )
        langchain_tools.append(tool)
        
    return langchain_tools

def fetch_mcp_tools_sync(server_url: str = DEFAULT_MCP_SERVER_URL) -> List[BaseTool]:
    return asyncio.run(get_mcp_tools(server_url))

if __name__ == "__main__":
    tools = fetch_mcp_tools_sync()
    print(f"\nSuccessfully loaded {len(tools)} LangChain MCP tools from {DEFAULT_MCP_SERVER_URL}:")
    for t in tools:
        print(f" - Tool [{t.name}]: {t.description[:70]}...")
        print(f"   Args Schema: {t.args_schema.schema()}")
