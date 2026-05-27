<p align="center">
  <img src="magenta.png" alt="Magenta leaf logo" width="110" />
</p>

<h1 align="center">🛡️ Magenta Insurance Agent</h1>

<p align="center">
  <strong>An agentic insurance workflow powered by VoyageAI, OpenAI + MongoDB Atlas</strong><br />
  Policy lookup, quotes, claims, risk scoring, human review, notifications, and vector-ready memory — all in one demo. 🚗💥📄
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img alt="MongoDB Atlas" src="https://img.shields.io/badge/MongoDB%20Atlas-System%20of%20Record-00ED64?style=for-the-badge&logo=mongodb&logoColor=white" />
  <img alt="OpenAI" src="https://img.shields.io/badge/OpenAI-Agent%20Reasoning-412991?style=for-the-badge&logo=openai&logoColor=white" />
</p>

---

## 🚀 What This Is

**Magenta Insurance Agent** is a Streamlit demo that shows how an LLM becomes more than a chatbot when it can safely act on real operational data.

The app demonstrates an insurance assistant that can:

- 🧑‍💼 look up customers and policies
- 💬 answer insurance questions conversationally
- 🧾 generate auto insurance quotes
- 🛡️ create policies
- 🚗 file claims
- 📊 analyze claim risk
- ✅ auto-approve low-risk claims
- 🧑‍⚖️ route high-risk claims to human review
- 🔔 log claim resolution notifications
- 🧠 store vector embeddings directly on claim records
- 🍃 show how MongoDB Atlas can act as operational store, memory layer, workflow state, audit trail, and semantic retrieval foundation

The key idea:

> **The LLM is the conversational interface. MongoDB Atlas is the durable system of record, workflow state store, memory layer, audit trail, and vector retrieval layer.**

---

## 🍃 Why MongoDB Atlas Matters Here

This is not just a chat UI wrapped around an LLM.

MongoDB Atlas stores the real business state:

| Collection | Purpose |
|---|---|
| `customers` | Customer profiles, prospects, loyalty metadata |
| `policies` | Active policy records and coverage information |
| `claims` | Filed claims, risk scores, statuses, workflow state, embeddings |
| `quotes` | Generated quote records |
| `claim_reviews` | Human adjuster decisions and notes |
| `notifications` | Logged customer notification events |

The agent retrieves facts from Atlas, writes new workflow records to Atlas, and uses Atlas state to resume or inspect workflows later.

That means a claim is not just something the assistant says happened. It is an actual durable document in MongoDB.

```json
{
  "claim_id": "CLM-9017",
  "policy_number": "POL-1003",
  "claim_type": "theft",
  "damage_amount": 26500.0,
  "risk_level": "high",
  "risk_score": 0.91,
  "status": "pending_human_review",
  "next_step": "resolve_claim"
}
```

That is the difference between a chatbot and an agentic workflow. 🧠➡️⚙️➡️🍃

---

## 🤖 What Makes It Agentic?

A basic chatbot generates text.

This app lets the model choose from approved backend tools and then lets Python perform the real action against MongoDB Atlas.

```text
Customer message
→ OpenAI interprets intent
→ Agent selects an approved business tool
→ Python executes the tool
→ MongoDB Atlas is read or updated
→ Result goes back to the model
→ Customer receives a grounded response
```

The agent has controlled tools such as:

- 🔎 `lookup_policy`
- 📋 `list_customer_policies`
- 💸 `get_quote`
- 🛡️ `create_policy`
- 🚗 `file_claim`
- 📊 `analyze_claim_risk`
- 🧾 `check_claim_status`
- 📚 `list_customer_claims`
- ⏸️ `list_pending_claims`

The LLM can reason about what to do, but the backend controls what is allowed to happen. That keeps the demo grounded, auditable, and explainable.

---

## 🧱 Architecture

```text
┌──────────────────────────────┐
│        Streamlit UI           │
│  Chat · Human Review · Data   │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│       OpenAI Chat Model       │
│ Intent + tool selection       │
└───────────────┬──────────────┘
                │ function call
                ▼
┌──────────────────────────────┐
│      Python Business Tools    │
│ policy · quote · claim · risk │
└───────────────┬──────────────┘
                │ read/write
                ▼
┌──────────────────────────────┐
│        MongoDB Atlas          │
│ operational data + memory     │
│ workflow state + audit trail  │
│ vectors for semantic search   │
└──────────────────────────────┘
```

