import os
import time
import json
import urllib.request
import urllib.parse
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. Connect to MongoDB
env_path = os.path.join(os.getcwd(), 'body-shop-clone', '.env.local')
load_dotenv(env_path)

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    MONGO_URI = input("Please paste your MongoDB Atlas Connection String here: ").strip()

print("Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client["omnichannel_db"]
collection = db["products"]

# 2. Setup the save directory
SAVE_DIR = os.path.join(os.getcwd(), 'body-shop-clone', 'public', 'products')
os.makedirs(SAVE_DIR, exist_ok=True)

products = list(collection.find({}))
downloaded_count = 0

print(f"Found {len(products)} products. Starting Bing Image download...\n")

def get_bing_image_url(query):
    """Scrapes Bing Images for the first high-res result."""
    url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(query) + "&form=HDRSC2"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read()
        soup = BeautifulSoup(html, 'html.parser')
        # Bing stores image data inside the 'm' attribute of 'iusc' classes
        a_tag = soup.find("a", class_="iusc")
        if a_tag and "m" in a_tag.attrs:
            m_data = json.loads(a_tag["m"])
            return m_data.get("murl")
    except Exception as e:
        pass
    return None

for p in products:
    pid = p.get("product_id")
    name = p.get("name")
    
    file_path = os.path.join(SAVE_DIR, f"{pid}.jpg")
    local_url = f"/products/{pid}.jpg"

    if os.path.exists(file_path):
        print(f"⏩ {pid}: Already downloaded locally, skipping.")
        collection.update_one({"_id": p["_id"]}, {"$set": {"image_url": local_url}})
        continue

    # Add 'white background' to get clean product shots
    query = f"The Body Shop {name} official product white background"
    
    try:
        image_url = get_bing_image_url(query)
        
        if image_url:
            # Download the actual image file
            headers = {"User-Agent": "Mozilla/5.0"}
            img_data = requests.get(image_url, headers=headers, timeout=10).content
            
            with open(file_path, 'wb') as handler:
                handler.write(img_data)
            
            # Update MongoDB
            collection.update_one(
                {"_id": p["_id"]},
                {"$set": {"image_url": local_url}}
            )
            
            print(f"✅ {pid}: Downloaded & saved to {local_url}")
            downloaded_count += 1
        else:
            print(f"❌ {pid}: No image found on Bing for {name}")
            
    except Exception as e:
        print(f"⚠️ {pid}: Download failed ({str(e)})")
        
    # Sleep to be polite to Bing
    time.sleep(2)

print("\n" + "="*50)
print(f"Download Complete! Saved {downloaded_count} new images to your public folder.")
print("="*50)

# Clean up database connection
client.close()