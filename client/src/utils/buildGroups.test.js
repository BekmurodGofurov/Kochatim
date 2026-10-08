/**
 * Tests — src/utils/buildGroups.js
 *
 * `buildGroupsFromDashboard` backend dashboard javobini (categories /
 * types / seedlings — uchta alohida ro'yxat) UI kutgan ichma-ich
 * tuzilmaga aylantiradi: guruh -> navlar -> miqdorlar.
 *
 * Markaziy xatti-harakat: ko'chat yozuvi YO'Q nav ham ro'yxatda
 * qolishi kerak, miqdori nol bilan. Aks holda yangi qo'shilgan nav
 * (hali ko'chati kiritilmagan) dashboardda ko'rinmay ketardi.
 */
import { describe, expect, it } from "vitest";

import { buildGroupsFromDashboard } from "./buildGroups";

const dashboard = {
  categories: [
    { c_id: 1, c_name: "Mevali daraxtlar" },
    { c_id: 2, c_name: "Manzarali" },
  ],
  types: [
    { t_id: 10, c_id: 1, t_name: "Olma", deff: "Yaxshi nav", i_url: "https://x/olma.png" },
    { t_id: 11, c_id: 1, t_name: "Nok" },
    { t_id: 20, c_id: 2, t_name: "Tol" },
  ],
  seedlings: [
    { t_id: 10, quality_1: 100, quality_2: 50, quality_3: 25, updated_at: "2026-06-13T12:00:00" },
    { t_id: 20, quality_1: 7, quality_2: 0, quality_3: 0 },
  ],
};

describe("buildGroupsFromDashboard — bo'sh kirishlar", () => {
  it("returns an empty array for null", () => {
    expect(buildGroupsFromDashboard(null)).toEqual([]);
  });

  it("returns an empty array for undefined", () => {
    expect(buildGroupsFromDashboard(undefined)).toEqual([]);
  });

  it("returns an empty array for an empty object", () => {
    expect(buildGroupsFromDashboard({})).toEqual([]);
  });

  it("tolerates missing types and seedlings", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "Faqat guruh" }],
    });
    expect(out).toHaveLength(1);
    expect(out[0].sorts).toEqual([]);
    expect(out[0].totalValue).toBe(0);
  });

  it("returns an empty array when categories is empty", () => {
    expect(buildGroupsFromDashboard({ categories: [], types: [{ t_id: 1 }] })).toEqual([]);
  });
});

describe("buildGroupsFromDashboard — guruh tuzilmasi", () => {
  it("returns one group per category", () => {
    expect(buildGroupsFromDashboard(dashboard)).toHaveLength(2);
  });

  it("maps c_id to id and c_name to groupName", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(first.id).toBe(1);
    expect(first.groupName).toBe("Mevali daraxtlar");
  });

  it("exposes the keys the UI reads", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(Object.keys(first).sort()).toEqual(
      ["groupImages", "groupName", "id", "sorts", "totalValue"].sort()
    );
  });

  it("coerces a string c_id to a number", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: "7", c_name: "X" }],
      types: [{ t_id: 1, c_id: "7", t_name: "A" }],
    });
    expect(out[0].id).toBe(7);
    expect(out[0].sorts).toHaveLength(1);
  });

  it("defaults a missing c_name to an empty string", () => {
    const out = buildGroupsFromDashboard({ categories: [{ c_id: 1 }] });
    expect(out[0].groupName).toBe("");
  });

  it("preserves category order", () => {
    const names = buildGroupsFromDashboard(dashboard).map((g) => g.groupName);
    expect(names).toEqual(["Mevali daraxtlar", "Manzarali"]);
  });
});

describe("buildGroupsFromDashboard — navlarni guruhlash", () => {
  it("puts each type in its own category", () => {
    const [mevali, manzarali] = buildGroupsFromDashboard(dashboard);
    expect(mevali.sorts.map((s) => s.name)).toEqual(["Olma", "Nok"]);
    expect(manzarali.sorts.map((s) => s.name)).toEqual(["Tol"]);
  });

  it("matches types to categories across string and number ids", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: "1", t_name: "Olma" }],
    });
    expect(out[0].sorts).toHaveLength(1);
  });

  it("drops a type whose category is not in the list", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 99, t_name: "Orphan" }],
    });
    expect(out[0].sorts).toEqual([]);
  });

  it("exposes both id and t_id on a sort", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(first.sorts[0].id).toBe(10);
    expect(first.sorts[0].t_id).toBe(10);
  });
});

