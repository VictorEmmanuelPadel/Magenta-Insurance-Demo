"""
Add more demo customers and claims to the Magenta Insurance Streamlit demo.

Python 3.10-compatible.

Install if needed:
  python3 -m pip install pymongo python-dotenv

Run:
  python3 seeder.py

What this does:
  - Adds more customers/prospects.
  - Adds more claims against existing policies POL-1001 through POL-1007.
  - Does NOT add any new policies.
  - Uses upserts, so you can run it multiple times without duplicating these seeded records.

Before running:
  Copy .env.example to .env and fill in MONGODB_URI and MONGODB_DB.
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

load_dotenv()

# -----------------------------
# Config
# -----------------------------

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "magenta_insurance_demo")


def now_iso(offset_days=0):
    dt = datetime.utcnow() + timedelta(days=offset_days)
    return dt.isoformat(timespec="seconds") + "Z"


# -----------------------------
# Additional customers
# -----------------------------
# These include prospects and household members.
# They do not require policies, which lets the UI show richer customer data
# while keeping the policy count unchanged.

CUSTOMERS = [
    {
        "customer_id": "CUST-007",
        "name": "Nina Brooks",
        "email": "nina@example.com",
        "age": 39,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Requested quote for bundled auto coverage.",
        "created_at": now_iso(-16),
    },
    {
        "customer_id": "CUST-008",
        "name": "Marcus Lee",
        "email": "marcus@example.com",
        "age": 47,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Interested in comprehensive coverage for new SUV.",
        "created_at": now_iso(-15),
    },
    {
        "customer_id": "CUST-009",
        "name": "Elena Garcia",
        "email": "elena@example.com",
        "age": 34,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Asked about glass coverage and deductible options.",
        "created_at": now_iso(-14),
    },
    {
        "customer_id": "CUST-010",
        "name": "Tyler Nguyen",
        "email": "tyler@example.com",
        "age": 22,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Young driver quote scenario.",
        "created_at": now_iso(-12),
    },
    {
        "customer_id": "CUST-011",
        "name": "Sofia Martinez",
        "email": "sofia@example.com",
        "age": 61,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Senior driver quote scenario.",
        "created_at": now_iso(-10),
    },
    {
        "customer_id": "CUST-012",
        "name": "Brandon Scott",
        "email": "brandon@example.com",
        "age": 30,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Comparing liability and collision coverage.",
        "created_at": now_iso(-8),
    },
    {
        "customer_id": "CUST-013",
        "name": "Rachel Kim",
        "email": "rachel@example.com",
        "age": 45,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Asked about multi-vehicle household pricing.",
        "created_at": now_iso(-6),
    },
    {
        "customer_id": "CUST-014",
        "name": "Owen Parker",
        "email": "owen@example.com",
        "age": 52,
        "loyalty_years": 0,
        "customer_type": "prospect",
        "notes": "Interested in low-deductible comprehensive coverage.",
        "created_at": now_iso(-4),
    },
]


# -----------------------------
# Additional claims
# -----------------------------
# These are all tied to the existing policies and existing customers.
# Status distribution is intentional so the demo has variety:
#   - approved low risk
#   - denied after review
#   - pending human review
#   - medium risk reviewed cases

CLAIMS = [
    {
        "claim_id": "CLM-9010",
        "policy_number": "POL-1002",
        "customer_id": "CUST-002",
        "claim_type": "glass",
        "damage_amount": 310.0,
        "description": "Small windshield chip caused by highway debris.",
        "risk_level": "low",
        "risk_score": 0.16,
        "risk_reasons": ["Claim amount is below $1,000.", "Glass-only claim has limited exposure."],
        "status": "approved",
        "resolution": "Auto-approved low-risk glass claim.",
        "notification_sent": True,
        "created_at": now_iso(-30),
        "updated_at": now_iso(-30),
    },
    {
        "claim_id": "CLM-9011",
        "policy_number": "POL-1003",
        "customer_id": "CUST-003",
        "claim_type": "collision",
        "damage_amount": 925.0,
        "description": "Minor parking lot scrape on passenger side door.",
        "risk_level": "low",
        "risk_score": 0.24,
        "risk_reasons": ["Claim amount is below $1,000."],
        "status": "approved",
        "resolution": "Auto-approved low-risk collision claim.",
        "notification_sent": True,
        "created_at": now_iso(-28),
        "updated_at": now_iso(-28),
    },
    {
        "claim_id": "CLM-9012",
        "policy_number": "POL-1005",
        "customer_id": "CUST-005",
        "claim_type": "comprehensive",
        "damage_amount": 1450.0,
        "description": "Tree branch damaged roof panel during storm.",
        "risk_level": "medium",
        "risk_score": 0.44,
        "risk_reasons": ["Claim amount is between $1,000 and $5,000."],
        "status": "approved",
        "resolution": "Approved after standard review.",
        "notification_sent": True,
        "created_at": now_iso(-26),
        "updated_at": now_iso(-25),
    },
    {
        "claim_id": "CLM-9013",
        "policy_number": "POL-1007",
        "customer_id": "CUST-001",
        "claim_type": "vandalism",
        "damage_amount": 1800.0,
        "description": "Soft top cut while vehicle was parked overnight.",
        "risk_level": "medium",
        "risk_score": 0.56,
        "risk_reasons": ["Claim amount is between $1,000 and $5,000.", "Vandalism typically requires additional verification."],
        "status": "pending_human_review",
        "next_step": "resolve_claim",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(-22),
        "updated_at": now_iso(-22),
    },
    {
        "claim_id": "CLM-9014",
        "policy_number": "POL-1004",
        "customer_id": "CUST-004",
        "claim_type": "collision",
        "damage_amount": 4900.0,
        "description": "Single-car incident with front bumper and radiator damage.",
        "risk_level": "medium",
        "risk_score": 0.59,
        "risk_reasons": ["Claim amount is near the $5,000 review threshold."],
        "status": "pending_human_review",
        "next_step": "resolve_claim",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(-20),
        "updated_at": now_iso(-20),
    },
    {
        "claim_id": "CLM-9015",
        "policy_number": "POL-1006",
        "customer_id": "CUST-006",
        "claim_type": "comprehensive",
        "damage_amount": 7200.0,
        "description": "Flood damage reported after heavy rain event.",
        "risk_level": "high",
        "risk_score": 0.76,
        "risk_reasons": ["Claim amount exceeds $5,000.", "Water damage requires additional documentation."],
        "status": "pending_human_review",
        "next_step": "resolve_claim",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(-18),
        "updated_at": now_iso(-18),
    },
    {
        "claim_id": "CLM-9016",
        "policy_number": "POL-1001",
        "customer_id": "CUST-001",
        "claim_type": "glass",
        "damage_amount": 680.0,
        "description": "Rear window shattered by road debris.",
        "risk_level": "low",
        "risk_score": 0.28,
        "risk_reasons": ["Claim amount is below $1,000."],
        "status": "approved",
        "resolution": "Auto-approved low-risk glass claim.",
        "notification_sent": True,
        "created_at": now_iso(-17),
        "updated_at": now_iso(-17),
    },
    {
        "claim_id": "CLM-9017",
        "policy_number": "POL-1003",
        "customer_id": "CUST-003",
        "claim_type": "theft",
        "damage_amount": 26500.0,
        "description": "Truck reported stolen from job site parking lot.",
        "risk_level": "high",
        "risk_score": 0.91,
        "risk_reasons": ["Claim amount exceeds $5,000.", "Theft claims require verification.", "High-value vehicle exposure."],
        "status": "pending_human_review",
        "next_step": "resolve_claim",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(-14),
        "updated_at": now_iso(-14),
    },
    {
        "claim_id": "CLM-9018",
        "policy_number": "POL-1005",
        "customer_id": "CUST-005",
        "claim_type": "collision",
        "damage_amount": 2350.0,
        "description": "Rear bumper damage from low-speed collision.",
        "risk_level": "medium",
        "risk_score": 0.48,
        "risk_reasons": ["Claim amount is between $1,000 and $5,000."],
        "status": "approved",
        "resolution": "Approved after standard review.",
        "notification_sent": True,
        "created_at": now_iso(-11),
        "updated_at": now_iso(-10),
    },
    {
        "claim_id": "CLM-9019",
        "policy_number": "POL-1004",
        "customer_id": "CUST-004",
        "claim_type": "collision",
        "damage_amount": 9800.0,
        "description": "Major front-end collision; possible frame damage.",
        "risk_level": "high",
        "risk_score": 0.79,
        "risk_reasons": ["Claim amount exceeds $5,000.", "Young driver profile requires additional review."],
        "status": "denied",
        "resolution": "Denied after review due to uncovered rideshare use at time of loss.",
        "notification_sent": True,
        "created_at": now_iso(-9),
        "updated_at": now_iso(-8),
    },
    {
        "claim_id": "CLM-9020",
        "policy_number": "POL-1002",
        "customer_id": "CUST-002",
        "claim_type": "vandalism",
        "damage_amount": 1350.0,
        "description": "Spray paint damage on driver side panels.",
        "risk_level": "medium",
        "risk_score": 0.52,
        "risk_reasons": ["Claim amount is between $1,000 and $5,000.", "Vandalism typically requires documentation."],
        "status": "pending_human_review",
        "next_step": "resolve_claim",
        "resolution": None,
        "notification_sent": False,
        "created_at": now_iso(-7),
        "updated_at": now_iso(-7),
    },
    {
        "claim_id": "CLM-9021",
        "policy_number": "POL-1006",
        "customer_id": "CUST-006",
        "claim_type": "glass",
        "damage_amount": 540.0,
        "description": "Cracked windshield on Tesla Model 3.",
        "risk_level": "low",
        "risk_score": 0.21,
        "risk_reasons": ["Claim amount is below $1,000."],
        "status": "approved",
        "resolution": "Auto-approved low-risk glass claim.",
        "notification_sent": True,
        "created_at": now_iso(-5),
        "updated_at": now_iso(-5),
    },
]


# -----------------------------
# Optional supporting records
# -----------------------------
# These make the Data tab more interesting if you select notifications.

NOTIFICATIONS = [
    {
        "notification_id": "NTF-9010",
        "claim_id": "CLM-9010",
        "customer_id": "CUST-002",
        "recipient_email_redacted": "ma***@example.com",
        "message": "Your claim CLM-9010 was approved as a low-risk glass claim.",
        "created_at": now_iso(-30),
    },
    {
        "notification_id": "NTF-9011",
        "claim_id": "CLM-9011",
        "customer_id": "CUST-003",
        "recipient_email_redacted": "ca***@example.com",
        "message": "Your claim CLM-9011 was approved as a low-risk collision claim.",
        "created_at": now_iso(-28),
    },
    {
        "notification_id": "NTF-9019",
        "claim_id": "CLM-9019",
        "customer_id": "CUST-004",
        "recipient_email_redacted": "av***@example.com",
        "message": "Your claim CLM-9019 was denied after human review.",
        "created_at": now_iso(-8),
    },
]


# -----------------------------
# Seeder
# -----------------------------

def ensure_indexes(db) -> None:
    # customers — lookup by customer_id
    db.customers.create_index(
        [("customer_id", ASCENDING)],
        unique=True,
        name="customer_id_unique",
    )

    # policies — lookup by policy_number; list by customer
    db.policies.create_index(
        [("policy_number", ASCENDING)],
        unique=True,
        name="policy_number_unique",
    )
    db.policies.create_index(
        [("customer_id", ASCENDING), ("created_at", DESCENDING)],
        name="policy_customer_created",
    )

    # claims — lookup/update by claim_id; list by customer; filter by status
    db.claims.create_index(
        [("claim_id", ASCENDING)],
        unique=True,
        name="claim_id_unique",
    )
    db.claims.create_index(
        [("customer_id", ASCENDING), ("created_at", DESCENDING)],
        name="claim_customer_created",
    )
    db.claims.create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)],
        name="claim_status_created",
    )


def upsert_many(collection, key_field, docs):
    inserted = 0
    updated = 0

    for doc in docs:
        result = collection.update_one(
            {key_field: doc[key_field]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += result.modified_count

    return inserted, updated


def main():
    if not MONGODB_URI or MONGODB_URI.startswith("PASTE_"):
        raise SystemExit("Paste your MongoDB Atlas URI into MONGODB_URI before running.")

    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    ensure_indexes(db)

    customer_inserted, customer_updated = upsert_many(db.customers, "customer_id", CUSTOMERS)
    claim_inserted, claim_updated = upsert_many(db.claims, "claim_id", CLAIMS)
    notification_inserted, notification_updated = upsert_many(db.notifications, "notification_id", NOTIFICATIONS)

    print("Done seeding additional demo data.")
    print(f"Customers inserted:     {customer_inserted}")
    print(f"Customers updated:      {customer_updated}")
    print(f"Claims inserted:        {claim_inserted}")
    print(f"Claims updated:         {claim_updated}")
    print(f"Notifications inserted: {notification_inserted}")
    print(f"Notifications updated:  {notification_updated}")
    print()
    print("Indexes ensured:")
    print("  customers:  customer_id (unique)")
    print("  policies:   policy_number (unique), customer_id + created_at")
    print("  claims:     claim_id (unique), customer_id + created_at, status + created_at")
    print()
    print("Policy count was not changed by this script.")
    print(f"Database: {MONGODB_DB}")


if __name__ == "__main__":
    main()
