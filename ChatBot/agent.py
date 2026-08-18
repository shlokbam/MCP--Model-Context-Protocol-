"""
LangGraph Agent Engine
Defines the state graph, ChatMistralAI model node, MCP tool execution node,
and conversational memory saver checkpointer.
"""

import os
import uuid
from typing import List, Optional, Literal
from dotenv import load_dotenv

from langchain_mistralai import ChatMistralAI
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

SYSTEM_PROMPT = """You are an expert Email Design Assistant powered by emailmd and MCP (Model Context Protocol).
Your job is to help users write, lint, format, and render responsive, email-safe HTML emails.

Available MCP Tools from https://www.emailmd.dev/api/mcp:
1. `read_docs`: Fetch emailmd documentation (directives like hero, columns, callout, buttons, frontmatter, theme, etc.). Use this whenever you need syntax guidance.
2. `lint`: Check emailmd markdown for deliverability, accessibility, or formatting issues.
3. `render`: Convert emailmd markdown into final email-safe HTML. Returns html, plain text, and a `previewUrl`.

Best Practices:
- When writing emails, use proper emailmd markdown syntax.
- Lint the email using `lint` to ensure deliverability.
- Render the email using `render` to obtain the final HTML and live `previewUrl`. Always present the previewUrl to the user.
"""

def sanitize_messages_for_mistral(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Scans the entire message history and rewrites tool call IDs so that:
    1. Every tool call ID in any AIMessage is strictly unique.
    2. Every corresponding ToolMessage tool_call_id is updated to match the rewritten ID.
    3. Prevents Mistral API 400 'Duplicate tool call id' errors in multi-turn conversations.
    """
    id_mapping = {}
    new_messages = []

    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            new_tool_calls = []
            for tc in msg.tool_calls:
                old_id = tc.get("id") or str(uuid.uuid4())
                new_id = f"call_{uuid.uuid4().hex[:10]}"
                id_mapping[old_id] = new_id
                
                tc_copy = dict(tc)
                tc_copy["id"] = new_id
                new_tool_calls.append(tc_copy)

            msg_copy = AIMessage(
                content=msg.content,
                tool_calls=new_tool_calls,
                id=msg.id,
                additional_kwargs=msg.additional_kwargs
            )
            new_messages.append(msg_copy)
            
        elif isinstance(msg, ToolMessage):
            old_id = msg.tool_call_id
            new_id = id_mapping.get(old_id, old_id)
            tool_msg_copy = ToolMessage(
                content=msg.content,
                tool_call_id=new_id,
                name=msg.name,
                id=msg.id,
                additional_kwargs=msg.additional_kwargs
            )
            new_messages.append(tool_msg_copy)
        else:
            new_messages.append(msg)

    return new_messages

def build_agent(
    tools: List[BaseTool],
    mistral_api_key: Optional[str] = None,
    model_name: str = "mistral-small-latest",
    checkpointer: Optional[MemorySaver] = None
):
    """
    Builds and compiles a pure LangGraph StateGraph agent.
    """
    api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY is missing. Please provide it in .env or settings.")

    # Configure LangSmith environment variable
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    if langsmith_key and langsmith_key.strip():
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    llm = ChatMistralAI(
        model=model_name,
        mistral_api_key=api_key,
        temperature=0.2
    )

    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    tool_node = ToolNode(tools) if tools else None

    # Define Model Node
    def call_model(state: MessagesState):
        raw_messages = state["messages"]
        
        # Ensure system prompt is present at start
        if not raw_messages or not isinstance(raw_messages[0], SystemMessage):
            full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(raw_messages)
        else:
            full_messages = list(raw_messages)

        # Sanitize message history to ensure unique tool_call_ids for Mistral API
        sanitized_messages = sanitize_messages_for_mistral(full_messages)
        
        response = llm_with_tools.invoke(sanitized_messages)
        
        # Sanitize the single response message if it contains tool calls
        if isinstance(response, AIMessage) and hasattr(response, "tool_calls") and response.tool_calls:
            response = sanitize_messages_for_mistral([response])[0]

        return {"messages": [response]}

    # Define Routing Condition
    def should_continue(state: MessagesState) -> Literal["tools", END]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build Graph
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    
    if tools:
        builder.add_node("tools", tool_node)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", should_continue, ["tools", END])
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    from mcp_client import fetch_mcp_tools_sync

    print("Fetching MCP tools...")
    tools = fetch_mcp_tools_sync()
    print(f"Loaded {len(tools)} tools. Initializing LangGraph StateGraph with ChatMistralAI...")

    agent = build_agent(tools)
    
    config = {"configurable": {"thread_id": "test-session-1"}}
    query = "Draft a short welcome email for an AI newsletter, lint it, and render it."

    print(f"\nUser Query: {query}\n" + "="*50)
    
    for chunk in agent.stream(
        {"messages": [("user", query)]},
        config=config,
        stream_mode="values"
    ):
        latest = chunk["messages"][-1]
        latest.pretty_print()
