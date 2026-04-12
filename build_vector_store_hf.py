"""
MongoDB → ChromaDB  (nvidia/llama-embed-nemotron-8b via TGI /embed)
=====================================================================
The previous script was hitting the WRONG URL.

nvidia/llama-embed-nemotron-8b runs inside a TGI (Text Generation
Inference) container in EMBEDDING mode.  TGI exposes TWO different
endpoints:

  Root  /          → text GENERATION  (throws sdpa error for embed models)
  Path  /embed     → text EMBEDDING   ← THIS is what we need

Every "sdpa" error we saw was a red herring — the root endpoint was
trying to run the model as a text generator, not as an embedder.
Hitting /embed bypasses that entirely.

TGI /embed payload:
    {"inputs": "your text"}            # single string
    {"inputs": ["text1", "text2"]}     # batch (up to 32)

Setup:
    pip install pymongo chromadb python-dotenv requests

.env file:
    MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/...
    HF_ENDPOINT_URL=https://your-endpoint-id.us-east-1.aws.endpoints.huggingface.cloud
    HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

Run:
    python build_vector_store_hf.py
"""

import os
import sys
import time
from dotenv import load_dotenv
import pymongo
import chromadb
import requests

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI", "")
HF_ENDPOINT_URL = os.getenv("HF_ENDPOINT_URL", "").rstrip("/")
HF_TOKEN        = os.getenv("HF_TOKEN", "")

DB_NAME         = "omnichannel_db"
COLLECTION_NAME = "products"

CHROMA_PATH     = "./chroma_db"        # used only for local fallback
CHROMA_COLL     = "tbs_cloud_vectors"

# ChromaDB Cloud — set these in .env to use cloud, leave blank for local
CHROMA_API_KEY  = os.getenv("CHROMA_API_KEY", "")
CHROMA_TENANT   = os.getenv("CHROMA_TENANT", "")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "omnichannel_db")

BATCH_SIZE      = 8      # TGI /embed supports batching — speeds up 51 products
SLEEP_BETWEEN   = 0.1    # seconds between batch calls
MAX_RETRIES     = 3
RETRY_BACKOFF   = 3.0

# Mutable so main() can update it after probe
WORKING_BACKEND = ["embed"]   # "embed" = /embed path, "feature" = root path

# ─────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────

def validate_env() -> None:
    missing = [v for v, val in [
        ("MONGO_URI", MONGO_URI),
        ("HF_ENDPOINT_URL", HF_ENDPOINT_URL),
        ("HF_TOKEN", HF_TOKEN),
    ] if not val]

    if missing:
        print("\n[ERROR] Missing variables in .env:")
        for v in missing:
            print(f"        • {v}")
        sys.exit(1)

    if CHROMA_API_KEY:
        print(f"  ChromaDB mode  : ☁️  Cloud  (tenant={CHROMA_TENANT}, db={CHROMA_DATABASE})")
    else:
        print(f"  ChromaDB mode  : 💾 Local  ({CHROMA_PATH})")


# ─────────────────────────────────────────────────────────────────────
# STEP 0 — Probe endpoint to find the working path
# ─────────────────────────────────────────────────────────────────────

def probe_endpoint() -> str:
    """
    TGI containers expose /embed for embedding models.
    Feature-extraction containers use the root /.
    We try /embed first, then fall back to root.
    Returns "embed" or "feature" so get_embedding() knows which to call.
    """
    print("\n[0/4] Probing HF endpoint for correct API path...")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type":  "application/json",
    }
    probe_text = "moisturiser for dry skin"

    # ── Try 1: Root / with plain payload  ───────────────────────
    # Debug confirmed: POST / with {"inputs": text} returns flat list[float]
    # This is the correct path for nvidia/llama-embed-nemotron-8b
    root_url = HF_ENDPOINT_URL
    try:
        r = requests.post(root_url, headers=headers,
                          json={"inputs": probe_text}, timeout=30)
        if r.ok:
            raw = r.json()
            vec = _parse_vector(raw)
            if vec:
                print(f"      ✓ Root / path works  →  dim={len(vec)}")
                return "feature"
        err = r.json().get("error", r.text) if r.text else str(r.status_code)
        print(f"      ✗ root plain: HTTP {r.status_code} — {str(err)[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ root plain: {e}")

    # ── Try 2: /embed path (some TGI containers use this) ────────
    embed_url = f"{HF_ENDPOINT_URL}/embed"
    try:
        r = requests.post(embed_url, headers=headers,
                          json={"inputs": probe_text}, timeout=30)
        if r.ok:
            raw = r.json()
            vec = _parse_vector(raw)
            if vec:
                print(f"      ✓ /embed path works  →  dim={len(vec)}")
                return "embed"
        if r.status_code != 404:  # 404 is expected if endpoint doesn't have /embed
            err = r.json().get("error", r.text) if r.text else str(r.status_code)
            print(f"      ✗ /embed: HTTP {r.status_code} — {str(err)[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ /embed: {e}")

    # ── Neither worked ────────────────────────────────────────────
    print("\n" + "="*60)
    print("  ENDPOINT UNREACHABLE OR MISCONFIGURED")
    print("="*60)
    print(f"""
  Tried both paths and neither returned a valid embedding:
    • {HF_ENDPOINT_URL}/embed
    • {HF_ENDPOINT_URL}

  Things to check:
    1. Is the endpoint status GREEN/"Running" in the HF dashboard?
       https://ui.endpoints.huggingface.co

    2. Is your HF_TOKEN correct and does it have access to this endpoint?

    3. Run the debug command to see raw server responses:
         python build_vector_store_hf.py --debug

  The model nvidia/llama-embed-nemotron-8b requires TGI in embedding
  mode.  Make sure the endpoint was deployed with task = "sentence-
  embeddings" or "feature-extraction", not "text-generation".
""")
    sys.exit(1)


