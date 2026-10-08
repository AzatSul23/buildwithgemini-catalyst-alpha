# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any, Dict, List, Optional
import re
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.base_memory_service import MemoryEntry
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.firestore_service import (
    list_investment_plays,
    get_investment_play_by_ticker,
    search_plays_by_catalyst,
    save_investment_play,
)

MODEL = "gemini-3.8-flash"
GCS_BUCKET_NAME = "catalyst-alpha-assets-1791489652"
PROJECT_ID = "qwiklabs-gcp-03-bd6b92beaf3e"
SANDBOX_RESOURCE_NAME = "projects/695179631001/locations/us-central1/reasoningEngines/3442808675956162560/sandboxEnvironments/5101956603985264640"
MEMORY_BANK_ID = "3442808675956162560"


async def generate_memories_callback(callback_context: CallbackContext):
    """Save salient user facts, preferred tickers, and trading risk tolerances to Vertex AI Memory Bank,
    specifically ensuring all proposed stock tickers are remembered across sessions."""
    # 1. Trigger managed Memory Bank extraction from the entire session
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Warning: add_session_to_memory failed: {e}")

    # 2. Explicitly extract and store proposed stock tickers into Memory Bank
    try:
        events = callback_context.session.events or []
        proposed_tickers = set()

        for event in events:
            # Check model responses or tool actions
            if event.author != "user" and event.content and event.content.parts:
                for part in event.content.parts:
                    text = getattr(part, "text", "") or ""
                    # Match ticker patterns like $AAPL, (AAPL), [Ticker: AAPL], or ticker: AAPL
                    matches = re.findall(r'(?:\$|\b(?:ticker|stock|symbol)[\s:]+)([A-Z]{1,5})\b', text, re.IGNORECASE)
                    for m in matches:
                        proposed_tickers.add(m.upper())
            # Check tool call inputs (e.g. fetch_market_snapshot, lookup_stock_play, record_new_investment_thesis)
            if hasattr(event, "actions") and event.actions:
                for act in event.actions:
                    if hasattr(act, "tool_call") and act.tool_call:
                        args = getattr(act.tool_call, "args", {}) or {}
                        if "ticker" in args:
                            proposed_tickers.add(str(args["ticker"]).upper().strip("$"))

        if proposed_tickers:
            memories_to_add = [
                MemoryEntry(
                    content=types.Content(
                        parts=[
                            types.Part(
                                text=f"Proposed stock ticker for user investment consideration: {ticker}"
                            )
                        ]
                    ),
                    custom_metadata={"ticker": ticker, "type": "proposed_stock_ticker"},
                )
                for ticker in sorted(proposed_tickers)
            ]
            await callback_context.add_memory(memories=memories_to_add)
    except Exception as e:
        print(f"Warning: explicit ticker memory persistence failed: {e}")

    return None






