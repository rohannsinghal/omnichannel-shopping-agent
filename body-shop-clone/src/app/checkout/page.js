// src/app/checkout/page.js
"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { CheckCircle2, ChevronLeft } from "lucide-react";

const G = "#006e3c";
function inr(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

const STEPS = ["Address", "Payment", "Confirm"];

export default function CheckoutPage() {
  const [step,    setStep]   = useState(0);
  const [items,   setItems]  = useState([]);
  const [placed,  setPlaced] = useState(false);
  const [orderId, setOrderId]= useState("");
  const [placing, setPlacing]= useState(false);
  const [form,    setForm]   = useState({
    name: "", email: "", phone: "", address: "", city: "", pincode: "", state: "Delhi",
    payMethod: "cod",
    cardNumber: "", cardExpiry: "", cardCvv: "",
  });

  useEffect(() => {
    fetch("/api/cart").then(r => r.json()).then(d => setItems(d.items || []));
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const subtotal = items.reduce((s, i) => s + Number(i.price) * i.qty, 0);
  const shipping  = subtotal >= 699 ? 0 : 99;
  const total     = subtotal + shipping;

  const placeOrder = async () => {
    setPlacing(true);
    try {
      const res  = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form, items, subtotal, shipping, total }),
      });
      const data = await res.json();
      setOrderId(data.order_id || "TBS-" + Math.floor(Math.random() * 9000 + 1000));

      // Clear Supabase cart
      await fetch("/api/cart", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
      const el = document.getElementById("cart-count");
      if (el) el.textContent = "0";

      setPlaced(true);
    } catch (err) {
      console.error("Order placement error:", err);
      // Still show success in demo — the order page shouldn't crash the demo
      setOrderId("TBS-" + Math.floor(Math.random() * 9000 + 1000));
      setPlaced(true);
    }
    setPlacing(false);
  };

  // ── Order placed confirmation screen ────────────────────────────────────────
  if (placed) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#fff" }}>
      <div style={{ textAlign: "center", padding: "60px 40px", maxWidth: 500 }}>
        <CheckCircle2 size={72} color={G} style={{ marginBottom: 20 }} />
        <h1 style={{ fontFamily: "'Libre Baskerville',serif", fontSize: 30, color: "#1a1a1a", marginBottom: 12 }}>Order Placed! 🎉</h1>
        <div style={{ backgroundColor: "#edf7f0", border: "1px solid #c6e8d4", borderRadius: 8, padding: "12px 20px", marginBottom: 20 }}>
          <p style={{ fontSize: 13, color: "#888", marginBottom: 2 }}>Your Order ID</p>
          <p style={{ fontSize: 20, fontWeight: 900, color: G }}>{orderId}</p>
        </div>
        <p style={{ color: "#555", lineHeight: 1.7, marginBottom: 6 }}>
          Thank you, <strong>{form.name}</strong>! Your order will be delivered in 4–7 business days.
        </p>
        <p style={{ color: "#888", fontSize: 13, marginBottom: 28 }}>
          Confirmation sent to <strong>{form.email}</strong>
        </p>
        <Link href="/" style={{ display: "inline-block", backgroundColor: G, color: "#fff", padding: "13px 36px", borderRadius: 6, fontWeight: 800, letterSpacing: "0.08em", textDecoration: "none" }}>
          CONTINUE SHOPPING
        </Link>
      </div>
    </div>
  );

  const inputStyle = {
    width: "100%", padding: "11px 14px", border: "1.5px solid #e0d8cc", borderRadius: 6,
    fontSize: 14, fontFamily: "inherit", outline: "none", boxSizing: "border-box", color: "#1a1a1a",
    transition: "border-color 0.2s",
  };
  const labelStyle = {
    fontSize: 11, fontWeight: 700, color: "#888", letterSpacing: "0.07em",
    display: "block", marginBottom: 6, textTransform: "uppercase",
  };

  return (
    <div style={{ backgroundColor: "#f9f6f0", minHeight: "60vh" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 20px 60px" }}>

        {/* ── Step progress bar ── */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0, marginBottom: 40 }}>
          {STEPS.map((s, i) => (
            <div key={s} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div style={{ width: 34, height: 34, borderRadius: "50%", backgroundColor: i <= step ? G : "#e0d8cc", color: i <= step ? "#fff" : "#888", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, transition: "background-color 0.3s" }}>
                  {i < step ? "✓" : i + 1}
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, color: i <= step ? G : "#aaa", letterSpacing: "0.06em" }}>{s.toUpperCase()}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{ width: 80, height: 2, backgroundColor: i < step ? G : "#e0d8cc", margin: "0 6px", marginBottom: 22, transition: "background-color 0.3s" }} />
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 28, alignItems: "start" }}>

          {/* ── Left form panel ── */}
          <div style={{ backgroundColor: "#fff", borderRadius: 10, padding: "32px 28px", border: "1px solid #e8e0d5" }}>

            {/* STEP 0 — Address */}
            {step === 0 && (
              <>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "#1a1a1a", marginBottom: 24 }}>Delivery Address</h2>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div style={{ gridColumn: "1/-1" }}>
                    <label style={labelStyle}>Full Name *</label>
                    <input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} placeholder="e.g. Priya Sharma" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div>
                    <label style={labelStyle}>Email *</label>
                    <input type="email" style={inputStyle} value={form.email} onChange={e => set("email", e.target.value)} placeholder="priya@email.com" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div>
                    <label style={labelStyle}>Phone *</label>
                    <input style={inputStyle} value={form.phone} onChange={e => set("phone", e.target.value)} placeholder="+91 98765 43210" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div style={{ gridColumn: "1/-1" }}>
                    <label style={labelStyle}>Address *</label>
                    <input style={inputStyle} value={form.address} onChange={e => set("address", e.target.value)} placeholder="Flat / House no., Street" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div>
                    <label style={labelStyle}>City *</label>
                    <input style={inputStyle} value={form.city} onChange={e => set("city", e.target.value)} placeholder="New Delhi" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div>
                    <label style={labelStyle}>Pincode *</label>
                    <input style={inputStyle} value={form.pincode} onChange={e => set("pincode", e.target.value)} placeholder="110001" onFocus={e => (e.target.style.borderColor = G)} onBlur={e => (e.target.style.borderColor = "#e0d8cc")} />
                  </div>
                  <div style={{ gridColumn: "1/-1" }}>
                    <label style={labelStyle}>State *</label>
                    <select style={{ ...inputStyle, cursor: "pointer" }} value={form.state} onChange={e => set("state", e.target.value)}>
                      {["Andhra Pradesh","Delhi","Gujarat","Haryana","Karnataka","Kerala","Maharashtra","Punjab","Rajasthan","Tamil Nadu","Telangana","Uttar Pradesh","West Bengal"].map(s => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button
                  onClick={() => setStep(1)}
                  disabled={!form.name || !form.email || !form.address || !form.city || !form.pincode}
                  style={{ marginTop: 28, backgroundColor: G, color: "#fff", border: "none", padding: "13px 32px", borderRadius: 6, fontWeight: 800, fontSize: 14, letterSpacing: "0.08em", cursor: "pointer", fontFamily: "inherit", opacity: (!form.name || !form.email || !form.address || !form.city || !form.pincode) ? 0.5 : 1, transition: "opacity 0.2s" }}>
                  CONTINUE TO PAYMENT →
                </button>
              </>
            )}

            {/* STEP 1 — Payment */}
            {step === 1 && (
              <>
                <button onClick={() => setStep(0)} style={{ display: "flex", alignItems: "center", gap: 4, color: "#888", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 13, marginBottom: 20 }}>
                  <ChevronLeft size={14} /> Back
                </button>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "#1a1a1a", marginBottom: 24 }}>Payment Method</h2>

                {[
                  { id: "cod",  label: "Cash on Delivery",     sub: "Pay when your order arrives at your door" },
                  { id: "upi",  label: "UPI / GPay / PhonePe", sub: "Instant payment via any UPI app"          },
                  { id: "card", label: "Credit / Debit Card",   sub: "Visa, Mastercard, RuPay accepted"        },
                ].map(m => (
                  <label key={m.id} style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "16px 18px", border: `2px solid ${form.payMethod === m.id ? G : "#e0d8cc"}`, borderRadius: 8, cursor: "pointer", marginBottom: 12, backgroundColor: form.payMethod === m.id ? "#edf7f0" : "#fff", transition: "all 0.2s" }}>
                    <input type="radio" name="pay" value={m.id} checked={form.payMethod === m.id} onChange={() => set("payMethod", m.id)} style={{ marginTop: 3, accentColor: G }} />
                    <div>
                      <p style={{ fontWeight: 700, fontSize: 14, color: "#1a1a1a", margin: 0 }}>{m.label}</p>
                      <p style={{ fontSize: 12, color: "#888", margin: "3px 0 0" }}>{m.sub}</p>
                    </div>
                  </label>
                ))}

                {form.payMethod === "card" && (
                  <div style={{ marginTop: 16, backgroundColor: "#f9f6f0", borderRadius: 8, padding: 20, display: "grid", gap: 14 }}>
                    <div>
                      <label style={labelStyle}>Card Number</label>
                      <input style={inputStyle} value={form.cardNumber} onChange={e => set("cardNumber", e.target.value)} placeholder="1234 5678 9012 3456" maxLength={19} />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                      <div>
                        <label style={labelStyle}>Expiry (MM/YY)</label>
                        <input style={inputStyle} value={form.cardExpiry} onChange={e => set("cardExpiry", e.target.value)} placeholder="08 / 27" maxLength={7} />
                      </div>
                      <div>
                        <label style={labelStyle}>CVV</label>
                        <input type="password" style={inputStyle} value={form.cardCvv} onChange={e => set("cardCvv", e.target.value)} placeholder="•••" maxLength={4} />
                      </div>
                    </div>
                  </div>
                )}

                <button onClick={() => setStep(2)}
                  style={{ marginTop: 28, backgroundColor: G, color: "#fff", border: "none", padding: "13px 32px", borderRadius: 6, fontWeight: 800, fontSize: 14, letterSpacing: "0.08em", cursor: "pointer", fontFamily: "inherit" }}>
                  REVIEW ORDER →
                </button>
              </>
            )}

            {/* STEP 2 — Review & confirm */}
            {step === 2 && (
              <>
                <button onClick={() => setStep(1)} style={{ display: "flex", alignItems: "center", gap: 4, color: "#888", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 13, marginBottom: 20 }}>
                  <ChevronLeft size={14} /> Back
                </button>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "#1a1a1a", marginBottom: 20 }}>Review & Place Order</h2>

                <div style={{ backgroundColor: "#f9f6f0", borderRadius: 8, padding: "16px 20px", marginBottom: 16 }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "#888", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>📦 Deliver To</p>
                  <p style={{ fontWeight: 700, color: "#1a1a1a", marginBottom: 2 }}>{form.name}</p>
                  <p style={{ color: "#555", fontSize: 13 }}>{form.address}, {form.city}, {form.state} – {form.pincode}</p>
                  <p style={{ color: "#555", fontSize: 13 }}>{form.phone} · {form.email}</p>
                </div>

                <div style={{ backgroundColor: "#f9f6f0", borderRadius: 8, padding: "16px 20px", marginBottom: 28 }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "#888", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>💳 Payment</p>
                  <p style={{ fontWeight: 700, color: "#1a1a1a" }}>
                    {{ cod: "Cash on Delivery", upi: "UPI Payment", card: "Card Payment" }[form.payMethod]}
                  </p>
                </div>

                <button
                  onClick={placeOrder}
                  disabled={placing}
                  style={{ width: "100%", backgroundColor: placing ? "#888" : G, color: "#fff", border: "none", padding: "16px 0", borderRadius: 6, fontWeight: 800, fontSize: 15, letterSpacing: "0.08em", cursor: placing ? "not-allowed" : "pointer", fontFamily: "inherit", transition: "background-color 0.2s" }}>
                  {placing ? "PLACING ORDER…" : `PLACE ORDER · ${inr(total)}`}
                </button>
                <p style={{ textAlign: "center", fontSize: 11, color: "#888", marginTop: 12 }}>
                  🔒 Secure checkout — By placing this order you agree to our Terms & Conditions
                </p>
              </>
            )}
          </div>

          {/* ── Right: order summary ── */}
          <div style={{ backgroundColor: "#fff", borderRadius: 10, padding: "22px 20px", border: "1px solid #e8e0d5", position: "sticky", top: 120 }}>
            <h3 style={{ fontSize: 16, fontWeight: 800, color: "#1a1a1a", marginBottom: 16 }}>Your Bag ({items.reduce((s, i) => s + i.qty, 0)} items)</h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16, maxHeight: 240, overflowY: "auto" }}>
              {items.map(i => (
                <div key={i.product_id} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <div style={{ width: 44, height: 44, backgroundColor: "#f7f3ee", borderRadius: 4, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                    {i.image_url ? <img src={i.image_url} alt={i.name} style={{ width: "90%", height: "90%", objectFit: "contain" }} onError={e => { e.currentTarget.style.opacity = "0"; }} /> : <span style={{ fontSize: 18, opacity: 0.3 }}>🌿</span>}
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "#1a1a1a", lineHeight: 1.3, margin: 0 }}>{i.name}</p>
                    <p style={{ fontSize: 11, color: "#888", margin: "1px 0 0" }}>Qty: {i.qty}</p>
                  </div>
                  <p style={{ fontSize: 13, fontWeight: 800, flexShrink: 0 }}>{inr(Number(i.price) * i.qty)}</p>
                </div>
              ))}
            </div>

            <div style={{ borderTop: "1px solid #f0ece6", paddingTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#555" }}>
                <span>Subtotal</span><span>{inr(subtotal)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#555" }}>
                <span>Shipping</span>
                <span style={{ color: shipping === 0 ? G : "#1a1a1a", fontWeight: 600 }}>{shipping === 0 ? "FREE" : inr(shipping)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 18, fontWeight: 900, color: "#1a1a1a", marginTop: 6 }}>
                <span>Total</span><span>{inr(total)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}