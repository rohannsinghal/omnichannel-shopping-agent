# tools_catalog.py
"""
LangGraph Agent Tool: Semantic Search for The Body Shop Product Catalog.

EMBEDDING STRATEGY — Primary + Automatic Fallback
──────────────────────────────────────────────────
PRIMARY   : llama-nemotron-embed-8b via your dedicated HuggingFace Inference
            Endpoint (HF_ENDPOINT_URL). Best quality. Requires HF credits.
            Uses ChromaDB collection: tbs_cloud_vectors

FALLBACK  : BAAI/bge-large-en-v1.5 via the free HuggingFace public Inference
            API. No dedicated endpoint. No credits. Top-tier quality on the
            MTEB leaderboard among free models. Activates automatically when
            the primary endpoint returns an error (e.g. 400 credit exhaustion,
            503 endpoint cold-start, timeout, etc.)
            Uses ChromaDB collection: tbs_bge_vectors

To enable the fallback collection, run embed_catalog_free.py once to re-embed
your catalog with BAAI/bge-large-en-v1.5. After that, the fallback is
permanently available and requires zero maintenance.

Switching logic (fully automatic — no manual intervention needed):
  1. Try primary endpoint (nemotron) + tbs_cloud_vectors
  2. If ANY exception is raised → silently switch to free model + tbs_bge_vectors
  3. Log which path was used so you always know what's running
"""

import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()

from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings

# ---------------------------------------------------------------------------
# Logger — tells you at runtime which embedding path was used
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
# Primary (nemotron) — your existing collection
PRIMARY_COLLECTION   = "tbs_cloud_vectors"

# Fallback (bge-large) — created by embed_catalog_free.py
FALLBACK_COLLECTION  = "tbs_bge_vectors"

# Best free model: BAAI/bge-large-en-v1.5
# • 1024-dim, MTEB top-tier, free via HF public Inference API
# • No dedicated endpoint, no credits
FREE_MODEL_ID        = "BAAI/bge-large-en-v1.5"
FREE_MODEL_URL       = f"https://router.huggingface.co/hf-inference/models/{FREE_MODEL_ID}"


# ---------------------------------------------------------------------------
# Internal helper — builds a ChromaDB cloud client (shared by both paths)
# ---------------------------------------------------------------------------
def _get_chroma_client():
    """Returns a connected ChromaDB HttpClient using env credentials."""
    import chromadb
    return chromadb.HttpClient(
        host    = "api.trychroma.com",
        ssl     = True,
        headers = {"x-chroma-token": os.getenv("CHROMA_API_KEY")},
        tenant  = os.getenv("CHROMA_TENANT"),
        database= os.getenv("CHROMA_DATABASE"),
    )


# ---------------------------------------------------------------------------
# Internal helper — runs similarity search given an embeddings object +
# collection name. Returns list of LangChain Document objects.
# ---------------------------------------------------------------------------
def _run_search(embeddings, collection_name: str, query: str, k: int = 3):
    """
    Connects to ChromaDB, binds the given embedding function to the
    named collection, and performs a semantic similarity search.

    Raises on any failure so the caller can decide to fall back.
    """
    chroma_client = _get_chroma_client()
    vector_store  = Chroma(
        client            = chroma_client,
        collection_name   = collection_name,
        embedding_function= embeddings,
    )
    return vector_store.similarity_search(query=query, k=k)


# ---------------------------------------------------------------------------
# Internal helper — formats raw LangChain Document results into clean JSON
# ---------------------------------------------------------------------------
def _format_results(results, query: str) -> str:
    """Formats a list of LangChain Document objects into a JSON string."""
    if not results:
        return (
            f"I searched the product catalog but could not find any products "
            f"matching '{query}'. Please try rephrasing your query or ask "
            "about a different skin concern or product type."
        )

    formatted_products = []
    for doc in results:
        meta = doc.metadata
        formatted_products.append({
            "product_id": meta.get("product_id", "N/A"),
            "name"      : meta.get("name",       "N/A"),
            "price"     : meta.get("price",      "N/A"),
            "category"  : meta.get("category",   "N/A"),
        })

    return json.dumps(
        {
            "query"         : query,
            "results_count" : len(formatted_products),
            "products"      : formatted_products,
        },
        indent=2,
    )


