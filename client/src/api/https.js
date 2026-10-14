import { clearDeviceKey, signProof } from "./deviceKey";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

// Identifies this app to the backend (X-Client-Key). It ships in the bundle,
// so it is NOT a secret -- it only keeps scanners and curl out. What protects
// a user is the session token plus the device key it is bound to.
export const CLIENT_KEY = import.meta.env.VITE_CLIENT_KEY || "";

if (!API_BASE) {
  console.error("[CONFIG] VITE_API_BASE_URL muhit o'zgaruvchisi sozlanmagan! client/.env faylini tekshiring.");
}
if (!CLIENT_KEY) {
  console.error("[CONFIG] VITE_CLIENT_KEY muhit o'zgaruvchisi sozlanmagan! client/.env faylini tekshiring.");
}

export function getSessionToken() {
  return localStorage.getItem("session_token") || "";
}

export async function apiFetch(path, { method = "GET", body, headers } = {}) {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE_URL sozlanmagan. client/.env faylini tekshiring.");
  }
  const token = getSessionToken();

  const isFormData = body instanceof FormData;

  // Sign exactly what goes on the wire: the URL parser's pathname + search
  // is the request target the server will see.
  let proof = null;
  if (token) {
    const url = new URL(`${API_BASE}${path}`);
    proof = await signProof({ method, pathWithQuery: url.pathname + url.search, token });
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(CLIENT_KEY ? { "X-Client-Key": CLIENT_KEY } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(proof ? { "X-Session-Proof": proof } : {}),
      ...(headers || {}),
    },
    body: isFormData ? body : (body ? JSON.stringify(body) : undefined),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok || !data || data.ok !== true) {
    const code = data?.error?.code;
    const msg = data?.error?.message || "Server bilan bog‘lanib bo‘lmadi";

    // session eskirgan bo‘lsa
    if (res.status === 401 || code === "UNAUTHORIZED") {
      localStorage.removeItem("session_token");
      // The key goes too -- unless this was a failed *login* (bad initData),
      // which says nothing about a session the browser may still hold.
      if (code !== "INVALID_INITDATA") await clearDeviceKey();
    }

    const err = new Error(msg);
    err.status = res.status;
    err.code = code;
    err.payload = data;
    throw err;
  }

  return data.data;
}
