"""Settings page for the Streamlit frontend."""

import streamlit as st


def render_settings_page():
    """Render the settings page."""
    st.header("⚙️ Settings")

    # Backend configuration
    st.subheader("Backend Configuration")

    backend_url = st.text_input(
        "Backend URL",
        value=st.session_state.backend_url,
        help="URL of the FastAPI backend server",
    )

    if backend_url != st.session_state.backend_url:
        st.session_state.backend_url = backend_url
        st.success("Backend URL updated")

    # Test connection
    if st.button("Test Connection"):
        import httpx

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{backend_url}/health")
                if response.status_code == 200:
                    st.success("✅ Connection successful!")
                else:
                    st.error(f"❌ Connection failed: Status {response.status_code}")
        except httpx.ConnectError:
            st.error("❌ Cannot connect to backend. Is the server running?")
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")

    st.markdown("---")

    # Display settings
    st.subheader("Display Settings")

    # Theme (placeholder - Streamlit handles this)
    st.write("Theme settings are managed in Streamlit's main menu (☰ → Settings)")

    st.markdown("---")

    # About
    st.subheader("About")
    st.write("**Alpha-Agent** - Intelligent Stock Investment Assistant")
    st.write("Version: 0.1.0")
    st.write("")
    st.write("**Powered by:**")
    st.write("- LangGraph for agent orchestration")
    st.write("- Gemini for language understanding")
    st.write("- yfinance for market data")
    st.write("- FastAPI for the backend")
    st.write("- Streamlit for the frontend")

    st.markdown("---")

    # Instructions
    st.subheader("Quick Start")
    st.markdown("""
    1. **Start the backend**: `uvicorn src.main:app --reload`
    2. **Start the frontend**: `streamlit run frontend/app.py`
    3. **Chat with the agent** to get stock information
    4. **Add positions** to track your portfolio
    5. **Analyze stocks** using the Analysis tab
    """)

    st.subheader("Example Queries")
    st.markdown("""
    Try asking the agent:
    - "What is the current price of AAPL?"
    - "Show me my portfolio"
    - "Compare AAPL, GOOGL, and MSFT"
    - "What are the options for TSLA?"
    - "Add 100 shares of NVDA at $500"
    """)
