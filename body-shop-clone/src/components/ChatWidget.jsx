"use client";
import { useState, useEffect, useRef } from "react";
import { MessageCircle, X, Send, User, Bot } from "lucide-react";

const GREEN = "#006e3c";

export default function ChatWidget() {
  const [isOpen,    setIsOpen]    = useState(false);
  const [messages,  setMessages]  = useState([
    { role: "ai", text: "Hi! 🌿 Welcome to The Body Shop. How can I help you find your perfect natural beauty product today?", ts: Date.now() },
  ]);
  const [input,     setInput]     = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sessionRef    = useRef(null);
  const bottomRef     = useRef(null);
  const inputRef      = useRef(null);

  useEffect(() => {
    sessionRef.current = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 120);
  }, [isOpen]);

  const send = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setMessages(m => [...m, { role: "user", text, ts: Date.now() }]);
    setInput("");
    setIsLoading(true);
    try {
      const res  = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionRef.current, message: text }),
      });
      const data = await res.json();
      setMessages(m => [...m, { role: "ai", text: data.reply, ts: Date.now() }]);
    } catch {
      setMessages(m => [...m, { role: "ai", text: "Sorry, I'm having trouble connecting. Please try again shortly.", ts: Date.now(), err: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const onKey = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };

  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 12 }}>

      {/* Chat window */}
      <div style={{
        width: 360, height: 500,
        backgroundColor: "#fff", borderRadius: 16,
        boxShadow: "0 16px 48px rgba(0,0,0,0.18)", border: "1px solid #e5e0d8",
        display: "flex", flexDirection: "column", overflow: "hidden",
        transition: "opacity 0.2s, transform 0.2s",
        opacity: isOpen ? 1 : 0, transform: isOpen ? "scale(1)" : "scale(0.92)",
        pointerEvents: isOpen ? "auto" : "none",
        transformOrigin: "bottom right",
      }}>
        {/* Header */}
        <div style={{ backgroundColor: GREEN, padding: "14px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 34, height: 34, borderRadius: "50%", backgroundColor: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Bot size={17} color="#fff" />
            </div>
            <div>
              <p style={{ color: "#fff", fontWeight: 700, fontSize: 14, margin: 0 }}>Body Shop Assistant</p>
              <p style={{ color: "#a7f3d0", fontSize: 11, margin: 0 }}>Online · Ready to help</p>
            </div>
          </div>
          <button onClick={() => setIsOpen(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "rgba(255,255,255,0.8)", display: "flex" }}>
            <X size={18} />
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "14px 14px 8px", display: "flex", flexDirection: "column", gap: 10 }}>
          {messages.map((msg, i) => (
            msg.role === "user" ? (
              <div key={i} style={{ display: "flex", alignItems: "flex-end", justifyContent: "flex-end", gap: 8 }}>
                <div style={{ maxWidth: "78%", backgroundColor: GREEN, color: "#fff", padding: "9px 14px", borderRadius: "16px 16px 4px 16px", fontSize: 13, lineHeight: 1.5 }}>
                  {msg.text}
                </div>
                <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#e5e0d8", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <User size={13} color="#666" />
                </div>
              </div>
            ) : (
              <div key={i} style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
                <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#edf7f0", border: "1px solid #c6e8d4", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Bot size={13} color={GREEN} />
                </div>
                <div style={{ maxWidth: "78%", backgroundColor: msg.err ? "#fef2f2" : "#f6fdf8", border: `1px solid ${msg.err ? "#fecaca" : "#c6e8d4"}`, color: msg.err ? "#dc2626" : "#1a1a1a", padding: "9px 14px", borderRadius: "16px 16px 16px 4px", fontSize: 13, lineHeight: 1.5 }}>
                  {msg.text}
                </div>
              </div>
            )
          ))}

          {isLoading && (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#edf7f0", border: "1px solid #c6e8d4", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Bot size={13} color={GREEN} />
              </div>
              <div style={{ backgroundColor: "#f6fdf8", border: "1px solid #c6e8d4", padding: "12px 16px", borderRadius: "16px 16px 16px 4px", display: "flex", gap: 5 }}>
                {[0,150,300].map(d => (
                  <span key={d} style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: GREEN, animation: "bounce 1s infinite", animationDelay: `${d}ms`, display: "inline-block" }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: "10px 12px", borderTop: "1px solid #e5e0d8", backgroundColor: "#faf7f2", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, backgroundColor: "#fff", border: "1.5px solid #e5e0d8", borderRadius: 12, padding: "8px 10px 8px 14px" }}>
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Ask about products, ingredients…"
              style={{ flex: 1, border: "none", outline: "none", fontSize: 13, color: "#1a1a1a", background: "transparent", resize: "none", fontFamily: "inherit", lineHeight: 1.4, maxHeight: 72 }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || isLoading}
              style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: input.trim() && !isLoading ? GREEN : "#e5e0d8", border: "none", cursor: input.trim() && !isLoading ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background-color 0.15s" }}
            >
              <Send size={14} color="#fff" />
            </button>
          </div>
          <p style={{ textAlign: "center", fontSize: 10, color: "#bbb", margin: "6px 0 0" }}>Powered by The Body Shop AI</p>
        </div>
      </div>

      {/* FAB */}
      <button
        onClick={() => setIsOpen(v => !v)}
        aria-label={isOpen ? "Close chat" : "Open chat"}
        style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: GREEN, border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 16px rgba(0,110,60,0.35)", transition: "transform 0.15s", position: "relative" }}
        onMouseEnter={e => e.currentTarget.style.transform = "scale(1.08)"}
        onMouseLeave={e => e.currentTarget.style.transform = "scale(1)"}
      >
        {!isOpen && (
          <span style={{ position: "absolute", inset: 0, borderRadius: "50%", backgroundColor: "rgba(0,110,60,0.35)", animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite" }} />
        )}
        {isOpen ? <X size={22} color="#fff" /> : <MessageCircle size={22} color="#fff" />}
      </button>

      <style>{`
        @keyframes bounce { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-4px) } }
        @keyframes ping   { 75%,100% { transform:scale(1.8); opacity:0 } }
      `}</style>
    </div>
  );
}