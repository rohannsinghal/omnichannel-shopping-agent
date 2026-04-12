# 🌿 GlowBot — AI-Powered Omnichannel Shopping Agent

> A production-grade skincare retail platform combining a vanilla HTML/JS e-commerce storefront with a LangGraph **Plan-and-Execute** AI agent, fine-tuned dermatology SLM, and PyTorch computer vision — all backed by a multi-database architecture.

---

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-000000?style=for-the-badge&logo=langchain&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)

---

## 📖 Overview

GlowBot is a full-stack **omnichannel retail agent** for a skincare brand. It pairs a traditional e-commerce UI (browse, cart, checkout, wishlists, order tracking) with an embedded AI consultant that can:

- Analyze a user's uploaded selfie with a **PyTorch MobileNetV2 model** to detect their skin type
- Consult a **fine-tuned dermatology SLM** (`rohannsinghal/skin-master-lora`) for expert skincare advice
- Search a **ChromaDB vector catalog** with semantic embeddings to find relevant products
- Query **live PostgreSQL inventory** to confirm stock before recommending a product
- Add items to cart, apply loyalty points, and trigger checkout — all via natural language
- Look up order status and tracking links from the database
- Find the nearest physical store using GPS-based Haversine distance queries

The agent is **not a simple chatbot**. It is a full **Plan-and-Execute graph** where a planner LLM decomposes the user's request, an executor dispatches real tool calls one at a time, and a re-planner self-heals or terminates based on observed outcomes.

---

## ✨ Key Features

- **AI Skincare Consultant** — GlowBot is embedded on every page as a floating chat widget, capable of answering dermatology questions, recommending products, and completing transactions entirely through conversation.
- **Plan-and-Execute Agent Architecture** — A multi-node LangGraph `StateGraph` with a dedicated Planner, Executor, and Re-Planner node. The graph loops until all tasks are completed or a terminal response is produced.
- **Self-Healing Re-Planner** — The re-planner node uses structured Pydantic output to either issue a final response or generate a revised plan. It is explicitly forbidden from collapsing mixed results (e.g., stock found / cart failed) into a single failure message.
- **Computer Vision Skin Analysis** — Users can upload a photo; the agent automatically routes to a TorchScript-traced MobileNetV2 classifier that detects one of five skin types (Oily, Dry, Combination, Normal, Sensitive) and uses the result to personalize product searches.
- **Fine-Tuned Dermatology Expert** — Complex skincare questions are delegated to a LoRA-fine-tuned SLM hosted on a Hugging Face Space via the Gradio API, providing medically-grounded responses beyond the capability of a general-purpose LLM.
- **Resilient Dual Embedding Strategy** — The semantic product catalog search has a primary path (dedicated HuggingFace Inference Endpoint with `llama-nemotron-embed-8b`) and an automatic silent fallback (free `BAAI/bge-large-en-v1.5` API + separate ChromaDB collection), requiring zero manual intervention.
- **Decoupled Frontend State Management** — Cart contents and authentication sessions are managed entirely via `localStorage`, completely decoupled from the database. This eliminates UI blocking and prevents Supabase connection timeouts during live demos where the backend may be cold.
- **Live Demo Resilience (Mock AI Fallback)** — The frontend intercepts all network failures to the FastAPI backend and seamlessly falls back to a built-in mock AI response, ensuring the chatbot UI never shows an error during demos — even when the server is unreachable.
- **Persistent Conversational Memory** — Agent state (messages, plans, past steps) is checkpointed to PostgreSQL via LangGraph's `PostgresSaver` after every node execution, keyed by the customer's phone number. Sessions are fully resumable across process restarts.
- **Multi-Model Strategy** — Three separate Groq-hosted LLMs are used for different roles: a 120B model for deep planning and self-healing decisions, and a 70B model for reliable tool-call dispatch — tuned to avoid free-tier rate limits.
- **Full E-Commerce UI** — Six HTML pages (Home, Shop, Product Detail, Cart, Checkout, Order Tracking, Account, Wishlist) built with Tailwind CSS and vanilla JavaScript.

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (HTML / JS)                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Shop    │  │  Cart    │  │ Checkout │  │  Account   │  │
│  │  Pages   │  │ (localStorage) │   Pages  │  │  Pages   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            GlowBot Chat Widget (JS)                   │   │
│  │   POST /chat  ──────────────────────►  FastAPI        │   │
│  │   (on error)  ──► Mock AI Fallback                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                    POST /chat (JSON)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (api.py)                          │
│                                                              │
│  Lifespan: psycopg3 conn → PostgresSaver → build_graph()    │
│  CORS: allow_origins=["*"]                                   │
│  Routes: /health  /chat  /api/register  /api/add-to-cart     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Plan-and-Execute Agent                │
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌────────────────────┐    │
│   │ Planner  │───►│ Executor │───►│    Re-Planner       │   │
│   │ (120B)   │    │  (70B)   │    │      (120B)         │   │
│   └──────────┘    └────┬─────┘    └────────┬───────────┘    │
│        ▲               │                   │                 │
│        └───────────────┘◄──────────────────┘                │
│              Loop until plan complete                        │
└───────────────────────┬─────────────────────────────────────┘
                        │  Tool Calls
          ┌─────────────┼──────────────────────┐
          ▼             ▼                       ▼
   ┌─────────────┐  ┌──────────────┐   ┌──────────────────┐
   │  ChromaDB   │  │  Supabase    │   │  HuggingFace     │
   │  (vectors)  │  │  PostgreSQL  │   │  Spaces/API      │
   └─────────────┘  └──────────────┘   └──────────────────┘
                                        (Skin Master SLM +
                                         Skin Vision Model)