@tool
def search_chroma_products(query: str) -> str:
    """
    Searches The Body Shop product catalog using semantic similarity search.

    Use this tool whenever a user asks about skincare products, ingredients,
    skin concerns, or product recommendations. This tool queries a vector
    database of The Body Shop's full product catalog and returns the most
    relevant matches based on the semantic meaning of the user's request.

    When to trigger this tool:
    - The user mentions a specific skin concern (e.g., dryness, acne, oiliness,
      sensitivity, dark spots, aging, redness, dullness, uneven tone).
    - The user asks for a product type (e.g., moisturiser, serum, cleanser,
      toner, face mask, sunscreen, eye cream, exfoliator, body lotion).
    - The user asks about a specific ingredient (e.g., Vitamin C, niacinamide,
      hyaluronic acid, retinol, tea tree, aloe vera, shea butter, CBD, peptides).
    - The user wants a recommendation for their skin type (e.g., oily skin,
      dry skin, combination skin, sensitive skin, mature skin).
    - The user asks what products are available for a general concern like
      "something hydrating", "brightening products", or "gentle cleansers".
    - The user is comparing or exploring product options from The Body Shop.

    Do NOT use this tool for:
    - General skincare advice not related to specific products.
    - Questions about order status, returns, or store locations.
    - Questions that are clearly off-topic from skincare or The Body Shop.

    Args:
        query (str): A natural language search query describing the user's
                     skincare need, concern, ingredient of interest, or the
                     type of product they are looking for.
                     Examples:
                       - "moisturiser for dry and sensitive skin"
                       - "face serum with Vitamin C for brightening"
                       - "gentle foaming cleanser for oily skin"
                       - "body butter with shea butter"

    Returns:
        str: A JSON-formatted string containing a list of the top 3 most
             semantically relevant products. Each product entry includes:
               - product_id (str): The unique identifier for the product.
               - name (str): The full product name.
               - price (str): The retail price of the product.
               - category (str): The product category (e.g., Skincare, Body).
             Returns a plain-text error message string if both the primary
             and fallback database connections fail.
    """

    # ── Validate env vars before attempting any network call ─────────────────
    hf_url   = os.getenv("HF_ENDPOINT_URL")
    hf_token = os.getenv("HF_TOKEN")
    chroma_key = os.getenv("CHROMA_API_KEY")

    if not hf_token:
        return "Error: HF_TOKEN environment variable is missing."
    if not chroma_key:
        return "Error: CHROMA_API_KEY environment variable is missing."

    # =========================================================================
    # PATH 1 — PRIMARY: nemotron endpoint + tbs_cloud_vectors
    #
    # Try this first. If the endpoint is up and credits are available, this
    # gives the highest-quality results since your catalog was originally
    # embedded with this model (same embedding space = accurate similarity).
    # =========================================================================
    if hf_url:
        try:
            logger.info(
                "[search_chroma_products] Attempting PRIMARY path: "
                "nemotron endpoint → collection '%s'", PRIMARY_COLLECTION
            )
            print(f"  🔍  [catalog] Using PRIMARY embeddings (nemotron) → {PRIMARY_COLLECTION}")

            primary_embeddings = HuggingFaceEndpointEmbeddings(
                model                    = hf_url,
                huggingfacehub_api_token = hf_token,
            )
            results = _run_search(primary_embeddings, PRIMARY_COLLECTION, query)

            logger.info(
                "[search_chroma_products] PRIMARY succeeded — %d results", len(results)
            )
            print(f"  ✅  [catalog] PRIMARY path succeeded ({len(results)} results).")
            return _format_results(results, query)

        except Exception as primary_err:
            # Primary failed — log it clearly so you can diagnose credit issues,
            # then fall through to the backup path below.
            logger.warning(
                "[search_chroma_products] PRIMARY path failed: %s — "
                "switching to FALLBACK (bge-large).", primary_err
            )
            print(
                f"  ⚠️   [catalog] PRIMARY path failed: {primary_err}\n"
                f"  🔄  [catalog] Switching to FALLBACK embeddings (bge-large)..."
            )
    else:
        # HF_ENDPOINT_URL not set at all — skip primary entirely
        logger.info(
            "[search_chroma_products] HF_ENDPOINT_URL not set — "
            "skipping PRIMARY, going straight to FALLBACK."
        )
        print("  ℹ️   [catalog] HF_ENDPOINT_URL not set — using FALLBACK directly.")

    # =========================================================================
    # PATH 2 — FALLBACK: bge-large-en-v1.5 (free) + tbs_bge_vectors
    #
    # Activates automatically when:
    #   • The nemotron endpoint returns an error (e.g. 400 credit exhausted)
    #   • HF_ENDPOINT_URL is not set in the environment
    #   • The dedicated endpoint is cold / timing out
    #
    # IMPORTANT: This collection (tbs_bge_vectors) must have been created by
    # running embed_catalog_free.py at least once. If it doesn't exist yet,
    # this path will also fail and return a user-friendly error.
    # =========================================================================
    try:
        logger.info(
            "[search_chroma_products] Attempting FALLBACK path: "
            "bge-large-en-v1.5 (free) → collection '%s'", FALLBACK_COLLECTION
        )

        fallback_embeddings = HuggingFaceEndpointEmbeddings(
            model                    = FREE_MODEL_URL,
            huggingfacehub_api_token = hf_token,
        )
        results = _run_search(fallback_embeddings, FALLBACK_COLLECTION, query)

        logger.info(
            "[search_chroma_products] FALLBACK succeeded — %d results", len(results)
        )
        print(f"  ✅  [catalog] FALLBACK path succeeded ({len(results)} results).")
        return _format_results(results, query)

    except Exception as fallback_err:
        # Both paths failed — return a safe, executor-friendly string so the
        # agent gracefully informs the user instead of raising an unhandled exception.
        logger.error(
            "[search_chroma_products] FALLBACK path also failed: %s", fallback_err
        )
        print(f"  ❌  [catalog] FALLBACK path also failed: {fallback_err}")
        return "Error: Catalog search is temporarily down. Please inform the user."