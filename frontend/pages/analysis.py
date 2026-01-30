"""Analysis page for the Streamlit frontend."""

import httpx
import streamlit as st


def render_analysis_page():
    """Render the stock analysis page."""
    st.header("📈 Stock Analysis")

    # Stock symbol input
    symbol = st.text_input("Enter Stock Symbol", placeholder="AAPL").upper()

    if not symbol:
        st.info("Enter a stock symbol to view analysis")
        return

    # Analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Quote", "ℹ️ Company Info", "📈 Returns", "⚡ Options"]
    )

    with tab1:
        render_quote_tab(symbol)

    with tab2:
        render_info_tab(symbol)

    with tab3:
        render_returns_tab(symbol)

    with tab4:
        render_options_tab(symbol)


def render_quote_tab(symbol: str):
    """Render the stock quote tab."""
    backend_url = st.session_state.backend_url

    with st.spinner("Loading quote..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{backend_url}/api/analysis/quote/{symbol}")
                response.raise_for_status()
                quote = response.json()
        except httpx.ConnectError:
            st.error("Cannot connect to backend")
            return
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return

    if "error" in quote:
        st.error(quote["error"])
        return

    # Display quote data
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Price",
            f"${float(quote.get('price', 0)):,.2f}",
        )

    with col2:
        change = float(quote.get("change", 0))
        change_pct = float(quote.get("change_percent", 0))
        st.metric(
            "Change",
            f"${change:+,.2f}",
            delta=f"{change_pct:+.2f}%",
        )

    with col3:
        st.metric(
            "Volume",
            f"{quote.get('volume', 0):,}",
        )

    with col4:
        if quote.get("market_cap"):
            market_cap = float(quote.get("market_cap", 0))
            if market_cap >= 1e12:
                cap_str = f"${market_cap / 1e12:.2f}T"
            elif market_cap >= 1e9:
                cap_str = f"${market_cap / 1e9:.2f}B"
            else:
                cap_str = f"${market_cap / 1e6:.2f}M"
            st.metric("Market Cap", cap_str)

    # Additional info
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if quote.get("pe_ratio"):
            st.write(f"**P/E Ratio:** {float(quote.get('pe_ratio')):.2f}")

    with col2:
        if quote.get("fifty_two_week_high"):
            st.write(f"**52W High:** ${float(quote.get('fifty_two_week_high')):,.2f}")

    with col3:
        if quote.get("fifty_two_week_low"):
            st.write(f"**52W Low:** ${float(quote.get('fifty_two_week_low')):,.2f}")


def render_info_tab(symbol: str):
    """Render the company info tab."""
    backend_url = st.session_state.backend_url

    with st.spinner("Loading company info..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{backend_url}/api/analysis/info/{symbol}")
                response.raise_for_status()
                info = response.json()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return

    if "error" in info:
        st.error(info["error"])
        return

    # Company overview
    st.subheader(info.get("name", symbol))

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Sector:** {info.get('sector', 'N/A')}")
        st.write(f"**Industry:** {info.get('industry', 'N/A')}")

    with col2:
        if info.get("beta"):
            st.write(f"**Beta:** {float(info.get('beta')):.2f}")
        if info.get("dividend_yield"):
            st.write(f"**Dividend Yield:** {float(info.get('dividend_yield')) * 100:.2f}%")

    # Fundamentals
    st.markdown("---")
    st.subheader("Fundamentals")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if info.get("pe_ratio"):
            st.metric("P/E Ratio", f"{float(info.get('pe_ratio')):.2f}")

    with col2:
        if info.get("forward_pe"):
            st.metric("Forward P/E", f"{float(info.get('forward_pe')):.2f}")

    with col3:
        if info.get("peg_ratio"):
            st.metric("PEG Ratio", f"{float(info.get('peg_ratio')):.2f}")

    with col4:
        if info.get("price_to_book"):
            st.metric("P/B Ratio", f"{float(info.get('price_to_book')):.2f}")

    # Description
    if info.get("description"):
        st.markdown("---")
        st.subheader("About")
        st.write(info.get("description"))