def _parse_vector(raw) -> list[float] | None:
    """
    Parse all known HF response shapes into a flat list[float].
    Nemotron-8b returns a flat list[float] directly from the root endpoint.
    """
    if not raw:
        return None
    if not isinstance(raw, list) or len(raw) == 0:
        return None

    first = raw[0]

    # Shape A: [float, float, ...]  — flat vector (Nemotron default)
    if isinstance(first, (float, int)):
        return [float(x) for x in raw]

    # Shape B: [[float, float, ...]]  — single vector wrapped in list
    if isinstance(first, list) and len(first) > 0 and isinstance(first[0], (float, int)):
        return [float(x) for x in first]

    # Shape C: [[[float,...],...]]  — token-level, mean pool across tokens
    if isinstance(first, list) and len(first) > 0 and isinstance(first[0], list):
        token_vecs = first          # shape: [seq_len, hidden_dim]
        dim = len(token_vecs[0])
        return [
            sum(float(t[d]) for t in token_vecs) / len(token_vecs)
            for d in range(dim)
        ]

    return None


# ─────────────────────────────────────────────────────────────────────
# STEP 1 — Fetch products from MongoDB
# ─────────────────────────────────────────────────────────────────────

def fetch_products() -> list[dict]:
    print("\n[1/4] Connecting to MongoDB Atlas...")
    try:
        client = pymongo.MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=15_000,
            tlsAllowInvalidCertificates=True,
        )
        client.admin.command("ping")
        print("      ✓ Connected")
    except pymongo.errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        sys.exit(1)

    col      = client[DB_NAME][COLLECTION_NAME]
    products = list(col.find({}, {"_id": 0}))
    client.close()

    if not products:
        print("[ERROR] No products found. Run load_tbs_products.py first.")
        sys.exit(1)

    print(f"      ✓ Fetched {len(products)} products from {DB_NAME}.{COLLECTION_NAME}")
    return products


# ─────────────────────────────────────────────────────────────────────
# STEP 2 — Build rich search_text per product
# ─────────────────────────────────────────────────────────────────────

def build_search_text(product: dict) -> str:
    name     = product.get("name", "Unknown Product")
    category = product.get("category", "General")
    price    = product.get("price", 0.0)
    ai       = product.get("ai_search_data", {})

    skin  = ", ".join(ai.get("skin_type", []))        or "all skin types"
    bens  = ", ".join(ai.get("benefits", []))          or "general care"
    ingrs = ", ".join(ai.get("key_ingredients", []))   or "natural ingredients"

    return (
        f"Product: {name}. "
        f"Category: {category}. "
        f"Price: ₹{price:.0f}. "
        f"Good for: {skin}. "
        f"Benefits: {bens}. "
        f"Key Ingredients: {ingrs}."
    )


# ─────────────────────────────────────────────────────────────────────
# STEP 3 — Init ChromaDB
# ─────────────────────────────────────────────────────────────────────

