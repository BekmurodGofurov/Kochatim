import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Leaf, Shield, Zap, Search } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { apiFetch, getSessionToken } from "../../api/https";
import Header from "../../components/header/Header";
import "./Home.scss";

export default function Home() {
    const { theme } = useTheme();
    const navigate = useNavigate();
    const isLoggedIn = !!getSessionToken();

    const [q, setQ] = useState("");
    const [gardeners, setGardeners] = useState([]);
    const [loadingGardeners, setLoadingGardeners] = useState(false);

    useEffect(() => {
        let cancelled = false;
        const t = setTimeout(async () => {
            setLoadingGardeners(true);
            try {
                const rows = await apiFetch(`/api/gardeners?q=${encodeURIComponent(q)}&limit=8`);
                if (!cancelled) setGardeners(Array.isArray(rows) ? rows : []);
            } catch {
                if (!cancelled) setGardeners([]);
            } finally {
                if (!cancelled) setLoadingGardeners(false);
            }
        }, 250);
        return () => {
            cancelled = true;
            clearTimeout(t);
        };
    }, [q]);

    return (
        <div className={`home-page ${theme}-mode`}>
            <Header />

            <main>
                <section className="hero">
                    <div className="container">
                        <h1><span>Ko'chatim</span> bilan o'zingizni ko'chatingizni boshqaring</h1>
                        <p className="hero-subtitle">
                            Ko'chatingiz va sotuvlarni boshqarish uchun eng yaxshi yechim.
                            Omboringizni kuzatib boring, sotuvlarni optimallashtiring va biznesingizni rivojlantiring.
                        </p>
                        <div className="hero-actions">
                            {isLoggedIn ? (
                                <Link to="/dashboard" className="btn btn-primary">
                                    Boshqaruv paneli <ArrowRight size={20} />
                                </Link>
                            ) : (
                                <>
                                    <Link to="/login" className="btn btn-primary">
                                        Boshlash <ArrowRight size={20} />
                                    </Link>
                                    <Link to="/dashboard" className="btn btn-secondary">
                                        Boshqaruv paneli
                                    </Link>
                                </>
                            )}
                        </div>
                    </div>
                </section>

                <section className="gardeners">
                    <div className="container">
                        <div className="gardeners-head">
                            <h2>Bog‘bonlar</h2>
                            <p>Faol bog‘bonlarni toping va profilini ko‘ring.</p>
                        </div>

                        <div className="gardeners-search">
                            <Search size={18} />
                            <input
                                value={q}
                                onChange={(e) => setQ(e.target.value)}
                                placeholder="Bog‘bon ID yoki ism bilan qidiring..."
                            />
                            {loadingGardeners && <span className="gardeners-loading">...</span>}
                        </div>

                        <div className="gardeners-grid">
                            {(gardeners || []).map((g) => (
                                <button
                                    key={g.u_id}
                                    type="button"
                                    className="gardener-card"
                                    onClick={() => navigate(`/gardeners/${g.u_id}`)}
                                >
                                    <div className="gardener-title">{g.u_name || g.u_id}</div>
                                    <div className="gardener-sub">
                                        {g.u_username ? `@${g.u_username}` : "—"} • {g.u_id}
                                    </div>
                                </button>
                            ))}
                            {(!loadingGardeners && gardeners.length === 0) && (
                                <div className="gardeners-empty">Hech narsa topilmadi.</div>
                            )}
                        </div>
                    </div>
                </section>

                <section className="features">
                    <div className="container">
                        <div className="features-grid">
                            <div className="feature-card">
                                <div className="icon leaf">
                                    <Leaf size={32} />
                                </div>
                                <h3>Oson boshqaruv</h3>
                                <p>Ko'chatlaringizni toifalarga ajrating va ularni osonlik bilan kuzatib boring.</p>
                            </div>
                            <div className="feature-card">
                                <div className="icon zap">
                                    <Zap size={32} />
                                </div>
                                <h3>Tezkor hisobot</h3>
                                <p>Sotuvlar va ombor holati haqida real vaqtdagi ma'lumotlarni oling.</p>
                            </div>
                            <div className="feature-card">
                                <div className="icon shield">
                                    <Shield size={32} />
                                </div>
                                <h3>Xavfsiz ma'lumotlar</h3>
                                <p>Biznesingiz haqidagi barcha ma'lumotlar xavfsiz holda saqlanadi.</p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer className="footer">
                <div className="container">
                    <p>&copy; 2024 Ko'chatim. Barcha huquqlar himoyalangan.</p>
                </div>
            </footer>
        </div>
    );
}
