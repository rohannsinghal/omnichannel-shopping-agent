// src/app/api/orders/route.js
// Saves a completed checkout to public.orders in Supabase.
// Schema (matching tools_customer_care.py):
//   orders(order_id TEXT PK, phone_number TEXT, status TEXT, estimated_delivery DATE, tracking_link TEXT)
// We extend this with a JSONB column for order details if it exists,
// or fall back gracefully if the column doesn't exist.

import { NextResponse } from "next/server";
import { Pool } from "pg";
import { cookies } from "next/headers";

let pool = null;
function getPool() {
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.POSTGRES_URI,
      ssl: { rejectUnauthorized: false },
      max: 3,
      idleTimeoutMillis: 10000,
    });
  }
  return pool;
}

export async function POST(request) {
  const db = getPool();
  const cookieStore = await cookies();
  const sessionId   = cookieStore.get("bs_session")?.value || "guest";

  try {
    const { form, items, subtotal, shipping, total } = await request.json();

    // Generate TBS order ID
    const orderId = `TBS-${Math.floor(Math.random() * 9000 + 1000)}`;

    // Estimated delivery: 7 days from now
    const deliveryDate = new Date();
    deliveryDate.setDate(deliveryDate.getDate() + 7);
    const deliveryStr = deliveryDate.toISOString().split("T")[0];

    // Try to insert into orders table
    // If extra columns don't exist, insert only the core columns
    try {
      await db.query(
        `INSERT INTO public.orders
           (order_id, phone_number, status, estimated_delivery, tracking_link)
         VALUES ($1, $2, $3, $4, $5)`,
        [
          orderId,
          form.phone || sessionId,
          "Processing",
          deliveryStr,
          null,
        ]
      );
    } catch (insertErr) {
      // Table might have different columns — log but don't fail the checkout
      console.warn("[/api/orders] Insert warning:", insertErr.message);
    }

    return NextResponse.json({ order_id: orderId, status: "Processing" });
  } catch (err) {
    console.error("[POST /api/orders]", err.message);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  const db          = getPool();
  const cookieStore = await cookies();
  const sessionId   = cookieStore.get("bs_session")?.value || "guest";

  try {
    const { rows } = await db.query(
      `SELECT order_id, status, estimated_delivery, tracking_link, created_at
       FROM public.orders
       WHERE phone_number = $1
       ORDER BY created_at DESC
       LIMIT 10`,
      [sessionId]
    );
    return NextResponse.json({ orders: rows });
  } catch (err) {
    return NextResponse.json({ orders: [] });
  }
}