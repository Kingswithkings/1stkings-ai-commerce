"use client";

import { useEffect, useMemo, useState } from "react";
import type { Product } from "../lib/products";
import { fetchProducts } from "../lib/products";

export default function ProductList({
  onPlus,
  onMinus,
  busy,
  height = 230,
  storeSlug,
}: {
  onPlus: (productName: string) => void;
  onMinus: (productName: string) => void;
  busy?: boolean;
  height?: number;
  storeSlug: string;
}) {
  const [products, setProducts] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [activeCat, setActiveCat] = useState<string>("All");

  useEffect(() => {
    fetchProducts(storeSlug).then(setProducts).catch(() => setProducts([]));
  }, [storeSlug]);

  const categories = useMemo(() => {
    const cats = Array.from(
      new Set(
        (products || []).map(
          (p) => (p.category || "Uncategorized").trim() || "Uncategorized"
        )
      )
    ).sort((a, b) => a.localeCompare(b));

    return ["All", ...cats];
  }, [products]);

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();

    return (products || []).filter((p) => {
      const cat = (p.category || "Uncategorized").trim() || "Uncategorized";
      const catOk = activeCat === "All" ? true : cat === activeCat;
      const qOk = !term ? true : p.name.toLowerCase().includes(term);
      return catOk && qOk;
    });
  }, [q, products, activeCat]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 10,
        }}
      >
        <div style={{ fontWeight: 900, color: "#e8eefc" }}>Products</div>
        <div style={{ fontSize: 12, opacity: 0.75, color: "#e8eefc" }}>
          {products.length} items
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        {categories.map((c) => {
          const active = activeCat === c;
          return (
            <button
              key={c}
              onClick={() => setActiveCat(c)}
              style={{
                padding: "6px 10px",
                borderRadius: 999,
                border: "1px solid #1d2b4a",
                background: active ? "#1b3a78" : "#0b1324",
                color: "#e8eefc",
                cursor: "pointer",
                fontWeight: 800,
                fontSize: 12,
              }}
              title={`Filter: ${c}`}
            >
              {c}
            </button>
          );
        })}
      </div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search products..."
        style={{
          width: "100%",
          padding: "10px 12px",
          borderRadius: 12,
          border: "1px solid #1d2b4a",
          background: "#0b1324",
          color: "#e8eefc",
          outline: "none",
          marginBottom: 12,
        }}
      />

      <div
        style={{
          maxHeight: height,
          overflowY: "auto",
          paddingRight: 6,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {filtered.map((p) => {
          const cat = (p.category || "Uncategorized").trim() || "Uncategorized";

          return (
            <div
              key={p.sku}
              style={{
                padding: 10,
                borderRadius: 12,
                background: "#0b1324",
                border: "1px solid #1d2b4a",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                  color: "#e8eefc",
                }}
              >
                <div style={{ fontWeight: 650 }}>
                  {p.name}
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>{cat}</div>
                </div>
                <div style={{ fontWeight: 900 }}>£{p.price.toFixed(2)}</div>
              </div>

              <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4, color: "#e8eefc" }}>
                Unit: {p.unit} • Stock: {p.in_stock > 0 ? p.in_stock : "Out"}
              </div>

              <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end", gap: 8 }}>
                <button
                  disabled={busy}
                  onClick={() => onMinus(p.name)}
                  style={{
                    width: 36,
                    height: 32,
                    borderRadius: 10,
                    border: "1px solid #1d2b4a",
                    background: "#0b1324",
                    color: "#e8eefc",
                    cursor: busy ? "not-allowed" : "pointer",
                    fontWeight: 900,
                    fontSize: 16,
                    lineHeight: "32px",
                  }}
                  aria-label={`Remove one ${p.name}`}
                  title="Remove one"
                >
                  –
                </button>

                <button
                  disabled={busy || p.in_stock <= 0}
                  onClick={() => onPlus(p.name)}
                  style={{
                    width: 36,
                    height: 32,
                    borderRadius: 10,
                    border: "1px solid #1d2b4a",
                    background: !busy && p.in_stock > 0 ? "#1b3a78" : "#0b1324",
                    color: "#e8eefc",
                    cursor: !busy && p.in_stock > 0 ? "pointer" : "not-allowed",
                    fontWeight: 900,
                    fontSize: 16,
                    lineHeight: "32px",
                  }}
                  aria-label={`Add one ${p.name}`}
                  title="Add one"
                >
                  +
                </button>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div style={{ opacity: 0.75, fontSize: 13, color: "#e8eefc" }}>
            No products match “{q}” in {activeCat}.
          </div>
        )}
      </div>
    </div>
  );
}