// src/app/api/cart/route.js
import { NextResponse } from "next/server";
import { Pool } from "pg";
import { cookies } from "next/headers";
import { randomUUID } from "crypto";

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

async function getSessionId() {
  const cookieStore = await cookies();
  return cookieStore.get("bs_session")?.value || `guest_${randomUUID()}`;
}

export async function GET() {
  const db = getPool();
  const sessionId = await getSessionId();
  try {
    const { rows } = await db.query(
      `SELECT sc.product_id, sc.quantity AS qty, inv.name, inv.price
       FROM public.shopping_cart sc
       LEFT JOIN public.inventory inv USING (product_id)
       WHERE sc.phone_number = $1 ORDER BY sc.added_at`,
      [sessionId]
    );
    return NextResponse.json({ items: rows });
  } catch (err) {
    return NextResponse.json({ items: [], error: err.message }, { status: 500 });
  }
}

export async function POST(request) {
  const db = getPool();
  const cookieStore = await cookies();
  let sessionId = cookieStore.get("bs_session")?.value || `guest_${randomUUID()}`;

  try {
    const { product_id, qty = 1 } = await request.json();

    // 1. Validate against Postgres Inventory (No image_url here!)
    const check = await db.query(
      "SELECT name, price, stock_quantity FROM public.inventory WHERE product_id = $1",
      [product_id]
    );
    
    if (check.rows.length === 0) {
      return NextResponse.json({ error: "Product not found in inventory" }, { status: 404 });
    }

    // Optional: You can add `if (check.rows[0].stock_quantity < qty) throw new Error("Out of stock");` here!

    // 2. Insert into the Cart
    await db.query(
      `INSERT INTO public.shopping_cart (cart_id, phone_number, product_id, quantity, added_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (phone_number, product_id)
       DO UPDATE SET quantity = shopping_cart.quantity + $4`,
      [randomUUID(), sessionId, product_id, qty]
    );

    // 3. Fetch the updated cart to send back to the UI
    const { rows } = await db.query(
      `SELECT sc.product_id, sc.quantity AS qty, inv.name, inv.price
       FROM public.shopping_cart sc
       LEFT JOIN public.inventory inv USING (product_id)
       WHERE sc.phone_number = $1 ORDER BY sc.added_at`,
      [sessionId]
    );

    const res = NextResponse.json({ items: rows, added: true });
    res.cookies.set("bs_session", sessionId, { httpOnly: true, maxAge: 60 * 60 * 24 * 30, sameSite: "lax", path: "/" });
    return res;
  } catch (err) {
    console.error("[POST /api/cart]", err.message);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  const db = getPool();
  const sessionId = await getSessionId();
  try {
    const body = await request.json().catch(() => ({}));
    if (body.product_id) {
      await db.query("DELETE FROM public.shopping_cart WHERE phone_number = $1 AND product_id = $2", [sessionId, body.product_id]);
    } else {
      await db.query("DELETE FROM public.shopping_cart WHERE phone_number = $1", [sessionId]);
    }
    const { rows } = await db.query(
      `SELECT sc.product_id, sc.quantity AS qty, inv.name, inv.price
       FROM public.shopping_cart sc
       LEFT JOIN public.inventory inv USING (product_id)
       WHERE sc.phone_number = $1 ORDER BY sc.added_at`,
      [sessionId]
    );
    return NextResponse.json({ items: rows });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function PATCH(request) {
  const db = getPool();
  const sessionId = await getSessionId();
  try {
    const { product_id, qty } = await request.json();
    if (qty < 1) {
      await db.query("DELETE FROM public.shopping_cart WHERE phone_number = $1 AND product_id = $2", [sessionId, product_id]);
    } else {
      await db.query("UPDATE public.shopping_cart SET quantity = $1 WHERE phone_number = $2 AND product_id = $3", [qty, sessionId, product_id]);
    }
    const { rows } = await db.query(
      `SELECT sc.product_id, sc.quantity AS qty, inv.name, inv.price
       FROM public.shopping_cart sc
       LEFT JOIN public.inventory inv USING (product_id)
       WHERE sc.phone_number = $1 ORDER BY sc.added_at`,
      [sessionId]
    );
    return NextResponse.json({ items: rows });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}