def get_all_investment_plays(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve existing event-driven stock recommendations and investment theses from Firestore.

    Args:
        limit: Max number of plays to return (default 10).

    Returns:
        List of investment play records including ticker, action, catalyst event, targets, and thesis summary.
    """
    return list_investment_plays(limit=limit)


def lookup_stock_play(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch an investment thesis and trade play for a given stock ticker from Firestore.

    Args:
        ticker: The stock ticker symbol (e.g., 'NVDA', 'TSLA', 'LLY', 'XOM').

    Returns:
        The play details if registered in Firestore, otherwise None.
    """
    return get_investment_play_by_ticker(ticker=ticker)


def find_plays_for_predicted_event(event_query: str) -> List[Dict[str, Any]]:
    """Search for existing investment theses matching a predicted future event or keyword.

    Args:
        event_query: Predicted event or market theme (e.g., 'AI datacenter capex', 'Robotaxi', 'GLP-1', 'clean energy').

    Returns:
        A list of matching stock investment theses from the database.
    """
    return search_plays_by_catalyst(query=event_query)


def record_new_investment_thesis(
    ticker: str,
    company_name: str,
    action: str,
    catalyst_event: str,
    thesis_summary: str,
    target_price: float,
    current_price: float,
    stop_loss: float,
    conviction_score: int,
    risk_level: str,
    time_horizon: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Store a newly formulated event-driven investment thesis and stock recommendation into Firestore.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'MSFT', 'AMD').
        company_name: Full company name.
        action: Recommended action ('BUY' or 'SELL').
        catalyst_event: The predicted future event driving this thesis.
        thesis_summary: Research rationale and evidence supporting the thesis.
        target_price: Projected target price.
        current_price: Current market price estimate.
        stop_loss: Stop-loss risk management price level.
        conviction_score: Conviction score from 1 to 10.
        risk_level: Risk classification ('LOW', 'MEDIUM', 'HIGH').
        time_horizon: Timeframe for the catalyst (e.g. '3-6 months', '1 year').
        tags: Optional list of industry or theme tags.

    Returns:
        Confirmation dictionary with the document ID and saved record.
    """
    return save_investment_play(
        ticker=ticker,
        company_name=company_name,
        action=action,
        catalyst_event=catalyst_event,
        thesis_summary=thesis_summary,
        target_price=target_price,
        current_price=current_price,
        stop_loss=stop_loss,
        conviction_score=conviction_score,
        risk_level=risk_level,
        time_horizon=time_horizon,
        tags=tags,
    )


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    """Fetch live market quote data including current price, currency, regular market high/low, and 52-week range.

    Args:
        ticker: The stock ticker symbol (e.g., 'NVDA', 'TSLA', 'AAPL', 'MSFT').

    Returns:
        A dictionary with live market price metrics or an error message if unavailable.
    """
    import json
    import urllib.request

    clean_ticker = ticker.strip().upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_ticker}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            result = data.get("chart", {}).get("result", [])
            if not result:
                return {"error": f"No market quote found for ticker '{clean_ticker}'."}

            meta = result[0].get("meta", {})
            current_price = meta.get("regularMarketPrice")
            prev_close = meta.get("chartPreviousClose")
            change = round(current_price - prev_close, 2) if (current_price and prev_close) else None
            change_percent = round((change / prev_close) * 100, 2) if (change and prev_close) else None

            return {
                "ticker": clean_ticker,
                "current_price": current_price,
                "previous_close": prev_close,
                "change": change,
                "change_percent": change_percent,
                "day_high": meta.get("regularMarketDayHigh"),
                "day_low": meta.get("regularMarketDayLow"),
                "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
                "currency": meta.get("currency", "USD"),
            }
    except Exception as exc:
        return {"error": f"Failed to fetch market quote for {clean_ticker}: {str(exc)}"}


def fetch_treasury_rates() -> Dict[str, Any]:
    """Fetch official latest U.S. Department of the Treasury average interest rates from fiscaldata.treasury.gov.

    Returns:
        A dictionary containing the latest benchmark rates (Treasury Bills, Notes, Bonds) and record date.
        Useful for assessing macroeconomic discount rates, Fed rate cut expectations, and cost of capital.
    """
    import json
    import os
    import urllib.request

    # Public API endpoint (no auth required; reads optional FISCAL_DATA_API_KEY if configured)
    api_key = os.environ.get("FISCAL_DATA_API_KEY", "").strip()
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?sort=-record_date&page[size]=6"
    if api_key:
        url += f"&api_key={api_key}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode())
            data = payload.get("data", [])
            rates = []
            for item in data:
                rates.append({
                    "security_type": item.get("security_type_desc"),
                    "security": item.get("security_desc"),
                    "avg_interest_rate": f"{item.get('avg_interest_rate_amt')}%",
                    "record_date": item.get("record_date"),
                })
            return {
                "source": "U.S. Department of the Treasury (Fiscal Data)",
                "rates": rates,
            }
    except Exception as exc:
        return {"error": f"Failed to fetch Treasury rates: {str(exc)}"}


def fetch_company_news_and_sentiment(ticker: str, limit: int = 5) -> Dict[str, Any]:
    """Fetch company-specific news headlines and automated sentiment scores from Finnhub API.

    Reads FINNHUB_API_KEY from environment variables. If an API key is not yet set,
    it returns clear setup instructions alongside fallback mock sentiment guidance.

    Args:
        ticker: The stock ticker symbol (e.g. 'NVDA', 'TSLA', 'AAPL', 'MSFT').
        limit: Number of recent news articles to return (default: 5).

    Returns:
        A dictionary containing recent news headlines, sources, URLs, and sentiment summary.
    """
    import datetime
    import json
    import os
    import urllib.request

    clean_ticker = ticker.strip().upper()
    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()

    if not api_key:
        return {
            "status": "missing_api_key",
            "message": (
                f"FINNHUB_API_KEY is not set in environment or .env. "
                f"To enable live Finnhub news, sign up for a free key at https://finnhub.io/register "
                f"and set FINNHUB_API_KEY in catalyst-alpha/.env"
            ),
            "ticker": clean_ticker,
            "sample_sentiment": "Neutral/Positive (mock fallback until FINNHUB_API_KEY is supplied)",
        }

    # Fetch last 7 days of news
    today = datetime.date.today()
    from_date = (today - datetime.timedelta(days=7)).isoformat()
    to_date = today.isoformat()

    news_url = (
        f"https://finnhub.io/api/v1/company-news?"
        f"symbol={clean_ticker}&from={from_date}&to={to_date}&token={api_key}"
    )

    sentiment_url = (
        f"https://finnhub.io/api/v1/news-sentiment?"
        f"symbol={clean_ticker}&token={api_key}"
    )

    result: Dict[str, Any] = {"ticker": clean_ticker, "articles": [], "sentiment": {}}

    try:
        req = urllib.request.Request(news_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            articles = json.loads(response.read().decode())
            if isinstance(articles, list):
                for art in articles[:limit]:
                    result["articles"].append({
                        "headline": art.get("headline"),
                        "source": art.get("source"),
                        "summary": art.get("summary", "")[:250],
                        "url": art.get("url"),
                        "datetime": art.get("datetime"),
                    })
    except Exception as exc:
        result["news_error"] = str(exc)

    try:
        req_sent = urllib.request.Request(sentiment_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_sent, timeout=5) as response:
            sent_data = json.loads(response.read().decode())
            if isinstance(sent_data, dict):
                result["sentiment"] = {
                    "articles_in_last_week": sent_data.get("articlesInLastWeek"),
                    "bullish_percent": sent_data.get("sentiment", {}).get("bullishPercent"),
                    "bearish_percent": sent_data.get("sentiment", {}).get("bearishPercent"),
                    "score": sent_data.get("companyNewsScore"),
                }
    except Exception as exc:
        result["sentiment_error"] = str(exc)

    return result


def fetch_sec_edgar_filings(ticker: str, limit: int = 5) -> Dict[str, Any]:
    """Fetch official recent SEC EDGAR regulatory filings (Form 8-K material events, 10-Q, 10-K, Form 4) for a stock.

    Directly queries the U.S. Securities and Exchange Commission (SEC) EDGAR public API.
    Zero API keys or accounts required.

    Args:
        ticker: The stock ticker symbol (e.g. 'NVDA', 'TSLA', 'AAPL', 'MSFT').
        limit: Maximum number of recent filings to return (default: 5).

    Returns:
        A dictionary containing company name, CIK, and list of recent filings with Form type, date, and description.
    """
    import json
    import urllib.request

    clean_ticker = ticker.strip().upper()
    headers = {"User-Agent": "CatalystAlpha research@catalystalpha.com"}

    try:
        # Step 1: Resolve ticker to SEC CIK
        cik_lookup_url = "https://www.sec.gov/files/company_tickers.json"
        req = urllib.request.Request(cik_lookup_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            tickers_data = json.loads(response.read().decode())

        cik_str = None
        company_title = None
        for item in tickers_data.values():
            if item.get("ticker", "").upper() == clean_ticker:
                cik_str = str(item["cik_str"]).zfill(10)
                company_title = item.get("title")
                break

        if not cik_str:
            return {"error": f"SEC CIK not found for ticker '{clean_ticker}'."}

        # Step 2: Query company submissions
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
        req_sub = urllib.request.Request(submissions_url, headers=headers)
        with urllib.request.urlopen(req_sub, timeout=5) as response:
            sub_data = json.loads(response.read().decode())

        recent = sub_data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        descriptions = recent.get("primaryDocDescription", [])
        accession_numbers = recent.get("accessionNumber", [])

        filings = []
        for i in range(min(limit, len(forms))):
            acc_num = accession_numbers[i].replace("-", "") if i < len(accession_numbers) else ""
            doc_desc = descriptions[i] if i < len(descriptions) else ""
            form_type = forms[i]
            filing_date = filing_dates[i]
            filings.append({
                "form": form_type,
                "filing_date": filing_date,
                "description": doc_desc,
                "sec_url": f"https://www.sec.gov/edgar/browse/?CIK={cik_str}",
            })

        return {
            "source": "U.S. Securities and Exchange Commission (SEC EDGAR)",
            "ticker": clean_ticker,
            "company_name": company_title or sub_data.get("name"),
            "cik": cik_str,
            "filings": filings,
        }
    except Exception as exc:
        return {"error": f"Failed to retrieve SEC EDGAR filings for {clean_ticker}: {str(exc)}"}


def fetch_prediction_market_odds(query: str = "", limit: int = 4) -> Dict[str, Any]:
    """Fetch live crowd-sourced prediction market probability odds on geopolitical, macro, and financial events.

    Queries the public Polymarket Gamma API.
    Zero authentication or API keys required. Reads optional POLYMARKET_API_KEY from environment if set.

    Args:
        query: Optional topic keyword to filter prediction markets (e.g., 'Fed', 'IPO', 'recession', 'rate', 'tariff').
        limit: Number of prediction events to return (default: 4).

    Returns:
        A list of active prediction markets with questions, outcome options, and implied probabilities (percentages).
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    api_key = os.environ.get("POLYMARKET_API_KEY", "").strip()
    headers = {"User-Agent": "CatalystAlpha/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    base_url = "https://gamma-api.polymarket.com/events?limit=40&active=true&closed=false"
    req = urllib.request.Request(base_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            events_data = json.loads(response.read().decode())

        filter_q = query.strip().lower()
        results = []
        for event in events_data:
            title = event.get("title", "")
            description = event.get("description", "")
            # Filter by query if supplied
            if filter_q and (filter_q not in title.lower() and filter_q not in description.lower()):
                continue

            event_markets = []
            for m in event.get("markets", []):
                question = m.get("question")
                outcomes = m.get("outcomes")
                prices = m.get("outcomePrices")

                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except Exception:
                        pass
                if isinstance(prices, str):
                    try:
                        prices = json.loads(prices)
                    except Exception:
                        pass

                odds_summary = []
                if isinstance(outcomes, list) and isinstance(prices, list):
                    for out, pr in zip(outcomes, prices):
                        try:
                            prob_pct = round(float(pr) * 100, 1)
                            odds_summary.append(f"{out}: {prob_pct}%")
                        except Exception:
                            odds_summary.append(f"{out}: {pr}")

                event_markets.append({
                    "question": question,
                    "implied_probability": ", ".join(odds_summary),
                })

            results.append({
                "event_title": title,
                "markets": event_markets[:3],
            })

            if len(results) >= limit:
                break

        return {
            "source": "Polymarket Prediction Markets",
            "filter_query": query,
            "events": results,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch prediction market odds: {str(exc)}"}


async def generate_wallstreet_thesis_meme(
    ticker: str,
    catalyst_event: str,
    action: str,
    humorous_concept: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a humorous, Wall Street-themed cartoon illustration supporting an investment thesis.

    Uses the gemini-3.1-flash-lite-image model in the global region.
    1. Saves the generated image as a session artifact via tool_context.save_artifact so it shows up in the Playground's Artifacts panel.
    2. Uploads the image bytes to Google Cloud Storage (gs://catalyst-alpha-assets-1791489652) and returns the public https URL.

    Args:
        ticker: The stock ticker symbol (e.g. 'NVDA', 'TSLA', 'COIN', 'LLY').
        catalyst_event: The event or catalyst driving the play.
        action: Recommended action ('BUY' or 'SELL').
        humorous_concept: A funny, entertaining visual prompt concept depicting the thesis on Wall Street.
        tool_context: ADK ToolContext injected automatically by the runtime.

    Returns:
        A dictionary with the public image URL, artifact filename, and humorous caption.
    """
    import time
    from google import genai
    from google.cloud import storage

    clean_ticker = ticker.strip().upper()
    timestamp = int(time.time())
    filename = f"meme_{clean_ticker.lower()}_{timestamp}.jpg"

    # Formulate a funny, Wall Street-themed digital art prompt
    prompt = (
        f"A funny, entertaining Wall Street themed editorial cartoon or digital art illustration. "
        f"Subject: {clean_ticker} stock ({action} recommendation) driven by catalyst: '{catalyst_event}'. "
        f"Visual joke: {humorous_concept}. "
        f"Style: Vibrant comic digital illustration, Wall Street trading floor or boardroom atmosphere, "
        f"with funny facial expressions, humorous stock ticker boards, money raining or flying rockets, "
        f"satirical and lighthearted, high quality."
    )

    try:
        # Call gemini-3.1-flash-lite-image in global region
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1"),
            ),
        )

        image_bytes = None
        for part in response.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return {"error": "Image generation model did not return image data."}

        # (1) Save to ADK Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        try:
            res = tool_context.save_artifact(
                filename=filename,
                artifact=part_artifact,
                custom_metadata={"ticker": clean_ticker, "action": action, "type": "thesis_meme"},
            )
            if inspect.iscoroutine(res):
                await res
        except Exception as artifact_err:
            pass  # Continue to upload even if local artifact storage encounters issues

        # (2) Upload image bytes to GCS bucket and return public URL
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "ticker": clean_ticker,
            "action": action,
            "image_url": public_url,
            "artifact_filename": filename,
            "caption": f"Wall Street Thesis Meme for {clean_ticker} ({action}): {humorous_concept}",
        }

    except Exception as exc:
        return {"error": f"Failed to generate thesis image: {str(exc)}"}


async def generate_catalyst_video(
    ticker: str,
    concept_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a short video for a stock catalyst or investment theme using Google's Omni model (gemini-omni-flash-preview).

    Args:
        ticker: The stock ticker symbol (e.g. 'NVDA', 'TSLA', 'AAPL', 'MSFT').
        concept_description: Narrative description of the catalyst scene to visualize (e.g. 'A high-speed automated robotic factory assembling electric vehicles').
        tool_context: ToolContext used to save the artifact into the Playground Artifacts panel.

    Returns:
        A dictionary with the public https Cloud Storage URL of the generated video and artifact details.
    """
    import base64
    import inspect
    import time
    from google import genai
    from google.genai import types
    from google.cloud import storage

    clean_ticker = ticker.strip().upper()
    timestamp = int(time.time())
    filename = f"video_{clean_ticker.lower()}_{timestamp}.mp4"

    video_prompt = (
        f"Cinematic short video depicting stock catalyst for {clean_ticker}: "
        f"{concept_description}. High quality, photorealistic, 720p."
    )

    try:
        # Call gemini-omni-flash-preview in global region using Interactions API
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=video_prompt,
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            out_vid = interaction.output_video
            if hasattr(out_vid, "data") and out_vid.data:
                if isinstance(out_vid.data, bytes):
                    video_bytes = out_vid.data
                else:
                    video_bytes = base64.b64decode(out_vid.data)
            elif isinstance(out_vid, (bytes, bytearray)):
                video_bytes = bytes(out_vid)

        if not video_bytes:
            return {"error": "gemini-omni-flash-preview did not return video bytes."}

        # (1) Save with tool_context.save_artifact so it shows up in Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        try:
            res = tool_context.save_artifact(
                filename=filename,
                artifact=part_artifact,
                custom_metadata={"ticker": clean_ticker, "type": "catalyst_video"},
            )
            if inspect.iscoroutine(res):
                await res
        except Exception:
            pass  # Continue to upload even if local artifact storage encounters issues

        # (2) Upload the same video bytes to the public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "ticker": clean_ticker,
            "video_url": public_url,
            "artifact_filename": filename,
            "description": f"Catalyst video for {clean_ticker}: {concept_description}",
        }

    except Exception as exc:
        return {"error": f"Failed to generate catalyst video: {str(exc)}"}


_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

_role_description = """You are CatalystAlpha, an event-driven stock investment advisor.
Your mission is to help investors capitalize on predicted future events by providing data-backed stock buy/sell advice supported by research evidence.
Whenever an investment thesis, catalyst, sector theme, or trade opportunity is requested, you generate exactly 5 distinct stock proposals — 1 proposal per unique stock ticker.
For each proposal, you incorporate live Polymarket prediction market odds for the relevant catalyst event to ground the thesis in real-world consensus probability.
You remember the user's stated investment preferences, risk tolerance, favorite sectors, and trading style from previous conversations.
Importantly, you remember all previously proposed stock tickers across conversations so you can provide updates, track performance, and maintain a running portfolio watchlist. Whenever proposing a stock, clearly cite its ticker symbol."""

_workflow_description = """When a user predicts a future event (e.g., regulatory approvals, tech breakthroughs, commodity shocks, interest rate or macroeconomic shifts, earnings inflection, or asks for plays/catalysts):
1. Query relevant Polymarket prediction market odds via `fetch_prediction_market_odds` using topic keywords (e.g. 'Fed', 'rate', 'tariff', 'crypto', 'AI', 'semiconductor', 'election', or specific event terms) to determine live crowd probabilities.
2. Select 5 distinct stock tickers that have direct upside or downside exposure to the event/catalyst.
3. For each of the 5 tickers:
   a. Check live market quotes and price ranges using `fetch_market_snapshot`.
   b. Check official regulatory filings (8-Ks, 10-Qs) using `fetch_sec_edgar_filings` or corporate news and sentiment using `fetch_company_news_and_sentiment`.
   c. Formulate a structured thesis detailing: Ticker, Company Name, Recommended Action (BUY or SELL), Catalyst Event, Relevant Polymarket Odds (e.g. 'Polymarket Implied Probability: 72% Yes'), Price Targets (Entry, Target, Stop-Loss), Conviction Score (1-10), and Risk Level.
   d. Save the thesis using `record_new_investment_thesis`.
4. Consult official benchmark yields via `fetch_treasury_rates` when macroeconomic or rate-sensitive plays are involved.
5. If quantitative modeling, risk ratios (Sharpe, Sortino), portfolio sizing, or options payoffs are needed, write and execute Python code in your Agent Engine sandbox.
6. When proposing or summarizing a high-conviction investment thesis, or whenever asked for visual or entertainment summary, generate a funny Wall Street-themed cartoon illustration using `generate_wallstreet_thesis_meme`.
7. Present all 5 stock proposals clearly to the user, highlighting the ticker symbol and current Polymarket consensus odds for each proposal."""

_ui_description = (
    "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
    "Never nest a Card inside a Card. "
    "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
    "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
    "nothing in adk web). "
    "You may include one Image component, but only when you have a public https "
    "URL for the image (for example the image_url that generate_wallstreet_thesis_meme returns "
    "after uploading to the public GCS bucket). Set the Image url to that exact https link, for example "
    '{"Image": {"url": {"literalString": "https://storage.googleapis.com/..."}}}. Never point an '
    "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
    "not have a public URL, add a short Text line noting the image instead. "
    "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
    "headings and emphasis. "
    "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
    "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
)

agent_instruction = _schema_manager.generate_system_prompt(
    role_description=_role_description,
    workflow_description=_workflow_description,
    ui_description=_ui_description,
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    instruction=agent_instruction,
    tools=[
        PreloadMemoryTool(),
        fetch_market_snapshot,
        fetch_prediction_market_odds,
        fetch_sec_edgar_filings,
        fetch_company_news_and_sentiment,
        fetch_treasury_rates,
        generate_wallstreet_thesis_meme,
        generate_catalyst_video,
        get_all_investment_plays,
        lookup_stock_play,
        find_plays_for_predicted_event,
        record_new_investment_thesis,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)