def render_returns_tab(symbol: str):
    """Render the returns analysis tab."""
    backend_url = st.session_state.backend_url

    period = st.selectbox(
        "Select Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,  # Default to 1y
    )

    with st.spinner("Calculating returns..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{backend_url}/api/analysis/returns/{symbol}",
                    params={"period": period},
                )
                response.raise_for_status()
                returns = response.json()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return

    if "error" in returns:
        st.error(returns["error"])
        return

    # Display returns metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        total_return = returns.get("total_return_percent", 0)
        color = "green" if total_return >= 0 else "red"
        st.metric(
            "Total Return",
            f"{total_return:+.2f}%",
        )

    with col2:
        st.metric(
            "Volatility (Annualized)",
            f"{returns.get('annualized_volatility_percent', 0):.2f}%",
        )

    with col3:
        st.metric(
            "Max Drawdown",
            f"{returns.get('max_drawdown_percent', 0):.2f}%",
        )

    # Price range
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**Start Price:** ${returns.get('start_price', 0):,.2f}")

    with col2:
        st.write(f"**End Price:** ${returns.get('end_price', 0):,.2f}")

    with col3:
        st.write(f"**Trading Days:** {returns.get('trading_days', 0)}")


def render_options_tab(symbol: str):
    """Render the options analysis tab."""
    backend_url = st.session_state.backend_url

    # Get available expirations
    with st.spinner("Loading options..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{backend_url}/api/analysis/options/{symbol}/expirations"
                )
                response.raise_for_status()
                expirations = response.json()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return

    if "error" in expirations:
        st.error(expirations["error"])
        return

    exp_dates = expirations.get("expiration_dates", [])
    if not exp_dates:
        st.info("No options available for this symbol")
        return

    # Expiration selector
    selected_exp = st.selectbox("Select Expiration", exp_dates)

    # Get options chain
    with st.spinner("Loading options chain..."):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{backend_url}/api/analysis/options/{symbol}",
                    params={"expiration": selected_exp},
                )
                response.raise_for_status()
                chain = response.json()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return

    if "error" in chain:
        st.error(chain["error"])
        return

    # Display calls and puts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Calls")
        calls = chain.get("calls", [])
        if calls:
            for call in calls[:10]:  # Show top 10
                with st.expander(f"Strike: ${float(call.get('strike', 0)):,.2f}"):
                    st.write(f"Last: ${float(call.get('last_price', 0) or 0):,.2f}")
                    st.write(f"Bid: ${float(call.get('bid', 0) or 0):,.2f}")
                    st.write(f"Ask: ${float(call.get('ask', 0) or 0):,.2f}")
                    if call.get("implied_volatility"):
                        st.write(f"IV: {float(call.get('implied_volatility')) * 100:.1f}%")
                    st.write(f"Volume: {call.get('volume', 0) or 0}")
                    st.write(f"OI: {call.get('open_interest', 0) or 0}")
        else:
            st.info("No calls available")

    with col2:
        st.subheader("Puts")
        puts = chain.get("puts", [])
        if puts:
            for put in puts[:10]:  # Show top 10
                with st.expander(f"Strike: ${float(put.get('strike', 0)):,.2f}"):
                    st.write(f"Last: ${float(put.get('last_price', 0) or 0):,.2f}")
                    st.write(f"Bid: ${float(put.get('bid', 0) or 0):,.2f}")
                    st.write(f"Ask: ${float(put.get('ask', 0) or 0):,.2f}")
                    if put.get("implied_volatility"):
                        st.write(f"IV: {float(put.get('implied_volatility')) * 100:.1f}%")
                    st.write(f"Volume: {put.get('volume', 0) or 0}")
                    st.write(f"OI: {put.get('open_interest', 0) or 0}")
        else:
            st.info("No puts available")
