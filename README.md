
# ⚙️ Installation Steps
   1. Start the Backend Server (FastAPI)
      Navigate to the backend directory:

      ```bash
      cd backend
      Build a virtual environment and install requirements:

      ```bash
      python -m venv venv
      source venv/bin/activate  # On Windows use `venv\Scripts\activate`
      pip install -r requirements.txt
      Run the uvicorn development server:

      ```bash
      uvicorn main:app --port 10000 --reload
   2. Start the Frontend App (Next.js)
   Navigate to the frontend directory:

   ```bash
   cd ../frontend
   Install npm packages:

   ```bash
   npm install
   Run the Next.js development server:

   ```bash
   npm run dev
   Access the application in your browser at http://localhost:3000.```

   3. Production Deployment Notes
   Frontend (Vercel): Deploy /frontend directly. Add environment variables under project settings.

   Backend (Render): Create a Python Web Service pointing to your repo.

   Build Command: pip install -r backend/requirements.txt

   Start Command: uvicorn backend.main:app --host 0.0.0.0 --port 10000

   Set CHROMA_PERSIST_DIRECTORY=/opt/render/project/src/chroma_db for persistent storage and whitelist 0.0.0.0/0 on MongoDB Atlas.


# 🔮 Future Improvements

[ ] Automated Mail Dispatch: Direct integration with email clients and speed-post APIs to send dispute letters to insurance ombudsmen instantly from the dashboard.

[ ] OCR Upgrade for Handwritten Bills: Integration of advanced vision models (like multimodal Llama/GPT models) to parse poorly scanned or handwritten doctor prescriptions and bills accurately.

[ ] Anonymized Analytics Ledger: A public dashboard analyzing common insurance rejection patterns by specific companies to empower consumer forums and policymakers.


# 🏗️ Architecture Design

System Workflow
ClaimSure operates via a state-of-the-art Multi-Agent AI system orchestration framework. The state flows sequentially or conditionally across specialized nodes to resolve medical queries and process multi-document insurance audits.

                                  [Patient Inputs]
                                         │
                        ┌────────────────┴────────────────┐
                        ▼                                 ▼
              [Symptom Intake Agent]         [Insurance Policy Analyzer]
                        │                                 │
                        ▼                                 ▼
            [Medical Knowledge RAG]           [Multi-Document RAG Agent]
                        │                                 │
                        └────────────────┬────────────────┘
                                         ▼
                           [Clause Mismatch Detective]
                                         │
                                         ▼
                            [Dispute Letter Generator]


Complete Folder Structure:
claimsure/
├── frontend/                          # Next.js app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Landing page
│   │   ├── auth/
│   │   │   ├── login/page.tsx
│   │   │   └── signup/page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx               # User case history
│   │   ├── triage/
│   │   │   └── page.tsx               # Symptom checker
│   │   ├── coverage-check/
│   │   │   └── page.tsx               # Pre-visit coverage check
│   │   └── dispute/
│   │       ├── page.tsx               # Upload + analyze
│   │       └── result/page.tsx        # Dispute result + letter
│   ├── components/
│   │   ├── ui/                        # Reusable UI components
│   │   ├── TriageChat.tsx
│   │   ├── DocumentUpload.tsx
│   │   ├── ClaimResult.tsx
│   │   ├── DisputeLetter.tsx
│   │   └── Navbar.tsx
│   ├── lib/
│   │   ├── supabase.ts
│   │   └── api.ts                     # Backend API calls
│   ├── .env.local
│   └── package.json
│
├── backend/                           # FastAPI app
│   ├── main.py                        # FastAPI entry point
│   ├── requirements.txt
│   ├── .env
│   ├── routers/
│   │   ├── triage.py                  # POST /triage/analyze
│   │   ├── documents.py               # GET /dashboard/cases
│   │   ├── coverage.py                # POST /coverage/check
│   │   └── dispute.py                 # POST /dispute/analyze
│   ├── services/
│   │   ├── groq_service.py            # All Groq LLM calls
│   │   ├── rag_service.py             # ChromaDB + embedding logic
│   │   ├── document_service.py        # PDF parsing + chunking
│   │   ├── dispute_agent.py           # LangGraph agent
│   │   └── evaluation_service.py      # RAGAS scoring
│   ├── models/
│   │   ├── schemas.py                 # Pydantic request/response models
│   │   └── database.py                # MongoDB client
│   └── utils/
│       ├── pdf_parser.py              # Extract text from PDFs
│       └── chunker.py                 # Smart text chunking
│
└── README.md


# ✨ Key Features
Module 1: Medical Triage Engine: Analyzes patient symptoms in natural language, determines urgency levels (Emergency, Urgent, Routine, Home Care), and provides localized medical guidance.

Module 2: Pre-Visit Insurance Claim Intelligence: Uses Retrieval-Augmented Generation (RAG) to read 50–100 page insurance policies, extract coverage details, and identify exclusions before a hospital visit.

