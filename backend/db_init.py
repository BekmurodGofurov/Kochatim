# backend/db_init.py
import time
from db import execute
from utils.cache import redis_client

def init_db():
    lock_key = "global_db_init_lock"
    
    # Kichik blokirovka (Distributed Lock). nx=True - faqat kalit yo'q bo'lsa yozadi, ex=15 - 15 sekundan keyin o'chadi
    try:
        acquired = redis_client.set(lock_key, "locked", nx=True, ex=15)
        if not acquired:
            # Boshqa worker (server) hozir bazani init qilmoqda.
            # Kichik pauza qilib o'tkazib yuboramiz.
            time.sleep(2)
            return
    except Exception as e:
        print(f"Redis lock xatosi: {e}")
        # Agar Redis ishlamay qolsa, qotib qolmasligi uchun odatiy davom etaveradi
        pass

    try:
        # 1) updated_at trigger function
        execute("""
        CREATE OR REPLACE FUNCTION update_modified_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """)

        # 2) main tables
        execute("""
        CREATE TABLE IF NOT EXISTS users(
            u_id BIGINT PRIMARY KEY,
            u_name TEXT,
            u_phone TEXT,
            u_username TEXT,
            u_age INTEGER,
            u_photo TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NULL
        );
        """)

        # MIGRATION: add u_photo if not exists
        try:
            execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS u_photo TEXT;")
        except Exception:
            pass

        execute("""
        CREATE TABLE IF NOT EXISTS categories(
            c_id SERIAL PRIMARY KEY,
            u_id BIGINT,
            c_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NULL
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS types(
            t_id SERIAL PRIMARY KEY,
            u_id BIGINT,
            c_id INTEGER,
            t_name TEXT,
            deff TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NULL
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS seedlings(
            s_id SERIAL PRIMARY KEY,
            u_id BIGINT,
            t_id INTEGER,
            quality_1 INTEGER DEFAULT 0,
            quality_2 INTEGER DEFAULT 0,
            quality_3 INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NULL
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS img(
            i_id SERIAL PRIMARY KEY,
            t_id INTEGER,
            i_url TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NULL
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS sales(
            sale_id SERIAL PRIMARY KEY,
            u_id BIGINT,
            c_id INTEGER,
            t_id INTEGER,
            q1_sold INTEGER DEFAULT 0,
            q2_sold INTEGER DEFAULT 0,
            q3_sold INTEGER DEFAULT 0,
            price REAL,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS seedlings_logs(
            log_id SERIAL PRIMARY KEY,
            u_id BIGINT NOT NULL,
            t_id INTEGER NOT NULL,
            change_q1 INTEGER DEFAULT 0,
            change_q2 INTEGER DEFAULT 0,
            change_q3 INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3) auth tables (OTP + sessions)
        execute("""
        CREATE TABLE IF NOT EXISTS login_codes(
            id SERIAL PRIMARY KEY,
            code_hash TEXT NOT NULL,
            u_id BIGINT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY,
            u_id BIGINT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id SERIAL,
            device_name TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            city TEXT DEFAULT ''
        );
        """)

        # MIGRATION: sessions device columns
        try:
            execute("ALTER TABLE sessions ADD COLUMN session_id SERIAL;")
        except Exception:
            pass
        
        try:
            execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS device_name TEXT DEFAULT '';")
            execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ip_address TEXT DEFAULT '';")
            execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS city TEXT DEFAULT '';")
        except Exception:
            pass

        # 3.1) partners
        execute("""
        CREATE TABLE IF NOT EXISTS partners(
            u_id BIGINT NOT NULL,
            p_id BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (u_id, p_id)
        );
        """)

        # 3.2) partner_invites
        execute("""
        CREATE TABLE IF NOT EXISTS partner_invites(
            token VARCHAR(32) PRIMARY KEY,
            inviter_u_id BIGINT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4) triggers for updated_at
        for table in ("users", "categories", "types", "seedlings", "img"):
            try:
                execute(f"""
                CREATE OR REPLACE TRIGGER update_{table}_modtime
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE PROCEDURE update_modified_column();
                """)
            except Exception as e:
                print(f"Trigger yaratishda xatolik ({table}): {e}")

        # 5) Performance Indexes
        try:
            execute("CREATE INDEX IF NOT EXISTS idx_categories_u_id ON categories (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_types_u_id ON types (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_types_c_id ON types (c_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_seedlings_u_id ON seedlings (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_seedlings_t_id ON seedlings (t_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_sales_u_id ON sales (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_sales_c_id ON sales (c_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_sales_t_id ON sales (t_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_img_t_id ON img (t_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_img_lookup ON img (t_id, i_id DESC);")
            execute("CREATE INDEX IF NOT EXISTS idx_types_lookup ON types (u_id, t_id DESC);")
            execute("CREATE INDEX IF NOT EXISTS idx_sessions_u_id ON sessions (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_partners_u_id ON partners (u_id);")
            execute("CREATE INDEX IF NOT EXISTS idx_partners_p_id ON partners (p_id);")
        except Exception as e:
            print(f"Index yaratishda xatolik: {e}")

    finally:
        # Lockni bo'shatamiz
        try:
            redis_client.delete(lock_key)
        except Exception:
            pass