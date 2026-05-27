"""
Add Voyage AI embeddings to the existing claims collection in MongoDB Atlas.

Python 3.10-compatible.

Install:
  python3 -m pip install pymongo voyageai python-dotenv

Run:
  python3 embedder.py

What this does:
  - Reads documents from the claims collection.
  - Builds a searchable text summary for each claim.
  - Sends those summaries to Voyage AI.
  - Writes the vector back onto the SAME claim document.
  - Does not create new policies or claims.

Result in Atlas:
  claims.embedding              -> vector array
  claims.embedding_text         -> source text used for embedding
  claims.embedding_model        -> Voyage model name
  claims.embedding_dimensions   -> vector dimension count
  claims.embedding_created_at   -> timestamp

Before running:
  Copy .env.example to .env and fill in MONGODB_URI, MONGODB_DB, and VOYAGE_API_KEY.
"""

import os
from datetime import datetime
from typing import Dict, List

import voyageai
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


# =============================================================================
# CONFIG
# =============================================================================

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "magenta_insurance_demo")
COLLECTION_NAME = "claims"

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-4-large")
OUTPUT_DIMENSION = 1024
BATCH_SIZE = 32

# Set to False if you want to overwrite existing embeddings.
SKIP_ALREADY_EMBEDDED = True


# =============================================================================
# HELPERS
# =============================================================================

def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def claim_to_embedding_text(claim: Dict) -> str:
    """Create a human-readable summary that is useful for semantic search."""
    risk_reasons = claim.get("risk_reasons") or []
    if isinstance(risk_reasons, list):
        risk_reasons_text = "; ".join(str(x) for x in risk_reasons)
    else:
        risk_reasons_text = str(risk_reasons)

    parts = [
        f"Insurance claim {claim.get('claim_id', 'unknown')}",
        f"Policy number: {claim.get('policy_number', 'unknown')}",
        f"Customer ID: {claim.get('customer_id', 'unknown')}",
        f"Claim type: {claim.get('claim_type', 'unknown')}",
        f"Damage amount: ${claim.get('damage_amount', 0)}",
        f"Status: {claim.get('status', 'unknown')}",
        f"Risk level: {claim.get('risk_level', 'unknown')}",
        f"Risk score: {claim.get('risk_score', 'unknown')}",
        f"Description: {claim.get('description', '')}",
        f"Risk reasons: {risk_reasons_text}",
        f"Resolution: {claim.get('resolution', '')}",
    ]
    return "\n".join(parts)


def chunks(items: List[Dict], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    if not MONGODB_URI or MONGODB_URI.startswith("PASTE_"):
        raise SystemExit("Paste your MongoDB Atlas URI into MONGODB_URI before running.")

    if not VOYAGE_API_KEY or VOYAGE_API_KEY.startswith("PASTE_"):
        raise SystemExit("Paste your Voyage API key into VOYAGE_API_KEY before running.")

    mongo = MongoClient(MONGODB_URI)
    db = mongo[MONGODB_DB]
    claims = db[COLLECTION_NAME]

    query = {}
    if SKIP_ALREADY_EMBEDDED:
        query = {"embedding": {"$exists": False}}

    docs = list(claims.find(query).sort("created_at", -1))
    if not docs:
        print("No claims need embeddings.")
        return

    vo = voyageai.Client(api_key=VOYAGE_API_KEY)

    total_updated = 0
    for batch in chunks(docs, BATCH_SIZE):
        texts = [claim_to_embedding_text(doc) for doc in batch]

        result = vo.embed(
            texts,
            model=VOYAGE_MODEL,
            input_type="document",
            output_dimension=OUTPUT_DIMENSION,
            truncation=True,
        )

        for doc, text, vector in zip(batch, texts, result.embeddings):
            claims.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "embedding": vector,
                        "embedding_text": text,
                        "embedding_model": VOYAGE_MODEL,
                        "embedding_dimensions": len(vector),
                        "embedding_created_at": now_iso(),
                    }
                },
            )
            total_updated += 1

        print(f"Embedded batch of {len(batch)} claims. Total updated: {total_updated}")

    print("Done.")
    print(f"Updated {total_updated} claim documents with Voyage embeddings.")
    print(f"Collection: {MONGODB_DB}.{COLLECTION_NAME}")
    print(f"Vector field: embedding")
    print(f"Dimensions: {OUTPUT_DIMENSION}")
    print(f"Model: {VOYAGE_MODEL}")


if __name__ == "__main__":
    main()
