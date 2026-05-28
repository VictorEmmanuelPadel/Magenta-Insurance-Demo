"""
Magenta Insurance Agent Demo
Flask web app using MongoDB Atlas + Anthropic Claude via Grove gateway.

Install:
  python3 -m pip install flask pymongo httpx voyageai python-dotenv

Run:
  python app.py

Config:
  Copy .env.example to .env and fill in your values.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

GROVE_API_KEY = os.getenv("GROVE_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv(
    "ANTHROPIC_BASE_URL",
    "https://grove-gateway-prod.azure-api.net/grove-foundry-prod/anthropic/v1/messages",
)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "magenta_insurance_demo")


# =============================================================================
# DATABASE
# =============================================================================

_mongo_client: Optional[MongoClient] = None


def get_mongo_client() -> Optional[MongoClient]:
    global _mongo_client
    if _mongo_client is None and MONGODB_URI and not MONGODB_URI.startswith("PASTE_"):
        _mongo_client = MongoClient(MONGODB_URI)
    return _mongo_client


def get_collection(name: str) -> Optional[Collection]:
    client = get_mongo_client()
    if client is None:
        return None
    return client[MONGODB_DB][name]


def db_connected() -> bool:
    return get_mongo_client() is not None


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def clean_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out


def redact_email(email: str) -> str:
    if "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    return name[:2] + "***@" + domain


# =============================================================================
# BASE SAMPLE DATA
# =============================================================================

SAMPLE_CUSTOMERS = [
    {"customer_id": "CUST-001", "name": "John Smith", "email": "john@example.com", "age": 35, "loyalty_years": 4, "customer_type": "policyholder", "created_at": now_iso()},
    {"customer_id": "CUST-002", "name": "Maya Patel", "email": "maya@example.com", "age": 28, "loyalty_years": 1, "customer_type": "policyholder", "created_at": now_iso()},
    {"customer_id": "CUST-003", "name": "Carlos Rivera", "email": "carlos@example.com", "age": 42, "loyalty_years": 7, "customer_type": "policyholder", "created_at": now_iso()},
    {"customer_id": "CUST-004", "name": "Avery Johnson", "email": "avery@example.com", "age": 23, "loyalty_years": 0, "customer_type": "policyholder", "created_at": now_iso()},
    {"customer_id": "CUST-005", "name": "Priya Shah", "email": "priya@example.com", "age": 56, "loyalty_years": 10, "customer_type": "policyholder", "created_at": now_iso()},
    {"customer_id": "CUST-006", "name": "Derek Wilson", "email": "derek@example.com", "age": 31, "loyalty_years": 2, "customer_type": "policyholder", "created_at": now_iso()},
]

SAMPLE_POLICIES = [
    {"policy_number": "POL-1001", "customer_id": "CUST-001", "customer_name": "John Smith", "vehicle": {"year": 2022, "make": "Toyota", "model": "Camry"}, "coverage_level": "comprehensive", "monthly_premium": 142.50, "coverage_limit": 25000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1002", "customer_id": "CUST-002", "customer_name": "Maya Patel", "vehicle": {"year": 2020, "make": "Honda", "model": "CR-V"}, "coverage_level": "collision", "monthly_premium": 119.25, "coverage_limit": 18000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1003", "customer_id": "CUST-003", "customer_name": "Carlos Rivera", "vehicle": {"year": 2023, "make": "Ford", "model": "F-150"}, "coverage_level": "comprehensive", "monthly_premium": 188.75, "coverage_limit": 35000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1004", "customer_id": "CUST-004", "customer_name": "Avery Johnson", "vehicle": {"year": 2018, "make": "Hyundai", "model": "Elantra"}, "coverage_level": "liability", "monthly_premium": 104.60, "coverage_limit": 12000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1005", "customer_id": "CUST-005", "customer_name": "Priya Shah", "vehicle": {"year": 2021, "make": "Subaru", "model": "Outback"}, "coverage_level": "comprehensive", "monthly_premium": 132.10, "coverage_limit": 28000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1006", "customer_id": "CUST-006", "customer_name": "Derek Wilson", "vehicle": {"year": 2019, "make": "Tesla", "model": "Model 3"}, "coverage_level": "collision", "monthly_premium": 171.40, "coverage_limit": 30000, "status": "active", "created_at": now_iso()},
    {"policy_number": "POL-1007", "customer_id": "CUST-001", "customer_name": "John Smith", "vehicle": {"year": 2017, "make": "Jeep", "model": "Wrangler"}, "coverage_level": "liability", "monthly_premium": 87.35, "coverage_limit": 10000, "status": "active", "created_at": now_iso()},
]

SAMPLE_CLAIMS = [
    {"claim_id": "CLM-9001", "policy_number": "POL-1001", "customer_id": "CUST-001", "claim_type": "collision", "damage_amount": 750.0, "description": "Small dent in rear bumper.", "risk_level": "low", "risk_score": 0.22, "risk_reasons": ["Claim amount is below $1,000."], "status": "approved", "resolution": "Auto-approved low-risk claim.", "notification_sent": True, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9002", "policy_number": "POL-1001", "customer_id": "CUST-001", "claim_type": "theft", "damage_amount": 15000.0, "description": "Vehicle reported stolen from apartment garage.", "risk_level": "high", "risk_score": 0.84, "risk_reasons": ["Claim amount exceeds $5,000.", "Claim type typically requires additional verification."], "status": "pending_human_review", "next_step": "resolve_claim", "resolution": None, "notification_sent": False, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9003", "policy_number": "POL-1002", "customer_id": "CUST-002", "claim_type": "glass", "damage_amount": 420.0, "description": "Windshield cracked by road debris.", "risk_level": "low", "risk_score": 0.18, "risk_reasons": ["Claim amount is below $1,000."], "status": "approved", "resolution": "Auto-approved low-risk glass claim.", "notification_sent": True, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9004", "policy_number": "POL-1003", "customer_id": "CUST-003", "claim_type": "collision", "damage_amount": 3800.0, "description": "Front-end damage after intersection collision.", "risk_level": "medium", "risk_score": 0.50, "risk_reasons": ["Claim amount is between $1,000 and $5,000."], "status": "approved", "resolution": "Approved after standard review.", "notification_sent": True, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9005", "policy_number": "POL-1004", "customer_id": "CUST-004", "claim_type": "vandalism", "damage_amount": 2200.0, "description": "Keyed doors and broken side mirror while parked downtown.", "risk_level": "medium", "risk_score": 0.58, "risk_reasons": ["Claim amount is between $1,000 and $5,000.", "Claim type typically requires additional verification."], "status": "pending_human_review", "next_step": "resolve_claim", "resolution": None, "notification_sent": False, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9006", "policy_number": "POL-1005", "customer_id": "CUST-005", "claim_type": "comprehensive", "damage_amount": 6400.0, "description": "Hail damage across roof, hood, and windshield.", "risk_level": "high", "risk_score": 0.72, "risk_reasons": ["Claim amount exceeds $5,000."], "status": "pending_human_review", "next_step": "resolve_claim", "resolution": None, "notification_sent": False, "created_at": now_iso(), "updated_at": now_iso()},
    {"claim_id": "CLM-9007", "policy_number": "POL-1006", "customer_id": "CUST-006", "claim_type": "collision", "damage_amount": 12200.0, "description": "Rear collision requiring battery enclosure inspection.", "risk_level": "high", "risk_score": 0.80, "risk_reasons": ["Claim amount exceeds $5,000."], "status": "denied", "resolution": "Denied after human review due to excluded commercial-use incident.", "notification_sent": True, "created_at": now_iso(), "updated_at": now_iso()},
]


def seed_database() -> Dict[str, Any]:
    if not db_connected():
        return {"error": "MongoDB not connected", "customers": 0, "policies": 0, "claims": 0}

    inserted: Dict[str, int] = {"customers": 0, "policies": 0, "claims": 0}

    for customer in SAMPLE_CUSTOMERS:
        result = get_collection("customers").update_one(
            {"customer_id": customer["customer_id"]},
            {"$setOnInsert": customer},
            upsert=True,
        )
        inserted["customers"] += 1 if result.upserted_id else 0

    for policy in SAMPLE_POLICIES:
        result = get_collection("policies").update_one(
            {"policy_number": policy["policy_number"]},
            {"$setOnInsert": policy},
            upsert=True,
        )
        inserted["policies"] += 1 if result.upserted_id else 0

    for claim in SAMPLE_CLAIMS:
        result = get_collection("claims").update_one(
            {"claim_id": claim["claim_id"]},
            {"$setOnInsert": claim},
            upsert=True,
        )
        inserted["claims"] += 1 if result.upserted_id else 0

    return inserted


# =============================================================================
# BUSINESS TOOLS
# =============================================================================

def lookup_policy(policy_number: str) -> Dict[str, Any]:
    policy = clean_doc(get_collection("policies").find_one({"policy_number": policy_number.upper()}))
    if not policy:
        return {"found": False, "message": f"No policy found for {policy_number}."}
    return {"found": True, "policy": policy}


def list_customer_policies(customer_id: str) -> Dict[str, Any]:
    docs = [clean_doc(d) for d in get_collection("policies").find({"customer_id": customer_id.upper()}).sort("created_at", -1)]
    return {"customer_id": customer_id.upper(), "policies": docs}


def get_quote(customer_id: str, vehicle_year: int, vehicle_make: str, vehicle_model: str, driver_age: int, coverage_level: str) -> Dict[str, Any]:
    coverage_level = coverage_level.lower().strip()
    base = 95.0
    current_year = datetime.now(tz=timezone.utc).year
    vehicle_age = max(current_year - int(vehicle_year), 0)

    if coverage_level == "comprehensive":
        base *= 1.45
    elif coverage_level == "collision":
        base *= 1.25
    elif coverage_level == "liability":
        base *= 0.85

    if driver_age < 25:
        base *= 1.35
    elif driver_age >= 55:
        base *= 0.92

    if vehicle_age <= 3:
        base *= 1.15
    elif vehicle_age >= 10:
        base *= 0.90

    customer = get_collection("customers").find_one({"customer_id": customer_id.upper()})
    loyalty_years = int(customer.get("loyalty_years", 0)) if customer else 0
    discounts = []

    if loyalty_years >= 3:
        base *= 0.90
        discounts.append("10% loyalty discount")

    quote = {
        "quote_id": make_id("QTE"),
        "customer_id": customer_id.upper(),
        "vehicle": {"year": vehicle_year, "make": vehicle_make, "model": vehicle_model},
        "driver_age": driver_age,
        "coverage_level": coverage_level,
        "monthly_premium": round(base, 2),
        "coverage_limit": 25000 if coverage_level == "comprehensive" else 15000,
        "discounts": discounts,
        "created_at": now_iso(),
    }
    get_collection("quotes").insert_one(dict(quote))
    return quote


def create_policy(customer_id: str, customer_name: str, vehicle_year: int, vehicle_make: str, vehicle_model: str, coverage_level: str, monthly_premium: float, coverage_limit: float) -> Dict[str, Any]:
    policy = {
        "policy_number": make_id("POL"),
        "customer_id": customer_id.upper(),
        "customer_name": customer_name,
        "vehicle": {"year": vehicle_year, "make": vehicle_make, "model": vehicle_model},
        "coverage_level": coverage_level.lower().strip(),
        "monthly_premium": float(monthly_premium),
        "coverage_limit": float(coverage_limit),
        "status": "active",
        "created_at": now_iso(),
    }
    get_collection("policies").insert_one(dict(policy))
    return policy


def file_claim(policy_number: str, claim_type: str, damage_amount: float, description: str) -> Dict[str, Any]:
    policy_number = policy_number.upper()
    policy = get_collection("policies").find_one({"policy_number": policy_number})
    if not policy:
        return {"error": f"No active policy found for {policy_number}."}

    claim = {
        "claim_id": make_id("CLM"),
        "policy_number": policy_number,
        "customer_id": policy["customer_id"],
        "claim_type": claim_type.lower().strip(),
        "damage_amount": float(damage_amount),
        "description": description,
        "risk_level": None,
        "risk_score": None,
        "risk_reasons": [],
        "status": "filed",
        "next_step": "analyze_claim_risk",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    get_collection("claims").insert_one(dict(claim))
    return claim


def analyze_claim_risk(claim_id: str) -> Dict[str, Any]:
    claims = get_collection("claims")
    policies = get_collection("policies")

    claim_id = claim_id.upper()
    claim = claims.find_one({"claim_id": claim_id})
    if not claim:
        return {"error": f"Claim {claim_id} not found."}

    policy = policies.find_one({"policy_number": claim["policy_number"]})
    if not policy:
        return {"error": f"Policy {claim['policy_number']} not found."}

    amount = float(claim["damage_amount"])
    previous_claims_count = claims.count_documents({"customer_id": claim["customer_id"], "claim_id": {"$ne": claim_id}})

    risk_score = 0.15
    reasons = []

    if amount < 1000:
        risk_level = "low"
        risk_score += 0.07
        reasons.append("Claim amount is below $1,000.")
    elif amount <= 5000:
        risk_level = "medium"
        risk_score += 0.35
        reasons.append("Claim amount is between $1,000 and $5,000.")
    else:
        risk_level = "high"
        risk_score += 0.65
        reasons.append("Claim amount exceeds $5,000.")

    if claim["claim_type"] in ["theft", "vandalism"]:
        risk_score += 0.08
        reasons.append("Claim type typically requires additional verification.")

    if amount > float(policy.get("coverage_limit", 0)):
        risk_score = max(risk_score, 0.92)
        risk_level = "high"
        reasons.append("Claim amount exceeds policy coverage limit.")

    if previous_claims_count >= 2:
        risk_score += 0.15
        reasons.append("Customer has multiple previous claims.")

    risk_score = min(round(risk_score, 2), 1.0)
    requires_human_review = risk_score >= 0.6 or risk_level == "high"

    if requires_human_review:
        status = "pending_human_review"
        next_step = "resolve_claim"
        resolution = None
    else:
        status = "approved"
        next_step = "complete"
        resolution = "Auto-approved low-risk claim."

    claims.update_one(
        {"claim_id": claim_id},
        {"$set": {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_reasons": reasons,
            "status": status,
            "next_step": next_step,
            "resolution": resolution,
            "updated_at": now_iso(),
        }},
    )

    if not requires_human_review:
        send_notification(claim_id)

    return {
        "claim": clean_doc(claims.find_one({"claim_id": claim_id})),
        "requires_human_review": requires_human_review,
        "risk_reasons": reasons,
    }


def resolve_claim(claim_id: str, decision: str, reviewer_notes: str = "") -> Dict[str, Any]:
    claims = get_collection("claims")
    reviews = get_collection("claim_reviews")

    claim_id = claim_id.upper()
    decision = decision.lower().strip()
    if decision not in ["approved", "denied"]:
        return {"error": "Decision must be approved or denied."}

    claim = claims.find_one({"claim_id": claim_id})
    if not claim:
        return {"error": f"Claim {claim_id} not found."}

    resolution = "Approved after human review." if decision == "approved" else "Denied after human review."
    review = {
        "review_id": make_id("REV"),
        "claim_id": claim_id,
        "decision": decision,
        "reviewer_notes": reviewer_notes,
        "reviewed_by": "demo-adjuster",
        "created_at": now_iso(),
    }
    reviews.insert_one(dict(review))

    claims.update_one(
        {"claim_id": claim_id},
        {"$set": {
            "status": decision,
            "resolution": resolution,
            "reviewer_notes": reviewer_notes,
            "next_step": "complete",
            "updated_at": now_iso(),
        }},
    )

    send_notification(claim_id)
    return clean_doc(claims.find_one({"claim_id": claim_id}))


def send_notification(claim_id: str) -> Dict[str, Any]:
    claims = get_collection("claims")
    customers = get_collection("customers")
    notifications = get_collection("notifications")

    claim_id = claim_id.upper()
    claim = claims.find_one({"claim_id": claim_id})
    if not claim:
        return {"error": f"Claim {claim_id} not found."}

    customer = customers.find_one({"customer_id": claim["customer_id"]})
    recipient = customer.get("email", "unknown@example.com") if customer else "unknown@example.com"

    notification = {
        "notification_id": make_id("NTF"),
        "claim_id": claim_id,
        "customer_id": claim["customer_id"],
        "recipient_email_redacted": redact_email(recipient),
        "message": f"Your claim {claim_id} is now {claim['status']}. {claim.get('resolution') or ''}",
        "created_at": now_iso(),
    }
    notifications.insert_one(dict(notification))
    claims.update_one({"claim_id": claim_id}, {"$set": {"notification_sent": True, "updated_at": now_iso()}})
    return notification


def check_claim_status(claim_id: str) -> Dict[str, Any]:
    claim = clean_doc(get_collection("claims").find_one({"claim_id": claim_id.upper()}))
    if not claim:
        return {"found": False, "message": f"No claim found for {claim_id}."}
    return {"found": True, "claim": claim}


def list_customer_claims(customer_id: str) -> Dict[str, Any]:
    docs = [clean_doc(d) for d in get_collection("claims").find({"customer_id": customer_id.upper()}).sort("created_at", -1)]
    return {"customer_id": customer_id.upper(), "claims": docs}


def list_pending_claims(customer_id: Optional[str] = None) -> Dict[str, Any]:
    query: Dict[str, Any] = {"status": "pending_human_review"}
    if customer_id:
        query["customer_id"] = customer_id.upper()
    docs = [clean_doc(d) for d in get_collection("claims").find(query).sort("created_at", -1)]
    return {"pending_claims": docs}


def _embed_query(text: str) -> List[float]:
    """Embed a single query string via the Atlas-hosted Voyage AI API."""
    response = httpx.post(
        "https://ai.mongodb.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {os.getenv('VOYAGE_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        json={"input": [text], "model": "voyage-4-lite"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def search_similar_claims(query: str, limit: int = 5, status: Optional[str] = None) -> Dict[str, Any]:
    try:
        query_vector = _embed_query(query)
    except Exception as exc:
        return {"error": f"Failed to embed query: {exc}", "results": [], "count": 0}

    pipeline: List[Dict[str, Any]] = [
        {
            "$vectorSearch": {
                "index": "claim_vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": limit * 20,
                "limit": limit,
                **({"filter": {"status": {"$eq": status}}} if status else {}),
            }
        },
        {
            "$project": {
                "_id": 0,
                "claim_id": 1,
                "policy_number": 1,
                "customer_id": 1,
                "claim_type": 1,
                "damage_amount": 1,
                "description": 1,
                "status": 1,
                "risk_level": 1,
                "risk_score": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    results = list(get_collection("claims").aggregate(pipeline))
    return {"query": query, "results": results, "count": len(results)}


TOOL_REGISTRY = {
    "lookup_policy": lookup_policy,
    "list_customer_policies": list_customer_policies,
    "get_quote": get_quote,
    "create_policy": create_policy,
    "file_claim": file_claim,
    "analyze_claim_risk": analyze_claim_risk,
    "check_claim_status": check_claim_status,
    "list_customer_claims": list_customer_claims,
    "list_pending_claims": list_pending_claims,
    "search_similar_claims": search_similar_claims,
}

TOOLS = [
    {"name": "lookup_policy", "description": "Look up an insurance policy by policy number.", "input_schema": {"type": "object", "properties": {"policy_number": {"type": "string"}}, "required": ["policy_number"]}},
    {"name": "list_customer_policies", "description": "List policies for a customer.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_quote", "description": "Generate an auto insurance quote.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "vehicle_year": {"type": "integer"}, "vehicle_make": {"type": "string"}, "vehicle_model": {"type": "string"}, "driver_age": {"type": "integer"}, "coverage_level": {"type": "string", "enum": ["liability", "collision", "comprehensive"]}}, "required": ["customer_id", "vehicle_year", "vehicle_make", "vehicle_model", "driver_age", "coverage_level"]}},
    {"name": "create_policy", "description": "Create a new auto insurance policy after the customer accepts a quote.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "customer_name": {"type": "string"}, "vehicle_year": {"type": "integer"}, "vehicle_make": {"type": "string"}, "vehicle_model": {"type": "string"}, "coverage_level": {"type": "string"}, "monthly_premium": {"type": "number"}, "coverage_limit": {"type": "number"}}, "required": ["customer_id", "customer_name", "vehicle_year", "vehicle_make", "vehicle_model", "coverage_level", "monthly_premium", "coverage_limit"]}},
    {"name": "file_claim", "description": "File an auto insurance claim. After filing, call analyze_claim_risk with the returned claim_id.", "input_schema": {"type": "object", "properties": {"policy_number": {"type": "string"}, "claim_type": {"type": "string", "enum": ["collision", "theft", "comprehensive", "glass", "vandalism"]}, "damage_amount": {"type": "number"}, "description": {"type": "string"}}, "required": ["policy_number", "claim_type", "damage_amount", "description"]}},
    {"name": "analyze_claim_risk", "description": "Analyze a filed claim. Auto-approves low-risk claims and marks high-risk claims pending human review.", "input_schema": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}},
    {"name": "check_claim_status", "description": "Check current claim status by claim ID.", "input_schema": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}},
    {"name": "list_customer_claims", "description": "List claims for a customer.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "list_pending_claims", "description": "List pending human-review claims, optionally for a customer.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": []}},
    {"name": "search_similar_claims", "description": "Semantic search over claims using natural language. Finds claims similar in meaning to the query. Optionally filter by status.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}, "status": {"type": "string", "enum": ["filed", "approved", "denied", "pending_human_review"]}}, "required": ["query"]}},
]

SYSTEM_PROMPT = """
You are the Magenta Insurance Agent, a helpful auto insurance assistant.
You help with policy lookup, quotes, policy creation, claims, and claim status.
Use tools for any real policy, quote, or claim data.
Risk decisions are made by backend tools, not guessed.
If a claim is pending_human_review, explain that it is paused for adjuster review.
If a claim is auto-approved, explain why briefly.
Keep responses concise and demo-friendly.
"""


# =============================================================================
# LLM LOOP
# =============================================================================

_ANTHROPIC_HEADERS = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
}


def anthropic_enabled() -> bool:
    return bool(GROVE_API_KEY and not GROVE_API_KEY.startswith("PASTE_"))


def run_agent(user_message: str, history: List[Dict[str, str]]) -> str:
    if not db_connected():
        return "MongoDB Atlas is not configured yet."

    if not anthropic_enabled():
        return fallback_agent(user_message)

    headers = {**_ANTHROPIC_HEADERS, "api-key": GROVE_API_KEY}
    messages: List[Dict[str, Any]] = list(history[-10:])
    messages.append({"role": "user", "content": user_message})

    for _ in range(5):
        payload = {
            "model": ANTHROPIC_MODEL,
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "tools": TOOLS,
            "max_tokens": 2048,
        }

        response = httpx.post(ANTHROPIC_BASE_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        content_blocks: List[Dict[str, Any]] = data["content"]
        stop_reason: str = data["stop_reason"]

        text_parts = [b["text"] for b in content_blocks if b["type"] == "text"]
        tool_uses = [b for b in content_blocks if b["type"] == "tool_use"]

        if stop_reason == "end_turn" or not tool_uses:
            return " ".join(text_parts) or "Done."

        messages.append({"role": "assistant", "content": content_blocks})

        tool_results = []
        for tool_use in tool_uses:
            try:
                result = TOOL_REGISTRY[tool_use["name"]](**tool_use["input"])
            except Exception as exc:
                result = {"error": str(exc), "tool": tool_use["name"]}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": json.dumps(result, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    return "I ran several steps, but need one more message to continue."


def fallback_agent(user_message: str) -> str:
    text = user_message.lower()
    policy_match = re.search(r"pol-\d+", user_message, flags=re.IGNORECASE)
    claim_match = re.search(r"clm-\d+", user_message, flags=re.IGNORECASE)
    amount_match = re.search(r"\$?([0-9][0-9,]*(?:\.\d+)?)", user_message)

    if "claim" in text and policy_match and amount_match:
        policy_number = policy_match.group(0).upper()
        amount = float(amount_match.group(1).replace(",", ""))
        claim_type = "collision"
        for possible in ["theft", "glass", "vandalism", "comprehensive", "collision"]:
            if possible in text:
                claim_type = possible
                break
        filed = file_claim(policy_number, claim_type, amount, user_message)
        if "error" in filed:
            return filed["error"]
        analyzed = analyze_claim_risk(filed["claim_id"])
        claim = analyzed["claim"]
        if analyzed["requires_human_review"]:
            return f"I filed claim {claim['claim_id']} and marked it pending human review. Risk score: {claim['risk_score']}."
        return f"I filed claim {claim['claim_id']} and it was auto-approved as low risk."

    if policy_match:
        result = lookup_policy(policy_match.group(0).upper())
        if not result["found"]:
            return result["message"]
        policy = result["policy"]
        return f"Policy {policy['policy_number']} is {policy['status']} for {policy['customer_name']} with {policy['coverage_level']} coverage."

    if claim_match:
        result = check_claim_status(claim_match.group(0).upper())
        if not result["found"]:
            return result["message"]
        claim = result["claim"]
        return f"Claim {claim['claim_id']} is currently {claim['status']}."

    return "I can help with quotes, policy lookup, and claims. Try: 'Look up policy POL-1001' or 'File a collision claim for POL-1001 for $750.'"


# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "magenta-demo-secret")


@app.route("/")
def index():
    return render_template(
        "index.html",
        anthropic_model=ANTHROPIC_MODEL,
        mongodb_db=MONGODB_DB,
    )


@app.route("/api/status")
def api_status():
    return jsonify({
        "mongodb": db_connected(),
        "anthropic": anthropic_enabled(),
        "model": ANTHROPIC_MODEL,
    })


@app.route("/api/counts")
def api_counts():
    if not db_connected():
        return jsonify({"customers": 0, "policies": 0, "claims": 0, "pending": 0})
    return jsonify({
        "customers": get_collection("customers").count_documents({}),
        "policies": get_collection("policies").count_documents({}),
        "claims": get_collection("claims").count_documents({}),
        "pending": get_collection("claims").count_documents({"status": "pending_human_review"}),
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "Empty message"}), 400
    response = run_agent(message, history)
    return jsonify({"response": response})


@app.route("/api/seed", methods=["POST"])
def api_seed():
    result = seed_database()
    return jsonify(result)


@app.route("/api/pending")
def api_pending():
    if not db_connected():
        return jsonify([])
    result = list_pending_claims()
    return jsonify(result["pending_claims"])


@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    data = request.get_json()
    result = resolve_claim(
        data["claim_id"],
        data["decision"],
        data.get("notes", ""),
    )
    return jsonify(result)


@app.route("/api/collection/<name>")
def api_collection(name: str):
    allowed = ["customers", "policies", "claims", "quotes", "claim_reviews", "notifications"]
    if name not in allowed:
        return jsonify({"error": "Unknown collection"}), 400
    if not db_connected():
        return jsonify([])
    query: Dict[str, Any] = {}
    status = request.args.get("status")
    if name == "claims" and status and status != "all":
        query["status"] = status
    docs = [clean_doc(d) for d in get_collection(name).find(query).sort("created_at", -1).limit(200)]
    return jsonify(docs)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8501))
    app.run(debug=True, host="0.0.0.0", port=port)