def init_chroma() -> chromadb.Collection:
    if CHROMA_API_KEY:
        print(f"\n[2/4] Connecting to ChromaDB Cloud...")
        print(f"      Tenant   : {CHROMA_TENANT}")
        print(f"      Database : {CHROMA_DATABASE}")
        client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
        )
        print(f"      ✓ Connected to ChromaDB Cloud")
    else:
        print(f"\n[2/4] Initialising ChromaDB locally at {CHROMA_PATH} ...")
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        print(f"      ✓ Local client ready")

    # Delete existing collection to start fresh
    existing = [c.name for c in client.list_collections()]
    if CHROMA_COLL in existing:
        client.delete_collection(name=CHROMA_COLL)
        print(f"      ✓ Deleted stale collection '{CHROMA_COLL}'")

    collection = client.create_collection(
        name=CHROMA_COLL,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"      ✓ Created collection '{CHROMA_COLL}' (cosine similarity)")
    return collection


# ─────────────────────────────────────────────────────────────────────
# STEP 4 — Embed via HF endpoint and store in ChromaDB
# ─────────────────────────────────────────────────────────────────────

def embed_batch(texts: list[str], ids_for_log: list[str]) -> list[list[float] | None]:
    """
    Calls the HF endpoint with a batch of texts.
    Returns a list of vectors (or None for any that failed).
    """
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type":  "application/json",
    }

    mode = WORKING_BACKEND[0]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if mode == "embed":
                # TGI /embed — accepts list input natively
                url     = f"{HF_ENDPOINT_URL}/embed"
                payload = {"inputs": texts}
            else:
                # Feature-extraction root — send one at a time
                # (batching handled by caller for this mode)
                url     = HF_ENDPOINT_URL
                payload = {"inputs": texts[0] if len(texts) == 1 else texts}

            r = requests.post(url, headers=headers, json=payload, timeout=60)

            if r.status_code == 503:
                wait = RETRY_BACKOFF * attempt
                print(f"        [503] Endpoint loading, retrying in {wait:.0f}s...")
                time.sleep(wait)
                continue

            if r.status_code == 429:
                wait = RETRY_BACKOFF * attempt * 2
                print(f"        [429] Rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
                continue

            if not r.ok:
                err = r.json().get("error", r.text) if r.text else r.status_code
                print(f"        [ERROR] HTTP {r.status_code} — {str(err)[:150]}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF)
                    continue
                return [None] * len(texts)

            raw = r.json()

            # TGI /embed returns [[vec1], [vec2], ...] for batch inputs
            if mode == "embed":
                if isinstance(raw, list) and len(raw) == len(texts):
                    result = []
                    for item in raw:
                        if isinstance(item, list) and isinstance(item[0], float):
                            result.append(item)
                        else:
                            result.append(_parse_vector(item))
                    return result
                # Unexpected shape — try parsing as single
                vec = _parse_vector(raw)
                return [vec] * len(texts) if vec else [None] * len(texts)
            else:
                vec = _parse_vector(raw)
                return [vec] if vec else [None]

        except requests.exceptions.Timeout:
            print(f"        [TIMEOUT] attempt {attempt}/{MAX_RETRIES}")
            time.sleep(RETRY_BACKOFF * attempt)
        except requests.exceptions.RequestException as e:
            print(f"        [NETWORK ERROR] {e}")
            return [None] * len(texts)

    return [None] * len(texts)


def embed_and_store(products: list[dict], collection: chromadb.Collection) -> int:
    total   = len(products)
    success = 0
    failed  = []

    mode = WORKING_BACKEND[0]
    # Feature-extraction mode doesn't support batch — force batch_size=1
    effective_batch = BATCH_SIZE if mode == "embed" else 1

    print(f"\n[3/4] Embedding {total} products via HF endpoint...")
    print(f"      Path      : {'<endpoint>/embed  (TGI batch mode)' if mode == 'embed' else '<endpoint>/  (feature-extraction)'}")
    print(f"      Batch size: {effective_batch}")
    print(f"      Model     : nvidia/llama-embed-nemotron-8b\n")

    # Build all texts + metadata first
    all_texts = [build_search_text(p) for p in products]
    all_pids  = [p.get("product_id", f"UNKNOWN_{i}") for i, p in enumerate(products)]

    for batch_start in range(0, total, effective_batch):
        batch_end   = min(batch_start + effective_batch, total)
        batch_texts = all_texts[batch_start:batch_end]
        batch_pids  = all_pids[batch_start:batch_end]
        batch_prods = products[batch_start:batch_end]

        # Print progress
        names_preview = batch_prods[0].get("name", "")[:40]
        suffix = f" + {len(batch_texts)-1} more" if len(batch_texts) > 1 else ""
        print(f"  [{batch_end:02d}/{total}] {names_preview}{suffix}...", end="  ", flush=True)

        vectors = embed_batch(batch_texts, batch_pids)

        # Store each result
        batch_success = 0
        for i, (pid, text, vec, prod) in enumerate(
            zip(batch_pids, batch_texts, vectors, batch_prods)
        ):
            if vec is None:
                failed.append(pid)
                continue

            collection.add(
                ids        =[pid],
                documents  =[text],
                embeddings =[vec],
                metadatas  =[{
                    "product_id": pid,
                    "name":       prod.get("name", ""),
                    "category":   prod.get("category", ""),
                    "price":      float(prod.get("price", 0.0)),
                    "image_url":  prod.get("image_url", ""),
                }],
            )
            success += 1
            batch_success += 1

        dim = len(vectors[0]) if vectors and vectors[0] else 0
        print(f"✓  ({batch_success}/{len(batch_texts)} stored, dim={dim})")

        if batch_end < total:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n      ✓ Embedded : {success}/{total}")
    if failed:
        print(f"      ✗ Failed   : {len(failed)}  — {', '.join(failed)}")

    return success


# ─────────────────────────────────────────────────────────────────────
# STEP 5 — Smoke test
# ─────────────────────────────────────────────────────────────────────

def smoke_test(collection: chromadb.Collection) -> None:
    print(f"\n[4/4] Running smoke test queries...")

    queries = [
        "moisturiser for dry skin",
        "anti dandruff shampoo",
        "gift set under 1500 rupees",
    ]

    for query in queries:
        print(f"\n  Query: \"{query}\"")
        vecs = embed_batch([query], ["SMOKE_TEST"])
        if not vecs or vecs[0] is None:
            print("    [WARN] Could not embed query — skipping")
            continue

        results = collection.query(
            query_embeddings=[vecs[0]],
            n_results=3,
            include=["metadatas", "distances"],
        )
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            sim = round(1 - dist, 3)
            print(f"    • {meta['name']:<50}  ₹{meta['price']:<8.0f}  sim={sim}")


# ─────────────────────────────────────────────────────────────────────
# DEBUG HELPER
# ─────────────────────────────────────────────────────────────────────

def endpoint_debug() -> None:
    """python build_vector_store_hf.py --debug"""
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }
    base = HF_ENDPOINT_URL

    print("\n── Endpoint debug ────────────────────────────────────────")
    for path in ["/info", "/health", "/embed", "/"]:
        url = base + path
        method = "GET" if path in ("/info", "/health") else "POST"
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10)
            else:
                r = requests.post(url, headers=headers,
                                  json={"inputs": "test"}, timeout=15)
            print(f"\n  {method} {path}  →  HTTP {r.status_code}")
            try:
                print(f"  {r.json()}")
            except Exception:
                print(f"  {r.text[:400]}")
        except Exception as e:
            print(f"\n  {method} {path}  →  ERROR: {e}")
    print("\n──────────────────────────────────────────────────────────")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true",
                    help="Dump raw endpoint responses and exit")
    args = ap.parse_args()

    print("=" * 60)
    print("  MongoDB → ChromaDB  (nvidia/llama-embed-nemotron-8b)")
    print("=" * 60)

    validate_env()

    if args.debug:
        endpoint_debug()
        sys.exit(0)

    WORKING_BACKEND[0] = probe_endpoint()

    products   = fetch_products()
    collection = init_chroma()
    n_embedded = embed_and_store(products, collection)
    smoke_test(collection)

    print(f"\n{'=' * 60}")
    print(f"  Pipeline complete!")
    print(f"  ChromaDB path  : {os.path.abspath(CHROMA_PATH)}")
    print(f"  Collection     : {CHROMA_COLL}")
    print(f"  Vectors stored : {collection.count()}")
    print(f"{'=' * 60}")
    print(f"""
  Load in your LangChain agent:

    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    import chromadb

    embeddings = HuggingFaceEndpointEmbeddings(
        model=os.getenv("HF_ENDPOINT_URL"),
        huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    )

    # ChromaDB Cloud
    chroma_client = chromadb.CloudClient(
        api_key=os.getenv("CHROMA_API_KEY"),
        tenant=os.getenv("CHROMA_TENANT"),
        database=os.getenv("CHROMA_DATABASE", "omnichannel_db"),
    )
    vectorstore = Chroma(
        client=chroma_client,
        collection_name="tbs_cloud_vectors",
        embedding_function=embeddings,
    )

    # Local fallback (comment out cloud block above and use this instead)
    # vectorstore = Chroma(
    #     collection_name="tbs_cloud_vectors",
    #     embedding_function=embeddings,
    #     persist_directory="./chroma_db",
    # )

    # Semantic search
    results = vectorstore.similarity_search("moisturiser for dry skin", k=3)
    for doc in results:
        print(doc.metadata["name"], doc.metadata["price"])
""")