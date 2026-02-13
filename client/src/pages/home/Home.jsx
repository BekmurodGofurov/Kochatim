import { useNavigate } from "react-router-dom";
import { ArrowRight, Leaf, Shield, Zap } from "lucide-react";

export default function Home() {
    const { theme } = useTheme();
    const navigate = useNavigate();
    const isLoggedIn = !!localStorage.getItem("session_token");

    React.useEffect(() => {
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
                                <div className="feature-icon">
                                    <Leaf size={32} />
                                </div>
                                <h3>Inventarni kuzatish</h3>
                                <p>Ko'chatlar zaxirasi va navlarini osongina boshqaring.</p>
                            </div>
                            <div className="feature-card">
                                <div className="feature-icon">
                                    <Zap size={32} />
                                </div>
                                <h3>Tez va qulay</h3>
                                <p>Barcha qurilmalaringizda chaqmoqdek tez ishlashni his qiling.</p>
                            </div>
                            <div className="feature-card">
                                <div className="feature-icon">
                                    <Shield size={32} />
                                </div>
                                <h3>Xavfsiz ma'lumotlar</h3>
                                <p>Biznes ma'lumotlaringiz zamonaviy xavfsizlik standartlari bilan himoyalangan.</p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer className="home-footer">
                <div className="container">
                    <p>&copy; {new Date().getFullYear()} Ko'chatim. Barcha huquqlar himoyalangan.</p>
                </div>
            </footer>
        </div>
    );
}
