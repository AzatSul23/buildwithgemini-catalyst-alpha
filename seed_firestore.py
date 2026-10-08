#!/usr/bin/env python3
"""Seed script for CatalystAlpha Firestore investment play collection."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-bd6b92beaf3e"

SEEDED_PLAYS = [
    {
        "id": "play-nvda-ai-dc",
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "action": "BUY",
        "catalyst_event": "Tier-1 hyperscalers accelerate next-gen AI datacenter capex spending",
        "thesis_summary": "Surging orders for Blackwell Ultra architecture and GB200 systems provide multi-quarter revenue visibility.",
        "target_price": 185.0,
        "current_price": 138.2,
        "stop_loss": 120.0,
        "conviction_score": 9,  # 1 to 10 scale
        "risk_level": "MEDIUM",
        "time_horizon": "6-12 months",
        "tags": ["AI", "Semiconductors", "Datacenter", "Hardware"],
    },
    {
        "id": "play-tsla-robotaxi",
        "ticker": "TSLA",
        "company_name": "Tesla, Inc.",
        "action": "BUY",
        "catalyst_event": "Full unsupervised FSD regulatory approval and commercial Robotaxi rollout",
        "thesis_summary": "Transition from automotive margins to high-margin recurring autonomous mobility software networks.",
        "target_price": 310.0,
        "current_price": 242.5,
        "stop_loss": 195.0,
        "conviction_score": 7,
        "risk_level": "HIGH",
        "time_horizon": "12-24 months",
        "tags": ["Autonomous Driving", "EV", "Robotics", "AI"],
    },
    {
        "id": "play-oil-legacy-fossil",
        "ticker": "XOM",
        "company_name": "Exxon Mobil Corporation",
        "action": "SELL",
        "catalyst_event": "Global clean energy transition accelerates with sustained OPEC+ output surplus",
        "thesis_summary": "Downside margin squeeze on legacy refining and crude spreads as alternative capacity outpaces demand growth.",
        "target_price": 95.0,
        "current_price": 118.0,
        "stop_loss": 125.0,
        "conviction_score": 6,
        "risk_level": "LOW",
        "time_horizon": "3-6 months",
        "tags": ["Energy", "Oil & Gas", "Commodities"],
    },
    {
        "id": "play-lly-glp1-pill",
        "ticker": "LLY",
        "company_name": "Eli Lilly and Company",
        "action": "BUY",
        "catalyst_event": "FDA approval of oral small-molecule GLP-1 receptor agonist for obesity/diabetes",
        "thesis_summary": "Oral pill formulations dramatically expand addressable market beyond injectables with superior manufacturing margins.",
        "target_price": 1050.0,
        "current_price": 880.0,
        "stop_loss": 790.0,
        "conviction_score": 8,
        "risk_level": "LOW",
        "time_horizon": "6-18 months",
        "tags": ["Biotech", "Pharma", "GLP-1", "Healthcare"],
    },
]

def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("investment_plays")
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    
    for play in SEEDED_PLAYS:
        doc_id = play["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(play)
        print(f"Seeded play: {doc_id} -> {play['action']} {play['ticker']} ({play['catalyst_event'][:40]}...)")

    print("\nSuccessfully seeded Firestore 'investment_plays' collection!")

if __name__ == "__main__":
    seed_database()
