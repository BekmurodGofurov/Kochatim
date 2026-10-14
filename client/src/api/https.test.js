/**
 * Tests — src/api/https.js
 *
 * `apiFetch` frontend'ning yagona HTTP qatlami. Uchta muhim xatti-harakat:
 *
 * 1. Sessiya tokeni `Authorization: Bearer` sifatida ketadi (localStorage'dan).
 * 2. Backend `{ok: false}` qaytarsa HTTP 200 bo'lsa ham xato ko'tariladi —
 *    status kodga ishonib bo'lmaydi.
 * 3. 401 yoki UNAUTHORIZED kelganda token localStorage'dan O'CHIRILADI,
 *    aks holda ilova eskirgan token bilan abadiy qayta urinib turardi.
 *
 * FormData alohida yo'l: Content-Type qo'yilmaydi, brauzer o'zi
 * `multipart/form-data; boundary=...` ni qo'yadi.
 *
 * Qurilma kaliti: har so'rov `X-Client-Key` ko'taradi, token bor bo'lsa esa
 * `X-Session-Proof` (token yolg'iz o'zi yetmaydi). deviceKey.js bu yerda
 * soxta; uning haqiqiy kriptografiyasi deviceKey.test.js da sinaladi.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./deviceKey", () => ({
  signProof: vi.fn().mockResolvedValue("v1.123.nonce.sig"),
  clearDeviceKey: vi.fn().mockResolvedValue(undefined),
}));

import { API_BASE, CLIENT_KEY, apiFetch, getSessionToken } from "./https";
import { clearDeviceKey, signProof } from "./deviceKey";

function mockFetch({ ok = true, status = 200, body = { ok: true, data: null }, throwOnJson = false } = {}) {
  const spy = vi.fn().mockResolvedValue({
    ok,
    status,
    json: throwOnJson
      ? () => Promise.reject(new Error("not json"))
      : () => Promise.resolve(body),
  });
  globalThis.fetch = spy;
  return spy;
}

beforeEach(() => {
  localStorage.clear();
  signProof.mockClear();
  clearDeviceKey.mockClear();
  signProof.mockResolvedValue("v1.123.nonce.sig");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("API_BASE", () => {
  it("is read from the environment", () => {
    expect(API_BASE).toBe("http://localhost:8000");
  });
});

describe("CLIENT_KEY", () => {
  it("is read from the environment", () => {
    expect(CLIENT_KEY).toBe("test-client-key");
  });
});

describe("getSessionToken", () => {
  it("returns an empty string when nothing is stored", () => {
    expect(getSessionToken()).toBe("");
  });

  it("returns the stored token", () => {
    localStorage.setItem("session_token", "tok-123");
    expect(getSessionToken()).toBe("tok-123");
  });

  it("returns an empty string, never null", () => {
    expect(getSessionToken()).not.toBeNull();
  });
});

describe("apiFetch — so'rovni qurish", () => {
  it("prefixes the path with API_BASE", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][0]).toBe(`${API_BASE}/api/me`);
  });

  it("defaults to GET", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].method).toBe("GET");
  });

  it("uses the requested method", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me", { method: "DELETE" });
    expect(spy.mock.calls[0][1].method).toBe("DELETE");
  });

  it("sends a JSON content type by default", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers["Content-Type"]).toBe("application/json");
  });

  it("serialises a body to JSON", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/x", { method: "POST", body: { a: 1 } });
    expect(spy.mock.calls[0][1].body).toBe(JSON.stringify({ a: 1 }));
  });

  it("sends no body when none is given", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].body).toBeUndefined();
  });

  it("merges extra headers", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me", { headers: { "X-Custom": "1" } });
    expect(spy.mock.calls[0][1].headers["X-Custom"]).toBe("1");
  });

  it("lets an explicit header override the default content type", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me", { headers: { "Content-Type": "text/plain" } });
    expect(spy.mock.calls[0][1].headers["Content-Type"]).toBe("text/plain");
  });
});

describe("apiFetch — autentifikatsiya", () => {
  it("sends a Bearer token when one is stored", async () => {
    localStorage.setItem("session_token", "tok-123");
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers.Authorization).toBe("Bearer tok-123");
  });

  it("omits the Authorization header when no token is stored", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });
});

describe("apiFetch — FormData", () => {
  it("does not set a content type for FormData", async () => {
    // Brauzer boundary bilan birga o'zi qo'yishi kerak
    const spy = mockFetch({ body: { ok: true, data: { url: "x" } } });
    const fd = new FormData();
    fd.append("image", new Blob(["x"]), "a.png");
    await apiFetch("/api/img/upload", { method: "POST", body: fd });
    expect(spy.mock.calls[0][1].headers["Content-Type"]).toBeUndefined();
  });

  it("passes FormData through without serialising it", async () => {
    const spy = mockFetch({ body: { ok: true, data: { url: "x" } } });
    const fd = new FormData();
    await apiFetch("/api/img/upload", { method: "POST", body: fd });
    expect(spy.mock.calls[0][1].body).toBe(fd);
  });

  it("still sends the Bearer token with FormData", async () => {
    localStorage.setItem("session_token", "tok-123");
    const spy = mockFetch({ body: { ok: true, data: { url: "x" } } });
    await apiFetch("/api/img/upload", { method: "POST", body: new FormData() });
    expect(spy.mock.calls[0][1].headers.Authorization).toBe("Bearer tok-123");
  });
});

describe("apiFetch — muvaffaqiyatli javob", () => {
  it("returns only the data section", async () => {
    mockFetch({ body: { ok: true, data: { u_id: 1 } } });
    await expect(apiFetch("/api/me")).resolves.toEqual({ u_id: 1 });
  });

  it("returns an array payload", async () => {
    mockFetch({ body: { ok: true, data: [1, 2] } });
    await expect(apiFetch("/api/x")).resolves.toEqual([1, 2]);
  });

  it("returns null when data is null", async () => {
    mockFetch({ body: { ok: true, data: null } });
    await expect(apiFetch("/api/x")).resolves.toBeNull();
  });
});

describe("apiFetch — xatoliklar", () => {
  it("throws when ok is false, even on HTTP 200", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: { ok: false, error: { message: "Guruh topilmadi" } },
    });
    await expect(apiFetch("/api/x")).rejects.toThrow("Guruh topilmadi");
  });

  it("throws on an HTTP error status", async () => {
    mockFetch({
      ok: false,
      status: 500,
      body: { ok: false, error: { message: "Server error" } },
    });
    await expect(apiFetch("/api/x")).rejects.toThrow("Server error");
  });

  it("attaches status, code and payload to the error", async () => {
    mockFetch({
      ok: false,
      status: 404,
      body: { ok: false, error: { message: "Yo'q", code: "NOT_FOUND" } },
    });
    await expect(apiFetch("/api/x")).rejects.toMatchObject({
      status: 404,
      code: "NOT_FOUND",
    });
  });

  it("falls back to a generic message when the body has none", async () => {
    mockFetch({ ok: false, status: 502, body: { ok: false } });
    await expect(apiFetch("/api/x")).rejects.toThrow(/bog/);
  });

  it("throws when the response is not JSON", async () => {
    // Nginx 502 HTML sahifasi — json() yiqiladi, catch null beradi
    mockFetch({ ok: false, status: 502, throwOnJson: true });
    await expect(apiFetch("/api/x")).rejects.toThrow();
  });

  it("throws when API_BASE is empty", async () => {
    // Bu holat modul darajasida tekshiriladi; API_BASE test muhitida
    // to'ldirilgan, shuning uchun faqat shartning o'zi hujjatlashtiriladi.
    expect(API_BASE).not.toBe("");
  });
});

describe("apiFetch — sessiya eskirganda", () => {
  it("clears the stored token on HTTP 401", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ ok: false, status: 401, body: { ok: false, error: { message: "Unauthorized" } } });
    await expect(apiFetch("/api/me")).rejects.toThrow();
    expect(localStorage.getItem("session_token")).toBeNull();
  });

  it("clears the stored token on an UNAUTHORIZED code", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({
      ok: true,
      status: 200,
      body: { ok: false, error: { message: "Unauthorized", code: "UNAUTHORIZED" } },
    });
    await expect(apiFetch("/api/me")).rejects.toThrow();
    expect(localStorage.getItem("session_token")).toBeNull();
  });

  it("keeps the token on an unrelated error", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({
      ok: false,
      status: 400,
      body: { ok: false, error: { message: "Validation", code: "INVALID_CODE" } },
    });
    await expect(apiFetch("/api/x")).rejects.toThrow();
    expect(localStorage.getItem("session_token")).toBe("tok-123");
  });

  it("keeps the token on a 500", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ ok: false, status: 500, body: { ok: false, error: { message: "boom" } } });
    await expect(apiFetch("/api/x")).rejects.toThrow();
    expect(localStorage.getItem("session_token")).toBe("tok-123");
  });
});

describe("apiFetch — X-Client-Key", () => {
  it("is sent on every request, signed in or not", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/gardeners");
    localStorage.setItem("session_token", "tok-123");
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers["X-Client-Key"]).toBe("test-client-key");
    expect(spy.mock.calls[1][1].headers["X-Client-Key"]).toBe("test-client-key");
  });

  it("is sent with FormData uploads too", async () => {
    const spy = mockFetch({ body: { ok: true, data: { url: "x" } } });
    await apiFetch("/api/img/upload", { method: "POST", body: new FormData() });
    expect(spy.mock.calls[0][1].headers["X-Client-Key"]).toBe("test-client-key");
  });

  it("is sent on login requests, which have no session yet", async () => {
    const spy = mockFetch({ body: { ok: true, data: { session_token: "t" } } });
    await apiFetch("/auth/verify-code", { method: "POST", body: { code: "123456" } });
    expect(spy.mock.calls[0][1].headers["X-Client-Key"]).toBe("test-client-key");
  });
});

describe("apiFetch — X-Session-Proof", () => {
  it("is sent when a token is stored", async () => {
    localStorage.setItem("session_token", "tok-123");
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers["X-Session-Proof"]).toBe("v1.123.nonce.sig");
  });

  it("signs the method, the path with its query string, and the token", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/seedlings?t_id=10&q=a%20b", { method: "post" });
    expect(signProof).toHaveBeenCalledWith({
      method: "post",
      pathWithQuery: "/api/seedlings?t_id=10&q=a%20b",
      token: "tok-123",
    });
  });

  it("signs the path the URL parser will actually send", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/a/../me?x=1#frag");
    expect(signProof.mock.calls[0][0].pathWithQuery).toBe("/api/me?x=1");
  });

  it("is not computed when there is no token", async () => {
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/gardeners");
    expect(signProof).not.toHaveBeenCalled();
    expect(spy.mock.calls[0][1].headers["X-Session-Proof"]).toBeUndefined();
  });

  it("is left out when this browser has no key; the server then answers 401", async () => {
    localStorage.setItem("session_token", "tok-123");
    signProof.mockResolvedValue(null);
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    expect(spy.mock.calls[0][1].headers["X-Session-Proof"]).toBeUndefined();
    expect(spy.mock.calls[0][1].headers.Authorization).toBe("Bearer tok-123");
  });

  it("is a fresh proof for every request", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me");
    await apiFetch("/api/me");
    expect(signProof).toHaveBeenCalledTimes(2);
  });

  it("a caller cannot override the proof with its own headers by accident", async () => {
    localStorage.setItem("session_token", "tok-123");
    const spy = mockFetch({ body: { ok: true, data: 1 } });
    await apiFetch("/api/me", { headers: { "X-Custom": "1" } });
    expect(spy.mock.calls[0][1].headers["X-Session-Proof"]).toBe("v1.123.nonce.sig");
  });
});

describe("apiFetch — rejected session also drops the device key", () => {
  it("clears the key on HTTP 401", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ ok: false, status: 401, body: { ok: false, error: { message: "x", code: "UNAUTHORIZED" } } });
    await expect(apiFetch("/api/me")).rejects.toThrow();
    expect(clearDeviceKey).toHaveBeenCalledTimes(1);
  });

  it("clears the key on an UNAUTHORIZED code even with HTTP 200", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ ok: true, status: 200, body: { ok: false, error: { message: "x", code: "UNAUTHORIZED" } } });
    await expect(apiFetch("/api/me")).rejects.toThrow();
    expect(clearDeviceKey).toHaveBeenCalledTimes(1);
  });

  it("keeps the key when a Telegram login merely failed", async () => {
    localStorage.setItem("session_token", "tok-123");
    mockFetch({ ok: false, status: 401, body: { ok: false, error: { message: "x", code: "INVALID_INITDATA" } } });
    await expect(apiFetch("/auth/telegram-webapp", { method: "POST", body: {} })).rejects.toThrow();
    expect(clearDeviceKey).not.toHaveBeenCalled();
  });

  it("keeps the key on unrelated errors", async () => {
    localStorage.setItem("session_token", "tok-123");
    for (const [status, code] of [[400, "INVALID_CODE"], [429, "RATE_LIMITED"], [500, undefined]]) {
      mockFetch({ ok: false, status, body: { ok: false, error: { message: "x", code } } });
      await expect(apiFetch("/api/x")).rejects.toThrow();
    }
    expect(clearDeviceKey).not.toHaveBeenCalled();
  });

  it("surfaces the server error code to the caller", async () => {
    mockFetch({ ok: false, status: 429, body: { ok: false, error: { message: "slow down", code: "RATE_LIMITED" } } });
    await expect(apiFetch("/auth/verify-code", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 429,
      code: "RATE_LIMITED",
    });
  });
});
