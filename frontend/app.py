"""Main Streamlit application entry point."""

import streamlit as st

st.set_page_config(
    page_title="Alpha-Agent | Trading Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"


def main():
    """Main application."""
    st.title("📈 Alpha-Agent")
    st.caption("Your Intelligent Stock Investment Assistant")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["💬 Chat", "📊 Portfolio", "📈 Analysis", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    if page == "💬 Chat":
        from pages.chat import render_chat_page
        render_chat_page()
    elif page == "📊 Portfolio":
        from pages.portfolio import render_portfolio_page
        render_portfolio_page()
    elif page == "📈 Analysis":
        from pages.analysis import render_analysis_page
        render_analysis_page()
    elif page == "⚙️ Settings":
        from pages.settings import render_settings_page
        render_settings_page()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Alpha-Agent v0.1.0")
    st.sidebar.caption("Powered by Gemini & LangGraph")


if __name__ == "__main__":
    main()
