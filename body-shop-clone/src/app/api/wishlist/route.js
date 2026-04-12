/**
 * PostgreSQL Schema — paste this into Supabase SQL Editor and run once:
 *
 * CREATE TABLE IF NOT EXISTS public.wishlist (
 *   id          BIGSERIAL PRIMARY KEY,
 *   session_id  TEXT        NOT NULL,
 *   product_id  TEXT        NOT NULL,
 *   added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 *   UNIQUE (session_id, product_id)           -- prevent duplicates
 * );
 *
 * -- Index for fast lookups by session
 * CREATE INDEX IF NOT EXISTS idx_wishlist_session ON public.wishlist (session_id);
 */

import { NextResponse } from "next/server";
import { Pool } from "pg";

// ── Postgres connection (reuses connection pool across hot reloads) ────────────
const pool =
  global._pgPool ||
  (global._pgPool = new Pool({
    connectionString: process.env.POSTGRES_URI, // Set in .env.local
    ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false,
  }));

// ── GET /api/wishlist?session_id=xxx ──────────────────────────────────────────
// Returns all wishlist product_ids for a session.
// Also accepts ?session_id=xxx&product_id=yyy to check a single item.
export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const session_id = searchParams.get("session_id");
    const product_id = searchParams.get("product_id");

    if (!session_id) {
      return NextResponse.json({ error: "session_id is required" }, { status: 400 });
    }

    // Single item check
    if (product_id) {
      const result = await pool.query(
        "SELECT 1 FROM public.wishlist WHERE session_id = $1 AND product_id = $2 LIMIT 1",
        [session_id, product_id]
      );
      return NextResponse.json({ wishlisted: result.rowCount > 0 });
    }

    // All items for session
    const result = await pool.query(
      "SELECT product_id, added_at FROM public.wishlist WHERE session_id = $1 ORDER BY added_at DESC",
      [session_id]
    );
    return NextResponse.json({ items: result.rows });
  } catch (err) {
    console.error("[wishlist GET]", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// ── POST /api/wishlist — add item (idempotent via ON CONFLICT DO NOTHING) ─────
// Body: { session_id: string, product_id: string }
export async function POST(request) {
  try {
    const { session_id, product_id } = await request.json();

    if (!session_id || !product_id) {
      return NextResponse.json(
        { error: "session_id and product_id are required" },
        { status: 400 }
      );
    }

    await pool.query(
      `INSERT INTO public.wishlist (session_id, product_id)
       VALUES ($1, $2)
       ON CONFLICT (session_id, product_id) DO NOTHING`,
      [session_id, product_id]
    );

    return NextResponse.json({ success: true, wishlisted: true });
  } catch (err) {
    console.error("[wishlist POST]", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// ── DELETE /api/wishlist — remove item ───────────────────────────────────────
// Body: { session_id: string, product_id: string }
export async function DELETE(request) {
  try {
    const { session_id, product_id } = await request.json();

    if (!session_id || !product_id) {
      return NextResponse.json(
        { error: "session_id and product_id are required" },
        { status: 400 }
      );
    }

    await pool.query(
      "DELETE FROM public.wishlist WHERE session_id = $1 AND product_id = $2",
      [session_id, product_id]
    );

    return NextResponse.json({ success: true, wishlisted: false });
  } catch (err) {
    console.error("[wishlist DELETE]", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}