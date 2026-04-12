// src/app/cart/page.js
"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Trash2, ShoppingBag, ArrowRight, ChevronLeft, RefreshCw } from "lucide-react";

const G = "#006e3c";
function inr(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

export default function CartPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false); // debounce qty updates

  const fetchCart = useCallback(async () => {
    try {
      // 1. Fetch BOTH the cart (Postgres) and products (Mongo) at the same time
      const [cartRes, prodRes] = await Promise.all([
        fetch("/api/cart"),
        fetch("/api/products?limit=100") // Limit high enough to grab the catalog
      ]);

      const cartData = await cartRes.json();
      const prodData = await prodRes.json();

      const rawCartItems = cartData.items || [];
      const catalog = prodData.products || [];

      // 2. Merge the image_url from Mongo into the Postgres cart items
      const mergedItems = rawCartItems.map((cartItem) => {
        const mongoProduct = catalog.find((p) => p.product_id === cartItem.product_id);
        return {
          ...cartItem,
          image_url: mongoProduct?.image_url || "" 
        };
      });

      setItems(mergedItems);
    } catch (error) {
      console.error("Error fetching cart data:", error);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchCart(); }, [fetchCart]);

  // Update cart badge in navbar
  const updateBadge = (cartItems) => {
    const el = document.getElementById("cart-count");
    if (el) el.textContent = String(cartItems.reduce((s, i) => s + i.qty, 0));
  };

  // 3. Helper to preserve images in state when updating quantities
  const preserveImages = (newCartItems) => {
    return newCartItems.map((newItem) => {
      // Find the existing item in our React state to steal its image_url
      const existingItem = items.find((i) => i.product_id === newItem.product_id);
      return {
        ...newItem,
        image_url: existingItem?.image_url || ""
      };
    });
  };

  const remove = async (product_id) => {
    const res = await fetch("/api/cart", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_id }) });
    const data = await res.json();
    
    // Inject images back into the updated Postgres response
    const updatedWithImages = preserveImages(data.items || []);
    
    setItems(updatedWithImages);
    updateBadge(updatedWithImages);
  };

  const setQty = async (product_id, qty) => {
    if (qty < 1) { remove(product_id); return; }
    setSyncing(true);
    const res = await fetch("/api/cart", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_id, qty }) });
    const data = await res.json();
    
    // Inject images back into the updated Postgres response
    const updatedWithImages = preserveImages(data.items || []);
    
    setItems(updatedWithImages);
    updateBadge(updatedWithImages);
    setSyncing(false);
  };

  const subtotal = items.reduce((s, i) => s + Number(i.price) * i.qty, 0);
  const shipping = subtotal >= 699 ? 0 : 99;
  const total = subtotal + shipping;

  if (loading) return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "80px 20px", textAlign: "center", color: "#888" }}>
      Loading your bag…
    </div>
  );

  return (
    <div style={{ backgroundColor: "#fff", minHeight: "60vh" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 20px 60px" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32, flexWrap: "wrap", gap: 12 }}>
          <Link href="/shop/skincare" style={{ display: "flex", alignItems: "center", gap: 4, color: "#888", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            <ChevronLeft size={16} /> Continue Shopping
          </Link>
          <h1 style={{ fontFamily: "'Libre Baskerville',serif", fontSize: 28, fontWeight: 700, color: "#1a1a1a", margin: 0 }}>
            My Bag {items.length > 0 && <span style={{ fontSize: 18, color: "#888", fontWeight: 400 }}>({items.reduce((s, i) => s + i.qty, 0)} items)</span>}
          </h1>
          <button onClick={fetchCart} style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", color: "#888", cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {items.length === 0 ? (
          /* Empty state */
          <div style={{ textAlign: "center", padding: "80px 20px" }}>
            <ShoppingBag size={64} color="#e0d8cc" style={{ marginBottom: 20 }} />
            <h2 style={{ fontSize: 22, color: "#1a1a1a", marginBottom: 10, fontFamily: "'Libre Baskerville',serif" }}>Your bag is empty</h2>
            <p style={{ color: "#888", marginBottom: 28, lineHeight: 1.6 }}>
              Discover our cruelty-free, naturally inspired beauty products.
            </p>
            <Link href="/shop/skincare"
              style={{ display: "inline-block", backgroundColor: G, color: "#fff", padding: "13px 36px", borderRadius: 6, fontWeight: 800, fontSize: 13, letterSpacing: "0.08em", textDecoration: "none" }}>
              SHOP NOW
            </Link>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 40, alignItems: "start" }}>

            {/* ── Cart items list ── */}
            <div>
              {syncing && (
                <div style={{ fontSize: 12, color: G, marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                  <RefreshCw size={12} /> Syncing cart…
                </div>
              )}

              {items.map(item => (
                <div key={item.product_id} style={{ display: "flex", gap: 20, padding: "20px 0", borderBottom: "1px solid #f0ece6", alignItems: "flex-start" }}>

                  {/* Product image */}
                  <Link href={`/product/${item.product_id}`}>
                    <div style={{ width: 108, height: 108, backgroundColor: "#f7f3ee", borderRadius: 8, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                      {item.image_url
                        ? <img src={item.image_url} alt={item.name} style={{ width: "85%", height: "85%", objectFit: "contain" }} onError={e => { e.currentTarget.style.opacity = "0"; }} />
                        : <span style={{ fontSize: 36, opacity: 0.3 }}>🌿</span>
                      }
                    </div>
                  </Link>

                  {/* Details */}
                  <div style={{ flex: 1 }}>
                    <Link href={`/product/${item.product_id}`} style={{ textDecoration: "none" }}>
                      <h3 style={{ fontSize: 14, fontWeight: 700, color: "#1a1a1a", marginBottom: 4, lineHeight: 1.35 }}>{item.name}</h3>
                    </Link>
                    <p style={{ fontSize: 12, color: "#888", marginBottom: 10 }}>ID: {item.product_id}</p>

                    <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                      {/* Qty stepper */}
                      <div style={{ display: "flex", alignItems: "center", border: "1.5px solid #e0d8cc", borderRadius: 6, overflow: "hidden" }}>
                        <button
                          onClick={() => setQty(item.product_id, item.qty - 1)}
                          style={{ width: 34, height: 36, background: "none", border: "none", cursor: "pointer", fontSize: 18, color: "#1a1a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>−</button>
                        <span style={{ width: 38, textAlign: "center", fontWeight: 700, fontSize: 14 }}>{item.qty}</span>
                        <button
                          onClick={() => setQty(item.product_id, item.qty + 1)}
                          style={{ width: 34, height: 36, background: "none", border: "none", cursor: "pointer", fontSize: 18, color: "#1a1a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
                      </div>

                      {/* Remove */}
                      <button onClick={() => remove(item.product_id)}
                        style={{ display: "flex", alignItems: "center", gap: 4, color: "#999", background: "none", border: "none", cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>
                        <Trash2 size={14} /> Remove
                      </button>
                    </div>
                  </div>

                  {/* Line price */}
                  <div style={{ flexShrink: 0, textAlign: "right" }}>
                    <p style={{ fontSize: 16, fontWeight: 900, color: "#1a1a1a" }}>{inr(Number(item.price) * item.qty)}</p>
                    {item.qty > 1 && <p style={{ fontSize: 11, color: "#888" }}>{inr(item.price)} each</p>}
                  </div>
                </div>
              ))}
            </div>

            {/* ── Order summary sidebar ── */}
            <div style={{ border: "1px solid #e8e0d5", borderRadius: 10, padding: "24px 22px", position: "sticky", top: 120 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: "#1a1a1a", marginBottom: 20 }}>Order Summary</h2>

              {/* Line items */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "#555" }}>
                  <span>Subtotal ({items.reduce((s, i) => s + i.qty, 0)} items)</span>
                  <span>{inr(subtotal)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "#555" }}>
                  <span>Shipping</span>
                  <span style={{ color: shipping === 0 ? G : "#1a1a1a", fontWeight: 600 }}>
                    {shipping === 0 ? "FREE" : inr(shipping)}
                  </span>
                </div>
              </div>

              {/* Free shipping nudge */}
              {subtotal < 699 && (
                <div style={{ backgroundColor: "#edf7f0", border: "1px solid #c6e8d4", borderRadius: 6, padding: "10px 12px", marginBottom: 16, fontSize: 12, color: G, lineHeight: 1.5 }}>
                  Add <strong>{inr(699 - subtotal)}</strong> more to get <strong>FREE shipping</strong>!
                </div>
              )}

              {/* Total */}
              <div style={{ borderTop: "1px solid #e8e0d5", paddingTop: 14, marginBottom: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, fontWeight: 900, color: "#1a1a1a" }}>
                  <span>Total</span>
                  <span>{inr(total)}</span>
                </div>
                <p style={{ fontSize: 11, color: "#888", marginTop: 4 }}>Inclusive of all taxes</p>
              </div>

              <Link href="/checkout"
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: G, color: "#fff", padding: "15px 0", borderRadius: 6, fontWeight: 800, fontSize: 14, letterSpacing: "0.08em", textDecoration: "none" }}>
                PROCEED TO CHECKOUT <ArrowRight size={16} />
              </Link>

              {/* Payment logos */}
              <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
                {["VISA", "MASTERCARD", "UPI", "AMEX", "COD"].map(m => (
                  <span key={m} style={{ fontSize: 9, fontWeight: 700, color: "#888", border: "1px solid #e0d8cc", borderRadius: 3, padding: "2px 6px" }}>{m}</span>
                ))}
              </div>

              {/* Trust badges */}
              <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  "🔒 100% Secure Payments",
                  "🚚 Free shipping above ₹699",
                  "↩️ Easy 30-day returns",
                ].map(t => <p key={t} style={{ fontSize: 11, color: "#888", margin: 0 }}>{t}</p>)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}