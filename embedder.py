"""
Add Voyage AI embeddings to the existing claims collection in MongoDB Atlas.

Install:
  python3 -m pip install pymongo httpx python-dotenv

Run:
  python3 embedder.py

What this does:
  - Reads documents from the claims collection.
  - Builds a searchable text summary for each claim.
  - Calls the Voyage AI API via MongoDB Atlas (https://ai.mongodb.com/v1/embeddings).
  - Writes the vector back onto the SAME claim document.
  - Creates (or skips if existing) an Atlas Vector Search index on the embedding field.
  - Does not create new policies or claims.

Result in Atlas:
  claims.embedding              -> vector array (1024 dims, cosine similarity)
  claims.embedding_text         -> source text used for embedding
  claims.embedding_model        -> Voyage model name
  claims.embedding_dimensions   -> vector dimension count
  claims.embedding_created_at   -> timestamp

Vector search index (claim_vector_index):
  type:          vectorSearch (vector field, manually embedded)
  index model:   voyage-4-large (1024 dims, cosine) — used by this script
  query model:   voyage-4-lite (1024 dims) — used at query-time in app.py
  vector field:  embedding
  filter fields: status, customer_id, risk_level

Before running:
  Copy .env.example to .env and fill in MONGODB_URI, MONGODB_DB, and VOYAGE_API_KEY.
  VOYAGE_API_KEY must be a Model API key created in MongoDB Atlas
  (Atlas UI → Models → API Keys). It routes automatically to https://ai.mongodb.com/.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure

load_dotenv()


# =============================================================================
# CONFIG
# =============================================================================

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "magenta_insurance_demo")
COLLECTION_NAME = "claims"

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_BASE_URL = "https://ai.mongodb.com/v1/embeddings"
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-4-large")
EMBEDDING_DIMENSIONS = 1024
BATCH_SIZE = 32

SKIP_ALREADY_EMBEDDED = True


# =============================================================================
# HELPERS
# =============================================================================

def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def claim_to_embedding_text(claim: Dict) -> str:
    """Build a human-readable summary suitable for semantic search."""
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


def chunks(items: List[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Call the Atlas-hosted Voyage AI embeddings endpoint via httpx."""
    response = httpx.post(
        VOYAGE_BASE_URL,
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"input": texts, "model": VOYAGE_MODEL},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    # Response follows the OpenAI embeddings format: data[].embedding
    return [item["embedding"] for item in data["data"]]


def ensure_vector_search_index(claims_collection) -> None:
    # Standard vector index — embeddings are generated manually by this script
    # via the Voyage AI API and stored in the `embedding` field.
    # voyage-4-large is used at index-time (higher quality); voyage-4-lite is
    # used at query-time in app.py (cheaper/faster). Both output 1024 dims.
    index_def = {
        "name": "claim_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": EMBEDDING_DIMENSIONS,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "status"},
                {"type": "filter", "path": "customer_id"},
                {"type": "filter", "path": "risk_level"},
            ]
        },
    }
    try:
        claims_collection.create_search_index(index_def)
        print("Vector search index 'claim_vector_index' created (autoEmbed, voyage-4-large, 1024 dims).")
    except OperationFailure as exc:
        if "already exists" in str(exc).lower() or exc.code in (68, 85):
            print("Vector search index 'claim_vector_index' already exists — skipping.")
        else:
            raise


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    if not MONGODB_URI or MONGODB_URI.startswith("PASTE_"):
        raise SystemExit("Set MONGODB_URI in your .env before running.")

    if not VOYAGE_API_KEY or VOYAGE_API_KEY.startswith("PASTE_"):
        raise SystemExit("Set VOYAGE_API_KEY (Atlas Model API key) in your .env before running.")

    mongo = MongoClient(MONGODB_URI)
    db = mongo[MONGODB_DB]
    claims = db[COLLECTION_NAME]

    query: Dict[str, Any] = {}
    if SKIP_ALREADY_EMBEDDED:
        query = {"embedding": {"$exists": False}}

    docs = list(claims.find(query).sort("created_at", -1))
    if not docs:
        print("No claims need embeddings.")
        ensure_vector_search_index(claims)
        return

    total_updated = 0
    for batch in chunks(docs, BATCH_SIZE):
        texts = [claim_to_embedding_text(doc) for doc in batch]
        vectors = embed_texts(texts)

        for doc, text, vector in zip(batch, texts, vectors):
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

    print()
    print(f"Done. Updated {total_updated} claim documents.")
    print(f"Collection  : {MONGODB_DB}.{COLLECTION_NAME}")
    print(f"Vector field: embedding ({EMBEDDING_DIMENSIONS} dims)")
    print(f"Model       : {VOYAGE_MODEL}")
    print()
    ensure_vector_search_index(claims)


if __name__ == "__main__":
    main()
