"""
Magenta Insurance Agent Demo
Python 3.10-compatible Streamlit app using MongoDB Atlas + legacy OpenAI SDK function calling.

Install:
  python3 -m pip install streamlit pymongo openai==0.28.1 python-dotenv

Run:
  streamlit run app.py

Config:
  Copy .env.example to .env and fill in your values. The app reads from .env automatically.
"""

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()

# =============================================================================
# CONFIG — values are loaded from .env; override here only if needed
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "magenta_insurance_demo")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")


# =============================================================================
# STREAMLIT PAGE + THEME
# =============================================================================

st.set_page_config(
    page_title="Magenta Insurance Agent",
    page_icon="🛡️",
    layout="wide",
)

MAGENTA_CSS = """
<style>
    :root {
        --magenta: #e0007a;
        --magenta-dark: #9b0056;
        --magenta-soft: #fff0f8;
        --purple: #8b2be2;
        --ink: #171321;
        --muted: #6b6475;
        --border: #f3c4dc;
    }

    .stApp {
        background: linear-gradient(135deg, #fff7fb 0%, #ffffff 42%, #f9f4ff 100%);
    }

    h1, h2, h3 {
        color: var(--ink);
    }

    .hero {
        padding: 1.3rem 1.4rem;
        border-radius: 24px;
        background: linear-gradient(135deg, var(--magenta) 0%, var(--purple) 100%);
        color: white;
        margin-bottom: 1.2rem;
        box-shadow: 0 16px 40px rgba(224, 0, 122, 0.2);
    }

    .hero h1 {
        color: white;
        margin: 0;
        font-size: 2.2rem;
    }

    .hero p {
        color: rgba(255,255,255,0.92);
        margin: 0.35rem 0 0 0;
        font-weight: 600;
    }

    /* Style the real Streamlit metric widgets. No fake wrapper divs. */
    [data-testid="stMetric"] {
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.88);
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 8px 30px rgba(155, 0, 86, 0.08);
    }

    [data-testid="stMetric"] label {
        color: var(--muted) !important;
        font-weight: 700;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink);
    }

    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 800;
        background: var(--magenta-soft);
        color: var(--magenta-dark);
        border: 1px solid var(--border);
    }

    .review-card {
        border: 1px solid var(--border);
        background: white;
        border-radius: 18px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 8px 30px rgba(155, 0, 86, 0.08);
    }

    .stButton > button {
        border-radius: 999px;
        border: 1px solid var(--magenta);
        color: white;
        background: var(--magenta);
        font-weight: 800;
    }

    .stButton > button:hover {
        border-color: var(--magenta-dark);
        background: var(--magenta-dark);
        color: white;
    }
</style>
"""

st.markdown(MAGENTA_CSS, unsafe_allow_html=True)


# =============================================================================
# DATABASE
# =============================================================================

@st.cache_resource
def get_mongo_client() -> Optional[MongoClient]:
    if not MONGODB_URI or MONGODB_URI.startswith("PASTE_"):
        return None
    return MongoClient(MONGODB_URI)


def get_collection(name: str) -> Optional[Collection]:
    client = get_mongo_client()
    if client is None:
        return None
    return client[MONGODB_DB][name]


def require_db() -> bool:
    if get_mongo_client() is None:
        st.error("MongoDB Atlas is not configured. Paste your Atlas URI into MONGODB_URI at the top of app.py.")
        return False
    return True


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


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


def seed_database() -> Dict[str, int]:
    if not require_db():
        return {"customers": 0, "policies": 0, "claims": 0}

    inserted = {"customers": 0, "policies": 0, "claims": 0}

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
    current_year = datetime.utcnow().year
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
    query = {"status": "pending_human_review"}
    if customer_id:
        query["customer_id"] = customer_id.upper()
    docs = [clean_doc(d) for d in get_collection("claims").find(query).sort("created_at", -1)]
    return {"pending_claims": docs}


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
}

