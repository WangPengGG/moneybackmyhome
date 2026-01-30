"""Portfolio page for the Streamlit frontend."""

from decimal import Decimal

import httpx
import streamlit as st


def render_portfolio_page():
    """Render the portfolio management page."""
    st.header("📊 Portfolio Management")

    # Tabs for different views
    tab1, tab2 = st.tabs(["📈 Holdings", "➕ Add Position"])

    with tab1:
        render_holdings_view()

    with tab2:
        render_add_position_form()


def render_holdings_view():
    """Render the current holdings view."""
    backend_url = st.session_state.backend_url

    # Refresh button
    col1, col2 = st.columns([6, 1])
    with col2:
        refresh = st.button("🔄 Refresh")

    if refresh or "portfolio_data" not in st.session_state:
        with st.spinner("Loading portfolio..."):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.get(f"{backend_url}/api/portfolio/")
                    response.raise_for_status()
                    st.session_state.portfolio_data = response.json()
            except httpx.ConnectError:
                st.error("Cannot connect to backend. Please ensure the API server is running.")
                return
            except Exception as e:
                st.error(f"Error loading portfolio: {str(e)}")
                return

    portfolio = st.session_state.get("portfolio_data")
    if not portfolio:
        st.info("No portfolio data available. Add some positions to get started!")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Value",
            f"${float(portfolio.get('total_value', 0)):,.2f}",
        )

    with col2:
        st.metric(
            "Total Cost",
            f"${float(portfolio.get('total_cost', 0)):,.2f}",
        )

    with col3:
        pnl = float(portfolio.get("total_pnl", 0))
        st.metric(
            "Total P&L",
            f"${pnl:,.2f}",
            delta=f"{float(portfolio.get('total_pnl_percent', 0)):.1f}%",
        )

    with col4:
        st.metric(
            "Positions",
            portfolio.get("positions_count", 0),
        )

    st.markdown("---")

    # Positions table
    positions = portfolio.get("positions", [])
    if not positions:
        st.info("No positions in portfolio. Add some holdings to get started!")
        return

    st.subheader("Holdings")

    for pos in positions:
        with st.expander(f"**{pos['symbol']}** - {pos.get('quantity', 0)} shares"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write("**Position Details**")
                st.write(f"Quantity: {pos.get('quantity', 0)}")
                st.write(f"Avg Cost: ${float(pos.get('average_cost', 0)):,.2f}")
                if pos.get("target_price"):
                    st.write(f"Target: ${float(pos.get('target_price')):,.2f}")
                if pos.get("stop_loss"):
                    st.write(f"Stop Loss: ${float(pos.get('stop_loss')):,.2f}")

            with col2:
                st.write("**Current Market**")
                if pos.get("current_price"):
                    st.write(f"Price: ${float(pos.get('current_price')):,.2f}")
                    st.write(f"Value: ${float(pos.get('market_value', 0)):,.2f}")

                    day_change = pos.get("day_change_percent")
                    if day_change is not None:
                        color = "green" if float(day_change) >= 0 else "red"
                        st.markdown(
                            f"Day Change: :{color}[{float(day_change):+.2f}%]"
                        )
                else:
                    st.write("Market data unavailable")

            with col3:
                st.write("**P&L**")
                if pos.get("unrealized_pnl") is not None:
                    pnl = float(pos.get("unrealized_pnl", 0))
                    pnl_pct = float(pos.get("unrealized_pnl_percent", 0))
                    color = "green" if pnl >= 0 else "red"
                    st.markdown(f"P&L: :{color}[${pnl:,.2f}]")
                    st.markdown(f"Return: :{color}[{pnl_pct:+.2f}%]")

            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 4])

            with col1:
                if st.button("✏️ Edit", key=f"edit_{pos['symbol']}"):
                    st.session_state.editing_symbol = pos["symbol"]
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete", key=f"delete_{pos['symbol']}"):
                    delete_position(pos["symbol"])
                    st.rerun()


def render_add_position_form():
    """Render the add position form."""
    st.subheader("Add New Position")

    with st.form("add_position_form"):
        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input("Symbol", placeholder="AAPL")
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
            average_cost = st.number_input("Average Cost ($)", min_value=0.0, step=0.01)

        with col2:
            asset_type = st.selectbox("Asset Type", ["stock", "etf", "option"])
            target_price = st.number_input("Target Price ($)", min_value=0.0, step=0.01)
            stop_loss = st.number_input("Stop Loss ($)", min_value=0.0, step=0.01)

        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Add Position")

        if submitted:
            if not symbol:
                st.error("Symbol is required")
            elif quantity <= 0:
                st.error("Quantity must be greater than 0")
            elif average_cost <= 0:
                st.error("Average cost must be greater than 0")
            else:
                add_position(
                    symbol=symbol.upper(),
                    quantity=quantity,
                    average_cost=average_cost,
                    asset_type=asset_type,
                    target_price=target_price if target_price > 0 else None,
                    stop_loss=stop_loss if stop_loss > 0 else None,
                    notes=notes if notes else None,
                )


def add_position(
    symbol: str,
    quantity: float,
    average_cost: float,
    asset_type: str,
    target_price: float | None,
    stop_loss: float | None,
    notes: str | None,
):
    """Add a new position via the API."""
    backend_url = st.session_state.backend_url

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{backend_url}/api/portfolio/positions",
                json={
                    "symbol": symbol,
                    "quantity": str(quantity),
                    "average_cost": str(average_cost),
                    "asset_type": asset_type,
                    "target_price": str(target_price) if target_price else None,
                    "stop_loss": str(stop_loss) if stop_loss else None,
                    "notes": notes,
                },
            )

            if response.status_code == 201:
                st.success(f"Added position for {symbol}")
                # Clear cached portfolio data
                if "portfolio_data" in st.session_state:
                    del st.session_state.portfolio_data
                st.rerun()
            elif response.status_code == 409:
                st.error(f"Position for {symbol} already exists")
            else:
                st.error(f"Error: {response.text}")

    except Exception as e:
        st.error(f"Error adding position: {str(e)}")


def delete_position(symbol: str):
    """Delete a position via the API."""
    backend_url = st.session_state.backend_url

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{backend_url}/api/portfolio/positions/{symbol}"
            )

            if response.status_code == 204:
                st.success(f"Removed position for {symbol}")
                # Clear cached portfolio data
                if "portfolio_data" in st.session_state:
                    del st.session_state.portfolio_data
            else:
                st.error(f"Error: {response.text}")

    except Exception as e:
        st.error(f"Error deleting position: {str(e)}")
