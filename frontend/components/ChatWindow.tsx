"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchStoreChannelConfig, sendChat, type StoreChannelConfig } from "../lib/api";
import CartPanel from "./CartPanel";
import ProductList from "./ProductList";

type Msg = { role: "user" | "assistant"; text: string };

const STORE_CONFIG: Record<
  string,
  { name: string; phone: string; opening: string; example: string }
> = {
  "naija-house": {
    name: "Naija House",
    phone: "07543494001",
    opening: "Monday – Sunday",
    example: "2 indomie onion and rice 5kg",
  },
  "global-food-market": {
    name: "Global Food Market",
    phone: "07466600834",
    opening: "Monday – Sunday",
    example: "2 indomie onion and rice 5kg",
  },
  "najeebullah": {
    name: "Doncaster Budget Shop",
    phone: "+44 7462638297",
    opening: "Monday – Sunday",
    example: "2 phone chargers, 1 toilet brush and 1 frying pan",
  },
};

function getSessionId(storeSlug: string): string {
  if (typeof window === "undefined") return "server";
  const k = `session_id_${storeSlug}`;
  let v = localStorage.getItem(k);
  if (!v) {
    v = Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(k, v);
  }
  return v;
}

export default function ChatWindow({
  storeSlug = "naija-house",
}: {
  storeSlug?: string;
}) {
  const store = STORE_CONFIG[storeSlug] ?? STORE_CONFIG["naija-house"];

  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text:
        `Hi 👋\n` +
        `Welcome to ${store.name}.\n` +
        `Contact: ${store.phone}\n\n` +
        `Tell me what you want to buy. Example: '${store.example}'.`,
    },
  ]);

  const [input, setInput] = useState("");
  const [cart, setCart] = useState<{
    items: any[];
    total: number;
    status: string;
  } | null>({
    items: [],
    total: 0,
    status: "draft",
  });

  const [busy, setBusy] = useState(false);
  const [channelConfig, setChannelConfig] = useState<StoreChannelConfig | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSessionId(getSessionId(storeSlug));
  }, [storeSlug]);

  useEffect(() => {
    let active = true;

    fetchStoreChannelConfig(storeSlug)
      .then((data) => {
        if (active) setChannelConfig(data);
      })
      .catch(() => {
        if (active) setChannelConfig(null);
      });

    return () => {
      active = false;
    };
  }, [storeSlug]);

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        text:
          `Hi 👋\n` +
          `Welcome to ${store.name}.\n` +
          `Contact: ${store.phone}\n\n` +
          `Tell me what you want to buy. Example: '${store.example}'.`,
      },
    ]);
    setCart({
      items: [],
      total: 0,
      status: "draft",
    });
    setInput("");
  }, [store.name, store.phone, store.example]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !busy && !!sessionId,
    [input, busy, sessionId]
  );

  async function sendText(text: string) {
    const clean = (text || "").trim();
    if (!clean || !sessionId) return;

    setMessages((m) => [...m, { role: "user", text: clean }]);
    setBusy(true);

    try {
      const res = await sendChat(sessionId, clean, storeSlug);
      setMessages((m) => [...m, { role: "assistant", text: res.reply }]);
      if (res.cart) setCart(res.cart);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Sorry — API temporarily unavailable. Please try again.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function onSend() {
    if (!canSend) return;
    const text = input.trim();
    setInput("");
    await sendText(text);
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 18 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
          borderBottom: "1px solid #1d2b4a",
          paddingBottom: 8,
        }}
      >
        <div>
          <div style={{ fontSize: 18, fontWeight: 800 }}>{store.name}</div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Smart AI Ordering</div>
        </div>

        <div style={{ fontSize: 12, opacity: 0.7 }}>
          Open • {store.opening} • {store.phone}
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
          }}
        >
          <div>
            <div style={{ fontSize: 22, fontWeight: 900 }}>
              {store.name} — Chat Order
            </div>
            <div style={{ fontSize: 11, opacity: 0.6 }}>
              Store slug: {storeSlug}
            </div>
          </div>

          <div style={{ fontSize: 12, opacity: 0.7 }}>
            Session: {sessionId ? sessionId.slice(0, 8) : "..."}
          </div>
        </div>
      </div>

      {channelConfig?.whatsapp.enabled && channelConfig.whatsapp.link ? (
        <div
          style={{
            marginBottom: 14,
            padding: 16,
            borderRadius: 14,
            border: "1px solid #1d2b4a",
            background:
              "linear-gradient(135deg, rgba(11,19,36,1) 0%, rgba(11,52,38,0.95) 100%)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 900 }}>WhatsApp AI Ordering</div>
              <div style={{ fontSize: 13, opacity: 0.8, maxWidth: 720, marginTop: 4 }}>
                Customers can place and confirm orders in WhatsApp using the same AI order flow as this web app.
              </div>
            </div>

            <a
              href={channelConfig.whatsapp.link}
              target="_blank"
              rel="noreferrer"
              style={{
                alignSelf: "center",
                textDecoration: "none",
                background: "#25D366",
                color: "#08110b",
                padding: "12px 16px",
                borderRadius: 999,
                fontWeight: 900,
              }}
            >
              Open WhatsApp
            </a>
          </div>

          <div style={{ fontSize: 12, opacity: 0.75, marginTop: 10 }}>
            WhatsApp number: {channelConfig.whatsapp.number}
          </div>
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 14 }}>
        <div
          style={{
            background: "#111a2e",
            borderRadius: 14,
            padding: 16,
            border: "1px solid #1d2b4a",
            minHeight: 560,
          }}
        >
          <ProductList
            storeSlug={storeSlug}
            busy={busy}
            height={470}
            onPlus={(name: string) => {
              if (!busy && sessionId) sendText(`1 ${name}`);
            }}
            onMinus={(name: string) => {
              if (!busy && sessionId) sendText(`remove ${name}`);
            }}
          />
        </div>

        <div
          style={{
            background: "#111a2e",
            borderRadius: 14,
            padding: 16,
            border: "1px solid #1d2b4a",
            minHeight: 560,
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 14 }}>
            <div
              style={{
                background: "#0b1324",
                borderRadius: 14,
                padding: 14,
                border: "1px solid #1d2b4a",
                minHeight: 520,
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div style={{ fontWeight: 900, marginBottom: 10, color: "#e8eefc" }}>
                Chat
              </div>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  flex: 1,
                  overflow: "auto",
                  paddingRight: 6,
                }}
              >
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    style={{
                      alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                      maxWidth: "85%",
                      padding: "10px 12px",
                      borderRadius: 14,
                      background: m.role === "user" ? "#1b3a78" : "#111a2e",
                      border: "1px solid #1d2b4a",
                      whiteSpace: "pre-wrap",
                      lineHeight: 1.35,
                      color: "#e8eefc",
                    }}
                  >
                    {m.text}
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => (e.key === "Enter" ? onSend() : null)}
                  placeholder={`Type your order… (e.g., ${store.example})`}
                  style={{
                    flex: 1,
                    padding: "12px 12px",
                    borderRadius: 12,
                    border: "1px solid #1d2b4a",
                    background: "#0b1324",
                    color: "#e8eefc",
                    outline: "none",
                  }}
                />
                <button
                  onClick={onSend}
                  disabled={!canSend}
                  style={{
                    padding: "12px 16px",
                    borderRadius: 12,
                    border: "1px solid #1d2b4a",
                    background: canSend ? "#1b3a78" : "#0b1324",
                    color: "#e8eefc",
                    cursor: canSend ? "pointer" : "not-allowed",
                    fontWeight: 800,
                  }}
                >
                  {busy ? "..." : "Send"}
                </button>
              </div>

              <div style={{ marginTop: 10, fontSize: 12, opacity: 0.75, color: "#e8eefc" }}>
                Tips: <b>show cart</b> • <b>remove item</b> • <b>checkout</b>
              </div>
            </div>

            <div style={{ minHeight: 520 }}>
              <CartPanel
                items={cart?.items || []}
                total={cart?.total || 0}
                status={cart?.status || "draft"}
              />
            </div>
          </div>
        </div>
      </div>

      <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 24 }}>
        Powered by 1stkings AI •{" "}
        <a
          href="https://1st-kings.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ textDecoration: "underline", color: "#9ca3af" }}
        >
          1st-kings.com
        </a>
      </div>
    </div>
  );
}
