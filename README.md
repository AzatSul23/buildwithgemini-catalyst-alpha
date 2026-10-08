# CatalystAlpha — Event-Driven Stock Investment Advisor

A conversational investment analysis agent built with Google Agent Development Kit (ADK) and `agents-cli`, deployed on Google Cloud Agent Platform. CatalystAlpha helps investors capitalize on predicted future events by generating data-grounded stock buy/sell proposals, crowd-sourced prediction market probability grounding, multi-source financial research, and rich visual thesis presentations.

---

## ⚡ What CatalystAlpha Does

CatalystAlpha transforms qualitative event predictions (e.g., AI compute capex expansions, semiconductor export shifts, energy demand inflections, Federal Reserve rate decisions) into actionable investment theses:

1. **5 Distinct Stock Proposals per Catalyst**: For any query or market theme, the agent formulates 5 separate proposals (1 per stock ticker), complete with action recommendations (`BUY`, `SELL`), entry and target price targets, stop-loss risk boundaries, conviction ratings (1–10), and risk classifications.
2. **Crowd-Sourced Prediction Market Grounding**: Queries live prediction market odds from Polymarket to validate catalyst consensus probability before recommending trades.
3. **Multi-Source Financial Research**: Pulls live equity market snapshots, official U.S. Treasury interest rates, real-time SEC EDGAR regulatory filings (Form 8-Ks, 10-Qs), and corporate news sentiment.
4. **Agent Engine Sandbox Execution**: Runs quantitative scenario calculations, risk-reward ratios, and position sizing models in an isolated Google Cloud sandbox environment.
5. **Cross-Session Memory & Portfolio Tracking**: Preserves user risk preferences, investment horizons, and tracked stock tickers across conversation sessions via Vertex AI Memory Bank.
6. **Rich Visual Cards & Media**: Emits A2UI schema cards and generates Wall Street-themed cartoon illustrations and short cinematic video summaries stored in Google Cloud Storage.

---

## 🏗️ Architecture & Google Cloud Integrations

CatalystAlpha is wired into the following Google Cloud and ADK services:

| Component | Service | How It Is Used in CatalystAlpha |
|---|---|---|
| **Core Reasoning Agent** | Google ADK + Gemini (`gemini-3.8-flash`) | Orchestrates the tool execution loop, reasoning, and system instructions. |
| **Long-Term Memory** | Vertex AI Memory Bank (`PreloadMemoryTool`) | Remembers user risk tolerance, portfolio preferences, and automatically indexes all proposed stock tickers across sessions. |
| **Structured Storage** | Cloud Firestore (`investment_plays` collection) | Stores and queries structured investment theses, target prices, risk profiles, and historical catalyst records. |
| **Blob Storage** | Google Cloud Storage (Public Bucket) | Stores generated image artifacts and short video files, providing public HTTPS URLs for UI rendering. |
| **Image Generation** | Google GenAI (`gemini-3.1-flash-lite-image`) | Generates humorous, Wall Street-themed thesis cartoon illustrations and saves them as session artifacts and GCS assets. |
| **Video Generation** | Google GenAI Omni (`gemini-omni-flash-preview`) | Generates cinematic short concept videos visualizing catalysts and saves them to session artifacts and GCS. |
| **Code Sandbox** | Agent Engine Sandbox Code Executor | Executes safe Python code in an isolated container for financial risk modeling, volatility, and payoff formulas. |
| **Agent-First UI** | A2UI (Catalog 0.8) | Generates structured UI components (cards, dividers, headers, badges, and images) rendered directly in the chat interface. |
| **Deployment & Protocol** | Agent Platform + A2A Protocol + Cloud Run | Deployed as an A2A agent on Vertex AI Reasoning Engine with a FastAPI proxy frontend on Cloud Run. |

