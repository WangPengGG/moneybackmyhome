"""Main orchestrator agent using LangGraph."""

import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.config import get_settings
from src.models.agent_state import AgentState
from src.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# System prompt for the orchestrator agent
SYSTEM_PROMPT = """You are an intelligent stock investment assistant called Alpha-Agent.
You help users manage their investment portfolios, analyze stocks, and make informed decisions.

Your capabilities include:
1. **Market Data**: Get real-time stock prices, company information, and historical data
2. **Portfolio Management**: Track user's holdings, add/update/remove positions
3. **Options Analysis**: View options chains, calculate Greeks, find options by delta
4. **Technical Analysis**: Calculate returns, compare stocks, analyze volatility

When answering questions:
- Be concise and actionable
- Use data to support your analysis
- Explain your reasoning clearly
- Highlight risks and opportunities
- Format numbers appropriately (e.g., prices with 2 decimals, percentages with 1 decimal)

For portfolio queries, always fetch the latest data before responding.

If a user asks about something you can't help with, politely explain your limitations and suggest what you can do instead.
"""


def create_orchestrator_agent():
    """Create and return the orchestrator agent graph."""
    settings = get_settings()

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.google_api_key,
        temperature=0.7,
        max_tokens=4096,
    )

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # Create tool node
    tool_node = ToolNode(ALL_TOOLS)

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        """Determine whether to continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message has tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Otherwise, end
        return END

    def call_model(state: AgentState) -> dict:
        """Call the LLM with the current state."""
        messages = state["messages"]

        # Ensure system message is first
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response = llm_with_tools.invoke(messages)

        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )

    # Tools always go back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph
    graph = workflow.compile()

    return graph


# Create a singleton instance
_agent = None


def get_agent():
    """Get or create the orchestrator agent."""
    global _agent
    if _agent is None:
        _agent = create_orchestrator_agent()
    return _agent


async def chat(message: str, history: list[dict] | None = None) -> str:
    """Send a message to the agent and get a response.

    Args:
        message: The user's message
        history: Optional list of previous messages [{"role": "user|assistant", "content": "..."}]

    Returns:
        The agent's response as a string.
    """
    agent = get_agent()

    # Build message history
    messages = []
    if history:
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Add current message
    messages.append(HumanMessage(content=message))

    # Run the agent
    try:
        result = await agent.ainvoke({"messages": messages})

        # Get the last AI message
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return "I apologize, but I couldn't generate a response. Please try again."

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return f"An error occurred: {str(e)}"


async def chat_stream(message: str, history: list[dict] | None = None):
    """Stream a response from the agent.

    Args:
        message: The user's message
        history: Optional list of previous messages

    Yields:
        Chunks of the response as they are generated.
    """
    agent = get_agent()

    # Build message history
    messages = []
    if history:
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=message))

    try:
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2"
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield content

    except Exception as e:
        logger.error(f"Error in chat_stream: {e}")
        yield f"An error occurred: {str(e)}"
