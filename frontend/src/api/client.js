import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const api = axios.create({ baseURL });

export function extractErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (!detail) return error?.message || "Something went wrong";
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d?.msg ? `${d.loc?.at(-1) ?? ""}: ${d.msg}` : JSON.stringify(d)))
      .join(", ");
  }

  return JSON.stringify(detail);
}
