import axios from "axios";

// Mismo origen siempre: Nginx (producción) o el proxy de Vite (desarrollo) enrutan /api
export const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  paramsSerializer: { indexes: null }, // severity=0&severity=2 (formato que espera FastAPI)
});

/** URL absoluta (MapLibre necesita URLs completas para las teselas vectoriales). */
export function absoluteApiUrl(path: string): string {
  const base = API_BASE.startsWith("http") ? API_BASE : `${window.location.origin}${API_BASE}`;
  return `${base}${path}`;
}
