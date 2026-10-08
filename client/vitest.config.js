import { defineConfig } from "vitest/config";

// Alohida config: vite.config.js dev-server sozlamalarini saqlaydi,
// bu fayl esa faqat testlar uchun. @vitejs/plugin-react kerak emas —
// hozirgi testlar toza funksiyalarni sinaydi, JSX ni emas.
export default defineConfig({
  test: {
    environment: "jsdom", // localStorage va fetch uchun
    include: ["src/**/*.test.{js,jsx}"],
    globals: true,
    env: {
      // https.js modul darajasida import.meta.env.VITE_API_BASE_URL ni
      // o'qiydi; bo'sh bo'lsa apiFetch darhol xato beradi.
      VITE_API_BASE_URL: "http://localhost:8000",
    },
  },
});
