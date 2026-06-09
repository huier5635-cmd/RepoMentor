const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "").trim();
const devApiBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
const API_ORIGIN = String(configuredApiBaseUrl || devApiBaseUrl).replace(/\/+$/, "");
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    const error = new Error(text || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export function getModelStatus() {
  return request("/model/status");
}

export function updateModelConfig(config) {
  return request("/model/config", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function testModelConnection() {
  return request("/model/test", { method: "POST" });
}
