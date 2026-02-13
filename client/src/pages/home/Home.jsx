import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Leaf, Shield, Zap } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import Header from "../../components/header/Header";
import "./Home.scss";

export default function Home() {
    const { theme } = useTheme();
    const isLoggedIn = !!localStorage.getItem("session_token");

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
