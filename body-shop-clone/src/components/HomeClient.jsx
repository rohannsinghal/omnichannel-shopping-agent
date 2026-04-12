"use client";
import { useState, useRef } from "react";
import Link from "next/link";
import { Heart, ChevronLeft, ChevronRight, ArrowRight, ShoppingBag } from "lucide-react";

const G = "#006e3c";

// Updated to use your local public images
const SLIDES = [
  { id: 1, href: "/about", imgSrc: "/hero-1.jpg" },
  { id: 2, href: "/shop/skincare", imgSrc: "/hero-2.jpg" },
  { id: 3, href: "/shop/range", imgSrc: "/hero-3.jpg" },
];

// Updated to use your local public images
const CATEGORY_BANNERS = [
  { label: "Bath & Body",     href: "/shop/body",      img: "/cat-body.jpg" },
  { label: "Face & Skincare", href: "/shop/skincare",  img: "/cat-face.jpg" },
  { label: "Hair Care",       href: "/shop/hair",      img: "/cat-hair.jpg" },
  { label: "Fragrance",       href: "/shop/fragrance", img: "/cat-fragrance.jpg" },
];

function IconRabbit() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <ellipse cx="11" cy="22" rx="4" ry="6" stroke="#006e3c" strokeWidth="2" strokeLinecap="round"/>
      <ellipse cx="25" cy="22" rx="4" ry="6" stroke="#006e3c" strokeWidth="2" strokeLinecap="round"/>
      <ellipse cx="18" cy="26" rx="8" ry="6" fill="#edf7f0" stroke="#006e3c" strokeWidth="2"/>
      <circle cx="15" cy="25" r="1.2" fill="#006e3c"/>
      <circle cx="21" cy="25" r="1.2" fill="#006e3c"/>
      <path d="M16 28 Q18 29.5 20 28" stroke="#006e3c" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}
function IconGlobe() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <circle cx="18" cy="18" r="13" stroke="#006e3c" strokeWidth="2"/>
      <path d="M5 18h26M18 5C14 10 13 14 13 18s1 8 5 13M18 5c4 5 5 9 5 13s-1 8-5 13" stroke="#006e3c" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M7 11h22M7 25h22" stroke="#006e3c" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}
function IconRecycle() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <path d="M18 6 L22 13 H14 Z" fill="#006e3c"/>
      <path d="M28 24 L22 30 V24 Z" fill="#006e3c"/>
      <path d="M8 24 L6 17 H13 Z" fill="#006e3c"/>
      <path d="M22 13 Q30 13 28 24" stroke="#006e3c" strokeWidth="2" strokeLinecap="round" fill="none"/>
      <path d="M22 30 Q12 30 8 24" stroke="#006e3c" strokeWidth="2" strokeLinecap="round" fill="none"/>
      <path d="M6 17 Q6 8 18 6" stroke="#006e3c" strokeWidth="2" strokeLinecap="round" fill="none"/>
    </svg>
  );
}
function IconStar() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <path d="M18 4 L21.5 13.5 H32 L23.5 19.5 L27 29 L18 23 L9 29 L12.5 19.5 L4 13.5 H14.5 Z" fill="#006e3c"/>
    </svg>
  );
}

const BRAND_VALUES = [
  { title: "Against Animal Testing", sub: "We've always been against animal testing", Icon: IconRabbit },
  { title: "Community Fair Trade",   sub: "Supporting communities since 1987",        Icon: IconGlobe  },
  { title: "Sustainable Packaging",  sub: "Working toward 100% recyclable",           Icon: IconRecycle },
  { title: "B Corp Certified",       sub: "Highest standards of social impact",       Icon: IconStar   },
];

function inr(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

function StarRow({ rating = 4 }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <svg key={i} width="13" height="13" viewBox="0 0 20 20">
          <polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7"
            fill={i < Math.round(rating) ? "#f59e0b" : "#e0d8cc"} />
        </svg>
      ))}
    </div>
  );
}

