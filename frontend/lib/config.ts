const rawApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE ??
  "http://localhost:8000";

export const API_BASE_URL = rawApiBaseUrl.trim().replace(/\/$/, "");
