import { pickImagesFromType } from "./imageUtils";

export function buildGroupsFromDashboard(dashboard) {
  if (!dashboard) return [];

  const cats = dashboard.categories || [];
  const types = dashboard.types || [];
  const seedlings = dashboard.seedlings || [];

  const seedMap = new Map();
  for (const s of seedlings) {
    seedMap.set(Number(s.t_id), {
      q1: Number(s.quality_1 || 0),
      q2: Number(s.quality_2 || 0),
      q3: Number(s.quality_3 || 0),
      updated_at: s.updated_at || null,
      added_at: s.added_at || null,
    });
  }

  return cats.map((c) => {
    const c_id = Number(c.c_id);
    const c_name = String(c.c_name || "");
    const myTypes = types.filter((t) => Number(t.c_id) === c_id);

    const sorts = myTypes.map((t) => {
      const t_id = Number(t.t_id);
      const q = seedMap.get(t_id) || { q1: 0, q2: 0, q3: 0 };
      const images = pickImagesFromType(t);
      return {
        id: t_id,
        t_id,
        name: String(t.t_name || ""),
        nav1: q.q1,
        nav2: q.q2,
        nav3: q.q3,
        images,
        description: t?.deff || t?.description || t?.t_desc || t?.t_deff || "",
        updated_at: q.updated_at || t?.updated_at || null,
        added_at: q.added_at || t?.added_at || null,
      };
    });

    const totalValue = sorts.reduce((sum, x) => sum + (x.nav1 || 0) + (x.nav2 || 0) + (x.nav3 || 0), 0);
    const groupImages = sorts.flatMap((s) => (Array.isArray(s.images) ? s.images : [])).filter(Boolean);

    return {
      id: c_id,
      groupName: c_name,
      totalValue,
      sorts,
      groupImages,
    };
  });
}