```

### LangGraph Node Flow

The agent follows a **Plan-and-Execute** pattern with a self-healing loop:

**Planner Node** — Takes the full conversation history and generates an ordered `List[str]` of single-action tasks using Pydantic structured output (validated, never a raw JSON blob).

**Executor Node** — Pops the first task from the plan, binds the full tool list to a 70B LLM via `.bind_tools()`, dispatches the correct tool via a manual `TOOL_MAP`, and records the `(task, observation)` pair in `past_steps`. One tool call per invocation — no nested graphs, no recursion.

**Re-Planner Node** — Inspects all `past_steps` and the original goal. Uses structured Pydantic output (`ReplannerOutput`) to choose between: (a) emitting a final `response` string to terminate, or (b) issuing a revised `Plan` to loop back to the Executor. A hardened system prompt prevents the model from collapsing mixed results into a single failure statement.

### Frontend State Management

Cart and authentication data are stored in `localStorage` and never written to the database during normal browsing. This design choice was deliberate:

- **No blocking UI** — adding to cart is instantaneous; no network round-trip required.
- **No connection pool pressure** — Supabase's free-tier connection limit is not exhausted by passive browsing.
- **Demo resilience** — the storefront is fully functional even when the backend is down.

Database writes only occur at two explicit points: **account registration** (POST `/api/register`) and **checkout** (POST `/api/checkout`), where transactional integrity is actually required.

### Embedding Resilience

The `search_chroma_products` tool implements a two-path strategy with automatic silent failover:

| Path | Model | ChromaDB Collection | Trigger |
|------|-------|-------------------|---------|
| Primary | `llama-nemotron-embed-8b` (dedicated HF endpoint) | `tbs_cloud_vectors` | Default |
| Fallback | `BAAI/bge-large-en-v1.5` (free HF public API) | `tbs_bge_vectors` | Any exception on primary |

The fallback activates on any exception — credit exhaustion, cold start, timeout — and requires no manual intervention.

### Database Schema

| Database | Tables / Collections | Purpose |
|----------|---------------------|---------|
| **Supabase PostgreSQL** | `customers`, `orders`, `inventory`, `stores`, `shopping_cart`, `wishlist` | Core transactional data |
| **Supabase PostgreSQL** | `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` | LangGraph `PostgresSaver` memory |
| **MongoDB** | `products` (51 docs) | Rich product data with `ai_search_data` fields for embedding |
| **ChromaDB Cloud** | `tbs_cloud_vectors`, `tbs_bge_vectors` | Semantic product search vectors |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI Agent | LangGraph (StateGraph), LangChain Core |
| LLM Provider | Groq (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`) |
| Computer Vision | PyTorch, MobileNetV2 (TorchScript), Pillow |
| Dermatology SLM | LoRA fine-tuned model via Hugging Face Spaces (Gradio) |
| Vector Search | ChromaDB Cloud, HuggingFace Endpoint Embeddings |
| Primary Database | Supabase (PostgreSQL), psycopg2, psycopg3 |
| Document Store | MongoDB Atlas |
| Memory / Checkpoints | LangGraph `PostgresSaver` (Supabase) |

