import { API_BASE_URL } from "./config";

export function resolveImageUrl(imageUrl?: string | null): string {
  const value = (imageUrl || "").trim();

  if (!value) return "";
  if (
    value.startsWith("http://") ||
    value.startsWith("https://") ||
    value.startsWith("blob:") ||
    value.startsWith("data:")
  ) {
    return value;
  }
  if (value.startsWith("/")) {
    return `${API_BASE_URL}${value}`;
  }
  return value;
}