function ProductCard({ p }) {
  const [wished, setWished] = useState(false);
  const [added,  setAdded]  = useState(false);
  const [imgError, setImgError] = useState(false); // State to track broken Nykaa links

  const sizeMatch = p.name.match(/\d+\s?(ml|g|pc|set)/i);
  const sizePart  = sizeMatch ? sizeMatch[0] : "";
  const displayName = sizePart
    ? p.name.replace(new RegExp("\\s*" + sizePart.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$", "i"), "").trim()
    : p.name;

  const handleAddToBag = async (e) => {
    e.preventDefault(); e.stopPropagation();
    setAdded(true); setTimeout(() => setAdded(false), 1600);
    try {
      await fetch("/api/cart", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_id: p.product_id, qty: 1 }) });
      const el = document.getElementById("cart-count");
      if (el) el.textContent = String(parseInt(el.textContent || "0") + 1);
    } catch (_) {}
  };

  return (
    <div className="pcard" style={{ width: 260, flexShrink: 0, scrollSnapAlign: "start" }}>
      <Link href={`/product/${p.product_id}`} style={{ textDecoration: "none" }}>
        <div style={{ position: "relative", backgroundColor: "#f7f3ee", height: 280, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
          
          {/* Automatically fallback to leaf emoji if Nykaa blocks the image load */}
          {!imgError && p.image_url ? (
            <img 
              // Route the image through our local Next.js proxy server!
              src={p.image_url}
              alt={p.name}
              style={{ width: "85%", height: "85%", objectFit: "contain", transition: "transform 0.35s ease" }}
              onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.06)")}
              onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
              onError={() => setImgError(true)} 
            />
          ) : (
            <div style={{ fontSize: 52, opacity: 0.3 }}>🌿</div>
          )}

          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setWished(v => !v); }}
            style={{ position: "absolute", top: 12, right: 12, width: 32, height: 32, borderRadius: "50%", background: "rgba(255,255,255,0.92)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Heart size={15} fill={wished ? "#e11d48" : "none"} color={wished ? "#e11d48" : "#666"} />
          </button>
          <button onClick={handleAddToBag} className="add-bag"
            style={{ position: "absolute", bottom: 0, left: 0, right: 0, backgroundColor: added ? "#004d2a" : G, color: "#fff", fontSize: 11, fontWeight: 800, letterSpacing: "0.08em", padding: "10px 0", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, transition: "background-color 0.2s" }}>
            <ShoppingBag size={13} />{added ? "✓ ADDED!" : "ADD TO BAG"}
          </button>
        </div>
      </Link>
      <Link href={`/product/${p.product_id}`} style={{ textDecoration: "none", color: "inherit", display: "block", padding: "12px 14px 14px" }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: "#1a1a1a", marginBottom: 2, lineHeight: 1.35 }}>{displayName}</h3>
        {sizePart && <p style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>{sizePart}</p>}
        <StarRow rating={4.2} />
        <div style={{ marginTop: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 900, color: "#1a1a1a" }}>{inr(p.price)}</span>
        </div>
        <div style={{ marginTop: 8, display: "inline-block", backgroundColor: "#ffe4f0", border: "1px solid #f9a8d4", borderRadius: 3, padding: "3px 8px", fontSize: 11, fontWeight: 700, color: "#9d174d" }}>
          Voucher with Purchase*
        </div>
      </Link>
    </div>
  );
}

