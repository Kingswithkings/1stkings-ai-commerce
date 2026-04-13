"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { API_BASE } from "../../../lib/api";
import { resolveImageUrl } from "../../../lib/images";

type Product = {
  id: number;
  sku: string;
  name: string;
  aliases: string;
  price: number;
  unit: string;
  stock_qty: number;
  in_stock: boolean;
  category: string;
  image_url?: string | null;
  description?: string | null;
  size_pricing?: { label: string; price: number }[];
  is_active: boolean;
  min_stock_level: number;
  low_stock?: boolean;
};

type ChannelSettings = {
  store_slug: string;
  store_name: string;
  whatsapp_enabled: boolean;
  whatsapp_provider: string;
  whatsapp_number: string;
  whatsapp_phone_number_id: string;
  whatsapp_bot_id: string;
  whatsapp_verify_token: string;
};

const emptyForm = {
  sku: "",
  name: "",
  aliases: "",
  price: "",
  unit: "each",
  stock_qty: "0",
  category: "Uncategorized",
  image_url: "",
  description: "",
  size_pricing: "",
  is_active: true,
  min_stock_level: "0",
};

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [channelSettings, setChannelSettings] = useState<ChannelSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingChannelSettings, setSavingChannelSettings] = useState(false);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const [form, setForm] = useState({ ...emptyForm });
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [selectedImagePreview, setSelectedImagePreview] = useState("");
  const [removeImage, setRemoveImage] = useState(false);
  const [imageInputKey, setImageInputKey] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const token =
    typeof window !== "undefined" ? localStorage.getItem("admin_token") : null;
  const isSendPulseProvider = channelSettings?.whatsapp_provider === "sendpulse";

  const authHeaders = useMemo(
    () => ({
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    }),
    [token]
  );

  const fetchProducts = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/admin/products`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load products");
      }

      setProducts(data);
    } catch (err: any) {
      setError(err.message || "Failed to load products");
    } finally {
      setLoading(false);
    }
  };

  const fetchChannelSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/products/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load store settings");
      }

      setChannelSettings(data);
    } catch (err: any) {
      setError(err.message || "Failed to load store settings");
    }
  };

  useEffect(() => {
    fetchProducts();
    fetchChannelSettings();
  }, []);

  useEffect(() => {
    if (!selectedImageFile) {
      setSelectedImagePreview("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedImageFile);
    setSelectedImagePreview(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedImageFile]);

  const resetForm = () => {
    setForm({ ...emptyForm });
    setSelectedImageFile(null);
    setSelectedImagePreview("");
    setRemoveImage(false);
    setImageInputKey((value) => value + 1);
    setEditingProduct(null);
    setShowCreateForm(false);
  };

  const startCreate = () => {
    setSuccess("");
    setError("");
    setEditingProduct(null);
    setForm({ ...emptyForm });
    setSelectedImageFile(null);
    setSelectedImagePreview("");
    setRemoveImage(false);
    setImageInputKey((value) => value + 1);
    setShowCreateForm(true);
  };

  const startEdit = (product: Product) => {
    setSuccess("");
    setError("");
    setShowCreateForm(false);
    setEditingProduct(product);
    setSelectedImageFile(null);
    setSelectedImagePreview("");
    setRemoveImage(false);
    setImageInputKey((value) => value + 1);

    setForm({
      sku: product.sku || "",
      name: product.name || "",
      aliases: product.aliases || "",
      price: String(product.price ?? ""),
      unit: product.unit || "each",
      stock_qty: String(product.stock_qty ?? 0),
      category: product.category || "Uncategorized",
      image_url: product.image_url || "",
      description: product.description || "",
      size_pricing: (product.size_pricing || [])
        .map((option) => `${option.label}:${option.price}`)
        .join("\n"),
      is_active: product.is_active,
      min_stock_level: String(product.min_stock_level ?? 0),
    });
  };

  const handleChange = (
    field: string,
    value: string | boolean
  ) => {
    if (field === "image_url") {
      setSelectedImageFile(null);
      setSelectedImagePreview("");
      setRemoveImage(false);
    }

    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleImageFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedImageFile(file);
    setRemoveImage(false);

    if (file) {
      setForm((prev) => ({
        ...prev,
        image_url: "",
      }));
    }
  };

  const clearSelectedImage = () => {
    setSelectedImageFile(null);
    setSelectedImagePreview("");
    setRemoveImage(true);
    setImageInputKey((value) => value + 1);
    setForm((prev) => ({
      ...prev,
      image_url: "",
    }));
  };

  const parseSizePricingText = (value: string) => {
    const lines = value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    return lines.map((line) => {
      const separatorIndex = line.lastIndexOf(":");
      if (separatorIndex <= 0) {
        throw new Error("Use one size per line in the format Size:Price");
      }

      const label = line.slice(0, separatorIndex).trim();
      const rawPrice = line.slice(separatorIndex + 1).trim();
      const price = Number(rawPrice);

      if (!label || Number.isNaN(price)) {
        throw new Error("Use one size per line in the format Size:Price");
      }

      return { label, price };
    });
  };

  const buildPayload = () => {
    const payload = new FormData();
    payload.set("sku", form.sku.trim());
    payload.set("name", form.name.trim());
    payload.set("aliases", form.aliases.trim());
    payload.set("price", String(Number(form.price)));
    payload.set("unit", form.unit.trim() || "each");
    payload.set("stock_qty", String(Number(form.stock_qty)));
    payload.set("category", form.category.trim() || "Uncategorized");
    payload.set("image_url", form.image_url.trim());
    payload.set("description", form.description.trim());
    payload.set("size_pricing", JSON.stringify(parseSizePricingText(form.size_pricing)));
    payload.set("is_active", String(Boolean(form.is_active)));
    payload.set("min_stock_level", String(Number(form.min_stock_level)));
    payload.set("remove_image", String(removeImage && !selectedImageFile && !form.image_url.trim()));

    if (selectedImageFile) {
      payload.set("image_file", selectedImageFile);
    }

    return payload;
  };

  const imagePreviewUrl = selectedImagePreview || resolveImageUrl(form.image_url);
  const showingExistingImage = Boolean(!selectedImageFile && form.image_url);

  const handleCreate = async () => {
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${API_BASE}/admin/products`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: buildPayload(),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to create product");
      }

      setSuccess("Product created successfully.");
      resetForm();
      fetchProducts();
    } catch (err: any) {
      setError(err.message || "Failed to create product");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingProduct) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(
        `${API_BASE}/admin/products/${editingProduct.id}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: buildPayload(),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to update product");
      }

      setSuccess("Product updated successfully.");
      resetForm();
      fetchProducts();
    } catch (err: any) {
      setError(err.message || "Failed to update product");
    } finally {
      setSaving(false);
    }
  };

  const deleteProduct = async (id: number) => {
    const confirmed = window.confirm("Delete this product?");
    if (!confirmed) return;

    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${API_BASE}/admin/products/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to delete product");
      }

      setSuccess("Product deleted.");
      fetchProducts();
    } catch (err: any) {
      setError(err.message || "Failed to delete product");
    }
  };

  const updateStock = async (id: number, stockQty: number) => {
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${API_BASE}/admin/products/${id}/stock`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify({ stock_qty: stockQty }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to update stock");
      }

      setSuccess("Stock updated.");
      fetchProducts();
    } catch (err: any) {
      setError(err.message || "Failed to update stock");
    }
  };

  const toggleStatus = async (id: number, isActive: boolean) => {
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${API_BASE}/admin/products/${id}/status`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify({ is_active: !isActive }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to update status");
      }

      setSuccess("Product status updated.");
      fetchProducts();
    } catch (err: any) {
      setError(err.message || "Failed to update status");
    }
  };

  const updateChannelField = (
    field: keyof ChannelSettings,
    value: string | boolean
  ) => {
    setChannelSettings((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        [field]: value,
      } as ChannelSettings;
    });
  };

  const saveChannelSettings = async () => {
    if (!channelSettings) return;

    setSavingChannelSettings(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${API_BASE}/admin/products/settings`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify({
          whatsapp_enabled: channelSettings.whatsapp_enabled,
          whatsapp_provider: channelSettings.whatsapp_provider,
          whatsapp_number: channelSettings.whatsapp_number,
          whatsapp_phone_number_id: channelSettings.whatsapp_phone_number_id,
          whatsapp_bot_id: channelSettings.whatsapp_bot_id,
          whatsapp_verify_token: channelSettings.whatsapp_verify_token,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to update store settings");
      }

      setSuccess("WhatsApp settings updated.");
      setChannelSettings(data.store);
    } catch (err: any) {
      setError(err.message || "Failed to update store settings");
    } finally {
      setSavingChannelSettings(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading products...</div>;
  }

  return (
    <div className="min-h-screen p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Admin Products</h1>
        <button
          onClick={startCreate}
          className="bg-black text-white px-4 py-2 rounded"
        >
          Add Product
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 rounded border border-green-300 bg-green-50 p-3 text-green-700">
          {success}
        </div>
      )}

      {channelSettings && (
        <div className="mb-8 rounded border p-5">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="text-xl font-semibold">WhatsApp AI Channel</h2>
              <p className="text-sm text-gray-600 mt-1">
                Connect either SendPulse or Meta so customers can order through the same conversational flow as the web app.
              </p>
            </div>
            <div className="text-sm text-gray-500">
              Store: {channelSettings.store_name}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={channelSettings.whatsapp_enabled}
                onChange={(e) =>
                  updateChannelField("whatsapp_enabled", e.target.checked)
                }
              />
              Enable WhatsApp ordering
            </label>

            <select
              className="border p-2 rounded"
              value={channelSettings.whatsapp_provider}
              onChange={(e) =>
                updateChannelField("whatsapp_provider", e.target.value)
              }
            >
              <option value="sendpulse">SendPulse</option>
              <option value="meta">Meta Cloud API</option>
            </select>

            <input
              className="border p-2 rounded"
              placeholder="WhatsApp number"
              value={channelSettings.whatsapp_number}
              onChange={(e) =>
                updateChannelField("whatsapp_number", e.target.value)
              }
            />

            {isSendPulseProvider ? (
              <input
                className="border p-2 rounded"
                placeholder="SendPulse bot ID"
                value={channelSettings.whatsapp_bot_id}
                onChange={(e) =>
                  updateChannelField("whatsapp_bot_id", e.target.value)
                }
              />
            ) : (
              <>
                <input
                  className="border p-2 rounded"
                  placeholder="Meta phone number ID"
                  value={channelSettings.whatsapp_phone_number_id}
                  onChange={(e) =>
                    updateChannelField("whatsapp_phone_number_id", e.target.value)
                  }
                />

                <input
                  className="border p-2 rounded"
                  placeholder="Webhook verify token"
                  value={channelSettings.whatsapp_verify_token}
                  onChange={(e) =>
                    updateChannelField("whatsapp_verify_token", e.target.value)
                  }
                />
              </>
            )}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={saveChannelSettings}
              disabled={savingChannelSettings}
              className="bg-green-700 text-white px-4 py-2 rounded"
            >
              {savingChannelSettings ? "Saving..." : "Save WhatsApp Settings"}
            </button>

            <div className="text-sm text-gray-600">
              Webhook URL: {API_BASE}/channels/whatsapp/webhook
            </div>
          </div>

          <div className="mt-3 text-sm text-gray-600">
            {channelSettings.whatsapp_provider === "sendpulse"
              ? "Set SENDPULSE_API_ID and SENDPULSE_API_SECRET on the backend, then use this webhook URL in your SendPulse bot workflow or webhook integration."
              : "Use the webhook URL and verify token in Meta WhatsApp Cloud API, plus set WHATSAPP_ACCESS_TOKEN on the backend."}
          </div>
        </div>
      )}

      {(showCreateForm || editingProduct) && (
        <div className="mb-8 rounded border p-5">
          <h2 className="text-xl font-semibold mb-4">
            {editingProduct ? "Edit Product" : "Add Product"}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              className="border p-2 rounded"
              placeholder="SKU"
              value={form.sku}
              onChange={(e) => handleChange("sku", e.target.value)}
            />

            <input
              className="border p-2 rounded"
              placeholder="Product Name"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
            />

            <input
              className="border p-2 rounded"
              placeholder="Aliases (comma separated)"
              value={form.aliases}
              onChange={(e) => handleChange("aliases", e.target.value)}
            />

            <input
              type="number"
              step="0.01"
              className="border p-2 rounded"
              placeholder="Price"
              value={form.price}
              onChange={(e) => handleChange("price", e.target.value)}
            />

            <input
              className="border p-2 rounded"
              placeholder="Unit (each, pack, bottle, kg)"
              value={form.unit}
              onChange={(e) => handleChange("unit", e.target.value)}
            />

            <input
              type="number"
              className="border p-2 rounded"
              placeholder="Stock Quantity"
              value={form.stock_qty}
              onChange={(e) => handleChange("stock_qty", e.target.value)}
            />

            <input
              className="border p-2 rounded"
              placeholder="Category"
              value={form.category}
              onChange={(e) => handleChange("category", e.target.value)}
            />

            <input
              type="number"
              className="border p-2 rounded"
              placeholder="Minimum Stock Level"
              value={form.min_stock_level}
              onChange={(e) => handleChange("min_stock_level", e.target.value)}
            />

            <input
              className="border p-2 rounded md:col-span-2"
              placeholder="Image URL"
              value={form.image_url}
              onChange={(e) => handleChange("image_url", e.target.value)}
            />

            <div className="md:col-span-2 rounded border border-dashed p-4">
              <div className="text-sm font-medium">Upload or snap a product image</div>
              <div className="mt-1 text-xs text-gray-600">
                Paste an external URL above, or upload directly from your device camera or gallery here.
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <label className="rounded border px-3 py-2 text-sm cursor-pointer">
                  Upload from device
                  <input
                    key={`library-${imageInputKey}`}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleImageFileChange}
                  />
                </label>

                <label className="rounded border px-3 py-2 text-sm cursor-pointer">
                  Snap photo
                  <input
                    key={`camera-${imageInputKey}`}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={handleImageFileChange}
                  />
                </label>

                {(selectedImageFile || form.image_url) && (
                  <button
                    type="button"
                    onClick={clearSelectedImage}
                    className="rounded border px-3 py-2 text-sm text-red-600"
                  >
                    {showingExistingImage ? "Remove current image" : "Clear selected image"}
                  </button>
                )}
              </div>

              {selectedImageFile && (
                <div className="mt-3 text-sm text-gray-700">
                  Selected file: {selectedImageFile.name}
                </div>
              )}

              {removeImage && !selectedImageFile && !form.image_url && (
                <div className="mt-3 text-sm text-red-600">
                  This product image will be removed when you save.
                </div>
              )}
            </div>

            <textarea
              className="border p-2 rounded md:col-span-2 min-h-[100px]"
              placeholder="Description"
              value={form.description}
              onChange={(e) => handleChange("description", e.target.value)}
            />

            <textarea
              className="border p-2 rounded md:col-span-2 min-h-[100px]"
              placeholder={`Size pricing (optional)\n500ml:1.50\n1L:2.50`}
              value={form.size_pricing}
              onChange={(e) => handleChange("size_pricing", e.target.value)}
            />

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => handleChange("is_active", e.target.checked)}
              />
              Active
            </label>
          </div>

          {imagePreviewUrl && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium">Image Preview</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagePreviewUrl}
                alt="Preview"
                className="h-20 w-20 object-cover rounded border"
              />
            </div>
          )}

          <div className="mt-5 flex gap-3">
            {editingProduct ? (
              <button
                onClick={handleUpdate}
                disabled={saving}
                className="bg-black text-white px-4 py-2 rounded"
              >
                {saving ? "Saving..." : "Update Product"}
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={saving}
                className="bg-black text-white px-4 py-2 rounded"
              >
                {saving ? "Saving..." : "Create Product"}
              </button>
            )}

            <button
              onClick={resetForm}
              className="border px-4 py-2 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="text-left p-3">Image</th>
              <th className="text-left p-3">Name</th>
              <th className="text-left p-3">SKU</th>
              <th className="text-left p-3">Price</th>
              <th className="text-left p-3">Stock</th>
              <th className="text-left p-3">Category</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Actions</th>
            </tr>
          </thead>

          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-t align-top">
                <td className="p-3">
                  {p.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={resolveImageUrl(p.image_url)}
                      alt={p.name}
                      className="h-14 w-14 object-cover rounded border"
                    />
                  ) : (
                    <div className="h-14 w-14 rounded border flex items-center justify-center text-xs text-gray-500">
                      No image
                    </div>
                  )}
                </td>

                <td className="p-3">
                  <div className="font-medium">{p.name}</div>
                  {p.size_pricing && p.size_pricing.length > 0 && (
                    <div className="text-xs text-gray-500 mt-1 max-w-xs">
                      {p.size_pricing
                        .map((option) => `${option.label}: £${Number(option.price).toFixed(2)}`)
                        .join(" • ")}
                    </div>
                  )}
                  {p.description && (
                    <div className="text-xs text-gray-500 mt-1 max-w-xs">
                      {p.description}
                    </div>
                  )}
                </td>

                <td className="p-3">{p.sku}</td>
                <td className="p-3">£{Number(p.price).toFixed(2)}</td>
                <td className="p-3">
                  <div>{p.stock_qty}</div>
                  {p.low_stock && (
                    <div className="text-xs text-orange-600">Low stock</div>
                  )}
                </td>
                <td className="p-3">{p.category}</td>
                <td className="p-3">
                  <button
                    onClick={() => toggleStatus(p.id, p.is_active)}
                    className={`px-2 py-1 rounded text-white ${
                      p.is_active ? "bg-green-600" : "bg-gray-500"
                    }`}
                  >
                    {p.is_active ? "Active" : "Hidden"}
                  </button>
                </td>

                <td className="p-3">
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => startEdit(p)}
                      className="text-blue-600 text-left"
                    >
                      Edit
                    </button>

                    <button
                      onClick={() => {
                        const value = window.prompt(
                          `Update stock for ${p.name}`,
                          String(p.stock_qty)
                        );
                        if (value !== null && value !== "") {
                          updateStock(p.id, Number(value));
                        }
                      }}
                      className="text-purple-600 text-left"
                    >
                      Update Stock
                    </button>

                    <button
                      onClick={() => deleteProduct(p.id)}
                      className="text-red-600 text-left"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {products.length === 0 && (
              <tr>
                <td colSpan={8} className="p-6 text-center text-gray-500">
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
