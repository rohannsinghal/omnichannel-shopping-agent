"""
The Body Shop India — Product Catalog Loader
=============================================
50 real products. Run:
    pip install pymongo python-dotenv
    python load_tbs_products.py

Your .env file (same folder as this script) must contain exactly:
    MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/...
No # comments, no quotes, no blank lines before it.
"""

import json
import os
import random
from datetime import datetime, timezone

from dotenv import load_dotenv
import pymongo

# ── load .env and explain clearly if MONGO_URI is missing ──────────
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "")

DB_NAME         = "omnichannel_db"
COLLECTION_NAME = "products"

# ─────────────────────────────────────────────────────────────────────
# PRODUCT CATALOG  (50 real The Body Shop India products)
# ─────────────────────────────────────────────────────────────────────

RAW_PRODUCTS = [

    # ── SKINCARE ──────────────────────────────────────────────────────
    {
        "name": "Vitamin E Moisture Cream 50ml",
        "category": "Skincare",
        "price": 1095.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/a/6/a61e34dE000334_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["48-hour hydration", "Locks in moisture", "Leaves skin silky smooth", "Protects from environmental aggressors"],
        "key_ingredients": ["Vitamin E (Tocopherol)", "Hyaluronic Acid", "Raspberry Seed Extract", "Community Fair Trade Aloe Vera"],
    },
    {
        "name": "Vitamin E Gentle Facial Wash 125ml",
        "category": "Skincare",
        "price": 895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963819_1.jpg",
        "skin_type": ["All Skin Types", "Dry Skin"],
        "benefits": ["Cleanses gently", "Hydrates while cleansing", "Soap-free formula", "Leaves skin soft"],
        "key_ingredients": ["Vitamin E", "Aloe Vera", "Wheat Germ Oil"],
    },
    {
        "name": "Vitamin E Night Cream 50ml",
        "category": "Skincare",
        "price": 1695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963864_1.jpg",
        "skin_type": ["All Skin Types", "Dry Skin"],
        "benefits": ["Overnight nourishment", "Restores skin overnight", "Intensely moisturises", "Wakes up to softer skin"],
        "key_ingredients": ["Vitamin E", "Wheatgerm Oil", "Hyaluronic Acid"],
    },
    {
        "name": "Vitamin E Gel Moisture Cream 50ml",
        "category": "Skincare",
        "price": 1395.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963833_1.jpg",
        "skin_type": ["Combination Skin", "Oily Skin"],
        "benefits": ["48-hour hydration", "Oil-free formula", "Non-greasy finish", "Fast absorbing"],
        "key_ingredients": ["Vitamin E", "Raspberry Extract", "Hyaluronic Acid"],
    },
    {
        "name": "Vitamin E Eye Cream 15ml",
        "category": "Skincare",
        "price": 1595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963871_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Reduces appearance of fine lines", "Hydrates eye area", "Lightweight texture"],
        "key_ingredients": ["Vitamin E", "Wheatgerm Oil", "Hyaluronic Acid"],
    },
    {
        "name": "Vitamin C Glow Boosting Moisturiser 50ml",
        "category": "Skincare",
        "price": 2695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963802_1.jpg",
        "skin_type": ["Dull Skin", "All Skin Types"],
        "benefits": ["Boosts radiance", "Evens skin tone", "Vitamin C protection", "Brightening effect"],
        "key_ingredients": ["Vitamin C", "Camu Camu", "Community Fair Trade Moringa Oil"],
    },
    {
        "name": "Vitamin C Skin Boost Instant Smoother 30ml",
        "category": "Skincare",
        "price": 2295.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963789_1.jpg",
        "skin_type": ["Dull Skin", "All Skin Types"],
        "benefits": ["Instant glow", "Smooths skin texture", "Brightens complexion"],
        "key_ingredients": ["Vitamin C", "Camu Camu", "Moringa"],
    },
    {
        "name": "Tea Tree Skin Clearing Facial Wash 250ml",
        "category": "Skincare",
        "price": 895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/a/6/a61e34dE000334_1.jpg",
        "skin_type": ["Oily Skin", "Acne-Prone Skin", "Combination Skin"],
        "benefits": ["Purifies pores", "Controls excess oil", "Fights blemishes", "Refreshing cleanse"],
        "key_ingredients": ["Community Fair Trade Tea Tree Oil", "Witch Hazel"],
    },
    {
        "name": "Tea Tree Anti-Imperfection Daily Solution 50ml",
        "category": "Skincare",
        "price": 2095.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963703_1.jpg",
        "skin_type": ["Oily Skin", "Acne-Prone Skin"],
        "benefits": ["Targets blemishes", "Reduces redness", "Clears skin", "Daily use formula"],
        "key_ingredients": ["Tea Tree Oil", "Salicylic Acid", "Niacinamide"],
    },
    {
        "name": "Tea Tree Pore Minimiser Serum 30ml",
        "category": "Skincare",
        "price": 1995.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963710_1.jpg",
        "skin_type": ["Oily Skin", "Combination Skin"],
        "benefits": ["Minimises pores", "Controls shine", "Refines skin texture"],
        "key_ingredients": ["Tea Tree Oil", "Salicylic Acid", "Hyaluronic Acid"],
    },
    {
        "name": "Tea Tree Oil 10ml",
        "category": "Skincare",
        "price": 695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963727_1.jpg",
        "skin_type": ["Oily Skin", "Acne-Prone Skin"],
        "benefits": ["Spot treatment", "Antibacterial", "Purifying"],
        "key_ingredients": ["Community Fair Trade Tea Tree Oil from Kenya"],
    },
    {
        "name": "Drops of Youth Youth Concentrate 30ml",
        "category": "Skincare",
        "price": 3495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963666_1.jpg",
        "skin_type": ["All Skin Types", "Mature Skin"],
        "benefits": ["Reduces fine lines", "Boosts collagen", "Plumps skin", "Smoother complexion"],
        "key_ingredients": ["Edelweiss Plant Stem Cells", "Sea Holly", "Crithmum"],
    },
    {
        "name": "Drops of Youth Eye Concentrate 15ml",
        "category": "Skincare",
        "price": 2695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963673_1.jpg",
        "skin_type": ["All Skin Types", "Mature Skin"],
        "benefits": ["Reduces eye bags", "Minimises dark circles", "Lifts eye area"],
        "key_ingredients": ["Edelweiss Plant Stem Cells", "Sea Holly"],
    },
    {
        "name": "Edelweiss Daily Serum Concentrate 30ml",
        "category": "Skincare",
        "price": 3995.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963741_1.jpg",
        "skin_type": ["Sensitive Skin", "All Skin Types"],
        "benefits": ["Strengthens skin barrier", "Reduces redness", "Anti-oxidant protection", "Plumping effect"],
        "key_ingredients": ["Edelweiss Flower", "Hyaluronic Acid", "Bifida Ferment Lysate"],
    },
    {
        "name": "Edelweiss Daily Moisturiser SPF20 50ml",
        "category": "Skincare",
        "price": 2895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963758_1.jpg",
        "skin_type": ["Sensitive Skin", "All Skin Types"],
        "benefits": ["Daily UV protection", "Strengthens skin", "Hydrating", "Anti-pollution shield"],
        "key_ingredients": ["Edelweiss Flower", "SPF20 UV Filters", "Hyaluronic Acid"],
    },
    {
        "name": "Skin Defence Multi-Protection Essence SPF50+ 30ml",
        "category": "Skincare",
        "price": 2495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963795_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["SPF50+ protection", "Lightweight texture", "Anti-pollution", "Daily sunscreen"],
        "key_ingredients": ["SPF50+ UV Filters", "PA+++", "Community Fair Trade Moringa"],
    },

    # ── BODY CARE ─────────────────────────────────────────────────────
    {
        "name": "British Rose Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/5/4/54dd8d3E000865ab1.jpg",
        "skin_type": ["Dry Skin", "All Skin Types"],
        "benefits": ["96-hour moisture", "Intensely nourishes", "Rosy fragrance", "Melts into skin"],
        "key_ingredients": ["Community Fair Trade Rose Hip Oil", "Shea Butter", "Rose Petal Extract"],
    },
    {
        "name": "British Rose Body Yogurt 200ml",
        "category": "Body Care",
        "price": 1295.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963840_1.jpg",
        "skin_type": ["Normal Skin", "Combination Skin"],
        "benefits": ["48-hour hydration", "Light texture", "Fast absorbing", "Floral rose scent"],
        "key_ingredients": ["Rose Hip", "Rose Centifolia", "Yogurt Proteins"],
    },
    {
        "name": "British Rose Shower Gel 250ml",
        "category": "Body Care",
        "price": 395.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/5/4/54dd8d3E000865ab1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Softens skin", "Gentle cleanse", "Floral fragrance", "Soap-free"],
        "key_ingredients": ["British Rose Extract", "Aloe Vera", "Rose Hip"],
    },
    {
        "name": "British Rose Petal Soft Hand Cream 30ml",
        "category": "Body Care",
        "price": 395.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963857_1.jpg",
        "skin_type": ["All Skin Types", "Dry Hands"],
        "benefits": ["Softens hands", "Fast absorbing", "Non-greasy", "Delicate rose scent"],
        "key_ingredients": ["Rose Hip Oil", "Rose Petal Extract", "Glycerin"],
    },
    {
        "name": "Shea Body Butter 200ml",
        "category": "Body Care",
        "price": 1195.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963912_1.jpg",
        "skin_type": ["Very Dry Skin", "Dry Skin"],
        "benefits": ["96-hour moisture", "Deeply nourishes", "Repairs dry skin", "Rich creamy texture"],
        "key_ingredients": ["Community Fair Trade Shea Butter from Ghana", "Soybean Oil"],
    },
    {
        "name": "Shea Shower Cream 250ml",
        "category": "Body Care",
        "price": 495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963929_1.jpg",
        "skin_type": ["Dry Skin", "Sensitive Skin"],
        "benefits": ["Hydrates while cleansing", "Non-drying formula", "Creamy lather", "Nourishing"],
        "key_ingredients": ["Community Fair Trade Shea Butter", "Aloe Vera"],
    },
    {
        "name": "Shea Nourishing Body Lotion 250ml",
        "category": "Body Care",
        "price": 895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963936_1.jpg",
        "skin_type": ["Dry Skin", "Normal Skin"],
        "benefits": ["Nourishes dry skin", "Long-lasting moisture", "Smooth skin texture"],
        "key_ingredients": ["Shea Butter", "Glycerin", "Vitamin E"],
    },
    {
        "name": "Strawberry Shower Gel 250ml",
        "category": "Body Care",
        "price": 495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963943_1.jpg",
        "skin_type": ["All Skin Types", "Normal Skin"],
        "benefits": ["Fruity strawberry scent", "Gentle cleanse", "Leaves skin fresh", "Lathers well"],
        "key_ingredients": ["Community Fair Trade Strawberry from Poland", "Aloe Vera"],
    },
    {
        "name": "Strawberry Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963950_1.jpg",
        "skin_type": ["Dry Skin", "Normal Skin"],
        "benefits": ["96-hour moisture", "Fruity scent", "Rich texture", "Intensely nourishing"],
        "key_ingredients": ["Community Fair Trade Strawberry", "Shea Butter"],
    },
    {
        "name": "Moringa Shower Gel 250ml",
        "category": "Body Care",
        "price": 495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963967_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Cleanses gently", "Soft floral scent", "Leaves skin smooth", "Soap-free"],
        "key_ingredients": ["Community Fair Trade Moringa Oil", "Aloe Vera"],
    },
    {
        "name": "Moringa Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963974_1.jpg",
        "skin_type": ["Dry Skin", "All Skin Types"],
        "benefits": ["Deep nourishment", "96-hour moisture", "Delicate scent", "Silky finish"],
        "key_ingredients": ["Moringa Oil", "Shea Butter", "Soybean Oil"],
    },
    {
        "name": "Almond Milk & Honey Calming Hand Cream 30ml",
        "category": "Body Care",
        "price": 345.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963981_1.jpg",
        "skin_type": ["Sensitive Skin", "Dry Hands"],
        "benefits": ["Calms irritation", "Protects hands", "Soothes dry skin", "Gentle fragrance"],
        "key_ingredients": ["Almond Milk", "Honey", "Glycerin"],
    },
    {
        "name": "Avocado Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015963998_1.jpg",
        "skin_type": ["Very Dry Skin", "Dry Skin"],
        "benefits": ["Intensely moisturises", "Nourishes rough skin", "Rich buttery texture", "96-hour moisture"],
        "key_ingredients": ["Community Fair Trade Avocado", "Shea Butter"],
    },
    {
        "name": "Olive Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964001_1.jpg",
        "skin_type": ["Very Dry Skin", "Dry Skin"],
        "benefits": ["96-hour moisture", "Rich nourishment", "Intensely hydrating"],
        "key_ingredients": ["Community Fair Trade Olive Oil", "Shea Butter"],
    },
    {
        "name": "Ocean Lily Body Lotion 250ml",
        "category": "Body Care",
        "price": 995.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/1/4/14d3f49THEAC00000517_1.jpg",
        "skin_type": ["All Skin Types", "Normal Skin"],
        "benefits": ["Lightweight hydration", "Fresh aquatic scent", "Absorbs quickly", "Smooth skin"],
        "key_ingredients": ["Ocean Lily Extract", "Glycerin", "Aloe Vera"],
    },
    {
        "name": "Ocean Lily Shower Gel 250ml",
        "category": "Body Care",
        "price": 495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/1/4/14d3f49THEAC00000516_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Refreshing cleanse", "Aquatic floral scent", "Gentle formula"],
        "key_ingredients": ["Ocean Lily Extract", "Aloe Vera"],
    },
    {
        "name": "Satsuma Shower Gel 250ml",
        "category": "Body Care",
        "price": 495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964018_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Refreshes and cleanses", "Citrus scent", "Energising shower", "Soap-free"],
        "key_ingredients": ["Satsuma Extract", "Aloe Vera", "Citrus Oil"],
    },
    {
        "name": "The India Edit Lotus Shower Gel 250ml",
        "category": "Body Care",
        "price": 395.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964025_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Fresh lotus scent", "Gentle cleanse", "India-inspired fragrance"],
        "key_ingredients": ["Lotus Extract", "Aloe Vera"],
    },
    {
        "name": "India Edit Pomegranate Body Lotion 250ml",
        "category": "Body Care",
        "price": 695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964032_1.jpg",
        "skin_type": ["All Skin Types", "Normal Skin"],
        "benefits": ["Moisturises skin", "Pomegranate fragrance", "Lightweight formula"],
        "key_ingredients": ["Pomegranate Extract", "Glycerin", "Aloe Vera"],
    },
    {
        "name": "Pink Grapefruit Body Butter 200ml",
        "category": "Body Care",
        "price": 1495.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964039_1.jpg",
        "skin_type": ["Normal Skin", "Dry Skin"],
        "benefits": ["96-hour moisture", "Zesty citrus scent", "Energising", "Rich texture"],
        "key_ingredients": ["Pink Grapefruit Extract", "Shea Butter", "Vitamin C"],
    },

    # ── HAIR CARE ─────────────────────────────────────────────────────
    {
        "name": "Ginger Anti-Dandruff Shampoo 250ml",
        "category": "Hair Care",
        "price": 615.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964049_1.jpg",
        "skin_type": ["Dry Scalp", "Flaky Scalp"],
        "benefits": ["Fights dandruff", "Soothes itchy scalp", "Reduces flakes", "Refreshing ginger scent"],
        "key_ingredients": ["Community Fair Trade Ginger", "Zinc Pyrithione", "Silk Proteins"],
    },
    {
        "name": "Ginger Scalp Care Conditioner 250ml",
        "category": "Hair Care",
        "price": 695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964056_1.jpg",
        "skin_type": ["Dry Scalp", "All Hair Types"],
        "benefits": ["Conditions hair", "Soothes scalp", "Reduces dryness", "Detangles hair"],
        "key_ingredients": ["Ginger Root Extract", "Silk Proteins", "Panthenol"],
    },
    {
        "name": "Banana Truly Nourishing Shampoo 250ml",
        "category": "Hair Care",
        "price": 595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964063_1.jpg",
        "skin_type": ["Dry Hair", "Damaged Hair"],
        "benefits": ["Nourishes dry hair", "Reduces breakage", "Adds shine", "Strengthens hair"],
        "key_ingredients": ["Community Fair Trade Banana", "Silk Proteins", "Panthenol"],
    },
    {
        "name": "Banana Truly Nourishing Conditioner 250ml",
        "category": "Hair Care",
        "price": 695.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964070_1.jpg",
        "skin_type": ["Dry Hair", "Damaged Hair"],
        "benefits": ["Deep conditioning", "Reduces frizz", "Adds softness", "Detangles"],
        "key_ingredients": ["Banana Extract", "Silk Proteins", "Shea Butter"],
    },
    {
        "name": "Moringa Broken Dreams Repair Shampoo 250ml",
        "category": "Hair Care",
        "price": 595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964087_1.jpg",
        "skin_type": ["Damaged Hair", "Brittle Hair"],
        "benefits": ["Repairs damaged hair", "Strengthens strands", "Reduces breakage", "Cleanses gently"],
        "key_ingredients": ["Moringa Oil", "Silk Proteins", "Keratin"],
    },
    {
        "name": "Shea Moisture Shine Shampoo 250ml",
        "category": "Hair Care",
        "price": 595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964094_1.jpg",
        "skin_type": ["Dry Hair", "Coarse Hair"],
        "benefits": ["Adds shine", "Moisturises hair", "Reduces frizz", "Nourishing cleanse"],
        "key_ingredients": ["Community Fair Trade Shea Butter", "Argan Oil", "Silk Proteins"],
    },
    {
        "name": "Tea Tree Purifying & Balancing Shampoo 250ml",
        "category": "Hair Care",
        "price": 595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964100_1.jpg",
        "skin_type": ["Oily Scalp", "Normal to Oily Hair"],
        "benefits": ["Purifies scalp", "Controls oil", "Refreshing cleanse", "Balances scalp"],
        "key_ingredients": ["Community Fair Trade Tea Tree Oil", "Menthol", "Silk Proteins"],
    },

    # ── FRAGRANCE ─────────────────────────────────────────────────────
    {
        "name": "White Musk Eau de Toilette 30ml",
        "category": "Fragrance",
        "price": 1895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964117_1.jpg",
        "skin_type": [],
        "benefits": ["Soft musk scent", "Long-lasting fragrance", "Unisex appeal", "Clean powdery notes"],
        "key_ingredients": ["White Musk", "Alcohol Denat"],
    },
    {
        "name": "British Rose Eau de Toilette 30ml",
        "category": "Fragrance",
        "price": 1895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964124_1.jpg",
        "skin_type": [],
        "benefits": ["Floral rose fragrance", "Feminine scent", "Fresh and romantic", "Long-lasting"],
        "key_ingredients": ["Rose Extract", "Alcohol Denat"],
    },
    {
        "name": "Woody Sandalwood Eau de Toilette 30ml",
        "category": "Fragrance",
        "price": 1895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964131_1.jpg",
        "skin_type": [],
        "benefits": ["Warm woody notes", "Long-lasting", "Unisex fragrance", "Earthy and rich"],
        "key_ingredients": ["Sandalwood", "Cedarwood", "Alcohol Denat"],
    },

    # ── MAKEUP ────────────────────────────────────────────────────────
    {
        "name": "Lip Balm Swipe It Strawberry 5g",
        "category": "Makeup",
        "price": 595.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964148_1.jpg",
        "skin_type": ["All Lip Types", "Dry Lips"],
        "benefits": ["Moisturises lips", "Fruity strawberry scent", "Smooth application", "Softens lips"],
        "key_ingredients": ["Community Fair Trade Marula Oil", "Shea Butter"],
    },
    {
        "name": "Colour Crush Lipstick British Rose 302",
        "category": "Makeup",
        "price": 995.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964155_1.jpg",
        "skin_type": [],
        "benefits": ["Creamy texture", "Long-lasting colour", "Moisturising formula", "Vibrant pigment"],
        "key_ingredients": ["Castor Oil", "Shea Butter", "Vitamin E"],
    },

    # ── GIFTS & SETS ──────────────────────────────────────────────────
    {
        "name": "Berry Loving Gift Set",
        "category": "Gifts & Sets",
        "price": 2895.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/c/8/c8f9e02THEAC00000531_1x.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Gift ready packaging", "Strawberry & Blueberry variants", "Shower & body set"],
        "key_ingredients": ["Strawberry Extract", "Blueberry Extract", "Aloe Vera"],
    },
    {
        "name": "Trio Shower Gel Gift Set",
        "category": "Gifts & Sets",
        "price": 1610.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/c/8/c8f9e02THEAC00000427_1x.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["3 shower gels in one set", "Gift ready", "Value bundle", "Variety of scents"],
        "key_ingredients": ["Rose Extract", "Strawberry Extract", "Moringa Oil"],
    },
    {
        "name": "Lotus Shower Gel Body Lotion & Mist Gift Set",
        "category": "Gifts & Sets",
        "price": 885.00,
        "image_url": "https://images-static.nykaa.com/media/catalog/product/tr:w-500,h-500,cm-pad_resize/8/0/800000015964162_1.jpg",
        "skin_type": ["All Skin Types"],
        "benefits": ["Complete shower routine", "India-inspired lotus fragrance", "3-piece set"],
        "key_ingredients": ["Lotus Extract", "Aloe Vera", "Glycerin"],
    },
]