Module 3: Dispute Resolution Engine: Simultaneously audits three distinct documents (Policy + Hospital Bill + Doctor's Report) to pinpoint misapplied clauses, generate a dispute success probability score, and auto-create professional appeal letters in 30 seconds.

Multilingual Capability: Offers a real-world market advantage in India with interface support for Hindi, Tamil, and Telugu to break down complex insurance jargon.

Citation Grounding: Eradicates LLM hallucinations by tracing every generated claim back to the exact text in the policy, bill, or medical report.


# 🔧 Environmental Variables
To run this application locally or in production, configure the following credentials:

1. Frontend Configuration (frontend/.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_public_key
NEXT_PUBLIC_BACKEND_URL=http://localhost:10000
(If left blank, the frontend runs a seamless LocalStorage-based Mock Auth mode, enabling testing without immediate credentials).
```

2. Backend Configuration (backend/.env)
```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_secret_key
MONGODB_URI=your_mongodb_connection_uri
MONGODB_DB_NAME=claimsure
CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# LangSmith Tracing Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=claimsure
```

# 📺 Demo Link
🎥 Walkthrough Video: 
https://drive.google.com/file/d/1nNXqFeV8DKVORkGLHoCPvlyRjGbzJ4DH/view?usp=sharing

# 🚀 Tech Stack
Frontend: Next.js 14 (App Router) + Tailwind CSS + Lucide Icons + Supabase Auth

Backend: FastAPI (Python)

Vector Database: ChromaDB (locally persisted)

Database: MongoDB Atlas (async operations via Motor)

Auth: Supabase Auth (JWT session checking)

LLM: Groq API (llama-3.3-70b-versatile)

Embeddings: sentence-transformers (all-MiniLM-L6-v2)

AI Agent Workflow: LangGraph (6-node claims auditing state graph)

LLM Evaluation: RAGAS (faithfulness and answer relevancy metrics)


# 📊 Evaluation
The /evaluate endpoint computes factual consistency and answer quality for your RAG checks using RAGAS metrics:

Endpoint: POST http://localhost:10000/evaluate

Request Format:

```json
{
  "question": "Is outpatient therapy covered?",
  "answer": "Yes, outpatient physical therapy is covered up to 20 visits per calendar year under Section 4.",
  "contexts": [
    "Section 4.1: Outpatient physical therapy services are covered. Limits: 20 visits/year."
  ]
}
```

Response:

```json
{
  "faithfulness": 0.98,
  "answer_relevancy": 0.95
}
```

# ⚡ Challenges Overcome
Multi-Document Cross-Referencing: Traditional RAG architectures query a single type of document. Overcoming the complexity of instructing an LLM to dynamically correlate data across isolated formats (the legal jargon of policy files, tabular hospital invoice items, and free-form medical notes) required building a custom state machine utilizing LangGraph.

Hallucination Prevention in Legal Contexts: To protect patients from generating invalid legal appeals, a rigid grounding system was implemented. The system relies on isolated vector lookups with precise context injection, combined with a dedicated "Clause Mismatch" validation node that drops unverified data.


# 🛠️ How It Works
LangGraph Claims Agent Workflow
The Dispute Resolution feature runs a stateful LangGraph agent through these 6 distinct nodes:

parse_documents: Parses raw policy, bill, and medical report PDFs, runs word-based overlap chunking, and embeds them into the user's isolated ChromaDB instance.

extract_claim_info: Runs a vector search to locate treatment details, charges, and denial reasons, calling Groq to extract structured fields.

find_policy_clauses: Queries ChromaDB for specific insurance policy rules corresponding to the patient's procedures.

detect_mismatches: Assesses whether the rejection aligns with the policy or is a misapplied coverage term.

score_dispute: Scores the dispute from 0-100 and classifies standing strength as weak, moderate, or strong.

generate_letter: Formulates a formal medical claim appeal letter citing medical codes, bills, and policy sections, appended with an AI disclaimer.


# 👤 Author Info
Sowmya sri Vemuri - https://github.com/sowmyasri1310

Project Link: https://github.com/sowmyasri1310/ClaimSure

# ClaimSure — Medical Insurance Claim Dispute Resolver with Healthcare Triage
ClaimSure is a production-ready, full-stack AI-powered medical insurance assistant designed to help patients manage health symptoms, verify policy coverages, audit claims, and draft dispute letters.

# 📋 Problem Statement
In India’s healthcare ecosystem, middle-income families face a crushing financial and operational burden due to a fragmented journey between medical distress and insurance settlement. Every year, approximately 40 million insurance claims are rejected, with an estimated 20%—amounting to over ₹1,000 Crores in denied capital—being wrongfully rejected due to misapplied clauses or administrative oversight. Patients are fundamentally blind to their coverage because insurance policies consist of 50 to 100 pages of dense legal jargon, leaving them unable to predict claim viability before a hospital visit or identify invalid exclusions. Consequently, unexpected out-of-pocket expenses force families into sudden financial distress.

This issue is compounded by a lack of structured, localized medical guidance, which causes patients to misjudge symptom urgency—either overwhelming emergency rooms or delaying critical care. When a wrongful rejection does occur, patients lack the legal expertise, time, and multi-document reasoning required to audit medical bills against policy clauses and draft formal appeals. This manual dispute process is too slow and complex for the average citizen, allowing insurance companies to default on valid payouts while patients suffer the financial consequences silently.

