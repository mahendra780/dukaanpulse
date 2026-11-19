import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const POST_LOGIN_PATH_KEY = "dukaanpulse.postLoginPath";
const CSRF_COOKIE_NAME = "dukaanpulse_csrf";

let unauthorizedHandler = null;

// A timeout means a hung request ends in a clear message instead of a
// loading state that never finishes.
export const api = axios.create({ baseURL, timeout: 30000, withCredentials: true });

export function clearStoredSession() {
  // Authentication lives in HttpOnly cookies. This exists so callers can
  // clear only their in-memory UI state without touching browser storage.
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

// The first thing the app does is ask "am I signed in?". A 401 there only
// means "no", which is normal for someone visiting the landing page or the
// signup form. Only a 401 on a real request means the session expired.
function isSessionCheck(config) {
  const url = config?.url?.split("?")[0]?.replace(/\/+$/, "");
  return config?.method?.toLowerCase() === "get" && url === "/auth/me";
}

function rememberCurrentPath() {
  const path = window.location.pathname + window.location.search + window.location.hash;
  sessionStorage.setItem(POST_LOGIN_PATH_KEY, path);
}

api.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase();
  if (method && !["get", "head", "options"].includes(method)) {
    clearApiCache();
    const csrfToken = document.cookie
      .split("; ")
      .find((entry) => entry.startsWith(`${CSRF_COOKIE_NAME}=`))
      ?.split("=")
      .slice(1)
      .join("=");
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = decodeURIComponent(csrfToken);
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    const method = response.config?.method?.toLowerCase();
    if (method && !["get", "head", "options"].includes(method)) clearApiCache();
    return response;
  },
  (error) => {
    if (
      error?.response?.status === 401 &&
      !isLoginRequest(error.config) &&
      !isSessionCheck(error.config) &&
      window.location.pathname !== "/login"
    ) {
      rememberCurrentPath();
      clearStoredSession();
      unauthorizedHandler?.();
    }

    return Promise.reject(error);
  }
);

// ---- Short-lived cache for GET requests ----
// Without this every click on a sidebar link mounted the page again and
// asked the server for everything again. Now a repeat visit within
// CACHE_TTL_MS is answered instantly, identical requests that are already
// in flight share one network call, and any change (POST, PATCH, DELETE...)
// clears the cache so lists never show stale data after you edit something.
const CACHE_TTL_MS = 30000;
const responseCache = new Map();
const inFlight = new Map();
let cacheEpoch = 0;

export function clearApiCache() {
  cacheEpoch += 1;
  responseCache.clear();
  inFlight.clear();
}

const copyResponse = ({ data, status, statusText }) => ({
  data: structuredClone(data),
  status,
  statusText,
});

const networkGet = api.get.bind(api);

api.get = (url, config = {}) => {
  // Login state must always be fresh.
  if (config.cache === false || String(url).startsWith("/auth")) {
    return networkGet(url, config);
  }

  const key = `${url}?${JSON.stringify(config.params ?? {})}`;
  const hit = responseCache.get(key);
  if (hit && Date.now() - hit.time < CACHE_TTL_MS) {
    return Promise.resolve(copyResponse(hit.response));
  }

  const pending = inFlight.get(key);
  if (pending) return pending.then(copyResponse);

  const epoch = cacheEpoch;
  const request = networkGet(url, config)
    .then((response) => {
      const stored = {
        data: response.data,
        status: response.status,
        statusText: response.statusText,
      };
      if (epoch === cacheEpoch) {
        responseCache.set(key, { time: Date.now(), response: stored });
      }
      return copyResponse(stored);
    })
    .finally(() => {
      if (inFlight.get(key) === request) inFlight.delete(key);
    });

  inFlight.set(key, request);
  return request.then(copyResponse);
};

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