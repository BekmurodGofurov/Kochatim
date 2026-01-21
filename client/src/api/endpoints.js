import { apiFetch } from "./http";

export const api = {
  me: () => apiFetch("/api/me"),
  dashboard: () => apiFetch("/api/me/dashboard"),

  // inventory uchun keyin ishlatamiz:
  categoriesByUser: (u_id) => apiFetch(`/api/categories/by-user?u_id=${u_id}`),
  typesByUser: (u_id, c_id) => apiFetch(`/api/types/by-user?u_id=${u_id}&c_id=${c_id}`),
  seedlingCount: (u_id, t_id) => apiFetch(`/api/seedlings/count?u_id=${u_id}&t_id=${t_id}`),

  // sales uchun keyin:
  // salesList: (u_id) => apiFetch(`/api/sales?u_id=${u_id}`),
};