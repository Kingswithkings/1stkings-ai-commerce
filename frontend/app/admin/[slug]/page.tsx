"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL } from "../../../lib/config";

type Order = {
  id: number;
  session_id: string;
  store_slug: string;
  items: string;
  status: string;
  fulfillment_type?: string | null;
  pickup_time?: string | null;
  delivery_address?: string | null;
  customer_name?: string | null;
  customer_phone?: string | null;
  flagged: number;
  created_at: string;
  updated_at: string;
};

const API_BASE = API_BASE_URL;

function parseItems(items: string) {
  try {
    return JSON.parse(items) as Array<{
      name: string;
      qty: number;
      unit_price: number;
    }>;
  } catch {
    return [];
  }
}

export default function AdminStorePage({
  params,
}: {
  params: { slug: string };
}) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function loadOrders() {
    const res = await fetch(
      `${API_BASE}/admin/orders?store_slug=${encodeURIComponent(params.slug)}`,
      { cache: "no-store" }
    );

    if (!res.ok) {
      throw new Error(`Failed to load orders: ${res.status}`);
    }

    const data = await res.json();
    setOrders(data);
  }

  useEffect(() => {
    loadOrders();
  }, [params.slug]);

  async function setStatus(orderId: number, status: string) {
    setBusyId(orderId);
    try {
      const res = await fetch(`${API_BASE}/admin/orders/${orderId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!res.ok) {
        throw new Error(`Failed to update status: ${res.status}`);
      }

      await loadOrders();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>
        Admin Orders — {params.slug}
      </h1>
      <p style={{ opacity: 0.7, marginBottom: 20 }}>
        Store-specific orders dashboard
      </p>

      {orders.length === 0 ? (
        <div>No orders yet for this store.</div>
      ) : (
        <div style={{ display: "grid", gap: 16 }}>
          {orders.map((order) => {
            const items = parseItems(order.items);
            const total = items.reduce(
              (sum, item) => sum + Number(item.qty) * Number(item.unit_price),
              0
            );

            return (
              <div
                key={order.id}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 12,
                  padding: 16,
                  background: "#fff",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 12,
                    marginBottom: 10,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800 }}>Order #{order.id}</div>
                    <div style={{ fontSize: 13, opacity: 0.7 }}>
                      Status: {order.status}
                    </div>
                    <div style={{ fontSize: 13, opacity: 0.7 }}>
                      Fulfillment: {order.fulfillment_type || "pickup"}
                    </div>
                  </div>
                  <div style={{ textAlign: "right", fontSize: 13 }}>
                    <div>Customer: {order.customer_name || "—"}</div>
                    <div>Phone: {order.customer_phone || "—"}</div>
                    <div>
                      {order.fulfillment_type === "delivery"
                        ? `Delivery: ${order.delivery_address || "—"}`
                        : `Pickup: ${order.pickup_time || "—"}`}
                    </div>
                  </div>
                </div>

                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Items</div>
                  {items.length === 0 ? (
                    <div style={{ opacity: 0.7 }}>No items</div>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {items.map((item, idx) => (
                        <li key={idx}>
                          {item.name} × {item.qty} — £
                          {(Number(item.qty) * Number(item.unit_price)).toFixed(2)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div style={{ fontWeight: 800, marginBottom: 12 }}>
                  Total: £{total.toFixed(2)}
                </div>

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    onClick={() => setStatus(order.id, "accepted")}
                    disabled={busyId === order.id}
                  >
                    Accept
                  </button>

                  <button
                    onClick={() => setStatus(order.id, "ready")}
                    disabled={busyId === order.id}
                  >
                    Ready
                  </button>

                  <button
                    onClick={() => setStatus(order.id, "completed")}
                    disabled={busyId === order.id}
                  >
                    Completed
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
