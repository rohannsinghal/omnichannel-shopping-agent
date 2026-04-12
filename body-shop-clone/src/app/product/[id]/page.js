"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import {
  Plus,
  Minus,
  Heart,
  ShoppingBag,
  Star,
  ChevronRight,
  Leaf,
  Truck,
  RotateCcw,
} from "lucide-react";

// ─── Accordion Component ──────────────────────────────────────────────────────
function Accordion({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-[#e8e0d8]">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center py-4 text-left group"
        aria-expanded={open}
      >
        <span className="font-semibold text-[#1a1a1a] text-sm tracking-wide uppercase">
          {title}
        </span>
        <span className="text-[#006b3f] transition-transform duration-300">
          {open ? <Minus size={18} /> : <Plus size={18} />}
        </span>
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          open ? "max-h-96 pb-4" : "max-h-0"
        }`}
      >
        <div className="text-[#555] text-sm leading-relaxed">{children}</div>
      </div>
    </div>
  );
}

// ─── Rating Bar Component ─────────────────────────────────────────────────────
function RatingBar({ stars, percent, count }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-12 text-right text-[#555] shrink-0">{stars} star</span>
      <div className="flex-1 h-2 bg-[#e8e0d8] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#006b3f] rounded-full transition-all duration-700"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="w-8 text-[#555] shrink-0">{count}</span>
    </div>
  );
}

// ─── Static Reviews Data ──────────────────────────────────────────────────────
const REVIEWS_DATA = [
  { stars: 5, percent: 72, count: 312 },
  { stars: 4, percent: 18, count: 78 },
  { stars: 3, percent: 6, count: 26 },
  { stars: 2, percent: 2, count: 9 },
  { stars: 1, percent: 2, count: 8 },
];
const AVG_RATING = 4.6;
const TOTAL_REVIEWS = 433;

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [addingToCart, setAddingToCart] = useState(false);
  const [cartSuccess, setCartSuccess] = useState(false);
  const [wishlisted, setWishlisted] = useState(false);

  // ── Fetch product from MongoDB via /api/products ──
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/products?search=${encodeURIComponent(id)}`)
      .then((r) => r.json())
      .then((data) => {
        // API may return array or object; handle both
        const prod = Array.isArray(data) ? data[0] : data;
        if (!prod) throw new Error("Product not found");
        setProduct(prod);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // ── Check wishlist state on load ──
  useEffect(() => {
    const SESSION_ID =
      typeof window !== "undefined"
        ? localStorage.getItem("session_id") || "guest"
        : "guest";
    fetch(`/api/wishlist?session_id=${SESSION_ID}&product_id=${id}`)
      .then((r) => r.json())
      .then((data) => setWishlisted(!!data?.wishlisted))
      .catch(() => {});
  }, [id]);

  // ── Add to Cart ──
  const handleAddToCart = async () => {
    if (!product) return;
    setAddingToCart(true);
    try {
      const SESSION_ID =
        localStorage.getItem("session_id") || "guest";
      const res = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: product.product_id,
          quantity,
          session_id: SESSION_ID,
        }),
      });
      if (!res.ok) throw new Error("Failed to add to cart");
      setCartSuccess(true);
      setTimeout(() => setCartSuccess(false), 2500);
    } catch (e) {
      alert("Could not add to cart. Please try again.");
    } finally {
      setAddingToCart(false);
    }
  };

  // ── Toggle Wishlist ──
  const handleWishlist = async () => {
    const SESSION_ID =
      localStorage.getItem("session_id") || "guest";
    const newState = !wishlisted;
    setWishlisted(newState);
    await fetch("/api/wishlist", {
      method: newState ? "POST" : "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: SESSION_ID,
        product_id: product?.product_id || id,
      }),
    });
  };

  // ── States ──
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#faf8f5]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-[#006b3f] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#555] text-sm tracking-widest uppercase">
            Loading product…
          </p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#faf8f5]">
        <div className="text-center">
          <p className="text-xl font-semibold text-[#1a1a1a] mb-2">
            Product not found
          </p>
          <Link
            href="/shop/all"
            className="text-[#006b3f] underline text-sm"
          >
            Back to Shop
          </Link>
        </div>
      </div>
    );
  }

  const aiData = product.ai_search_data || {};

  return (
    <main className="min-h-screen bg-[#faf8f5]">
      {/* ── Breadcrumb ── */}
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-1 text-xs text-[#888]">
        <Link href="/" className="hover:text-[#006b3f] transition-colors">
          Home
        </Link>
        <ChevronRight size={12} />
        <Link
          href={`/shop/${product.category?.toLowerCase() || "all"}`}
          className="hover:text-[#006b3f] transition-colors capitalize"
        >
          {product.category || "Shop"}
        </Link>
        <ChevronRight size={12} />
        <span className="text-[#1a1a1a] font-medium truncate max-w-[200px]">
          {product.name}
        </span>
      </nav>

      {/* ── Product Split Layout ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16">

          {/* LEFT — Image Panel */}
          <div className="relative">
            <div className="sticky top-6">
              {/* Main image */}
              <div className="relative aspect-square bg-[#f0ede8] rounded-2xl overflow-hidden group">
                <Image
                  src={product.image_url || `/products/${product.product_id}.jpg`}
                  alt={product.name}
                  fill
                  className="object-cover object-center group-hover:scale-105 transition-transform duration-700"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                  priority
                />
                {/* Wishlist button overlay */}
                <button
                  onClick={handleWishlist}
                  className="absolute top-4 right-4 w-10 h-10 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-md hover:scale-110 transition-transform"
                  aria-label="Toggle wishlist"
                >
                  <Heart
                    size={18}
                    className={wishlisted ? "fill-[#c0392b] text-[#c0392b]" : "text-[#888]"}
                  />
                </button>
                {/* Eco badge */}
                <div className="absolute bottom-4 left-4 flex items-center gap-1 bg-[#006b3f]/90 text-white text-xs px-3 py-1.5 rounded-full">
                  <Leaf size={12} />
                  <span className="font-medium">Ethically Sourced</span>
                </div>
              </div>

              {/* Thumbnail strip (static placeholder) */}
              <div className="flex gap-3 mt-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className={`relative w-20 h-20 rounded-xl overflow-hidden cursor-pointer border-2 transition-all ${
                      i === 1 ? "border-[#006b3f]" : "border-transparent hover:border-[#ccc]"
                    }`}
                  >
                    <Image
                      src={product.image_url || `/products/${product.product_id}.jpg`}
                      alt={`View ${i}`}
                      fill
                      className="object-cover"
                      sizes="80px"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT — Details Panel */}
          <div className="flex flex-col gap-5 pt-2">

            {/* Category tag */}
            <span className="text-xs font-semibold tracking-[0.15em] uppercase text-[#006b3f]">
              {product.category || "Skin Care"}
            </span>

            {/* Product name */}
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1a1a1a] leading-tight">
              {product.name}
            </h1>

            {/* Star rating */}
            <div className="flex items-center gap-2">
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star
                    key={s}
                    size={15}
                    className={
                      s <= Math.round(AVG_RATING)
                        ? "fill-[#f5a623] text-[#f5a623]"
                        : "text-[#ddd]"
                    }
                  />
                ))}
              </div>
              <span className="text-sm text-[#555]">
                {AVG_RATING} ({TOTAL_REVIEWS} reviews)
              </span>
            </div>

            {/* Price */}
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-[#1a1a1a]">
                ₹{product.price?.toFixed ? product.price.toFixed(2) : product.price}
              </span>
              <span className="text-sm text-[#888] line-through">
                ₹{product.price ? (product.price * 1.2).toFixed(2) : ""}
              </span>
              <span className="text-xs font-semibold text-[#c0392b] bg-[#fdecea] px-2 py-0.5 rounded">
                20% OFF
              </span>
            </div>

            {/* Size selector (static) */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#888] mb-2">
                Size
              </p>
              <div className="flex gap-2">
                {["60ml", "125ml", "250ml"].map((s) => (
                  <button
                    key={s}
                    className={`px-4 py-2 text-sm border rounded-lg transition-all ${
                      s === "125ml"
                        ? "border-[#006b3f] bg-[#006b3f] text-white font-semibold"
                        : "border-[#ddd] text-[#555] hover:border-[#006b3f]"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Quantity + Add to Bag */}
            <div className="flex items-center gap-3">
              {/* Quantity stepper */}
              <div className="flex items-center border border-[#ddd] rounded-xl overflow-hidden">
                <button
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  className="w-10 h-12 flex items-center justify-center text-[#555] hover:bg-[#f0ede8] transition-colors"
                >
                  <Minus size={16} />
                </button>
                <span className="w-10 text-center text-sm font-semibold text-[#1a1a1a]">
                  {quantity}
                </span>
                <button
                  onClick={() => setQuantity((q) => q + 1)}
                  className="w-10 h-12 flex items-center justify-center text-[#555] hover:bg-[#f0ede8] transition-colors"
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* Add to Bag CTA */}
              <button
                onClick={handleAddToCart}
                disabled={addingToCart}
                className={`flex-1 h-12 flex items-center justify-center gap-2 rounded-xl font-semibold text-sm tracking-wide uppercase transition-all ${
                  cartSuccess
                    ? "bg-[#2ecc71] text-white"
                    : "bg-[#006b3f] hover:bg-[#005530] text-white active:scale-[0.98]"
                } disabled:opacity-70`}
              >
                {addingToCart ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : cartSuccess ? (
                  <>✓ Added to Bag!</>
                ) : (
                  <>
                    <ShoppingBag size={17} />
                    Add to Bag
                  </>
                )}
              </button>

              {/* Wishlist heart */}
              <button
                onClick={handleWishlist}
                className={`w-12 h-12 flex items-center justify-center border rounded-xl transition-all ${
                  wishlisted
                    ? "border-[#c0392b] bg-[#fdecea]"
                    : "border-[#ddd] hover:border-[#c0392b]"
                }`}
                aria-label="Wishlist"
              >
                <Heart
                  size={18}
                  className={wishlisted ? "fill-[#c0392b] text-[#c0392b]" : "text-[#888]"}
                />
              </button>
            </div>

            {/* Trust strip */}
            <div className="flex gap-4 py-4 border-y border-[#e8e0d8]">
              {[
                { icon: <Truck size={16} />, label: "Free delivery ₹499+" },
                { icon: <RotateCcw size={16} />, label: "Easy returns" },
                { icon: <Leaf size={16} />, label: "Cruelty-free" },
              ].map(({ icon, label }) => (
                <div key={label} className="flex items-center gap-1.5 text-xs text-[#555]">
                  <span className="text-[#006b3f]">{icon}</span>
                  {label}
                </div>
              ))}
            </div>

            {/* ── What does it do for you? ── */}
            <div className="bg-[#f0ede8] rounded-2xl p-6">
              <h2 className="font-serif text-xl text-[#1a1a1a] mb-3">
                What does it do for you?
              </h2>
              <p className="text-[#555] text-sm leading-relaxed">
                {aiData.benefits
                  ? Array.isArray(aiData.benefits)
                    ? aiData.benefits.join(". ") + "."
                    : aiData.benefits
                  : `Formulated to deeply nourish and revitalise your skin, this product is enriched with community trade ingredients sourced directly from our partners around the world. It absorbs quickly without leaving a greasy residue, leaving skin feeling soft, hydrated, and looking healthy — all while honouring our commitment to being kind to the planet.`}
              </p>
              {aiData.skin_type && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {(Array.isArray(aiData.skin_type)
                    ? aiData.skin_type
                    : [aiData.skin_type]
                  ).map((type) => (
                    <span
                      key={type}
                      className="text-xs bg-white text-[#006b3f] border border-[#006b3f]/20 px-3 py-1 rounded-full font-medium"
                    >
                      {type}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* ── Accordions ── */}
            <div className="border-b border-[#e8e0d8]">
              <Accordion title="Key Ingredients">
                <ul className="space-y-2">
                  {aiData.key_ingredients
                    ? (Array.isArray(aiData.key_ingredients)
                        ? aiData.key_ingredients
                        : [aiData.key_ingredients]
                      ).map((ing) => (
                        <li key={ing} className="flex items-start gap-2">
                          <span className="text-[#006b3f] mt-0.5">•</span>
                          <span>{ing}</span>
                        </li>
                      ))
                    : [
                        "Community Trade shea butter from Ghana — intensely moisturising",
                        "Glycerine — draws moisture to the skin",
                        "Vitamin E — a powerful antioxidant",
                        "Aloe vera leaf extract — soothing and hydrating",
                      ].map((ing) => (
                        <li key={ing} className="flex items-start gap-2">
                          <span className="text-[#006b3f] mt-0.5">•</span>
                          <span>{ing}</span>
                        </li>
                      ))}
                </ul>
              </Accordion>

              <Accordion title="Full Ingredients List">
                <p className="text-xs text-[#777] leading-loose">
                  Aqua (Water), Glycerin, Butyrospermum Parkii (Shea) Butter, Cetearyl Alcohol,
                  Ceteareth-20, Dimethicone, Tocopheryl Acetate, Carbomer, Sodium Hydroxide,
                  Parfum (Fragrance), Phenoxyethanol, Ethylhexylglycerin, Benzyl Alcohol,
                  Limonene, Linalool, Citronellol.
                </p>
              </Accordion>

              <Accordion title="How to Use">
                <ol className="space-y-2 list-decimal list-inside text-[#555]">
                  <li>Apply a generous amount to clean, slightly damp skin.</li>
                  <li>Massage in circular motions until fully absorbed.</li>
                  <li>Focus on dry areas like elbows, knees, and heels.</li>
                  <li>Use morning and evening for best results.</li>
                  <li>For external use only. Avoid contact with eyes.</li>
                </ol>
              </Accordion>

              <Accordion title="Delivery & Returns">
                <div className="space-y-2 text-[#555]">
                  <p>
                    <strong className="text-[#1a1a1a]">Standard Delivery:</strong> 5–7 working
                    days. Free on orders over ₹499.
                  </p>
                  <p>
                    <strong className="text-[#1a1a1a]">Express Delivery:</strong> 2–3 working
                    days. ₹99.
                  </p>
                  <p>
                    <strong className="text-[#1a1a1a]">Returns:</strong> We accept returns within
                    30 days of delivery for unused products in original packaging.
                  </p>
                </div>
              </Accordion>
            </div>
          </div>
        </div>
      </section>

      {/* ── Ratings & Reviews Section ── */}
      <section className="bg-white border-t border-[#e8e0d8] py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <h2 className="font-serif text-2xl text-[#1a1a1a] mb-8">
            Ratings &amp; Reviews
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 lg:gap-16">
            {/* Score overview */}
            <div className="flex items-center gap-8">
              <div className="text-center shrink-0">
                <p className="text-7xl font-serif text-[#1a1a1a] leading-none">{AVG_RATING}</p>
                <div className="flex justify-center gap-0.5 mt-2">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star
                      key={s}
                      size={16}
                      className={
                        s <= Math.round(AVG_RATING)
                          ? "fill-[#f5a623] text-[#f5a623]"
                          : "fill-[#ddd] text-[#ddd]"
                      }
                    />
                  ))}
                </div>
                <p className="text-xs text-[#888] mt-1">{TOTAL_REVIEWS} reviews</p>
              </div>
              <div className="flex-1 space-y-2">
                {REVIEWS_DATA.map((r) => (
                  <RatingBar key={r.stars} {...r} />
                ))}
              </div>
            </div>

            {/* Sample review card */}
            <div className="bg-[#faf8f5] rounded-2xl p-6 border border-[#e8e0d8]">
              <div className="flex gap-0.5 mb-2">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star key={s} size={14} className="fill-[#f5a623] text-[#f5a623]" />
                ))}
              </div>
              <p className="font-semibold text-[#1a1a1a] mb-1">
                Absolutely love this product!
              </p>
              <p className="text-sm text-[#555] leading-relaxed">
                I've been using this for three months and my skin has never felt better.
                The texture is luxurious without being heavy, and it absorbs instantly.
                Will definitely repurchase!
              </p>
              <p className="text-xs text-[#888] mt-3">— Priya S., Mumbai · Verified Purchase</p>
            </div>
          </div>

          <button className="mt-8 px-8 py-3 border border-[#006b3f] text-[#006b3f] rounded-xl text-sm font-semibold hover:bg-[#006b3f] hover:text-white transition-all">
            Read All Reviews
          </button>
        </div>
      </section>
    </main>
  );
}