# =============================================================================
# embed_catalog_free.py
# The Body Shop — Re-Embed Product Catalog with Free Backup Embeddings
#
# PURPOSE:
#   Your primary HuggingFace Inference Endpoint (llama-nemotron-embed-8b) uses
#   credits. When credits run out, the endpoint returns 400. This script
#   re-embeds your full product catalog using a FREE, high-quality alternative:
#
#       BAAI/bge-large-en-v1.5  ← Best free model available on HF Inference API
#           • 1024-dim embeddings (vs 4096 for nemotron, but far better quality
#             than MiniLM — MTEB leaderboard top-tier for free-tier models)
#           • Runs on HuggingFace's free Inference API (no dedicated endpoint
#             needed, no credits consumed)
#           • Natively understands skincare/beauty product descriptions
#
# WHAT THIS SCRIPT DOES:
#   1. Reads your existing ChromaDB collection (tbs_cloud_vectors) which was
#      embedded with nemotron. Pulls all documents + metadata.
#   2. Re-embeds every document using BAAI/bge-large-en-v1.5 via the free
#      HF Inference API.
#   3. Writes them into a NEW ChromaDB cloud collection: tbs_bge_vectors
#      (leaves your original nemotron collection completely untouched).
#
# USAGE:
#   python embed_catalog_free.py
#
# PRE-REQUISITES (.env must have):
#   HF_TOKEN        — your HuggingFace token (free account is fine)
#   CHROMA_API_KEY  — your ChromaDB cloud API key
#   CHROMA_TENANT   — your ChromaDB tenant ID
#   CHROMA_DATABASE — your ChromaDB database name
#
# After running this once, tools_catalog.py will automatically use this
# collection as a fallback whenever the nemotron endpoint is unavailable.
# =============================================================================

import os
import time
import chromadb
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SOURCE_COLLECTION = "tbs_cloud_vectors"     # your existing nemotron collection
TARGET_COLLECTION = "tbs_bge_vectors"       # new free-model collection
FREE_MODEL_ID     = "BAAI/bge-large-en-v1.5"  # best free model on HF
BATCH_SIZE        = 32                      # HF free API: safe batch size
SLEEP_BETWEEN_BATCHES = 1.5                 # seconds — avoid rate limits

# ---------------------------------------------------------------------------
# STEP 1 — Connect to ChromaDB Cloud
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("  The Body Shop — Catalog Re-Embedder (Free Model)")
print("=" * 60)

print("\n[1/5] Connecting to ChromaDB Cloud...")

chroma_client = chromadb.HttpClient(
    host    = "api.trychroma.com",
    ssl     = True,
    headers = {"x-chroma-token": os.getenv("CHROMA_API_KEY")},
    tenant  = os.getenv("CHROMA_TENANT"),
    database= os.getenv("CHROMA_DATABASE"),
)
print("      ✅  ChromaDB connected.")

# ---------------------------------------------------------------------------
# STEP 2 — Pull all documents from the source (nemotron) collection
# ---------------------------------------------------------------------------
print(f"\n[2/5] Reading source collection: '{SOURCE_COLLECTION}'...")

source_col = chroma_client.get_collection(SOURCE_COLLECTION)
total_docs  = source_col.count()
print(f"      Found {total_docs} documents.")

if total_docs == 0:
    raise RuntimeError(
        f"Source collection '{SOURCE_COLLECTION}' is empty. "
        "Nothing to re-embed."
    )

# Fetch all documents with their metadata (no embeddings needed from source)
raw = source_col.get(
    include=["documents", "metadatas"],
    limit=total_docs,
)

doc_ids    = raw["ids"]
documents  = raw["documents"]
metadatas  = raw["metadatas"]

print(f"      ✅  Pulled {len(doc_ids)} docs with metadata.")

# ---------------------------------------------------------------------------
# STEP 3 — Initialise Free Embeddings (BAAI/bge-large-en-v1.5)
#
# We use HuggingFaceEndpointEmbeddings pointed at the PUBLIC inference API
# endpoint for this model — no dedicated endpoint, no credits.
#
# Public HF Inference API URL format:
#   https://api-inference.huggingface.co/models/{model_id}
# ---------------------------------------------------------------------------
print(f"\n[3/5] Initialising free embeddings: '{FREE_MODEL_ID}'...")