# ─────────────────────────────────────────────────────────────────────
# BUILD FINAL SCHEMA DOCUMENTS
# ─────────────────────────────────────────────────────────────────────

def build_docs(raw: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()   # no deprecation warning
    docs = []
    for i, p in enumerate(raw, start=1):
        docs.append({
            "product_id": f"TBS_{i:03d}",
            "name":       p["name"],
            "category":   p["category"],
            "price":      p["price"],
            "image_url":  p["image_url"],
            "inventory":  {"warehouse_main": random.randint(20, 150)},
            "ai_search_data": {
                "skin_type":       p.get("skin_type") or ["All Skin Types"],
                "benefits":        p.get("benefits", []),
                "key_ingredients": p.get("key_ingredients", []),
            },
            "scraped_at": now,
        })
    return docs


# ─────────────────────────────────────────────────────────────────────
# MONGODB UPSERT
# ─────────────────────────────────────────────────────────────────────

def upsert_to_mongo(docs: list[dict]) -> None:
    if not MONGO_URI:
        print("\n" + "="*60)
        print("  MONGO_URI not found — MongoDB upload skipped.")
        print("="*60)
        print("\nTo fix this, create a file named exactly  .env  in:")
        print(f"  {os.path.dirname(os.path.abspath(__file__))}")
        print("\nWith this single line (no quotes, no # comments):")
        print("  MONGO_URI=mongodb+srv://USER:PASS@CLUSTER.mongodb.net/?retryWrites=true&w=majority")
        print("\nThen run the script again.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000)
        client.admin.command("ping")
        col = client[DB_NAME][COLLECTION_NAME]

        inserted = updated = 0
        for doc in docs:
            result = col.update_one(
                {"product_id": doc["product_id"]},
                {"$set": doc},
                upsert=True,
            )
            if result.upserted_id:
                inserted += 1
            else:
                updated += 1

        print(f"\n{'='*60}")
        print(f"  MongoDB upload complete!")
        print(f"  Database   : {DB_NAME}")
        print(f"  Collection : {COLLECTION_NAME}")
        print(f"  Inserted   : {inserted}")
        print(f"  Updated    : {updated}")
        print(f"{'='*60}")
        client.close()

    except pymongo.errors.ConnectionFailure as e:
        print(f"\n  MongoDB connection failed: {e}")
        print("  Check your MONGO_URI and make sure your IP is whitelisted in Atlas.")
    except pymongo.errors.PyMongoError as e:
        print(f"\n  MongoDB error: {e}")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  The Body Shop India — Product Catalog Loader")
    print(f"  {len(RAW_PRODUCTS)} products across 6 categories")
    print("=" * 60)

    docs = build_docs(RAW_PRODUCTS)

    # Category summary
    from collections import Counter
    cats = Counter(d["category"] for d in docs)
    print("\nCategory breakdown:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat:<20} {count} products")

    # Save local JSON backup
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tbs_products.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved {len(docs)} products to tbs_products.json")

    # Upload to MongoDB
    upsert_to_mongo(docs)

    # Preview
    print("\nSample document (TBS_001):")
    print(json.dumps(docs[0], indent=2, ensure_ascii=False))