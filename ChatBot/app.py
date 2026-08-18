"""
Streamlit MCP Chatbot App
Powered by LangChain, LangGraph, LangSmith, and ChatMistralAI.
Connected to emailmd MCP Server (https://www.emailmd.dev/api/mcp).
"""

import os
import re
import json
import asyncio
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from mcp_client import fetch_mcp_tools_sync, DEFAULT_MCP_SERVER_URL
from agent import build_agent

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="emailmd AI Assistant (MCP Client)",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark Glassmorphism Styling
st.markdown("""
<style>
    /* Dark theme customization */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        padding: 1.2rem 1.8rem;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 1rem;
    }
    .main-title {
        color: #f3f4f6;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .subtitle {
        color: #9ca3af;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-mcp { background-color: #3b82f6; color: white; }
    .badge-mistral { background-color: #f59e0b; color: black; }
    .badge-langgraph { background-color: #10b981; color: white; }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "session_1"
if "preview_url" not in st.session_state:
    st.session_state.preview_url = None
if "rendered_html" not in st.session_state:
    st.session_state.rendered_html = None

# Sidebar Configuration
with st.sidebar:
    st.title("⚙️ MCP & Agent Settings")
    
    st.subheader("🤖 Model Settings")
    mistral_key = st.text_input(
        "Mistral API Key",
        value=os.getenv("MISTRAL_API_KEY", ""),
        type="password",
        help="API Key for ChatMistralAI"
    )
    
    model_choice = st.selectbox(
        "Mistral Model",
        ["mistral-small-latest", "mistral-large-latest", "open-mistral-7b"],
        index=0
    )
    
    st.markdown("---")
    st.subheader("🌐 MCP Server Config")
    mcp_url = st.text_input(
        "MCP Server Endpoint",
        value=os.getenv("MCP_SERVER_URL", DEFAULT_MCP_SERVER_URL),
        help="Remote MCP Server URL"
    )
    
    if st.button("🔄 Refresh / Connect MCP Tools"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Refreshed tools!")

    st.markdown("---")
    st.subheader("📊 LangSmith Observability")
    langsmith_key = st.text_input(
        "LangSmith API Key (Optional)",
        value=os.getenv("LANGCHAIN_API_KEY", ""),
        type="password",
        help="Required to push traces to LangSmith dashboard"
    )
    
    if langsmith_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = langsmith_key
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "emailmd-mcp-chatbot")
        st.markdown("🟢 **LangSmith Tracing:** ACTIVE")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        st.markdown("⚪ **LangSmith Tracing:** INACTIVE (Key missing)")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.preview_url = None
        st.session_state.rendered_html = None
        st.rerun()

# Main Header
st.markdown(f"""
<div class="main-header">
    <div class="main-title">
        📧 emailmd AI Assistant
    </div>
    <div class="subtitle">
        <span class="badge badge-mcp">MCP Client</span>
        <span class="badge badge-mistral">Mistral AI</span>
        <span class="badge badge-langgraph">LangGraph Engine</span>
        Connected to <code>{mcp_url}</code>
    </div>
</div>
""", unsafe_allow_html=True)

# Fetch MCP Tools
@st.cache_resource(show_spinner="Connecting to emailmd MCP Server...")
def load_tools(url: str):
    return fetch_mcp_tools_sync(url)

try:
    mcp_tools = load_tools(mcp_url)
except Exception as err:
    st.error(f"Failed to connect to MCP Server: {err}")
    mcp_tools = []

# Top expander displaying active MCP tools
with st.expander(f"🛠️ Active MCP Tools from Server ({len(mcp_tools)} tools discovered)", expanded=False):
    if mcp_tools:
        cols = st.columns(len(mcp_tools))
        for idx, tool in enumerate(mcp_tools):
            with cols[idx]:
                st.markdown(f"**`{tool.name}`**")
                st.caption(tool.description)
    else:
        st.warning("No tools loaded from MCP server.")

# Layout Tabs
tab_chat, tab_preview = st.tabs(["💬 Chat Workspace", "👁️ Email Live Preview"])

with tab_chat:
    # Display Chat History
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "tool_calls" in msg and msg["tool_calls"]:
                    with st.expander("🛠️ Intermediate Tool Calls", expanded=False):
                        for tc in msg["tool_calls"]:
                            st.json(tc)

with tab_preview:
    st.subheader("🖼️ Rendered Email Live Preview")
    
    if st.session_state.preview_url:
        st.success(f"🌐 Live Preview URL: [{st.session_state.preview_url}]({st.session_state.preview_url})")
        st.markdown(f'<iframe src="{st.session_state.preview_url}" width="100%" height="600" style="border:1px solid #30363d; border-radius:8px;"></iframe>', unsafe_allow_html=True)
    elif st.session_state.rendered_html:
        st.info("Rendered HTML Document:")
        components.html(st.session_state.rendered_html, height=600, scrolling=True)
    else:
        st.info("No email has been rendered yet in this session. Ask the assistant to render an email!")

# Chat Input at Root Level (Always pinned at the bottom of the page)
if prompt := st.chat_input("Ask me to draft, lint, or render an email in emailmd markdown..."):
    if not mistral_key:
        st.error("Please enter your MISTRAL_API_KEY in the sidebar settings!")
        st.stop()

    # Save User Query
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Render User Message immediately inside chat container
    with tab_chat:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            status_container = st.container()

            try:
                agent = build_agent(
                    tools=mcp_tools,
                    mistral_api_key=mistral_key,
                    model_name=model_choice
                )
                
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                final_text = ""
                tool_calls_executed = []

                with st.spinner("Thinking & invoking MCP tools..."):
                    for event in agent.stream(
                        {"messages": [("user", prompt)]},
                        config=config,
                        stream_mode="values"
                    ):
                        latest_msg = event["messages"][-1]
                        
                        # Capture tool calls
                        if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                            for tc in latest_msg.tool_calls:
                                tool_calls_executed.append({
                                    "tool": tc.get("name"),
                                    "args": tc.get("args")
                                })
                                status_container.info(f"🛠️ Executing MCP Tool: `{tc.get('name')}`")
                        
                        if latest_msg.type == "tool":
                            content_str = str(latest_msg.content)
                            status_container.success(f"✅ Executed `{latest_msg.name}`")
                            
                            # Extract previewUrl / HTML
                            if "previewUrl" in content_str:
                                try:
                                    data = json.loads(content_str)
                                    if "previewUrl" in data:
                                        st.session_state.preview_url = data["previewUrl"]
                                    if "html" in data:
                                        st.session_state.rendered_html = data["html"]
                                except Exception:
                                    urls = re.findall(r'https://[^\s"]+preview[^\s"]*', content_str)
                                    if urls:
                                        st.session_state.preview_url = urls[0]

                        if latest_msg.type == "ai" and latest_msg.content:
                            final_text = str(latest_msg.content)
                            response_placeholder.markdown(final_text)

                if not final_text and tool_calls_executed:
                    final_text = "Completed MCP tool operations successfully."
                    response_placeholder.markdown(final_text)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_text,
                    "tool_calls": tool_calls_executed
                })

            except Exception as e:
                st.error(f"Error during agent execution: {e}")

    # Rerun to cleanly render state and update preview tab
    st.rerun()