---

## 🧭 App Views

### 💬 Agent Chat

The customer-facing insurance assistant.

Try asking:

```text
Look up policy POL-1001
```

```text
List claims for customer CUST-003
```

```text
File a glass claim for POL-1002 for $310. Small windshield chip caused by highway debris.
```

```text
What is the status of claim CLM-9017?
```

---

### 🧑‍⚖️ Human Review Queue

High-risk or medium-risk claims can be routed to human review.

An adjuster can:

- inspect risk score and risk reasons 📊
- review claim details 🧾
- approve the claim ✅
- deny the claim ❌
- write reviewer notes 📝

The app then writes a review record and logs a notification.

This gives the demo a business-state version of:

```text
SUSPEND → HUMAN REVIEW → RESUME
```

The workflow state is persisted in MongoDB Atlas, not trapped inside a chat session.

---

### 🍃 Atlas Data View

The Data tab exposes live MongoDB collections inside the demo:

- customers
- policies
- claims
- quotes
- claim_reviews
- notifications

This is useful for showing that agent actions create real durable records.

---

## 🚗 Claims Workflow

```text
Customer files claim
        │
        ▼
file_claim creates claim document in Atlas
        │
        ▼
analyze_claim_risk scores claim
        │
        ├── Low risk
        │      ├── auto-approve
        │      ├── log notification
        │      └── complete ✅
        │
        └── Medium / High risk
               ├── mark pending_human_review
               ├── wait for adjuster
               ├── approve or deny
               ├── write claim_reviews record
               ├── log notification
               └── complete 🧑‍⚖️
```

Example pending review claim:

```json
{
  "claim_id": "CLM-9017",
  "policy_number": "POL-1003",
  "claim_type": "theft",
  "damage_amount": 26500.0,
  "risk_level": "high",
  "risk_score": 0.91,
  "risk_reasons": [
    "Claim amount exceeds $5,000.",
    "Theft claims require verification.",
    "High-value vehicle exposure."
  ],
  "status": "pending_human_review",
  "next_step": "resolve_claim"
}
```

---

## 🧠 Vector-Ready Memory with Voyage AI

The project can enrich claim documents with Voyage AI embeddings.

Each embedded claim gets fields like:

```text
embedding_text
embedding
embedding_model
embedding_dimensions
embedding_created_at
```

That means operational data and semantic retrieval data live together:

```text
claims
├── claim_id
├── policy_number
├── customer_id
├── claim_type
├── damage_amount
├── description
├── risk_level
├── status
├── resolution
├── embedding_text
├── embedding
├── embedding_model
├── embedding_dimensions
└── embedding_created_at
```

This enables a strong MongoDB Atlas story:

> **Atlas is not just storing app data. It is also storing the vectors that let the agent retrieve semantically similar claims, prior review decisions, claim notes, risk patterns, and customer history.**

In production, this pattern can expand to include:

- 📄 policy language
- 🧑‍⚖️ adjuster notes
- 🛠️ repair estimates
- 📜 claim-handling guidelines
- 🧾 customer communication history
- 🧠 conversation summaries

---

## 🔎 Atlas Vector Search Index

After embeddings are written to the `claims` collection, create an Atlas Vector Search index on the `embedding` field.

Suggested index name:

```text
claim_vector_index
```

