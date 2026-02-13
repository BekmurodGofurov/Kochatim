import { useEffect, useState } from "react";
import { api } from "../api/endpoints";

export default function TelegramHandler({ children }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        if (!tg) return;

        // Mini App muhitidaligini tekshirish
        const initData = tg.initData;
        const token = localStorage.getItem("session_token");

        if (initData && !token) {
            setLoading(true);
            api
                .telegramLogin(initData)
                .then((res) => {
                    localStorage.setItem("session_token", res.session_token);
                    localStorage.setItem("u_id", res.u_id);
                    // Sahifani yangilash shart emas, lekin hamma narsa to'g'ri ishlashi uchun:
                    window.location.reload();
                })
                .catch((err) => {
                    console.error("Telegram login failed", err);
                    setError("Telegram orqali kirishda xatolik yuz berdi.");
                })
                .finally(() => {
                    setLoading(false);
                });
        }

        // Expand if needed
        tg.expand();
    }, []);

    if (loading) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
                <p>Telegram orqali kirilmoqda...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", color: "red" }}>
                <p>{error}</p>
            </div>
        );
    }

    return children;
}
