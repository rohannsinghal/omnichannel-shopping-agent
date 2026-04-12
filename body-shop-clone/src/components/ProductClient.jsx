"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import { Heart, ShoppingBag, SlidersHorizontal, ChevronDown, X } from "lucide-react";

const G = "#006e3c";

function inr(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

function StarRow({ rating = 4 }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <svg key={i} width="12" height="12" viewBox="0 0 20 20">
          <polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7"
            fill={i < Math.round(rating) ? "#f59e0b" : "#e0d8cc"} />
        </svg>
      ))}
    </div>
  );
}

function PLPCard({ p }) {
  const [wished, setWished] = useState(false);
  const [added,  setAdded]  = useState(false);

  const sizeMatch = p.name.match(/\d+\s?(ml|g|pc|set)/i);
  const sizePart  = sizeMatch?.[0] || "";
  const displayName = sizePart
    ? p.name.replace(new RegExp("\\s*" + sizePart.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$", "i"), "").trim()
    : p.name;

  const handleAdd = async (e) => {
    e.preventDefault(); e.stopPropagation();
    setAdded(true); setTimeout(() => setAdded(false), 1500);
    try {
      await fetch("/api/cart", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_id: p.product_id, qty: 1 }) });
      const el = document.getElementById("cart-count");
      if (el) el.textContent = String(parseInt(el.textContent || "0") + 1);
    } catch (_) {}
  };

  return (
    <div style={{ border: "1px solid #e8e0d5", borderRadius: 4, overflow: "hidden", background: "#fff", transition: "box-shadow 0.2s", display: "flex", flexDirection: "column" }}
      onMouseEnter={e => (e.currentTarget.style.boxShadow = "0 6px 24px rgba(0,0,0,0.12)")}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = "none")}>

      <Link href={`/product/${p.product_id}`} style={{ textDecoration: "none" }}>
        <div style={{ position: "relative", backgroundColor: "#f7f3ee", paddingTop: "100%", overflow: "hidden" }}>
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {p.image_url
              ? <img src={p.image_url} alt={p.name} style={{ width: "80%", height: "80%", objectFit: "contain", transition: "transform 0.3s" }}
                  onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.06)")}
                  onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
                  onError={e => { e.currentTarget.style.opacity = "0"; }} />
              : <div style={{ fontSize: 48, opacity: 0.3 }}>🌿</div>
            }
          </div>
          {/* Wishlist */}
          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setWished(v => !v); }}
            style={{ position: "absolute", top: 10, right: 10, width: 30, height: 30, borderRadius: "50%", background: "rgba(255,255,255,0.92)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Heart size={14} fill={wished ? "#e11d48" : "none"} color={wished ? "#e11d48" : "#666"} />
          </button>
        </div>
      </Link>

      <div style={{ padding: "12px 14px 14px", display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
        <Link href={`/product/${p.product_id}`} style={{ textDecoration: "none", color: "inherit" }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: "#1a1a1a", lineHeight: 1.35, margin: 0 }}>{displayName}</h3>
          {sizePart && <p style={{ fontSize: 12, color: "#888", margin: "2px 0 0" }}>{sizePart}</p>}
        </Link>
        <StarRow rating={4.1} />
        <div style={{ fontSize: 15, fontWeight: 900, color: "#1a1a1a" }}>{inr(p.price)}</div>
        <div style={{ display: "inline-block", backgroundColor: "#ffe4f0", border: "1px solid #f9a8d4", borderRadius: 3, padding: "2px 7px", fontSize: 10, fontWeight: 700, color: "#9d174d" }}>
          Voucher with Purchase*
        </div>
        <button onClick={handleAdd}
          style={{ marginTop: "auto", backgroundColor: added ? "#004d2a" : G, color: "#fff", border: "none", padding: "9px 0", borderRadius: 3, fontSize: 11, fontWeight: 800, letterSpacing: "0.08em", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, transition: "background-color 0.2s" }}>
          <ShoppingBag size={13} />{added ? "✓ ADDED!" : "ADD TO BAG"}
        </button>
      </div>
    </div>
  );
}

export default function ShopClient({ products, categoryLabel, bannerImg, categorySlug }) {
  const [sort,       setSort]       = useState("default");
  const [maxPrice,   setMaxPrice]   = useState(5000);
  const [filtersOpen,setFiltersOpen]= useState(false);
  const [search,     setSearch]     = useState("");

  const sorted = useMemo(() => {
    let list = [...products];

    // Text search
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q));
    }

    // Price filter
    list = list.filter(p => Number(p.price) <= maxPrice);

    // Sort
    if (sort === "price-asc")  list.sort((a, b) => a.price - b.price);
    if (sort === "price-desc") list.sort((a, b) => b.price - a.price);
    if (sort === "name")       list.sort((a, b) => a.name.localeCompare(b.name));

    return list;
  }, [products, sort, maxPrice, search]);

  const allPrices = products.map(p => Number(p.price));
  const priceMax  = Math.max(...allPrices, 5000);

  return (
    <div style={{ backgroundColor: "#fff", minHeight: "60vh" }}>
      {/* Category banner */}
      <div style={{ position: "relative", height: 200, overflow: "hidden" }}>
        <img src={bannerImg} alt={categoryLabel} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center" }} />
        <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <h1 style={{ color: "#fff", fontFamily: "'Libre Baskerville',serif", fontSize: "clamp(24px,4vw,42px)", fontWeight: 700, letterSpacing: "0.04em", margin: 0, textAlign: "center" }}>
            {categoryLabel}
          </h1>
        </div>
      </div>

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "24px 20px" }}>
        {/* Toolbar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          <p style={{ fontSize: 13, color: "#666" }}>{sorted.length} products</p>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Search */}
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search products…"
              style={{ padding: "8px 14px", border: "1px solid #e0d8cc", borderRadius: 6, fontSize: 13, outline: "none", fontFamily: "inherit", width: 200 }}
            />

            {/* Filter toggle */}
            <button onClick={() => setFiltersOpen(v => !v)}
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", border: "1px solid #e0d8cc", borderRadius: 6, background: filtersOpen ? G : "#fff", color: filtersOpen ? "#fff" : "#1a1a1a", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
              <SlidersHorizontal size={14} /> Filters
            </button>

            {/* Sort */}
            <div style={{ position: "relative" }}>
              <select value={sort} onChange={e => setSort(e.target.value)}
                style={{ appearance: "none", padding: "8px 32px 8px 14px", border: "1px solid #e0d8cc", borderRadius: 6, fontSize: 13, fontFamily: "inherit", color: "#1a1a1a", background: "#fff", cursor: "pointer", outline: "none" }}>
                <option value="default">Sort: Featured</option>
                <option value="price-asc">Price: Low to High</option>
                <option value="price-desc">Price: High to Low</option>
                <option value="name">Name A–Z</option>
              </select>
              <ChevronDown size={14} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "#888" }} />
            </div>
          </div>
        </div>

        {/* Collapsible filters */}
        {filtersOpen && (
          <div style={{ background: "#f9f6f0", border: "1px solid #e8e0d5", borderRadius: 8, padding: "20px 24px", marginBottom: 24, display: "flex", alignItems: "center", gap: 32, flexWrap: "wrap" }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 700, color: "#888", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>Max Price: {inr(maxPrice)}</p>
              <input type="range" min={200} max={priceMax} step={100} value={maxPrice} onChange={e => setMaxPrice(Number(e.target.value))}
                style={{ width: 220, accentColor: G }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#888", marginTop: 4 }}>
                <span>₹200</span><span>{inr(priceMax)}</span>
              </div>
            </div>
            <button onClick={() => { setMaxPrice(priceMax); setSearch(""); setSort("default"); }}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#888", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit" }}>
              <X size={13} /> Clear filters
            </button>
          </div>
        )}

        {/* Product grid */}
        {sorted.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "#888" }}>
            <p style={{ fontSize: 18, marginBottom: 8 }}>No products found</p>
            <p style={{ fontSize: 14 }}>Try adjusting your filters or search term</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 20 }}>
            {sorted.map(p => <PLPCard key={p._id} p={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}