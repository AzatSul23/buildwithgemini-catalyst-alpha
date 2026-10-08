"""Firestore service for CatalystAlpha investment plays and event-driven theses."""

from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcode GCP project ID as a string to prevent project-number resolution issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-bd6b92beaf3e"
COLLECTION_NAME = "investment_plays"


def get_firestore_client() -> firestore.Client:
    """Return a Firestore client pinned to the explicit project ID string."""
    return firestore.Client(project=PROJECT_ID)


def list_investment_plays(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve existing event-driven investment plays and theses from Firestore.

    Args:
        limit: Maximum number of plays to return (default: 10).

    Returns:
        A list of dictionaries representing investment plays.
    """
    db = get_firestore_client()
    docs = db.collection(COLLECTION_NAME).limit(limit).stream()
    plays = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        plays.append(data)
    return plays


def get_investment_play_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Look up an investment play for a specific stock ticker.

    Args:
        ticker: The stock ticker symbol (e.g. NVDA, TSLA, LLY, XOM).

    Returns:
        The play details dictionary if found, or None.
    """
    db = get_firestore_client()
    query = db.collection(COLLECTION_NAME).where("ticker", "==", ticker.upper()).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def search_plays_by_catalyst(query: str) -> List[Dict[str, Any]]:
    """Search for investment plays matching an event or keyword in their catalyst or tags.

    Args:
        query: Search keyword or event theme (e.g., 'AI', 'Robotaxi', 'energy', 'GLP-1').

    Returns:
        A list of matching investment play dictionaries.
    """
    db = get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    q_lower = query.lower()
    matches = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        catalyst = data.get("catalyst_event", "").lower()
        summary = data.get("thesis_summary", "").lower()
        tags = [t.lower() for t in data.get("tags", [])]
        if q_lower in catalyst or q_lower in summary or any(q_lower in tag for tag in tags):
            matches.append(data)
    return matches


def save_investment_play(
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
    """Save or update an event-driven stock investment thesis and trade play in Firestore.

    Args:
        ticker: Stock symbol (e.g. 'NVDA', 'AAPL', 'MSFT').
        company_name: Name of the company.
        action: Recommended trade action, e.g. 'BUY' or 'SELL'.
        catalyst_event: The predicted future event that triggers this thesis.
        thesis_summary: The research evidence and rationale supporting the trade thesis.
        target_price: Projected upside/downside price target.
        current_price: Current market price of the stock.
        stop_loss: Suggested stop-loss risk mitigation price.
        conviction_score: Conviction score from 1 (lowest) to 10 (highest).
        risk_level: 'LOW', 'MEDIUM', or 'HIGH'.
        time_horizon: Expected timeframe for the catalyst (e.g. '3-6 months', '1 year').
        tags: Optional category/sector tags (e.g. ['AI', 'Datacenter']).

    Returns:
        A dictionary confirming the saved investment play with its document ID.
    """
    db = get_firestore_client()
    clean_ticker = ticker.strip().upper()
    doc_id = f"play-{clean_ticker.lower()}-{int(target_price)}"
    
    play_data = {
        "id": doc_id,
        "ticker": clean_ticker,
        "company_name": company_name.strip(),
        "action": action.strip().upper(),
        "catalyst_event": catalyst_event.strip(),
        "thesis_summary": thesis_summary.strip(),
        "target_price": float(target_price),
        "current_price": float(current_price),
        "stop_loss": float(stop_loss),
        "conviction_score": int(conviction_score),
        "risk_level": risk_level.strip().upper(),
        "time_horizon": time_horizon.strip(),
        "tags": tags or [],
    }

    db.collection(COLLECTION_NAME).document(doc_id).set(play_data)
    return {
        "status": "success",
        "message": f"Saved investment thesis for {clean_ticker} on event: '{catalyst_event}'",
        "play": play_data,
    }
