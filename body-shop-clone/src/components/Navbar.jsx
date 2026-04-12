"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, Heart, User, ShoppingBag, MapPin, X, ChevronDown } from "lucide-react";

const G = "#006e3c";
const W = "#ffffff";

const NAV_ITEMS = [
  { label: "MOST LOVED",     href: "/most-loved",   highlight: true },
  { label: "BESTSELLERS",    href: "/bestsellers" },
  { label: "SALE",           href: "/sale",         highlight: true },
  { label: "COMBOS",         href: "/combos" },
  {
    label: "BATH & BODY", href: "/shop/body",
    cols: [
      { head: "Shop Body",  links: [["View All Body","/shop/body"],["Body Butters","/shop/body?sub=body-butters"],["Body Lotions","/shop/body?sub=body-lotions"],["Body Scrubs","/shop/body?sub=body-scrubs"],["Shower Gels","/shop/body?sub=shower-gels"],["Foot Care","/shop/body?sub=foot-care"],["Deodorants","/shop/body?sub=deodorants"]] },
      { head: "Shop Hands", links: [["Hand Moisturisers","/shop/body?sub=hand-moisturisers"],["Soaps","/shop/body?sub=soaps"]] },
    ],
  },
  {
    label: "FACE & SKINCARE", href: "/shop/skincare",
    cols: [
      { head: "By Product Type", links: [["View All Face","/shop/skincare"],["Moisturisers","/shop/skincare?sub=moisturisers"],["Cleansers & Toners","/shop/skincare?sub=cleansers"],["Face Masks","/shop/skincare?sub=face-masks"],["Serums & Essences","/shop/skincare?sub=serums"],["Skin Care with SPF","/shop/skincare?sub=spf"],["Exfoliators & Peels","/shop/skincare?sub=exfoliators"]] },
      { head: "More",            links: [["Night Care","/shop/skincare?sub=night-care"],["Eye Care","/shop/skincare?sub=eye-care"],["Men's Grooming","/shop/skincare?sub=mens"],["Lip Care","/shop/skincare?sub=lip-care"]] },
      { head: "By Skin Type",    links: [["Oily & Blemish Prone","/shop/skincare?skin=oily"],["Dry Skin","/shop/skincare?skin=dry"],["Combination Skin","/shop/skincare?skin=combination"],["Sensitive Skin","/shop/skincare?skin=sensitive"],["Normal Skin","/shop/skincare?skin=normal"]] },
    ],
  },
  {
    label: "HAIR", href: "/shop/hair",
    cols: [
      { head: "By Product", links: [["View All Hair","/shop/hair"],["Shampoo","/shop/hair?sub=shampoo"],["Conditioner","/shop/hair?sub=conditioner"],["Hair Styling","/shop/hair?sub=styling"]] },
      { head: "By Concern",  links: [["Frizz Prone","/shop/hair?concern=frizz"],["Dry Hair & Scalp","/shop/hair?concern=dry"],["Dull Hair","/shop/hair?concern=dull"],["Damage Prone","/shop/hair?concern=damaged"],["Oily Prone","/shop/hair?concern=oily"]] },
    ],
  },
  {
    label: "FRAGRANCE", href: "/shop/fragrance",
    cols: [
      { head: "Fragrance",    links: [["View All","/shop/fragrance"],["Body Mists","/shop/fragrance?sub=body-mists"],["Eau De Toilette","/shop/fragrance?sub=edt"],["Eau De Parfum","/shop/fragrance?sub=edp"]] },
      { head: "By Recipient", links: [["For Her","/shop/fragrance?for=her"],["For Him","/shop/fragrance?for=him"]] },
    ],
  },
  {
    label: "RANGE", href: "/shop/range",
    cols: [
      { head: "Popular",    links: [["British Rose","/shop/range?range=british-rose"],["Vitamin C","/shop/range?range=vitamin-c"],["Tea Tree","/shop/range?range=tea-tree"],["Strawberry","/shop/range?range=strawberry"],["Ginger","/shop/range?range=ginger"]] },
      { head: "Skincare",   links: [["Edelweiss","/shop/range?range=edelweiss"],["Aloe","/shop/range?range=aloe"],["Vitamin E","/shop/range?range=vitamin-e"],["Camomile","/shop/range?range=camomile"]] },
      { head: "Body Care",  links: [["Shea Butter","/shop/range?range=shea-butter"],["Moringa","/shop/range?range=moringa"],["Almond Milk","/shop/range?range=almond-milk"]] },
    ],
  },
  {
    label: "GIFTS", href: "/shop/gifts",
    cols: [
      { head: "Shop By Product", links: [["View All Gifts","/shop/gifts"],["Skin Care Gifts","/shop/gifts?type=skincare"],["Fragrance Gifts","/shop/gifts?type=fragrance"],["Bags & Boxes","/shop/gifts?type=bags-boxes"]] },
      { head: "Shop By Price",   links: [["Under ₹1000","/shop/gifts?price=under-1000"],["₹1000 – ₹2000","/shop/gifts?price=1000-2000"],["₹2000 & Above","/shop/gifts?price=above-2000"]] },
      { head: "By Recipient",    links: [["For Him","/shop/gifts?for=him"],["For Her","/shop/gifts?for=her"],["For Teenager","/shop/gifts?for=teenager"]] },
    ],
  },
  { label: "TIPS & ADVICE", href: "/tips-and-advice" },
  { label: "OFFERS",        href: "/offers", highlight: true },
  { label: "ABOUT US",      href: "/about" },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileExp,  setMobileExp]  = useState(null);
  const [scrolled,   setScrolled]   = useState(false);
  const [wishlistCount, setWishlistCount] = useState(0);

  useEffect(() => {
  const session_id = localStorage.getItem("session_id") || "guest";
  fetch(`/api/wishlist?session_id=${session_id}`)
    .then((r) => r.json())
    .then((data) => setWishlistCount(data.items?.length || 0))
    .catch(() => {});
}, []);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 2);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <>
      <style>{`
        .nav-link { font-size:12px; font-weight:700; letter-spacing:0.08em; color:#fff; text-decoration:none; padding:14px 10px; display:flex; align-items:center; gap:3px; border-bottom:2px solid transparent; transition:border-color 0.15s; white-space:nowrap; position:relative; }
        .nav-link:hover { border-bottom-color:rgba(255,255,255,0.7); }
        .nav-link.hl { color:#f5c518; }
        .mega { display:none; position:absolute; top:100%; left:50%; transform:translateX(-50%); background:#fff; border-top:3px solid #006e3c; box-shadow:0 8px 32px rgba(0,0,0,0.15); z-index:400; padding:28px 32px; gap:32px; min-width:520px; }
        .nav-has-mega:hover .mega { display:flex; }
        .mega-head { font-size:10px; font-weight:700; letter-spacing:0.1em; color:#888; text-transform:uppercase; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid #f0ece6; }
        .mega-link { display:block; font-size:13px; color:#1a1a1a; text-decoration:none; padding:4px 0; font-family:'Josefin Sans',sans-serif; transition:color 0.1s; }
        .mega-link:hover { color:#006e3c; }
        .icon-btn { width:38px; height:38px; display:flex; align-items:center; justify-content:center; background:transparent; border:none; cursor:pointer; color:#fff; border-radius:50%; transition:background 0.15s; text-decoration:none; }
        .icon-btn:hover { background:rgba(255,255,255,0.12); }
        .hamburger-btn { display:none; }
        @media (max-width: 767px) {
          .hamburger-btn { display:flex !important; }
          .stores-link span { display:none; }
        }
      `}</style>

      <header style={{ position: "sticky", top: 0, zIndex: 200, boxShadow: scrolled ? "0 2px 16px rgba(0,0,0,0.18)" : "none" }}>

        {/* ── TOP BAR ── */}
        <div style={{ backgroundColor: "#004d2a", padding: "0 20px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between" }}>

          {/* Left — only visible on mobile */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, flex: 1 }}>
            {/* Hamburger: hidden on desktop via CSS, shown on mobile */}
            <button
              className="hamburger-btn icon-btn hamburger-btn"
              onClick={() => setMobileOpen(v => !v)}
              aria-label="Open menu"
              style={{ display: "none" }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <Link href="/store-finder" className="stores-link" style={{ display: "flex", alignItems: "center", gap: 5, color: "#fff", textDecoration: "none", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em" }}>
              <MapPin size={14} />
              <span>STORES</span>
            </Link>
          </div>

          {/* Center: Logo */}
          <Link href="/" style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <img
              src="https://www.thebodyshop.in/images/anniversaryLogo4.svg"
              alt="The Body Shop"
              style={{ height: 42, filter: "brightness(0) invert(1)" }}
            />
          </Link>

          {/* Right icons */}
          <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1, justifyContent: "flex-end" }}>
            <button onClick={() => setSearchOpen(v => !v)} className="icon-btn"><Search size={20} /></button>
            <Link href="/wishlist" className="icon-btn" style={{ position: "relative" }}>
              <Heart size={20} />
              {wishlistCount > 0 && (
                <span style={{ position: "absolute", top: 4, right: 4, width: 16, height: 16, borderRadius: "50%", background: "#c0392b", color: "#fff", fontSize: 9, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {wishlistCount > 9 ? "9+" : wishlistCount}
                </span>
              )}
            </Link>
            <Link href="/account" className="icon-btn"><User size={20} /></Link>
            <Link href="/cart" className="icon-btn" style={{ position: "relative" }}>
              <ShoppingBag size={20} />
              <span id="cart-count" style={{ position: "absolute", top: 4, right: 4, width: 16, height: 16, borderRadius: "50%", background: "#e8b84b", color: "#1a1a1a", fontSize: 9, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>0</span>
            </Link>
          </div>
        </div>

        {/* ── SEARCH BAR ── */}
        <div style={{ backgroundColor: "#004d2a", overflow: "hidden", height: searchOpen ? 48 : 0, transition: "height 0.25s ease", borderTop: searchOpen ? "1px solid rgba(255,255,255,0.15)" : "none" }}>
          <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", gap: 10, height: 48 }}>
            <Search size={15} color="rgba(255,255,255,0.6)" />
            <input
              autoFocus={searchOpen}
              type="text"
              placeholder="Search for products, ingredients or routines…"
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#fff", fontSize: 13, fontFamily: "inherit" }}
            />
            <button onClick={() => setSearchOpen(false)} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.6)", fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>Close</button>
          </div>
        </div>

        {/* ── NAV LINKS ROW — desktop only ── */}
        <nav style={{ backgroundColor: "#006e3c", borderBottom: "1px solid rgba(255,255,255,0.1)", display: "none" }} className="desktop-nav">
          <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 12px", display: "flex", alignItems: "center", justifyContent: "center", flexWrap: "nowrap" }}>
            {NAV_ITEMS.map(item => (
              <div key={item.label} className={item.cols ? "nav-has-mega" : ""} style={{ position: "relative" }}>
                <Link href={item.href} className={`nav-link${item.highlight ? " hl" : ""}`}>
                  {item.label}
                  {item.cols && <ChevronDown size={10} style={{ opacity: 0.6 }} />}
                </Link>
                {item.cols && (
                  <div className="mega">
                    {item.cols.map(col => (
                      <div key={col.head} style={{ minWidth: 140 }}>
                        <p className="mega-head">{col.head}</p>
                        {col.links.map(([l, h]) => (
                          <Link key={l} href={h} className="mega-link">{l}</Link>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </nav>

        {/* ── PROMO STRIP ── */}
        <div style={{ backgroundColor: "#e8b84b", padding: "8px 0", textAlign: "center", fontSize: 13, fontWeight: 600, color: "#1a1a1a", borderBottom: "1px solid #d4a43a" }}>
          Free Shipping on All Orders for Club and Platinum Members –{" "}
          <Link href="/offers" style={{ textDecoration: "underline", color: "#006e3c", fontWeight: 700 }}>Shop Now</Link>
          {" "}| Not a Member?{" "}
          <Link href="/account" style={{ textDecoration: "underline", color: "#006e3c", fontWeight: 700 }}>Join Now</Link>
        </div>
      </header>

      {/* ── MOBILE MENU ── */}
      {mobileOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "#fff", zIndex: 500, overflowY: "auto", paddingTop: 0 }}>
          <div style={{ padding: "12px 20px", borderBottom: "1px solid #f0ece6", display: "flex", alignItems: "center", gap: 10, background: "#004d2a" }}>
            <Search size={16} color="rgba(255,255,255,0.7)" />
            <input type="text" placeholder="Search…" style={{ flex: 1, border: "none", outline: "none", fontSize: 14, background: "transparent", fontFamily: "inherit", color: "#fff" }} />
            <button onClick={() => setMobileOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#fff" }}><X size={20} /></button>
          </div>
          {NAV_ITEMS.map(item => (
            <div key={item.label} style={{ borderBottom: "1px solid #f0ece6" }}>
              <button
                onClick={() => setMobileExp(mobileExp === item.label ? null : item.label)}
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 700, letterSpacing: "0.06em", color: item.highlight ? "#006e3c" : "#1a1a1a", textAlign: "left" }}
              >
                {item.label}
                {item.cols && <ChevronDown size={14} color="#888" style={{ transform: mobileExp === item.label ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />}
              </button>
              {item.cols && mobileExp === item.label && (
                <div style={{ background: "#faf7f2", padding: "8px 20px 16px" }}>
                  {item.cols.map(col => (
                    <div key={col.head} style={{ marginBottom: 14 }}>
                      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "#888", textTransform: "uppercase", marginBottom: 6 }}>{col.head}</p>
                      {col.links.map(([l, h]) => (
                        <Link key={l} href={h} onClick={() => setMobileOpen(false)} style={{ display: "block", fontSize: 13, color: "#1a1a1a", padding: "5px 0", textDecoration: "none" }}>{l}</Link>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <style>{`
        @media (min-width: 768px) {
          .desktop-nav { display: block !important; }
        }
      `}</style>
    </>
  );
}