Suggested index definition:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    }
  ]
}
```

---

## 🧰 Project Files

Typical local files:

```text
app.py                         # Streamlit insurance agent app
seeder.py                      # Adds richer customers, claims, notifications
embedder.py                    # Adds Voyage embeddings to claims
magenta.png                    # Pink Magenta leaf logo
README.md                      # This file
```

---

## ⚙️ Setup

This demo is intentionally simple and Python 3.10-friendly.

Install dependencies:

```bash
python3 -m pip install streamlit pymongo openai==0.28.1 voyageai python-dotenv
```

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```text
MONGODB_URI=<your Atlas connection string>
MONGODB_DB=magenta_insurance_demo
OPENAI_API_KEY=<your OpenAI key>
OPENAI_MODEL=gpt-4.1
VOYAGE_API_KEY=<your Voyage AI key>   # only needed for embedder.py
```

Run the app:

```bash
streamlit run app.py
```

---

## 🌱 Seed More Demo Data

The app includes a small base seed option. For a richer demo dataset, run:

```bash
python3 seeder.py
```

The expanded dataset includes:

- 14 customers / prospects 🧑‍💼
- 7 policies 🛡️
- 19 claims 🚗
- approved, denied, and pending-review states ✅❌⏸️
- low, medium, and high-risk cases 📊
- notification records 🔔

The seeder uses upserts, so it can be run multiple times without duplicating the known records.

---

## 🧬 Add Claim Embeddings

To add Voyage embeddings to the existing `claims` collection:

```bash
python3 embedder.py
```

Make sure `MONGODB_URI`, `MONGODB_DB`, and `VOYAGE_API_KEY` are set in your `.env` file, then run:

```bash
python3 embedder.py
```

The script updates existing claim documents and does not create new policies or claims.

---

## 🎬 Recommended Demo Flow

### 1. Show the Dashboard 📊

Point out the counts:

- customers
- policies
- claims
- pending review

Explain:

> This is backed by MongoDB Atlas, not a static mockup.

---

### 2. Show Policies in the Data Tab 🛡️

Open the `policies` collection.

Explain:

> The model does not memorize policies. It calls a backend tool that reads them from Atlas.

---

### 3. Look Up a Policy 🔎

Ask the chat:

```text
Look up policy POL-1003
```

Explain:

> Natural language becomes a controlled policy lookup tool call.

---

### 4. Show Claim History 📚

Ask:

```text
List claims for customer CUST-003
```

Explain:

> Atlas gives the agent durable memory of customer history.

---

### 5. File a Low-Risk Claim ✅

Ask:

```text
File a glass claim for POL-1002 for $310. Small windshield chip caused by highway debris.
```

Explain:

> The app creates a real claim document, scores it, auto-approves it, and logs a notification.

---

### 6. Show Human Review 🧑‍⚖️

Use a seeded claim such as:

```text
CLM-9017
```

Show:

```text
status: pending_human_review
next_step: resolve_claim
risk_level: high
risk_score: 0.91
```

Approve it in the Human Review tab.

Explain:

> This is the human-in-the-loop workflow. The adjuster decision updates Atlas, writes an audit record, and logs a notification.

---

### 7. Confirm the Status 🔁

Ask:

```text
What is the status of claim CLM-9017?
```

Explain:

> The agent can report the updated state because Atlas is the source of truth.

---

### 8. Show Vectors in Atlas 🍃🧠

Open a claim document in Atlas or Compass and show:

```text
embedding_text
embedding
embedding_model
embedding_dimensions
```

Explain:

> The operational claim and its vector live together. Atlas can power both workflow state and semantic retrieval.

---

## 💬 Executive Summary

This demo shows an insurance workflow where an LLM is connected to real operational data and controlled business tools.

It demonstrates:

- 🤖 agentic tool calling
- 🍃 MongoDB Atlas as durable memory and system of record
- 🚗 claim filing and risk analysis
- 🧑‍⚖️ human-in-the-loop review
- 🔔 notification logging
- 🧾 auditability
- 🧠 vector-ready claim memory
- 🔎 Atlas Vector Search readiness

The punchline:

> **This is not a chatbot. It is an agentic application where MongoDB Atlas stores the business truth, workflow state, audit trail, and semantic memory.**

---

## 🧡 Demo Sound Bites

Use these when explaining the project:

- 🍃 **“The LLM is the interface. MongoDB Atlas is the memory.”**
- 🛡️ **“Policy data comes from Atlas, not the model’s imagination.”**
- 🚗 **“Filing a claim creates a real durable document.”**
- 🧑‍⚖️ **“Human review is just workflow state in Atlas.”**
- 🧠 **“The vectors live next to the operational data.”**
- 🔎 **“Atlas can be the system of record and the retrieval layer.”**
- 🤖 **“This is an agent because it acts, persists state, and resumes workflows.”**

---

## 🏁 Final Takeaway

Insurance is a perfect demo domain because it has everything enterprise agents need:

- customers 🧑‍💼
- policies 🛡️
- regulated decisions ⚖️
- claims 🚗
- risk scoring 📊
- human review 🧑‍⚖️
- notifications 🔔
- auditability 🧾
- memory 🧠
- semantic search 🔎

This project shows how those pieces come together with:

```text
OpenAI + Python tools + Streamlit + MongoDB Atlas + Voyage embeddings
```

🍃 Built to show how MongoDB makes agents durable, grounded, auditable, and useful.
