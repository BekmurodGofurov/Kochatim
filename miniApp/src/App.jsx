import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.scss';

// Backend URL - Load from env or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.kochatim.uz';

export default function App() {
    const [user, setUser] = useState(null);
    const [initData, setInitData] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isRegistered, setIsRegistered] = useState(false);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        if (!tg) {
            setLoading(false);
            setError("Telegram SDK topilmadi. Iltimos, ushbu sahifani Telegram ichida oching.");
            return;
        }

        tg.ready();
        tg.expand();

        const rawData = tg.initData;
        setInitData(rawData);

        if (!rawData) {
            setLoading(false);
            setError("initData topilmadi. Autentifikatsiya imkonsiz.");
            return;
        }

        // Auto-login logic
        axios.post(`${API_BASE_URL}/auth/telegram-webapp`, { init_data: rawData })
            .then(res => {
                const { session_token, u_id, is_registered, user_info } = res.data;
                localStorage.setItem("session_token", session_token);
                localStorage.setItem("u_id", u_id);
                setIsRegistered(is_registered);
                setUser(tg.initDataUnsafe?.user || { first_name: "Foydalanuvchi" });
            })
            .catch(err => {
                console.error("TMA Login error:", err);
                setError("Login qilishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.");
            })
            .finally(() => {
                setLoading(false);
            });

    }, []);

    if (loading) {
        return (
            <div className="tma-container loading">
                <div className="spinner"></div>
                <p>Yuklanmoqda...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="tma-container error">
                <h1>Xatolik ❌</h1>
                <p>{error}</p>
                <button onClick={() => window.location.reload()}>Qayta urinish</button>
            </div>
        );
    }

    return (
        <div className="tma-container">
            <header className="tma-header">
                <h1>Ko'chatim Mini App</h1>
            </header>

            <main className="tma-main">
                <section className="user-profile">
                    <div className="user-avatar">
                        {user?.photo_url ? <img src={user.photo_url} alt="User" /> : <span>{user?.first_name?.charAt(0)}</span>}
                    </div>
                    <h2>Salom, {user?.first_name}!</h2>
                    {user?.username && <p className="username">@{user.username}</p>}
                </section>

                <section className="registration-status">
                    {isRegistered ? (
                        <div className="status-badge success">✅ Siz ro'yxatdan o'tgansiz</div>
                    ) : (
                        <div className="status-badge warning">⚠️ Siz hali ro'yxatdan o'tmagansiz</div>
                    )}
                </section>

                <section className="actions">
                    {isRegistered ? (
                        <button className="btn-main" onClick={() => window.location.href = 'https://kochatim.uz/dashboard'}>
                            Asosiy saytga o'tish
                        </button>
                    ) : (
                        <p className="hint">Iltimos, botga qaytib ro'yxatdan o'ting (telefon raqamingizni yuboring).</p>
                    )}
                    <button className="btn-secondary" onClick={() => window.Telegram.WebApp.close()}>
                        Yopish
                    </button>
                </section>

                <section className="debug-info">
                    <h3>Debug ma'lumotlari:</h3>
                    <pre>{JSON.stringify(user, null, 2)}</pre>
                </section>
            </main>
        </div>
    );
}
