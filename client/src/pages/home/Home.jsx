import React, { useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, Leaf, Shield, Zap } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import Header from "../../components/header/Header";
import "./Home.scss";

export default function Home() {
    const navigate = useNavigate();
    const { theme } = useTheme();
    const isLoggedIn = !!localStorage.getItem("session_token");

    useEffect(() => {
        if (isLoggedIn) {
            navigate("/dashboard", { replace: true });
        }
    }, [isLoggedIn, navigate]);

    return (
        <div className={`home-page ${theme}-mode`}>
            <Header />

            <main>
                <section className="hero">
                    <div className="container">
                        <h1>Manage Your Greenery with <span>Ko'chatim</span></h1>
                        <p className="hero-subtitle">
                            The ultimate solution for greenhouse inventory and sales management.
                            Track your plants, optimize your sales, and grow your business.
                        </p>
                        <div className="hero-actions">
                            {isLoggedIn ? (
                                <Link to="/dashboard" className="btn btn-primary">
                                    Go to Dashboard <ArrowRight size={20} />
                                </Link>
                            ) : (
                                <>
                                    <Link to="/login" className="btn btn-primary">
                                        Get Started <ArrowRight size={20} />
                                    </Link>
                                    <Link to="/dashboard" className="btn btn-secondary">
                                        Go to Dashboard
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
                                <div className="feature-icon">
                                    <Leaf size={32} />
                                </div>
                                <h3>Inventory Tracking</h3>
                                <p>Efficiently manage your plant stock and varieties with ease.</p>
                            </div>
                            <div className="feature-card">
                                <div className="feature-icon">
                                    <Zap size={32} />
                                </div>
                                <h3>Fast & Responsive</h3>
                                <p>Experience lightning-fast performance across all your devices.</p>
                            </div>
                            <div className="feature-card">
                                <div className="feature-icon">
                                    <Shield size={32} />
                                </div>
                                <h3>Secure Data</h3>
                                <p>Your business data is protected with industry-standard security.</p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer className="home-footer">
                <div className="container">
                    <p>&copy; {new Date().getFullYear()} Ko'chatim. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}
