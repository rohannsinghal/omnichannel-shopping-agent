// src/app/api/products/[id]/route.js
import { NextResponse } from "next/server";
import { MongoClient } from "mongodb";

let cachedClient = null;
async function getClient() {
  if (cachedClient) return cachedClient;
  const client = new MongoClient(process.env.MONGO_URI);
  await client.connect();
  cachedClient = client;
  return client;
}

export async function GET(request, { params }) {
  const { id } = await params;
  try {
    const client  = await getClient();
    const db      = client.db("bodyshop");
    const col     = db.collection("products");
    const product = await col.findOne({ product_id: id });
    if (!product) return NextResponse.json({ product: null }, { status: 404 });
    return NextResponse.json({ product: { ...product, _id: product._id.toString() } });
  } catch (err) {
    return NextResponse.json({ product: null, error: err.message }, { status: 500 });
  }
}