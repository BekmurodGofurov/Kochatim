import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://api.kochatim.uz";

/**
 * Bu komponent Telegram Mini App ichida ochilganini aniqlaydi 
 * va avtomatik loginni amalga oshiradi.
 */
export default function TelegramHandler() {
    const navigate = useNavigate();

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        if (!tg) return;

        tg.ready();
        tg.expand();

        // 500ms kutamiz (ba'zi platformalarda SDK kechroq yuklanadi)
        const timer = setTimeout(() => {
            const rawData = tg.initData;

            console.log("Main Site - TMA Debug:", {
                href: window.location.href,
                hash: window.location.hash,
                initData: !!rawData
            });

            if (rawData) {
                console.log("TMA Detected. Attempting auto-login...");
                axios.post(`${API_BASE}/auth/telegram-webapp`, { initData: rawData })
                    .then(res => {
                        const { session_token, u_id } = res.data.data || {};
                        if (session_token) {
                            localStorage.setItem("session_token", session_token);
                            localStorage.setItem("u_id", u_id);
                            console.log("Auto-login success. Redirecting...");
                            navigate("/dashboard", { replace: true });
                        }
                    })
                    .catch(err => {
                        console.error("Auto-login error:", err);
                    });
            }
        }, 500);

        return () => clearTimeout(timer);
    }, [navigate]);

    return null; // Hech narsa render qilmaydi
}