FUNCTIONS = [
    {"name": "lookup_policy", "description": "Look up an insurance policy by policy number.", "parameters": {"type": "object", "properties": {"policy_number": {"type": "string"}}, "required": ["policy_number"]}},
    {"name": "list_customer_policies", "description": "List policies for a customer.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_quote", "description": "Generate an auto insurance quote.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}, "vehicle_year": {"type": "integer"}, "vehicle_make": {"type": "string"}, "vehicle_model": {"type": "string"}, "driver_age": {"type": "integer"}, "coverage_level": {"type": "string", "enum": ["liability", "collision", "comprehensive"]}}, "required": ["customer_id", "vehicle_year", "vehicle_make", "vehicle_model", "driver_age", "coverage_level"]}},
    {"name": "create_policy", "description": "Create a new auto insurance policy after the customer accepts a quote.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}, "customer_name": {"type": "string"}, "vehicle_year": {"type": "integer"}, "vehicle_make": {"type": "string"}, "vehicle_model": {"type": "string"}, "coverage_level": {"type": "string"}, "monthly_premium": {"type": "number"}, "coverage_limit": {"type": "number"}}, "required": ["customer_id", "customer_name", "vehicle_year", "vehicle_make", "vehicle_model", "coverage_level", "monthly_premium", "coverage_limit"]}},
    {"name": "file_claim", "description": "File an auto insurance claim. After filing, call analyze_claim_risk with the returned claim_id.", "parameters": {"type": "object", "properties": {"policy_number": {"type": "string"}, "claim_type": {"type": "string", "enum": ["collision", "theft", "comprehensive", "glass", "vandalism"]}, "damage_amount": {"type": "number"}, "description": {"type": "string"}}, "required": ["policy_number", "claim_type", "damage_amount", "description"]}},
    {"name": "analyze_claim_risk", "description": "Analyze a filed claim. Auto-approves low-risk claims and marks high-risk claims pending human review.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}},
    {"name": "check_claim_status", "description": "Check current claim status by claim ID.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}},
    {"name": "list_customer_claims", "description": "List claims for a customer.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "list_pending_claims", "description": "List pending human-review claims, optionally for a customer.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": []}},
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
# LLM LOOP — legacy OpenAI SDK, Python 3.10-friendly
# =============================================================================

def openai_enabled() -> bool:
    return bool(OPENAI_API_KEY and not OPENAI_API_KEY.startswith("PASTE_"))


def run_agent(user_message: str, history: List[Dict[str, str]]) -> str:
    if not require_db():
        return "MongoDB Atlas is not configured yet."

    if not openai_enabled():
        return fallback_agent(user_message)

    openai.api_key = OPENAI_API_KEY

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})

    for _ in range(5):
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto",
        )
        message = response["choices"][0]["message"]
        messages.append(message)

        function_call = message.get("function_call")
        if not function_call:
            return message.get("content") or "Done."

        name = function_call.get("name")
        raw_args = function_call.get("arguments") or "{}"
        try:
            args = json.loads(raw_args)
            result = TOOL_REGISTRY[name](**args)
        except Exception as exc:
            result = {"error": str(exc), "tool": name}

        messages.append({"role": "function", "name": name, "content": json.dumps(result, default=str)})

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
# UI
# =============================================================================

def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>Magenta Insurance Agent</h1>
            <p>Policy management, quotes, claims processing, and human-in-the-loop review.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_counts() -> Dict[str, int]:
    if get_mongo_client() is None:
        return {"customers": 0, "policies": 0, "claims": 0, "pending": 0}
    return {
        "customers": get_collection("customers").count_documents({}),
        "policies": get_collection("policies").count_documents({}),
        "claims": get_collection("claims").count_documents({}),
        "pending": get_collection("claims").count_documents({"status": "pending_human_review"}),
    }


def render_connection_status() -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("MongoDB Atlas", "Connected" if get_mongo_client() else "Missing URI")
    with col2:
        st.metric("OpenAI", "Enabled" if openai_enabled() else "Fallback Mode")
    with col3:
        st.metric("Model", OPENAI_MODEL if openai_enabled() else "No API key")


def render_demo_metrics() -> None:
    counts = get_counts()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Customers", counts["customers"])
    with col2:
        st.metric("Policies", counts["policies"])
    with col3:
        st.metric("Claims", counts["claims"])
    with col4:
        st.metric("Pending Review", counts["pending"])


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Demo Controls")
        st.write("Seed the base data if the database is empty. Your separate seeder can add the larger dataset.")
        if st.button("Seed base sample data"):
            inserted = seed_database()
            st.success(f"Seeded base data: {inserted}")
            st.rerun()

        st.divider()
        st.caption("Demo architecture")
        st.write("Streamlit → OpenAI function calling → Python tools → MongoDB Atlas")

        st.divider()
        st.caption("Try")
        st.code("Look up policy POL-1001")
        st.code("File a collision claim for POL-1001 for $750. Small dent in bumper.")
        st.code("File a theft claim for POL-1003 for $26,500. Truck was stolen.")


def render_chat_tab() -> None:
    st.subheader("Customer Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi — I can help with quotes, policy lookup, and claims. Try asking about POL-1001 or filing a claim."}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Ask for a quote, look up a policy, or file a claim...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = run_agent(prompt, history)
            st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})


def render_review_tab() -> None:
    st.subheader("Human Review Queue")
    if not require_db():
        return

    pending = list(get_collection("claims").find({"status": "pending_human_review"}).sort("created_at", -1))
    if not pending:
        st.success("No claims are waiting for human review.")
        return

    for raw in pending:
        claim = clean_doc(raw)
        st.markdown("<div class='review-card'>", unsafe_allow_html=True)
        st.markdown(f"### {claim['claim_id']} <span class='status-pill'>{claim.get('risk_level', 'unknown')} risk</span>", unsafe_allow_html=True)
        st.write(f"**Policy:** {claim['policy_number']}")
        st.write(f"**Customer:** {claim['customer_id']}")
        st.write(f"**Type:** {claim['claim_type']}")
        st.write(f"**Amount:** ${claim['damage_amount']:,.2f}")
        st.write(f"**Risk score:** {claim.get('risk_score')}")
        st.write(f"**Description:** {claim.get('description')}")
        if claim.get("risk_reasons"):
            st.write("**Reasons:**")
            for reason in claim["risk_reasons"]:
                st.write(f"- {reason}")

        notes = st.text_area(
            "Reviewer notes",
            value="Documentation reviewed. Decision entered by demo adjuster.",
            key=f"notes_{claim['claim_id']}",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Approve", key=f"approve_{claim['claim_id']}"):
                resolve_claim(claim["claim_id"], "approved", notes)
                st.success(f"Approved {claim['claim_id']} and logged notification.")
                st.rerun()
        with col_b:
            if st.button("Deny", key=f"deny_{claim['claim_id']}"):
                resolve_claim(claim["claim_id"], "denied", notes)
                st.warning(f"Denied {claim['claim_id']} and logged notification.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_data_tab() -> None:
    st.subheader("Atlas Data")
    if not require_db():
        return

    collection_name = st.selectbox("Collection", ["customers", "policies", "claims", "quotes", "claim_reviews", "notifications"])
    status_filter = None
    if collection_name == "claims":
        status_filter = st.selectbox("Status filter", ["all", "approved", "denied", "pending_human_review", "filed"])

    query: Dict[str, Any] = {}
    if collection_name == "claims" and status_filter and status_filter != "all":
        query["status"] = status_filter

    docs = [clean_doc(d) for d in get_collection(collection_name).find(query).sort("created_at", -1).limit(200)]
    if docs:
        st.dataframe(docs, use_container_width=True)
    else:
        st.info(f"No documents found in {collection_name}.")


def main() -> None:
    render_header()
    render_sidebar()
    render_connection_status()
    st.write("")
    render_demo_metrics()
    st.write("")

    tab_chat, tab_review, tab_data = st.tabs(["Chat", "Human Review", "Data"])
    with tab_chat:
        render_chat_tab()
    with tab_review:
        render_review_tab()
    with tab_data:
        render_data_tab()


if __name__ == "__main__":
    main()
