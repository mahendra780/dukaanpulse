import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const ACCESS_TOKEN_KEY = "dukaanpulse.accessToken";
const POST_LOGIN_PATH_KEY = "dukaanpulse.postLoginPath";

let unauthorizedHandler = null;

// A timeout means a hung request ends in a clear message instead of a
// loading state that never finishes.
export const api = axios.create({ baseURL, timeout: 30000 });

export function getStoredToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeToken(token) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getPostLoginPath() {
  return sessionStorage.getItem(POST_LOGIN_PATH_KEY);
}

export function clearPostLoginPath() {
  sessionStorage.removeItem(POST_LOGIN_PATH_KEY);
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;

  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

function isLoginRequest(config) {
  const url = config?.url?.split("?")[0]?.replace(/\/+$/, "");
  return config?.method?.toLowerCase() === "post" && url === "/auth/login";
}

function rememberCurrentPath() {
  const path = window.location.pathname + window.location.search + window.location.hash;
  sessionStorage.setItem(POST_LOGIN_PATH_KEY, path);
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error?.response?.status === 401 &&
      !isLoginRequest(error.config) &&
      window.location.pathname !== "/login"
    ) {
      rememberCurrentPath();
      clearStoredSession();
      unauthorizedHandler?.();
    }

    return Promise.reject(error);
  }
);

const STATUS_FALLBACKS = {
  400: "The information provided is not valid. Please check your details and try again.",
  401: "Your session has expired. Please sign in again.",
  403: "You don't have permission to perform this action.",
  404: "We couldn't find the requested item.",
  409: "This record already exists or conflicts with an existing record.",
  422: "Please check the highlighted fields and correct the information.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "Something went wrong on our side. Please try again later.",
  502: "The service is temporarily unavailable. Please try again in a moment.",
  503: "The service is temporarily unavailable. Please try again in a moment.",
  504: "The service is temporarily unavailable. Please try again in a moment.",
};

// Normalizes FastAPI's error shape ({"detail": "..."} or a validation
// array) into a single readable string for the UI to display. Falls
// back to a generic, status-aware message when there's no specific
// detail, to a timeout message when the request took too long, and to a
// network-failure message when it never got a response at all.
export function extractErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (detail) {
    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d?.msg ? `${d.loc?.at(-1) ?? ""}: ${d.msg}` : JSON.stringify(d)))
        .join(", ");
    }

    return JSON.stringify(detail);
  }

  const status = error?.response?.status;
  if (status && STATUS_FALLBACKS[status]) return STATUS_FALLBACKS[status];

  // Checked BEFORE the generic network case: a timeout also has a
  // request and no response, but the right advice is different.
  if (error?.code === "ECONNABORTED" || error?.code === "ETIMEDOUT") {
    return "The request is taking longer than expected. Please try again in a moment.";
  }

  if (error?.request && !error?.response) {
    return "We couldn't connect to the server. Please check your internet connection and try again.";
  }

  return error?.message || "Something went wrong. Please try again.";
}