// src/app/api/products/route.js
// Returns products from MongoDB.  Supports ?limit=N and ?category=X

import { NextResponse } from "next/server";
import { MongoClient } from "mongodb";

// Reuse the MongoClient across hot-reloads in dev (avoids connection floods)
let cachedClient = null;

async function getClient() {
  if (cachedClient) return cachedClient;
  const client = new MongoClient(process.env.MONGO_URI);
  await client.connect();
  cachedClient = client;
  return client;
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const limit    = parseInt(searchParams.get("limit")    || "12", 10);
  const category = searchParams.get("category") || null;  // e.g. "Skincare"
  const search   = searchParams.get("search")   || null;

  try {
    const client = await getClient();
    const db     = client.db("omnichannel_db");            // ← your DB name
    const col    = db.collection("products");        // ← your collection name

    // Build query filter
    const filter = {};
    if (category) filter.category = { $regex: category, $options: "i" };
    if (search)   filter.name     = { $regex: search,   $options: "i" };

    const products = await col
      .find(filter)
      .limit(limit)
      .toArray();

    // Sanitise _id (ObjectId → string) for JSON serialisation
    const sanitised = products.map(p => ({
      ...p,
      _id: p._id.toString(),
    }));

    return NextResponse.json({ products: sanitised });
  } catch (err) {
    console.error("MongoDB error:", err);
    return NextResponse.json({ products: [], error: err.message }, { status: 500 });
  }
}