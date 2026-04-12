"use client";

import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { Heart, ShoppingBag, Trash2, ArrowRight } from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getSessionId() {
  if (typeof window === "undefined") return "guest";
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = `sess_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("session_id", id);
  }
  return id;
}

// ─── Product Card (matches your existing ProductCard style) ──────────────────
function WishlistCard({ product, onRemove, onAddToCart }) {
  const [removing, setRemoving] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addedSuccess, setAddedSuccess] = useState(false);

  const handleRemove = async () => {
    setRemoving(true);
    await onRemove(product.product_id);
  };

  const handleAddToCart = async () => {
    setAdding(true);
    const ok = await onAddToCart(product.product_id);
    if (ok) {
      setAddedSuccess(true);
      setTimeout(() => setAddedSuccess(false), 2000);
    }
    setAdding(false);
  };

  return (
    <div
      className={`group relative bg-white rounded-2xl overflow-hidden border border-[#e8e0d8] transition-all duration-500 hover:shadow-xl hover:-translate-y-1 ${
        removing ? "opacity-0 scale-95 pointer-events-none" : "opacity-100 scale-100"
      }`}
      style={{ transition: "opacity 0.4s, transform 0.4s" }}
    >
      {/* Image */}
      <Link href={`/product/${product.product_id}`} className="block">
        <div className="relative aspect-square bg-[#f0ede8] overflow-hidden">
          <Image
            src={product.image_url || `/products/${product.product_id}.jpg`}
            alt={product.name || "Product"}
            fill
            className="object-cover object-center group-hover:scale-105 transition-transform duration-700"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          />
        </div>
      </Link>

      {/* Remove button */}
      <button
        onClick={handleRemove}
        className="absolute top-3 right-3 w-8 h-8 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow hover:bg-[#fdecea] transition-colors"
        aria-label="Remove from wishlist"
      >
        <Trash2 size={14} className="text-[#c0392b]" />
      </button>

      {/* Details */}
      <div className="p-4 flex flex-col gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#006b3f]">
          {product.category || "Skin Care"}
        </span>
        <Link href={`/product/${product.product_id}`}>
          <h3 className="text-sm font-semibold text-[#1a1a1a] leading-snug line-clamp-2 hover:text-[#006b3f] transition-colors">
            {product.name}
          </h3>
        </Link>

        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-lg font-bold text-[#1a1a1a]">
            ₹{product.price?.toFixed ? product.price.toFixed(2) : product.price}
          </span>
          {product.price && (
            <span className="text-xs text-[#aaa] line-through">
              ₹{(product.price * 1.2).toFixed(2)}
            </span>
          )}
        </div>

        {/* AI skin type tags */}
        {product.ai_search_data?.skin_type && (
          <div className="flex flex-wrap gap-1 mt-1">
            {(Array.isArray(product.ai_search_data.skin_type)
              ? product.ai_search_data.skin_type
              : [product.ai_search_data.skin_type]
            )
              .slice(0, 2)
              .map((t) => (
                <span
                  key={t}
                  className="text-[10px] bg-[#f0ede8] text-[#555] px-2 py-0.5 rounded-full"
                >
                  {t}
                </span>
              ))}
          </div>
        )}

        {/* Add to Bag */}
        <button
          onClick={handleAddToCart}
          disabled={adding}
          className={`mt-2 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            addedSuccess
              ? "bg-[#2ecc71] text-white"
              : "bg-[#006b3f] hover:bg-[#005530] text-white active:scale-[0.97]"
          } disabled:opacity-70`}
        >
          {adding ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : addedSuccess ? (
            <>✓ Added!</>
          ) : (
            <>
              <ShoppingBag size={15} />
              Add to Bag
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyWishlist() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-20 h-20 bg-[#f0ede8] rounded-full flex items-center justify-center mb-6">
        <Heart size={36} className="text-[#ccc]" />
      </div>
      <h2 className="font-serif text-2xl text-[#1a1a1a] mb-2">
        Your wishlist is empty
      </h2>
      <p className="text-[#888] text-sm max-w-xs mb-8">
        Save your favourite products here so you never lose track of what you love.
      </p>
      <Link
        href="/shop/all"
        className="flex items-center gap-2 px-8 py-3 bg-[#006b3f] text-white rounded-xl text-sm font-semibold hover:bg-[#005530] transition-all"
      >
        Start Shopping <ArrowRight size={16} />
      </Link>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function WishlistPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // ── Load wishlist: Postgres → product_ids → MongoDB details ──
  const loadWishlist = useCallback(async () => {
    setLoading(true);
    try {
      const session_id = getSessionId();

      // 1. Fetch product_ids from Postgres via wishlist API
      const pgRes = await fetch(`/api/wishlist?session_id=${session_id}`);
      const pgData = await pgRes.json();
      const items = pgData.items || [];

      if (items.length === 0) {
        setProducts([]);
        return;
      }

      // 2. Fetch product details from MongoDB for each product_id
      // Batch them if your /api/products supports it, otherwise parallelise
      const detailPromises = items.map((item) =>
        fetch(`/api/products?search=${encodeURIComponent(item.product_id)}`)
          .then((r) => r.json())
          .then((data) => {
            // API may return array or single object
            const prod = Array.isArray(data) ? data[0] : data;
            return prod || null;
          })
          .catch(() => null)
      );

      const details = await Promise.all(detailPromises);
      // Filter out nulls (products that may have been removed from catalog)
      setProducts(details.filter(Boolean));
    } catch (err) {
      console.error("[wishlist load]", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWishlist();
  }, [loadWishlist]);

  // ── Remove from wishlist ──
  const handleRemove = async (product_id) => {
    const session_id = getSessionId();
    // Optimistic UI — remove from state first
    setProducts((prev) => prev.filter((p) => p.product_id !== product_id));
    await fetch("/api/wishlist", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, product_id }),
    });
  };

  // ── Add to Cart ──
  const handleAddToCart = async (product_id) => {
    const session_id = getSessionId();
    try {
      const res = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id, quantity: 1, session_id }),
      });
      return res.ok;
    } catch {
      return false;
    }
  };

  return (
    <main className="min-h-screen bg-[#faf8f5]">
      {/* ── Header ── */}
      <div className="bg-white border-b border-[#e8e0d8]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Heart size={24} className="text-[#006b3f]" />
              <h1 className="font-serif text-3xl text-[#1a1a1a]">My Wishlist</h1>
              {!loading && products.length > 0 && (
                <span className="text-sm text-[#888] ml-1">
                  ({products.length} {products.length === 1 ? "item" : "items"})
                </span>
              )}
            </div>
            {!loading && products.length > 0 && (
              <Link
                href="/shop/all"
                className="flex items-center gap-1.5 text-sm text-[#006b3f] font-semibold hover:underline"
              >
                Continue Shopping <ArrowRight size={14} />
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-2xl overflow-hidden border border-[#e8e0d8]">
                <div className="aspect-square bg-[#f0ede8] animate-pulse" />
                <div className="p-4 space-y-2">
                  <div className="h-3 bg-[#f0ede8] rounded animate-pulse w-1/2" />
                  <div className="h-4 bg-[#f0ede8] rounded animate-pulse" />
                  <div className="h-4 bg-[#f0ede8] rounded animate-pulse w-2/3" />
                  <div className="h-10 bg-[#f0ede8] rounded-xl animate-pulse mt-2" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && products.length === 0 && <EmptyWishlist />}

        {/* Product grid */}
        {!loading && products.length > 0 && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map((product) => (
                <WishlistCard
                  key={product.product_id}
                  product={product}
                  onRemove={handleRemove}
                  onAddToCart={handleAddToCart}
                />
              ))}
            </div>

            {/* Move all to bag CTA */}
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-between gap-4 bg-[#f0ede8] rounded-2xl p-6">
              <div>
                <p className="font-semibold text-[#1a1a1a]">Ready to checkout?</p>
                <p className="text-sm text-[#555]">
                  Add all your wishlist items to the bag and complete your order.
                </p>
              </div>
              <button
                onClick={async () => {
                  for (const p of products) {
                    await handleAddToCart(p.product_id);
                  }
                  window.location.href = "/cart";
                }}
                className="shrink-0 flex items-center gap-2 px-8 py-3 bg-[#006b3f] text-white rounded-xl text-sm font-semibold hover:bg-[#005530] transition-all"
              >
                <ShoppingBag size={16} />
                Move All to Bag
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}