free_embeddings = HuggingFaceEndpointEmbeddings(
    model                  = f"https://router.huggingface.co/hf-inference/models/{FREE_MODEL_ID}",
    huggingfacehub_api_token = os.getenv("HF_TOKEN"),
)
print("      ✅  Free embedding model ready.")

# ---------------------------------------------------------------------------
# STEP 4 — Create (or overwrite) the target collection
# ---------------------------------------------------------------------------
print(f"\n[4/5] Setting up target collection: '{TARGET_COLLECTION}'...")

# get_or_create is idempotent — safe to run multiple times
target_col = chroma_client.get_or_create_collection(
    name     = TARGET_COLLECTION,
    metadata = {
        "description"  : "TBS product catalog embedded with BAAI/bge-large-en-v1.5",
        "embedding_model": FREE_MODEL_ID,
        "created_by"   : "embed_catalog_free.py",
    }
)
print(f"      ✅  Collection ready (existing docs: {target_col.count()}).")

# If collection already has docs (re-run), we clear and re-embed from scratch
# to avoid duplicate IDs. Skip if this is a first run.
existing = target_col.count()
if existing > 0:
    print(f"      ⚠️   Collection has {existing} existing docs — clearing for fresh re-embed.")
    # ChromaDB doesn't have a truncate; delete all by IDs
    existing_ids = target_col.get(include=[], limit=existing)["ids"]
    target_col.delete(ids=existing_ids)
    print(f"      🗑️   Cleared {len(existing_ids)} old documents.")

# ---------------------------------------------------------------------------
# STEP 5 — Embed in batches and upsert into target collection
# ---------------------------------------------------------------------------
print(f"\n[5/5] Re-embedding {total_docs} documents in batches of {BATCH_SIZE}...")
print(f"      This will take a few minutes on the free API tier. Please wait.\n")

total_embedded = 0
failed_batches  = []

for batch_start in range(0, total_docs, BATCH_SIZE):
    batch_end   = min(batch_start + BATCH_SIZE, total_docs)
    batch_docs  = documents[batch_start:batch_end]
    batch_meta  = metadatas[batch_start:batch_end]
    batch_ids   = doc_ids[batch_start:batch_end]

    batch_num   = (batch_start // BATCH_SIZE) + 1
    total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"  Batch {batch_num}/{total_batches} — docs {batch_start+1}–{batch_end}...")

    try:
        # Embed this batch using the free model
        batch_embeddings = free_embeddings.embed_documents(batch_docs)

        # Upsert into target collection
        target_col.upsert(
            ids        = batch_ids,
            documents  = batch_docs,
            metadatas  = batch_meta,
            embeddings = batch_embeddings,
        )

        total_embedded += len(batch_docs)
        print(f"    ✅  Embedded & stored {len(batch_docs)} docs "
              f"(total so far: {total_embedded}/{total_docs})")

    except Exception as e:
        print(f"    ❌  Batch {batch_num} failed: {e}")
        failed_batches.append((batch_start, batch_end, str(e)))

    # Rate-limit guard for HF free API
    if batch_end < total_docs:
        time.sleep(SLEEP_BETWEEN_BATCHES)

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("  Re-Embedding Complete")
print("=" * 60)
print(f"  ✅  Successfully embedded : {total_embedded} / {total_docs} documents")
print(f"  📦  Target collection      : '{TARGET_COLLECTION}'")
print(f"  🔑  Embedding model        : {FREE_MODEL_ID}")

if failed_batches:
    print(f"\n  ⚠️   {len(failed_batches)} batch(es) failed:")
    for start, end, err in failed_batches:
        print(f"       Docs {start+1}–{end}: {err}")
    print("  Re-run the script to retry. Upsert is idempotent — no duplicates.")
else:
    print("\n  🎉  All batches succeeded! No retries needed.")

print("\n  Your tools_catalog.py will now automatically use this collection")
print("  as a fallback whenever the nemotron endpoint is unavailable.\n")