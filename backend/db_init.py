# backend/db_init.py
from db import execute


def init_db():
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

    # 2) main tables (sizdagi database.py nomlari saqlangan + users fieldlari kengaydi)

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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3.1) partners (hamkorlar) - symmetric relation (A<->B as two rows)
    execute("""
    CREATE TABLE IF NOT EXISTS partners(
        u_id BIGINT NOT NULL,
        p_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (u_id, p_id)
    );
    """)

    # 3.2) partner_invites — short token (Telegram deep-link safe)
    execute("""
    CREATE TABLE IF NOT EXISTS partner_invites(
        token VARCHAR(32) PRIMARY KEY,
        inviter_u_id BIGINT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4) triggers for updated_at (CREATE OR REPLACE avoids DROP+CREATE on every startup)
    for table in ("users", "categories", "types", "seedlings", "img"):
        execute(f"""
        CREATE OR REPLACE TRIGGER update_{table}_modtime
        BEFORE UPDATE ON {table}
        FOR EACH ROW
        EXECUTE PROCEDURE update_modified_column();
        """)

    # 5) Performance Indexes
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