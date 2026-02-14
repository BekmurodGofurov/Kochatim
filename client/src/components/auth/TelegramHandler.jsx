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

        // Agar Telegram bo'lsa va initData bo'lsa
        if (tg && tg.initData) {
            console.log("TMA Detected on Main Website. Attempting auto-login...");

            tg.ready();
            tg.expand();

            // Auto-login request
            axios.post(`${API_BASE}/auth/telegram-webapp`, { initData: tg.initData })
                .then(res => {
                    const { session_token, u_id } = res.data.data || {};

                    if (session_token) {
                        localStorage.setItem("session_token", session_token);
                        localStorage.setItem("u_id", u_id);

                        console.log("TMA Auto-login successful. Redirecting to dashboard...");
                        navigate("/dashboard", { replace: true });
                    }
                })
                .catch(err => {
                    console.error("TMA Auto-login error on main site:", err);
                });
        }
    }, [navigate]);

    return null; // Hech narsa render qilmaydi
}
