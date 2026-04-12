import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Force absolute path to the .env.local file
env_path = os.path.join(os.getcwd(), 'body-shop-clone', '.env.local')
load_dotenv(env_path)

MONGO_URI = os.getenv("MONGO_URI")

# If it still can't find it, ask you to paste it safely in the terminal!
if not MONGO_URI:
    print("❌ Could not find MONGO_URI in .env.local!")
    MONGO_URI = input("Please paste your MongoDB Atlas Connection String here: ").strip()

print("\nConnecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client["omnichannel_db"]
collection = db["products"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

broken_products = []
products = list(collection.find({}))

print(f"Scanning {len(products)} products for broken images...\n")

for p in products:
    pid = p.get("product_id", "Unknown ID")
    url = p.get("image_url")

    if not url:
        print(f"❌ {pid}: No URL found in database")
        broken_products.append(pid)
        continue

    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            print(f"✅ {pid}: Image OK")
        else:
            print(f"❌ {pid}: Broken (Status {response.status_code})")
            broken_products.append(pid)
    except requests.exceptions.RequestException:
        print(f"❌ {pid}: Connection Error")
        broken_products.append(pid)

print("\n" + "="*40)
print(f"Audit Complete! You have {len(broken_products)} broken images.")
print(", ".join(broken_products))
print("="*40)