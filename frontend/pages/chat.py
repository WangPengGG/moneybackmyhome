"""Chat page for the Streamlit frontend."""

import httpx
import streamlit as st


def render_chat_page():
    """Render the chat interface."""
    st.header("💬 Chat with Alpha-Agent")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about stocks, your portfolio, or market analysis..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response from backend
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = send_chat_message(prompt)
                    st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

    # Sidebar options
    with st.sidebar:
        st.subheader("Chat Options")

        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.subheader("Quick Actions")

        if st.button("📊 Show Portfolio"):
            st.session_state.messages.append(
                {"role": "user", "content": "Show me my current portfolio"}
            )
            st.rerun()

        if st.button("📈 Market Overview"):
            st.session_state.messages.append(
                {"role": "user", "content": "Give me an overview of the major indices"}
            )
            st.rerun()

        if st.button("⚠️ Risk Analysis"):
            st.session_state.messages.append(
                {"role": "user", "content": "Analyze the risk in my portfolio"}
            )
            st.rerun()


def send_chat_message(message: str) -> str:
    """Send a message to the backend and get a response.

    Args:
        message: User's message

    Returns:
        Agent's response
    """
    backend_url = st.session_state.backend_url

    # Prepare history (last 10 messages for context)
    history = st.session_state.messages[-10:] if st.session_state.messages else []

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{backend_url}/api/chat/",
                json={
                    "message": message,
                    "history": history,
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success", True):
                return data.get("response", "No response received")
            else:
                return f"Error: {data.get('error', 'Unknown error')}"

    except httpx.ConnectError:
        return "❌ Cannot connect to backend. Please ensure the API server is running on http://localhost:8000"
    except httpx.TimeoutException:
        return "⏳ Request timed out. The query might be too complex or the server is overloaded."
    except Exception as e:
        return f"❌ Error: {str(e)}"
