/**
 * Device-bound session key.
 *
 * At login the browser makes an ECDSA P-256 key pair with extractable=false:
 * the private half can sign but can never be read back out -- not by page
 * script, and not by copying localStorage. Only the public half goes to the
 * server, which stores it on the session. Every later request carries a
 * signature (X-Session-Proof) made with the private half, so a session token
 * copied into another browser is worthless: that browser has no key.
 *
 * The private key lives in IndexedDB as a CryptoKey object (structured clone
 * keeps non-extractable keys non-extractable).
 *
 * Proof format, checked by backend/utils/device_proof.py:
 *   v1.<ts_ms>.<nonce>.<signature>
 * signature = ECDSA/SHA-256 (raw 64-byte r||s, which is what WebCrypto emits)
 * over  "<ts>.<nonce>.<METHOD>.<path?query>.<sha256 hex of the token>".
 */

const DB_NAME = "kochatim-device";
const STORE = "keys";
const KEY_ID = "session";
const ALGORITHM = { name: "ECDSA", namedCurve: "P-256" };
const SIGN_ALGORITHM = { name: "ECDSA", hash: "SHA-256" };

export class DeviceKeyUnsupportedError extends Error {
  constructor() {
    super("Bu brauzer xavfsiz kirishni qo'llab-quvvatlamaydi");
    this.name = "DeviceKeyUnsupportedError";
    this.code = "DEVICE_KEY_UNSUPPORTED";
  }
}

function isSupported() {
  return (
    typeof crypto !== "undefined" &&
    !!crypto.subtle &&
    typeof indexedDB !== "undefined"
  );
}

// ---- encoding helpers ------------------------------------------------------

function base64url(bytes) {
  let bin = "";
  for (const b of new Uint8Array(bytes)) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function toHex(bytes) {
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Hex(text) {
  return toHex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)));
}

// ---- IndexedDB -------------------------------------------------------------

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(mode, fn) {
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const request = fn(tx.objectStore(STORE));
      tx.oncomplete = () => resolve(request?.result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

async function loadPrivateKey() {
  const record = await withStore("readonly", (s) => s.get(KEY_ID));
  return record?.privateKey ?? null;
}

// ---- public API ------------------------------------------------------------

/**
 * Make a new key pair for a login that is about to happen. Nothing is stored
 * yet: if the login fails, the browser's existing session keeps its key. Send
 * `publicJwk` to the server, and call `save()` once the login succeeded.
 */
export async function generateDeviceKey() {
  if (!isSupported()) throw new DeviceKeyUnsupportedError();

  const pair = await crypto.subtle.generateKey(ALGORITHM, false, ["sign", "verify"]);
  const jwk = await crypto.subtle.exportKey("jwk", pair.publicKey);

  return {
    // Only the four members the server looks at; WebCrypto adds ext/key_ops.
    publicJwk: { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y },
    save: () =>
      withStore("readwrite", (s) => s.put({ privateKey: pair.privateKey }, KEY_ID)),
  };
}

/** Sign one request. Returns null when this browser holds no key. */
export async function signProof({ method, pathWithQuery, token }) {
  if (!isSupported()) return null;

  let privateKey;
  try {
    privateKey = await loadPrivateKey();
  } catch {
    return null; // storage blocked or wiped: the request goes out unsigned and gets a 401
  }
  if (!privateKey) return null;

  const ts = String(Date.now());
  const nonce = base64url(crypto.getRandomValues(new Uint8Array(16)));
  const message = `${ts}.${nonce}.${method.toUpperCase()}.${pathWithQuery}.${await sha256Hex(token)}`;
  const signature = await crypto.subtle.sign(
    SIGN_ALGORITHM,
    privateKey,
    new TextEncoder().encode(message)
  );
  return `v1.${ts}.${nonce}.${base64url(signature)}`;
}

/** Forget the key (logout, or the server stopped accepting the session). */
export async function clearDeviceKey() {
  if (typeof indexedDB === "undefined") return;
  try {
    await withStore("readwrite", (s) => s.delete(KEY_ID));
  } catch {
    // nothing stored, or storage unavailable: either way there is nothing to keep
  }
}

export async function hasDeviceKey() {
  if (!isSupported()) return false;
  try {
    return (await loadPrivateKey()) !== null;
  } catch {
    return false;
  }
}