---

## ⚙️ Local Setup

### Prerequisites

- Python 3.11+
- A Supabase project with the schema described above
- A Groq API key (free tier sufficient for development)
- A HuggingFace account and API token
- MongoDB Atlas connection string (optional — for product document store)
- ChromaDB Cloud credentials

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/omnichannel-agent.git
cd omnichannel-agent
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# ── Groq ──────────────────────────────────────────────────
GROQ_API_KEY=your_groq_api_key_here

# ── Supabase / PostgreSQL ──────────────────────────────────
# Use the Session Mode URI (port 5432) — NOT the pooler (6543)
# The agent handles prepare_threshold=0 internally for pgbouncer compatibility
POSTGRES_URI=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

# ── HuggingFace ────────────────────────────────────────────
HF_TOKEN=hf_your_token_here
HUGGINGFACEHUB_API_TOKEN=hf_your_token_here

# Primary embedding endpoint (optional — fallback activates automatically)
HF_ENDPOINT_URL=https://your-dedicated-endpoint.huggingface.cloud

# ── ChromaDB Cloud ─────────────────────────────────────────
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_tenant_id
CHROMA_DATABASE=your_database_name

# ── MongoDB Atlas (optional) ───────────────────────────────
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/omnichannel_db
```

> **Note on `POSTGRES_URI`:** Supabase's pgbouncer pooler (port `6543`) does not support server-side prepared statements. The agent works around this automatically using `prepare_threshold=0` on the psycopg3 connection, but you must use the correct URI. If you see `"prepared statement already exists"` errors, switch to the direct connection URI (port `5432`).

### 5. (Optional) Build the Fallback Embedding Collection

If your dedicated HuggingFace endpoint is unavailable, run this once to create the free fallback vector collection:

```bash
python embed_catalog_free.py
```

This populates the `tbs_bge_vectors` ChromaDB collection using the free `BAAI/bge-large-en-v1.5` model. After this, the agent will automatically fall back to it whenever the primary endpoint fails.

### 6. Start the API Server

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

On startup you should see:

```
✅  Checkpoint store ready (Supabase Postgres).
✅  LangGraph compiled with PostgresSaver checkpointer.
INFO:     Application startup complete.
```

### 7. Open the Frontend

Open `index.html` in your browser directly (no build step required):

```bash
open index.html       # macOS
# or simply double-click index.html in your file explorer
```

The GlowBot chat widget will appear on every page. If the backend is not running, the widget automatically switches to the built-in Mock AI so the UI remains functional.

### 8. (Optional) Run the CLI Agent

For a terminal-based session with the agent (useful for debugging tool calls):

```bash
python agent.py
```

You will be prompted for a phone number, which scopes the PostgreSQL checkpoint session. Returning with the same number resumes the previous conversation.

---

## 📂 Project Structure

```
omnichannel-agent/
│
├── 🤖 Core Agent
│   ├── agent.py                    # LangGraph Plan-and-Execute StateGraph
│   ├── api.py                      # FastAPI server + lifespan manager
│   ├── vision.py                   # PyTorch MobileNetV2 skin classifier
│   └── best_skin_model.pth         # Trained MobileNetV2 weights
│
├── 🛠️ Agent Tools
│   ├── tools_catalog.py            # ChromaDB semantic search (dual-path embedding)
│   ├── tools_inventory.py          # PostgreSQL real-time stock check
│   ├── tools_commerce.py           # Cart, checkout, loyalty points
│   ├── tools_customer_care.py      # Order status lookup
│   ├── tools_store.py              # GPS-based Haversine store locator
│   ├── tools_skin_master.py        # Dermatology SLM via HF Spaces (Gradio)
│   └── tools_vision.py             # Skin type vision model inference
│
├── 🌐 Frontend
│   ├── index.html                  # Home page
│   ├── shop.html                   # Product listing
│   ├── product.html                # Product detail
│   ├── cart.html                   # Shopping cart (localStorage-backed)
│   ├── checkout.html               # Checkout flow
│   ├── order.html                  # Order tracking
│   ├── account.html                # Login / registration
│   ├── wishlist.html               # Wishlist
│   └── debug_collection.html       # ChromaDB debug utility
│
├── 🗄️ Data & Embeddings
│   ├── build_vector_store_hf.py    # Builds primary ChromaDB collection (nemotron)
│   ├── embed_catalog_free.py       # Builds fallback ChromaDB collection (bge-large)
│   ├── load_tbs_products.py        # Loads product catalog into MongoDB
│   ├── mongo_to_postgres.py        # Syncs MongoDB products → PostgreSQL inventory
│   ├── tbs_products.json           # Raw product catalog data
│   └── merged_skin_data.jsonl      # Merged dermatology training data
│
├── 🧠 ML / Model Training
│   ├── skin_master_lora/           # LoRA fine-tuning artifacts
│   ├── skin_master_lora.zip        # Packaged LoRA weights for HF Space deployment
│   ├── model dataset/              # Skin type image classification dataset
│   ├── model dataset.zip           # Archived dataset
│   ├── processed_data/             # Preprocessed training data
│   ├── raw_data/                   # Raw scraped/collected data
│   ├── check_model.py              # Model validation / sanity check script
│   ├── create_space_files.py       # Generates HF Space deployment files
│   ├── clean_and_merge.py          # Data cleaning pipeline
│   ├── merge_and_clean.py          # Alternate merge utility
│   ├── download_datasets.py        # Dataset download script
│   ├── download_images.py          # Product image scraper
│   ├── find_broken_images.py       # Image validation utility
│   └── Modelfile                   # Ollama Modelfile (local inference config)
│
├── 🖼️ Assets
│   ├── hero-1.jpg / hero-2.jpg / hero-3.jpg   # Homepage hero images
│   ├── cat-body.jpg / cat-face.jpg / ...       # Product category images
│   ├── logo.png                                # Brand logo
│   ├── test_face.jpg                           # Vision model test image
│   └── products/                               # Product image assets
│
├── 🔧 Utilities & Config
│   ├── db_diagnostics.py           # Full multi-DB connectivity check
│   ├── body-shop-clone/            # Reference clone / scraping source
│   ├── chroma_db/                  # Local ChromaDB persistence (dev)
│   ├── package.json                # Node dependencies (if any JS tooling)
│   ├── requirements.txt            # Python dependencies
│   ├── requirements_backup.txt     # Dependency backup
│   ├── .env                        # Environment variables (not committed)
│   └── .gitignore                  # Git ignore rules
```

---

## 🧠 Technical Challenges Solved

**pgbouncer Prepared Statement Collision** — Supabase's connection pooler rejects server-side prepared statements. LangGraph's `PostgresSaver` uses psycopg3 internally, which aggressively prepares statements. Solved by opening the psycopg3 connection manually with `prepare_threshold=0` and passing the live connection object directly to `PostgresSaver`, bypassing pool-level config that doesn't propagate correctly.

**LangGraph Tracer Flood** — Mismatched `langsmith` / `langchain` package versions caused every callback to fire a `PydanticUserError`, producing hundreds of noise lines per request. Solved by setting `LANGCHAIN_TRACING_V2=false` before any langchain import in the process.

**Re-Planner Result Collapse** — The re-planner would summarize multi-step plans with mixed results (e.g., stock found / cart failed) into a single vague failure. Solved by hardening the system prompt with an explicit directive requiring each `past_step` observation to be reported individually and accurately.

**Groq Rate Limiting** — The free tier has strict RPM limits; running a single model for all three agent roles caused 429 errors under load. Solved with a multi-model strategy: a 120B model for low-volume high-reasoning tasks (planning, re-planning) and a 70B model for higher-volume tool dispatch.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
