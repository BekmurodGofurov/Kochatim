/**
 * Tests — src/api/deviceKey.js
 *
 * The device key is what makes a stolen session token useless: the token
 * only works together with a signature from a private key that cannot be
 * exported. These tests use real WebCrypto and an in-memory IndexedDB
 * (fake-indexeddb), so they exercise the actual signing and storage code.
 */
import "fake-indexeddb/auto";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DeviceKeyUnsupportedError,
  clearDeviceKey,
  generateDeviceKey,
  hasDeviceKey,
  signProof,
} from "./deviceKey";

// jsdom does not implement SubtleCrypto; Node's does.
beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
});

const TOKEN = "session-token-abc";

async function sha256Hex(text) {
  const digest = await webcrypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function fromBase64url(s) {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4);
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

async function importPublic(jwk) {
  return webcrypto.subtle.importKey(
    "jwk", { ...jwk, ext: true }, { name: "ECDSA", namedCurve: "P-256" }, true, ["verify"]
  );
}

async function verifies(publicJwk, proof, { method, target, token }) {
  const [v, ts, nonce, sig] = proof.split(".");
  if (v !== "v1") return false;
  const message = `${ts}.${nonce}.${method.toUpperCase()}.${target}.${await sha256Hex(token)}`;
  return webcrypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" },
    await importPublic(publicJwk),
    fromBase64url(sig),
    new TextEncoder().encode(message)
  );
}

/** Read the stored record straight from IndexedDB, bypassing the module. */
function readStoredRecord() {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open("kochatim-device", 1);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const req = open.result.transaction("keys").objectStore("keys").get("session");
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    };
  });
}

beforeEach(async () => {
  await clearDeviceKey();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("generateDeviceKey", () => {
  it("returns a P-256 public JWK with exactly the members the server reads", async () => {
    const { publicJwk } = await generateDeviceKey();
    expect(Object.keys(publicJwk).sort()).toEqual(["crv", "kty", "x", "y"]);
    expect(publicJwk.kty).toBe("EC");
    expect(publicJwk.crv).toBe("P-256");
    expect(fromBase64url(publicJwk.x)).toHaveLength(32);
    expect(fromBase64url(publicJwk.y)).toHaveLength(32);
  });

  it("never exposes private key material", async () => {
    const { publicJwk } = await generateDeviceKey();
    expect(JSON.stringify(publicJwk)).not.toMatch(/"d"/);
  });

  it("stores nothing until save() is called", async () => {
    await generateDeviceKey();
    expect(await hasDeviceKey()).toBe(false);
  });

  it("a key generated for a login that then fails does not disturb the stored one", async () => {
    const first = await generateDeviceKey();
    await first.save();
    await generateDeviceKey(); // a second login attempt that is never saved
    const proof = await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN });
    expect(await verifies(first.publicJwk, proof, { method: "GET", target: "/api/me", token: TOKEN })).toBe(true);
  });

  it("makes a different key every time", async () => {
    const a = await generateDeviceKey();
    const b = await generateDeviceKey();
    expect(a.publicJwk.x).not.toBe(b.publicJwk.x);
  });

  it("save() stores the private key as non-extractable", async () => {
    const dk = await generateDeviceKey();
    await dk.save();
    const { privateKey } = await readStoredRecord();
    expect(privateKey.extractable).toBe(false);
    expect(privateKey.usages).toEqual(["sign"]);
    await expect(webcrypto.subtle.exportKey("jwk", privateKey)).rejects.toThrow();
    await expect(webcrypto.subtle.exportKey("pkcs8", privateKey)).rejects.toThrow();
  });

  it("stores the private key and nothing else", async () => {
    const dk = await generateDeviceKey();
    await dk.save();
    expect(Object.keys(await readStoredRecord())).toEqual(["privateKey"]);
  });

  it("saving a new key replaces the old one", async () => {
    const first = await generateDeviceKey();
    await first.save();
    const second = await generateDeviceKey();
    await second.save();
    const proof = await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN });
    const args = { method: "GET", target: "/api/me", token: TOKEN };
    expect(await verifies(second.publicJwk, proof, args)).toBe(true);
    expect(await verifies(first.publicJwk, proof, args)).toBe(false);
  });
});

