"use client";
import Link from "next/link";

const GD = "#004d2a";
const G  = "#006e3c";

const COLS = [
  {
    heading: "USEFUL INFORMATION",
    headColor: "#e8b84b",
    links: [["Help & FAQs","/help"],["Terms & Conditions","/terms"],["Returns Refund & Cancellation","/returns"],["Privacy Policy","/privacy"],["Donation","/donation"]],
  },
  {
    heading: "WAYS TO SHOP",
    headColor: "#e8b84b",
    links: [["Store Finder","/store-finder"],["Gift Cards","/gift-cards"],["Corporate Gifting","/corporate-gifting"]],
  },
  {
    heading: "ABOUT US",
    headColor: "#e8b84b",
    links: [["Our Loyalty Club","/loyalty"],["Careers","/careers"],["Contact Us","/contact"]],
  },
];

export default function Footer() {
  return (
    <footer>
      <style>{`
        .f-link { display:block; font-size:14px; color:rgba(255,255,255,0.85); text-decoration:none; padding:4px 0; font-family:'Josefin Sans',sans-serif; transition:color 0.15s; }
        .f-link:hover { color:#fff; }
        .f-legal { font-size:12px; color:rgba(255,255,255,0.5); text-decoration:none; transition:color 0.15s; }
        .f-legal:hover { color:rgba(255,255,255,0.8); }
        .social-btn { width:44px; height:44px; border-radius:50%; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); display:flex; align-items:center; justify-content:center; color:#fff; font-size:18px; text-decoration:none; transition:background 0.15s; }
        .social-btn:hover { background:rgba(255,255,255,0.2); }
        .nl-input { flex:1; padding:12px 18px; border:2px solid #006e3c; background:#fff; font-size:13px; outline:none; font-family:'Josefin Sans',sans-serif; color:#1a1a1a; }
        .nl-input::placeholder { color:#aaa; }
        .nl-btn { padding:12px 24px; background:#e8b84b; border:none; color:#1a1a1a; font-weight:800; font-size:13px; letter-spacing:0.08em; cursor:pointer; font-family:'Josefin Sans',sans-serif; white-space:nowrap; transition:background 0.15s; }
        .nl-btn:hover { background:#d4a43a; }
        .help-panel { flex:1; padding:32px 24px; border-right:1px solid #e8e0d5; text-align:center; }
        .help-panel h3 { font-size:16px; font-weight:800; letter-spacing:0.06em; margin-bottom:10px; color:#1a1a1a; }
        .help-panel p { font-size:13px; color:#555; line-height:1.6; }
      `}</style>

      {/* ── 3-panel top bar ── */}
      <div style={{ backgroundColor: "#f5f1eb", borderTop: "1px solid #e8e0d5" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", display: "flex", flexWrap: "wrap" }}>
          {/* Need Help */}
          <div className="help-panel">
            <h3>NEED HELP?</h3>
            <p>Our Customer Care is always available for your help.<br />Reach us at <strong>customercare.tbs@questretail.in</strong><br />or contact us at <strong>+91-9599227343</strong></p>
            <p style={{ marginTop: 8, fontSize: 13, fontWeight: 700, color: "#1a1a1a" }}>Monday to Sunday: 9AM – 6PM</p>
          </div>

          {/* Follow Us */}
          <div className="help-panel" style={{ flex: 1 }}>
            <h3>FOLLOW US</h3>
            <p style={{ marginBottom: 16 }}>Be first to know new arrivals &amp; exclusive offers.</p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              {[
                { href: "https://facebook.com/thebodyshopindia",  icon: "f", label: "Facebook"  },
                { href: "https://twitter.com/thebodyshopindia",   icon: "𝕏", label: "Twitter"   },
                { href: "https://instagram.com/thebodyshopindia", icon: "📷", label: "Instagram" },
                { href: "https://youtube.com/thebodyshop",        icon: "▶", label: "YouTube"   },
              ].map(s => (
                <a key={s.label} href={s.href} target="_blank" rel="noopener noreferrer" className="social-btn" aria-label={s.label} style={{ color: "#1a1a1a", background: "rgba(0,0,0,0.06)", border: "1px solid rgba(0,0,0,0.1)" }}>
                  <span style={{ fontSize: 15 }}>{s.icon}</span>
                </a>
              ))}
            </div>
          </div>

          {/* Newsletter */}
          <div className="help-panel" style={{ borderRight: "none", flex: 1.4 }}>
            <h3>SUBSCRIBE TO OUR NEWSLETTER</h3>
            <p style={{ marginBottom: 16 }}>Be the first to know about our exclusive offers.</p>
            <form onSubmit={e => e.preventDefault()} style={{ display: "flex" }}>
              <input type="email" placeholder="Email Address" className="nl-input" />
              <button type="submit" className="nl-btn">SUBSCRIBE</button>
            </form>
          </div>
        </div>
      </div>

      {/* ── Dark green links grid ── */}
      <div style={{ backgroundColor: GD }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "40px 20px 32px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "32px 24px" }}>
          {COLS.map(col => (
            <div key={col.heading}>
              <p style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.1em", color: col.headColor, marginBottom: 16, textTransform: "uppercase" }}>
                {col.heading}
              </p>
              {col.links.map(([label, href]) => (
                <Link key={label} href={href} className="f-link">{label}</Link>
              ))}
            </div>
          ))}

          {/* App download column */}
          <div>
            <p style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.1em", color: "#e8b84b", marginBottom: 12, textTransform: "uppercase" }}>
              The Body Shop In Your Hands
            </p>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginBottom: 14, lineHeight: 1.5 }}>Download Now!</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <a href="https://apps.apple.com" target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", width: 130 }}>
                <div style={{ backgroundColor: "#000", borderRadius: 8, padding: "8px 14px", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 20 }}>🍎</span>
                  <div>
                    <p style={{ color: "#fff", fontSize: 9, margin: 0 }}>Download on the</p>
                    <p style={{ color: "#fff", fontSize: 13, fontWeight: 700, margin: 0 }}>App Store</p>
                  </div>
                </div>
              </a>
              <a href="https://play.google.com" target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", width: 130 }}>
                <div style={{ backgroundColor: "#000", borderRadius: 8, padding: "8px 14px", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 20 }}>▶</span>
                  <div>
                    <p style={{ color: "#fff", fontSize: 9, margin: 0 }}>GET IT ON</p>
                    <p style={{ color: "#fff", fontSize: 13, fontWeight: 700, margin: 0 }}>Google Play</p>
                  </div>
                </div>
              </a>
            </div>
          </div>
        </div>

        {/* Bottom legal bar */}
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", padding: "16px 20px" }}>
          <div style={{ maxWidth: 1280, margin: "0 auto", textAlign: "center" }}>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginBottom: 4 }}>
              © {new Date().getFullYear()} The Body Shop. All Rights Reserved.
            </p>
            <p style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>
              The Body Shop International Limited (Company No. 1284170), Watersmead, Littlehampton, West Sussex, BN17 6LS.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}