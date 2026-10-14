import { API_BASE, CLIENT_KEY } from "../api/https";

// <img src> cannot send headers, so the proxy route takes the client key as
// ?k= (it is public anyway -- see CLIENT_KEY in api/https.js).
export function apiImgUrl(fileId) {
  if (!fileId) return "";
  const key = CLIENT_KEY ? `?k=${encodeURIComponent(CLIENT_KEY)}` : "";
  return `${API_BASE}/api/img/${encodeURIComponent(String(fileId))}${key}`;
}

export function toWebImgUrl(raw) {
  if (!raw) return "";
  if (typeof raw === "string" && (raw.startsWith("http://") || raw.startsWith("https://"))) {
    return raw;
  }
  return apiImgUrl(raw);
}

export function pickImagesFromType(t) {
  const one =
    t?.i_url ||
    t?.image ||
    t?.image_url ||
    t?.t_image ||
    t?.img ||
    t?.photo ||
    t?.photo_url;
  return one ? [one] : [];
}
