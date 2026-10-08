/**
 * Tests — src/utils/imageUtils.js
 *
 * `toWebImgUrl` ikki xil qiymatni qabul qiladi: to'liq URL (ImgBB) va
 * Telegram file_id. file_id backend proksisi orqali o'tadi, shuning
 * uchun u URL ga kodlanishi SHART — aks holda "/" yoki "?" belgisi
 * bo'lgan id yo'lni buzadi.
 */
import { describe, expect, it } from "vitest";

import { pickImagesFromType, toWebImgUrl } from "./imageUtils";
import { API_BASE } from "../api/https";

describe("toWebImgUrl", () => {
  it("passes an https URL through untouched", () => {
    const url = "https://i.ibb.co/abc/photo.png";
    expect(toWebImgUrl(url)).toBe(url);
  });

  it("passes an http URL through untouched", () => {
    const url = "http://i.ibb.co/abc/photo.png";
    expect(toWebImgUrl(url)).toBe(url);
  });

  it("routes a Telegram file_id through the backend proxy", () => {
    expect(toWebImgUrl("AgACAgIAAxk")).toBe(`${API_BASE}/api/img/AgACAgIAAxk`);
  });

  it("url-encodes a file_id containing slashes", () => {
    expect(toWebImgUrl("abc/def")).toBe(`${API_BASE}/api/img/abc%2Fdef`);
  });

  it("url-encodes a file_id containing a question mark", () => {
    expect(toWebImgUrl("abc?x=1")).toBe(`${API_BASE}/api/img/abc%3Fx%3D1`);
  });

  it("returns an empty string for an empty input", () => {
    expect(toWebImgUrl("")).toBe("");
  });

  it("returns an empty string for null", () => {
    expect(toWebImgUrl(null)).toBe("");
  });

  it("returns an empty string for undefined", () => {
    expect(toWebImgUrl(undefined)).toBe("");
  });

  it("returns an empty string for 0", () => {
    // Falsy qiymat — <img src=""> bo'lib qoladi, "/api/img/0" emas
    expect(toWebImgUrl(0)).toBe("");
  });

  it("stringifies a numeric file_id", () => {
    expect(toWebImgUrl(12345)).toBe(`${API_BASE}/api/img/12345`);
  });

  it("treats an uppercase scheme as a file_id", () => {
    // Tekshiruv startsWith("https://") — hujjatlashtirilgan cheklov
    expect(toWebImgUrl("HTTPS://e.com/a.png")).toContain("/api/img/");
  });

  it("never returns a bare file_id", () => {
    const out = toWebImgUrl("AgACAgIAAxk");
    expect(out.startsWith("/")).toBe(API_BASE === "");
    expect(out).toContain("/api/img/");
  });
});

describe("pickImagesFromType", () => {
  it("reads i_url, the field the backend actually sends", () => {
    expect(pickImagesFromType({ i_url: "https://x/a.png" })).toEqual([
      "https://x/a.png",
    ]);
  });

  it("returns an array, not a bare value", () => {
    expect(Array.isArray(pickImagesFromType({ i_url: "x" }))).toBe(true);
  });

  it("returns an empty array when no image field is present", () => {
    expect(pickImagesFromType({ t_name: "Olma" })).toEqual([]);
  });

  it("returns an empty array for null", () => {
    expect(pickImagesFromType(null)).toEqual([]);
  });

  it("returns an empty array for undefined", () => {
    expect(pickImagesFromType(undefined)).toEqual([]);
  });

  it("returns an empty array when i_url is null", () => {
    expect(pickImagesFromType({ i_url: null })).toEqual([]);
  });

  it("returns an empty array when i_url is an empty string", () => {
    expect(pickImagesFromType({ i_url: "" })).toEqual([]);
  });

  it.each([
    ["image", { image: "a" }],
    ["image_url", { image_url: "a" }],
    ["t_image", { t_image: "a" }],
    ["img", { img: "a" }],
    ["photo", { photo: "a" }],
    ["photo_url", { photo_url: "a" }],
  ])("falls back to the %s field", (_name, type) => {
    expect(pickImagesFromType(type)).toEqual(["a"]);
  });

  it("prefers i_url over the fallback fields", () => {
    expect(
      pickImagesFromType({ i_url: "first", image: "second", photo: "third" })
    ).toEqual(["first"]);
  });

  it("returns at most one image", () => {
    expect(
      pickImagesFromType({ i_url: "a", image: "b", photo: "c" })
    ).toHaveLength(1);
  });
});
