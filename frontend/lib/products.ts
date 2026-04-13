// frontend/lib/products.ts

import { API_BASE_URL } from "./config";

export type Product = {
  sku: string;
  name: string;
  price: number;
  unit: string;
  in_stock: number;
  aliases: string[];
  category: string;
  size_pricing: { label: string; price: number }[];
};

const API_BASE = API_BASE_URL;

export async function fetchProducts(storeSlug: string): Promise<Product[]> {
  const res = await fetch(
    `${API_BASE}/products?store_slug=${encodeURIComponent(storeSlug)}`,
    {
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error(`Products API error: ${res.status}`);
  }

  const data = await res.json();

  return (data ?? []).map((p: any) => ({
    sku: p.sku,
    name: p.name,
    price: Number(p.price),
    unit: p.unit,
    in_stock: Number(p.in_stock),
    aliases: Array.isArray(p.aliases) ? p.aliases : [],
    category: p.category || "Uncategorized",
    size_pricing: Array.isArray(p.size_pricing) ? p.size_pricing : [],
  }));
}
