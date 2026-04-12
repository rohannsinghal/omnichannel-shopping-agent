import os
import psycopg
from pymongo import MongoClient
import chromadb
from chromadb.config import Settings

# --- Credentials ---
MONGO_URI = "XXXXX"
POSTGRES_URI = "postgXXXXX"

CHROMA_API_KEY = "cXXXXXX"
CHROMA_TENANT = "9XXXXXXXXX"
CHROMA_DATABASE = "omnichannel_db"

print("🔍 STARTING MASTER DATABASE DIAGNOSTICS...\n")

# ==========================================
# 1. POSTGRES (SUPABASE)
# ==========================================
print("==========================================")
print("🐘 POSTGRESQL (Supabase)")
print("==========================================")
try:
    with psycopg.connect(POSTGRES_URI) as conn:
        with conn.cursor() as cur:
            # Get all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = cur.fetchall()
            print(f"✅ Connection Successful. Found {len(tables)} tables:")
            
            for table in tables:
                table_name = table[0]
                cur.execute(f"SELECT COUNT(*) FROM public.{table_name};")
                count = cur.fetchone()[0]
                print(f"   - Table: {table_name} (Rows: {count})")
                
                # Get schema for the table
                cur.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}';
                """)
                columns = cur.fetchall()
                cols_str = ", ".join([f"{c[0]} ({c[1]})" for c in columns])
                print(f"     Columns: {cols_str}\n")
except Exception as e:
    print(f"❌ Postgres Error: {e}\n")

# ==========================================
# 2. MONGODB
# ==========================================
print("==========================================")
print("🍃 MONGODB")
print("==========================================")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db_names = client.list_database_names()
    print(f"✅ Connection Successful. Found databases: {db_names}")
    
    for db_name in db_names:
        if db_name in ['admin', 'local']: continue # Skip system DBs
        db = client[db_name]
        collections = db.list_collection_names()
        print(f"   Database: {db_name}")
        for coll in collections:
            count = db[coll].count_documents({})
            print(f"     - Collection: {coll} (Documents: {count})")
            # Print sample document keys
            sample = db[coll].find_one()
            if sample:
                keys = list(sample.keys())
                print(f"       Keys: {keys}")
except Exception as e:
    print(f"❌ MongoDB Error: {e}\n")

# ==========================================
# 3. CHROMADB (CLOUD)
# ==========================================
print("\n==========================================")
print("🧠 CHROMADB (Cloud)")
print("==========================================")
try:
    chroma_client = chromadb.HttpClient(
        host="api.trychroma.com",
        port=8000,
        ssl=True,
        headers={"x-chroma-token": CHROMA_API_KEY},
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
    )
    
    collections = chroma_client.list_collections()
    print(f"✅ Connection Successful. Found {len(collections)} collections:")
    
    for col_name in collections:
        col = chroma_client.get_collection(col_name)
        count = col.count()
        print(f"   - Collection: {col_name} (Vectors: {count})")
        
except Exception as e:
    print(f"❌ ChromaDB Error: {e}\n")

print("\n🏁 DIAGNOSTICS COMPLETE.")
