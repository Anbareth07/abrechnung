import axios from "axios";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

/** Wandelt einen Wert (string/number/null) sicher in eine Zahl um. */
export const num = (v: unknown): number =>
  v === null || v === undefined || v === "" ? 0 : Number(v);

/** Formatiert eine Zahl deutsch mit fester Nachkommastellenzahl. */
export const fmt = (v: unknown, digits = 2): string =>
  num(v).toLocaleString("de-DE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

/** Generische CRUD-Funktionen für einen Ressourcen-Pfad. */
export function crud<T>(path: string) {
  return {
    list: (params?: Record<string, unknown>) => api.get<T[]>(path, { params }),
    create: (data: Partial<T>) => api.post<T>(path, data),
    update: (id: number, data: Partial<T>) => api.patch<T>(`${path}/${id}`, data),
    remove: (id: number) => api.delete(`${path}/${id}`),
  };
}