describe("buildGroupsFromDashboard — miqdorlar", () => {
  it("maps quality_1..3 onto nav1..3", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    const olma = first.sorts.find((s) => s.t_id === 10);
    expect([olma.nav1, olma.nav2, olma.nav3]).toEqual([100, 50, 25]);
  });

  it("keeps a type with no seedling row, at zero", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    const nok = first.sorts.find((s) => s.t_id === 11);
    expect([nok.nav1, nok.nav2, nok.nav3]).toEqual([0, 0, 0]);
  });

  it("treats null quantities as zero", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A" }],
      seedlings: [{ t_id: 10, quality_1: null, quality_2: null, quality_3: null }],
    });
    expect(out[0].sorts[0].nav1).toBe(0);
  });

  it("coerces string quantities to numbers", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A" }],
      seedlings: [{ t_id: 10, quality_1: "5", quality_2: "3", quality_3: "1" }],
    });
    expect(out[0].sorts[0].nav1).toBe(5);
    expect(out[0].totalValue).toBe(9);
  });

  it("matches seedlings to types across string and number ids", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A" }],
      seedlings: [{ t_id: "10", quality_1: 4 }],
    });
    expect(out[0].sorts[0].nav1).toBe(4);
  });
});

describe("buildGroupsFromDashboard — totalValue", () => {
  it("sums all three qualities across all sorts", () => {
    const [mevali] = buildGroupsFromDashboard(dashboard);
    expect(mevali.totalValue).toBe(175); // 100+50+25 + 0+0+0
  });

  it("counts only the sorts in its own group", () => {
    const [, manzarali] = buildGroupsFromDashboard(dashboard);
    expect(manzarali.totalValue).toBe(7);
  });

  it("is zero for a group with no sorts", () => {
    const out = buildGroupsFromDashboard({ categories: [{ c_id: 9, c_name: "Bo'sh" }] });
    expect(out[0].totalValue).toBe(0);
  });

  it("is a number, never NaN", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A" }],
      seedlings: [{ t_id: 10, quality_1: "oops" }],
    });
    expect(Number.isNaN(out[0].totalValue)).toBe(false);
  });
});

describe("buildGroupsFromDashboard — tavsif va rasmlar", () => {
  it("reads the description from deff", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(first.sorts[0].description).toBe("Yaxshi nav");
  });

  it("defaults a missing description to an empty string", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    const nok = first.sorts.find((s) => s.t_id === 11);
    expect(nok.description).toBe("");
  });

  it.each(["description", "t_desc", "t_deff"])(
    "falls back to the %s field for the description",
    (field) => {
      const out = buildGroupsFromDashboard({
        categories: [{ c_id: 1, c_name: "X" }],
        types: [{ t_id: 10, c_id: 1, t_name: "A", [field]: "matn" }],
      });
      expect(out[0].sorts[0].description).toBe("matn");
    }
  );

  it("collects group images from its sorts", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(first.groupImages).toEqual(["https://x/olma.png"]);
  });

  it("gives an empty groupImages when no sort has an image", () => {
    const [, manzarali] = buildGroupsFromDashboard(dashboard);
    expect(manzarali.groupImages).toEqual([]);
  });

  it("filters falsy entries out of groupImages", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [
        { t_id: 10, c_id: 1, t_name: "A", i_url: "https://x/a.png" },
        { t_id: 11, c_id: 1, t_name: "B", i_url: null },
      ],
    });
    expect(out[0].groupImages).toEqual(["https://x/a.png"]);
  });
});

describe("buildGroupsFromDashboard — vaqt belgilari", () => {
  it("prefers the seedling updated_at", () => {
    const [first] = buildGroupsFromDashboard(dashboard);
    expect(first.sorts[0].updated_at).toBe("2026-06-13T12:00:00");
  });

  it("falls back to the type updated_at", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A", updated_at: "2026-01-01" }],
    });
    expect(out[0].sorts[0].updated_at).toBe("2026-01-01");
  });

  it("is null when neither has a timestamp", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A" }],
    });
    expect(out[0].sorts[0].updated_at).toBeNull();
  });

  it("falls back to the type added_at", () => {
    const out = buildGroupsFromDashboard({
      categories: [{ c_id: 1, c_name: "X" }],
      types: [{ t_id: 10, c_id: 1, t_name: "A", added_at: "2025-12-01" }],
    });
    expect(out[0].sorts[0].added_at).toBe("2025-12-01");
  });
});
