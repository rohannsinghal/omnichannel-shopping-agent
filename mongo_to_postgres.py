"""
MongoDB Atlas → Supabase PostgreSQL Migration
=============================================
Migrates the product catalog from MongoDB omnichannel_db.products
into a Supabase PostgreSQL table named `inventory`.

Setup:
    pip install pymongo psycopg2-binary python-dotenv

.env file (same folder as this script):
    MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
    POSTGRES_URI=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

Run:
    python mongo_to_postgres.py
"""

import random
import sys
from dotenv import load_dotenv
import os
import pymongo
import psycopg2
from psycopg2.extras import execute_batch

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────

load_dotenv()

MONGO_URI    = os.getenv("MONGO_URI", "")
POSTGRES_URI = os.getenv("POSTGRES_URI", "")

MONGO_DB         = "omnichannel_db"
MONGO_COLLECTION = "products"
PG_TABLE         = "inventory"

STOCK_MIN = 0
STOCK_MAX = 50


# ─────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────

def validate_env() -> None:
    missing = []
    if not MONGO_URI:
        missing.append("MONGO_URI")
    if not POSTGRES_URI:
        missing.append("POSTGRES_URI")

    if missing:
        print("\n[ERROR] Missing required variables in .env:")
        for v in missing:
            print(f"        • {v}")
        print("\n  Your .env file must contain:")
        print("  MONGO_URI=mongodb+srv://...")
        print("  POSTGRES_URI=postgresql://postgres.[ref]:[password]@[host]:6543/postgres")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────
# STEP 1 — Fetch all products from MongoDB
# ─────────────────────────────────────────────────────────────────────

def fetch_from_mongo() -> list[dict]:
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
        print("        Ensure your IP is whitelisted in Atlas → Network Access.")
        sys.exit(1)

    col      = client[MONGO_DB][MONGO_COLLECTION]
    products = list(col.find({}))   # keep _id for product_id mapping
    client.close()

    if not products:
        print(f"[ERROR] No documents found in {MONGO_DB}.{MONGO_COLLECTION}")
        sys.exit(1)

    print(f"      ✓ Fetched {len(products)} documents from {MONGO_DB}.{MONGO_COLLECTION}")
    return products


# ─────────────────────────────────────────────────────────────────────
# STEP 2 — Connect to Supabase PostgreSQL
# ─────────────────────────────────────────────────────────────────────

def connect_postgres() -> psycopg2.extensions.connection:
    print("\n[2/4] Connecting to Supabase PostgreSQL...")
    try:
        conn = psycopg2.connect(POSTGRES_URI)
        conn.autocommit = False    # we manage transactions manually
        print("      ✓ Connected")
        return conn
    except psycopg2.OperationalError as e:
        print(f"[ERROR] PostgreSQL connection failed:\n        {e}")
        print("\n  Check your POSTGRES_URI in .env.")
        print("  Format: postgresql://postgres.[ref]:[password]@[host]:6543/postgres")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────
# STEP 3 — Drop and recreate the inventory table
# ─────────────────────────────────────────────────────────────────────

def setup_table(conn: psycopg2.extensions.connection) -> None:
    print(f"\n[3/4] Setting up '{PG_TABLE}' table in PostgreSQL...")

    create_sql = f"""
        CREATE TABLE {PG_TABLE} (
            product_id     TEXT PRIMARY KEY,
            name           TEXT,
            category       TEXT,
            price          REAL,
            stock_quantity INTEGER
        );
    """

    with conn.cursor() as cur:
        # Drop if exists — safe for re-runs
        cur.execute(f"DROP TABLE IF EXISTS {PG_TABLE} CASCADE;")
        print(f"      ✓ Dropped existing '{PG_TABLE}' table (if any)")

        cur.execute(create_sql)
        print(f"      ✓ Created '{PG_TABLE}' table with schema:")
        print(f"          product_id     TEXT PRIMARY KEY")
        print(f"          name           TEXT")
        print(f"          category       TEXT")
        print(f"          price          REAL")
        print(f"          stock_quantity INTEGER")

    conn.commit()


# ─────────────────────────────────────────────────────────────────────
# STEP 4 — Transform and insert all products
# ─────────────────────────────────────────────────────────────────────

def insert_products(
    conn: psycopg2.extensions.connection,
    products: list[dict],
) -> int:
    print(f"\n[4/4] Inserting {len(products)} products into '{PG_TABLE}'...")

    insert_sql = f"""
        INSERT INTO {PG_TABLE}
            (product_id, name, category, price, stock_quantity)
        VALUES
            (%s, %s, %s, %s, %s)
        ON CONFLICT (product_id) DO NOTHING;
    """

    rows: list[tuple] = []

    for product in products:
        # Map MongoDB _id → product_id
        # Use product_id field if present, otherwise stringify ObjectId
        pid = product.get("product_id") or str(product.get("_id", ""))

        name     = product.get("name", "")
        category = product.get("category", "")
        price    = float(product.get("price", 0.0))

        # Simulate stock — MongoDB has no stock data
        stock = random.randint(STOCK_MIN, STOCK_MAX)

        rows.append((pid, name, category, price, stock))

        print(f"  ✓ Prepared  {pid:<12}  {name[:45]:<45}  "
              f"₹{price:<8.0f}  stock={stock}")

    # Bulk insert using execute_batch — much faster than row-by-row
    with conn.cursor() as cur:
        execute_batch(cur, insert_sql, rows, page_size=50)
        inserted = cur.rowcount

    conn.commit()
    return len(rows)


# ─────────────────────────────────────────────────────────────────────
# STEP 5 — Verify: count rows in Postgres
# ─────────────────────────────────────────────────────────────────────

def verify_count(conn: psycopg2.extensions.connection) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {PG_TABLE};")
        return cur.fetchone()[0]


def preview_rows(conn: psycopg2.extensions.connection, n: int = 3) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT product_id, name, category, price, stock_quantity "
            f"FROM {PG_TABLE} ORDER BY product_id LIMIT %s;",
            (n,)
        )
        rows = cur.fetchall()

    print(f"\n  Preview — first {n} rows:")
    print(f"  {'product_id':<12}  {'name':<45}  {'category':<15}  "
          f"{'price':>8}  {'stock':>5}")
    print(f"  {'─'*12}  {'─'*45}  {'─'*15}  {'─'*8}  {'─'*5}")
    for row in rows:
        pid, name, cat, price, stock = row
        print(f"  {pid:<12}  {name[:45]:<45}  {cat:<15}  "
              f"₹{price:>7.0f}  {stock:>5}")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  MongoDB Atlas → Supabase PostgreSQL Migration")
    print(f"  Source : {MONGO_DB}.{MONGO_COLLECTION}")
    print(f"  Target : PostgreSQL table '{PG_TABLE}'")
    print("=" * 60)

    validate_env()

    # 1. Fetch
    products = fetch_from_mongo()

    # 2. Connect Postgres
    conn = connect_postgres()

    try:
        # 3. Setup table
        setup_table(conn)

        # 4. Insert
        n_inserted = insert_products(conn, products)

        # 5. Verify
        n_confirmed = verify_count(conn)
        preview_rows(conn)

        print(f"\n{'=' * 60}")
        print(f"  Migration complete!")
        print(f"  Rows prepared  : {n_inserted}")
        print(f"  Rows confirmed : {n_confirmed}  (verified via SELECT COUNT(*))")
        print(f"  Table          : {PG_TABLE}")
        print(f"{'=' * 60}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed — rolled back transaction.")
        print(f"        {e}")
        sys.exit(1)

    finally:
        conn.close()
        print("\n  PostgreSQL connection closed.")