export default function HomeClient({ products }) {
  const [slide, setSlide] = useState(0);
  const carouselRef = useRef(null);
  const prev = () => setSlide(s => (s - 1 + SLIDES.length) % SLIDES.length);
  const next = () => setSlide(s => (s + 1) % SLIDES.length);
  const cur  = SLIDES[slide];

  return (
    <div style={{ backgroundColor: "#fff" }}>
      <style>{`
        .arrow-btn{width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,0.2);border:2px solid rgba(255,255,255,0.5);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.15s;}
        .arrow-btn:hover{background:rgba(255,255,255,0.38);}
        .cat-banner{position:relative;overflow:hidden;border-radius:6px;text-decoration:none;display:block;aspect-ratio:3/4;}
        .cat-banner img{width:100%;height:100%;object-fit:cover;transition:transform 0.45s ease;}
        .cat-banner:hover img{transform:scale(1.06);}
        .cat-label{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top,rgba(0,0,0,0.68) 0%,transparent 100%);padding:36px 18px 18px;color:#fff;font-size:17px;font-weight:800;letter-spacing:0.04em;}
        .scroll-btn{width:40px;height:40px;border-radius:50%;background:#fff;border:2px solid #e0d8cc;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.1);transition:border-color 0.15s;flex-shrink:0;}
        .scroll-btn:hover{border-color:#006e3c;}
        .section-head{font-family:'Libre Baskerville',serif;font-size:26px;font-weight:700;color:#1a1a1a;}
        .add-bag{transform:translateY(100%);transition:transform 0.22s ease;}
        .pcard:hover .add-bag{transform:translateY(0);}
        .pcard{background:#fff;border:1px solid #e8e0d5;border-radius:4px;overflow:hidden;display:flex;flex-direction:column;transition:box-shadow 0.2s;}
        .pcard:hover{box-shadow:0 6px 24px rgba(0,0,0,0.13);}
        #carousel-rec{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;padding-bottom:4px;flex:1;}
        #carousel-rec::-webkit-scrollbar{display:none;}
        @keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
      `}</style>

      {/* ═══ HERO SLIDER ═══ */}
      <section style={{ position: "relative", width: "100%", height: "520px", overflow: "hidden" }}>
        {/* Link wraps the entire image since text is baked in */}
        <Link href={cur.href}>
          <img key={cur.id} src={cur.imgSrc} alt="The Body Shop Banner"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "center top", cursor: "pointer" }} />
        </Link>
        <button onClick={prev} className="arrow-btn" style={{ position: "absolute", left: 20, top: "50%", transform: "translateY(-50%)", zIndex: 3 }}><ChevronLeft size={20} /></button>
        <button onClick={next} className="arrow-btn" style={{ position: "absolute", right: 20, top: "50%", transform: "translateY(-50%)", zIndex: 3 }}><ChevronRight size={20} /></button>
        <div style={{ position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)", display: "flex", gap: 6, zIndex: 3 }}>
          {SLIDES.map((_, i) => (
            <button key={i} onClick={() => setSlide(i)}
              style={{ width: i === slide ? 24 : 8, height: 8, borderRadius: 4, background: i === slide ? "#fff" : "rgba(255,255,255,0.5)", border: "none", cursor: "pointer", transition: "all 0.2s", padding: 0 }} />
          ))}
        </div>
      </section>

      {/* ═══ RECOMMENDED ═══ */}
      <section style={{ maxWidth: 1280, margin: "0 auto", padding: "48px 20px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <h2 className="section-head">Recommended For You</h2>
          {/* View All Button fixed */}
          <Link href="/shop/skincare" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, fontWeight: 700, color: G, textDecoration: "none" }}>View All <ArrowRight size={14} /></Link>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Left Arrow */}
          <button className="scroll-btn" onClick={() => carouselRef.current.scrollBy({ left: -280, behavior: "smooth" })}><ChevronLeft size={18} color="#1a1a1a" /></button>
          
          {/* Container with ref */}
          <div id="carousel-rec" ref={carouselRef}>
            {products.slice(0, 10).length > 0
              ? products.slice(0, 10).map(p => <ProductCard key={p._id} p={p} />)
              : Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} style={{ width: 260, flexShrink: 0, height: 380, borderRadius: 4, background: "linear-gradient(90deg,#f0ece6 25%,#e8e0d5 50%,#f0ece6 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.5s infinite" }} />
                ))
            }
          </div>
          
          {/* Right Arrow */}
          <button className="scroll-btn" onClick={() => carouselRef.current.scrollBy({ left: 280, behavior: "smooth" })}><ChevronRight size={18} color="#1a1a1a" /></button>
        </div>
      </section>


      {/* ═══ SHOP BY CATEGORY ═══ */}
      <section style={{ maxWidth: 1280, margin: "0 auto", padding: "16px 20px 48px" }}>
        <h2 className="section-head" style={{ marginBottom: 20 }}>Shop By Category</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {CATEGORY_BANNERS.map(cat => (
            <Link key={cat.label} href={cat.href} className="cat-banner">
              <img src={cat.img} alt={cat.label} />
              <div className="cat-label">{cat.label}</div>
            </Link>
          ))}
        </div>
      </section>

      {/* ═══ BRAND VALUES ═══ */}
      <section style={{ backgroundColor: "#f5f1eb", padding: "48px 20px", borderTop: "1px solid #e8e0d5", borderBottom: "1px solid #e8e0d5" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 36, textAlign: "center" }}>
          {BRAND_VALUES.map(({ title, sub, Icon }) => (
            <div key={title} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
              <div style={{ width: 76, height: 76, borderRadius: "50%", backgroundColor: "#edf7f0", border: "1.5px solid #c6e8d4", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icon />
              </div>
              <p style={{ fontSize: 14, fontWeight: 800, color: "#1a1a1a", letterSpacing: "0.04em" }}>{title}</p>
              <p style={{ fontSize: 12, color: "#666", lineHeight: 1.6, marginTop: -4 }}>{sub}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}