describe("signProof", () => {
  async function loggedIn() {
    const dk = await generateDeviceKey();
    await dk.save();
    return dk.publicJwk;
  }

  it("produces v1.<ts>.<nonce>.<signature>", async () => {
    await loggedIn();
    const proof = await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN });
    const parts = proof.split(".");
    expect(parts).toHaveLength(4);
    expect(parts[0]).toBe("v1");
    expect(parts[1]).toMatch(/^\d{13}$/);
    expect(parts[2]).toMatch(/^[A-Za-z0-9_-]{16,64}$/);
    expect(fromBase64url(parts[3])).toHaveLength(64); // raw r||s, not DER
  });

  it("the signature verifies against the public key it was registered with", async () => {
    const pub = await loggedIn();
    const proof = await signProof({ method: "POST", pathWithQuery: "/api/x?a=1", token: TOKEN });
    expect(await verifies(pub, proof, { method: "POST", target: "/api/x?a=1", token: TOKEN })).toBe(true);
  });

  it("covers the method, the path with its query, and the token", async () => {
    const pub = await loggedIn();
    const proof = await signProof({ method: "POST", pathWithQuery: "/api/x?a=1", token: TOKEN });
    const ok = { method: "POST", target: "/api/x?a=1", token: TOKEN };
    expect(await verifies(pub, proof, { ...ok, method: "DELETE" })).toBe(false);
    expect(await verifies(pub, proof, { ...ok, target: "/api/x?a=2" })).toBe(false);
    expect(await verifies(pub, proof, { ...ok, target: "/api/y?a=1" })).toBe(false);
    expect(await verifies(pub, proof, { ...ok, token: TOKEN + "x" })).toBe(false);
  });

  it("upper-cases the method, matching what the server compares", async () => {
    const pub = await loggedIn();
    const proof = await signProof({ method: "get", pathWithQuery: "/api/me", token: TOKEN });
    expect(await verifies(pub, proof, { method: "GET", target: "/api/me", token: TOKEN })).toBe(true);
  });

  it("uses a fresh nonce every time", async () => {
    await loggedIn();
    const nonces = new Set();
    for (let i = 0; i < 25; i++) {
      const p = await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN });
      nonces.add(p.split(".")[2]);
    }
    expect(nonces.size).toBe(25);
  });

  it("timestamps with the current time in milliseconds", async () => {
    await loggedIn();
    const before = Date.now();
    const proof = await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN });
    const ts = Number(proof.split(".")[1]);
    expect(ts).toBeGreaterThanOrEqual(before);
    expect(ts).toBeLessThanOrEqual(Date.now());
  });

  it("signs percent-encoded targets as given", async () => {
    const pub = await loggedIn();
    const target = "/api/x?q=%D1%88%20y";
    const proof = await signProof({ method: "GET", pathWithQuery: target, token: TOKEN });
    expect(await verifies(pub, proof, { method: "GET", target, token: TOKEN })).toBe(true);
  });

  it("returns null when this browser holds no key (the request goes out unsigned)", async () => {
    expect(await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN })).toBeNull();
  });

  it("returns null instead of throwing when storage is unavailable", async () => {
    await loggedIn();
    vi.spyOn(indexedDB, "open").mockImplementation(() => {
      throw new Error("storage blocked");
    });
    expect(await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN })).toBeNull();
  });
});

describe("clearDeviceKey / hasDeviceKey", () => {
  it("removes the stored key so nothing can be signed afterwards", async () => {
    const dk = await generateDeviceKey();
    await dk.save();
    expect(await hasDeviceKey()).toBe(true);
    await clearDeviceKey();
    expect(await hasDeviceKey()).toBe(false);
    expect(await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN })).toBeNull();
  });

  it("is harmless when there is nothing to clear", async () => {
    await expect(clearDeviceKey()).resolves.toBeUndefined();
    await expect(clearDeviceKey()).resolves.toBeUndefined();
  });

  it("does not throw when storage is unavailable", async () => {
    vi.spyOn(indexedDB, "open").mockImplementation(() => {
      throw new Error("storage blocked");
    });
    await expect(clearDeviceKey()).resolves.toBeUndefined();
    await expect(hasDeviceKey()).resolves.toBe(false);
  });
});

describe("browsers without WebCrypto or IndexedDB", () => {
  it("refuses to start a login with a clear error instead of silently weakening it", async () => {
    vi.stubGlobal("crypto", {});
    await expect(generateDeviceKey()).rejects.toBeInstanceOf(DeviceKeyUnsupportedError);
    await expect(generateDeviceKey()).rejects.toMatchObject({ code: "DEVICE_KEY_UNSUPPORTED" });
    vi.unstubAllGlobals();
  });

  it("refuses when IndexedDB is missing", async () => {
    vi.stubGlobal("indexedDB", undefined);
    await expect(generateDeviceKey()).rejects.toBeInstanceOf(DeviceKeyUnsupportedError);
    vi.unstubAllGlobals();
  });

  it("cannot sign without support, and says so with null", async () => {
    vi.stubGlobal("crypto", {});
    expect(await signProof({ method: "GET", pathWithQuery: "/api/me", token: TOKEN })).toBeNull();
    vi.unstubAllGlobals();
  });
});
