# Alpha-Agent: Trading Assistant

An intelligent stock investment assistant powered by LangGraph, Gemini, and yfinance.

## Features

- **Chat Interface**: Natural language interaction for stock queries and portfolio management
- **Portfolio Management**: Track holdings, P&L, and market values
- **Market Data**: Real-time stock prices, company info, and historical data
- **Options Analysis**: Options chains with Greeks calculation
- **Technical Analysis**: Returns, volatility, and stock comparison

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your_api_key_here
```

### 3. Start the Backend

```bash
uvicorn src.main:app --reload
```

The API will be available at http://localhost:8000

### 4. Start the Frontend

```bash
streamlit run frontend/app.py
```

The UI will be available at http://localhost:8501

### 5. (Optional) Seed Sample Data

```bash
python scripts/seed_data.py
```

## Project Structure

```
trading_assistant/
├── src/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── api/routes/          # API endpoints
│   ├── agents/              # LangGraph agents
│   ├── tools/               # LangChain tools
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── db/                  # Database layer
├── frontend/
│   ├── app.py               # Streamlit entry point
│   └── pages/               # UI pages
├── tests/                   # Test files
└── scripts/                 # Utility scripts
```

## API Endpoints

### Chat
- `POST /api/chat/` - Send a message to the agent
- `POST /api/chat/stream` - Stream a response from the agent

### Portfolio
- `GET /api/portfolio/` - Get portfolio summary with market data
- `GET /api/portfolio/positions` - Get all positions
- `GET /api/portfolio/positions/{symbol}` - Get specific position
- `POST /api/portfolio/positions` - Add new position
- `PUT /api/portfolio/positions/{symbol}` - Update position
- `DELETE /api/portfolio/positions/{symbol}` - Remove position

### Analysis
- `GET /api/analysis/quote/{symbol}` - Get current quote
- `GET /api/analysis/info/{symbol}` - Get company info
- `GET /api/analysis/history/{symbol}` - Get historical prices
- `GET /api/analysis/returns/{symbol}` - Calculate returns
- `POST /api/analysis/compare` - Compare multiple stocks
- `GET /api/analysis/options/{symbol}` - Get options chain
- `GET /api/analysis/options/{symbol}/expirations` - Get option expirations
- `GET /api/analysis/options/{symbol}/greeks` - Calculate Greeks

## Example Chat Queries

- "What is the current price of AAPL?"
- "Show me my portfolio"
- "Compare AAPL, GOOGL, and MSFT over the past year"
- "What are the options available for TSLA?"
- "Add 100 shares of NVDA at $500 to my portfolio"
- "Calculate the Greeks for AAPL $200 call expiring next month"

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Agent Framework**: LangGraph, LangChain
- **LLM**: Google Gemini
- **Market Data**: yfinance
- **Frontend**: Streamlit
- **Options Math**: Black-Scholes (local calculation)

## Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
ruff check src/
ruff format src/
```

## License

MIT
