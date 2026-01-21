const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function getSessionToken() {
  return localStorage.getItem("session_token") || "";
}

export async function apiFetch(path, { method = "GET", body, headers } = {}) {
  const token = getSessionToken();

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => null);

  if (!res.ok || !data || data.ok !== true) {
    const code = data?.error?.code;
    const msg = data?.error?.message || "Server bilan bog‘lanib bo‘lmadi";

    // session eskirgan bo‘lsa
    if (res.status === 401 || code === "UNAUTHORIZED") {
      localStorage.removeItem("session_token");
    }

    const err = new Error(msg);
    err.status = res.status;
    err.code = code;
    err.payload = data;
    throw err;
  }

  return data.data;
}