> **Note on Project Brief Status**:
> - **Implemented**: Vertex AI Memory Bank, Cloud Firestore persistence, Cloud Storage public asset hosting, Gemini 3.1 Flash Lite Image generation, Gemini Omni Flash video generation, Agent Engine code sandbox execution, A2UI cards and tables, SEC EDGAR search, Polymarket odds search, Treasury rates lookup, Yahoo Finance quotes, Finnhub news/sentiment, and Cloud Run A2A frontend.
> - **Planned, not yet implemented**: Direct brokerage API order execution, automated real-money portfolio rebalancing, and custom backtesting engine against multi-decade tick data.

---

## 🧰 Agent Tools & Data Sources

The agent has access to 11 specialized tools defined in `app/agent.py`:

- `fetch_prediction_market_odds`: Queries live probability odds from Polymarket for geopolitical, tech, and macroeconomic events.
- `fetch_market_snapshot`: Retrieves real-time stock prices, 52-week ranges, and daily changes.
- `fetch_sec_edgar_filings`: Searches the U.S. SEC EDGAR system for official corporate 8-K material events, 10-K, and 10-Q filings.
- `fetch_company_news_and_sentiment`: Analyzes recent company headlines and news sentiment scores via Finnhub.
- `fetch_treasury_rates`: Retrieves benchmark interest rates directly from the U.S. Department of the Treasury.
- `generate_wallstreet_thesis_meme`: Uses `gemini-3.1-flash-lite-image` to generate Wall Street digital cartoon art illustrating an investment play.
- `generate_catalyst_video`: Uses `gemini-omni-flash-preview` to generate short cinematic videos of catalyst scenarios.
- `record_new_investment_thesis`: Writes formatted investment recommendations directly to Cloud Firestore.
- `lookup_stock_play`: Retrieves stored investment play details for a specific ticker from Firestore.
- `find_plays_for_predicted_event`: Searches existing database theses matching specific catalyst keywords.
- `get_all_investment_plays`: Lists recent investment theses stored in Firestore.

---

## 📁 Repository Structure

```
.
├── agents-cli-manifest.yaml   # Deployment manifest (ADK, us-east1, A2A enabled)
├── project_brief.md           # Original design brief and concept specifications
├── pyproject.toml             # Python dependencies and packaging configuration
├── app/
│   ├── agent.py               # Core ADK agent, tools, callbacks, and system prompt
│   ├── a2ui_utils.py          # A2UI callback and JSON extractor
│   ├── firestore_service.py   # Firestore client and database operations
│   └── fast_api_app.py        # Local FastAPI wrapper
├── frontend/
│   ├── main.py                # FastAPI A2A client proxy connecting browser to agent
│   ├── Dockerfile             # Container image for Cloud Run deployment
│   ├── requirements.txt       # Frontend dependencies (a2a-sdk, fastapi, uvicorn, httpx)
│   └── static/
│       └── index.html         # A2UI chat interface with custom theme and markdown renderer
└── tests/                     # Unit and integration test suite
```

---

## 🚀 Setup & Running Locally

### Prerequisites

- **Python 3.11+**
- **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Google Cloud SDK** (`gcloud`) authenticated to your GCP project
- **agents-cli** installed (`uv tool install google-agents-cli`)

### 1. Authenticate with Google Cloud

Ensure you have authenticated your gcloud CLI and Application Default Credentials (ADC):

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### 2. Install Dependencies

```bash
cd catalyst-alpha
uv sync
```

### 3. Seed Initial Firestore Data (Optional)

To populate Firestore with initial catalyst plays:

```bash
uv run python seed_firestore.py
```

### 4. Run Locally with ADK Playground

Test the agent in the local interactive development environment:

```bash
agents-cli playground
```

### 5. Run the Frontend Locally

In a separate terminal, launch the FastAPI A2A chat proxy:

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```

The web interface will be available locally on port `8080`.

---

## ☁️ Deployment

### Deploy Agent to Vertex AI Agent Platform

Deploy the agent logic and sandbox configuration using `agents-cli`:

```bash
agents-cli deploy
```

### Deploy Frontend to Cloud Run

Deploy the web proxy container to Google Cloud Run:

```bash
cd frontend
gcloud run deploy catalyst-alpha-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_ENGINE_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```

---

## 📄 License

Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
