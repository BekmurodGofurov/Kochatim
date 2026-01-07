import psycopg2
from data.config import DB_URL

# Neon.tech (PostgreSQL) ulanishi
db = psycopg2.connect(DB_URL)
cur = db.cursor()


async def db_start():
    # 1. Avtomatik vaqtni yangilaydigan funksiya (Trigger funksiyasi)
    cur.execute("""
        CREATE OR REPLACE FUNCTION update_modified_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # 2. Jadvallarni yaratish
    # Users (u_id BIGINT chunki Telegram ID katta son)
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
                        u_id BIGINT PRIMARY KEY,
                        u_name TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT NULL)""")

    # Categories
    cur.execute("""CREATE TABLE IF NOT EXISTS categories(
                        c_id SERIAL PRIMARY KEY,
                        u_id BIGINT,
                        c_name TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT NULL)""")

    # Types (Navlar)
    cur.execute("""CREATE TABLE IF NOT EXISTS types (
                        t_id SERIAL PRIMARY KEY,
                        u_id BIGINT,
                        c_id INTEGER,
                        t_name TEXT,
                        deff TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT NULL)""")

    # Seedlings (Zaxira)
    cur.execute("""CREATE TABLE IF NOT EXISTS seedlings (
                        s_id SERIAL PRIMARY KEY,
                        u_id BIGINT,
                        t_id INTEGER,
                        quality_1 INTEGER DEFAULT 0,
                        quality_2 INTEGER DEFAULT 0,
                        quality_3 INTEGER DEFAULT 0,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT NULL)""")

    # Img
    cur.execute("""CREATE TABLE IF NOT EXISTS img (
                       i_id SERIAL PRIMARY KEY,
                       t_id INTEGER,
                       i_url TEXT,
                       added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       updated_at TIMESTAMP DEFAULT NULL)""")

    # Sales (Sotuvlar)
    cur.execute("""CREATE TABLE IF NOT EXISTS sales (
                        sale_id SERIAL PRIMARY KEY,
                        u_id BIGINT,
                        c_id INTEGER,
                        t_id INTEGER,
                        q1_sold INTEGER DEFAULT 0,
                        q2_sold INTEGER DEFAULT 0,
                        q3_sold INTEGER DEFAULT 0,
                        price REAL,
                        sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    # 3. Triggerlarni bog'lash
    tables = ['users', 'categories', 'types', 'seedlings', 'img']
    for table in tables:
        cur.execute(f"DROP TRIGGER IF EXISTS update_{table}_modtime ON {table};")
        cur.execute(f"""
            CREATE TRIGGER update_{table}_modtime
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE update_modified_column();
        """)

    db.commit()


# --- USERS ---
def new_user(user_id, name):
    cur.execute("SELECT u_id FROM users WHERE u_id = %s", (user_id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (u_id, u_name) VALUES (%s, %s)", (user_id, name))
        db.commit()
        return True
    return False


def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE u_id = %s", (user_id,))
    return cur.fetchone()


# --- CATEGORIES ---
def new_cat(u_id, c_name):
    cur.execute("SELECT c_name FROM categories WHERE c_name = %s AND u_id = %s", (c_name, u_id))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO categories (u_id, c_name) VALUES (%s, %s)", (u_id, c_name))
        db.commit()
        return True
    return False


def get_all_cat(u_id):
    cur.execute("SELECT c_name FROM categories WHERE u_id = %s", (u_id,))
    return [row[0] for row in cur.fetchall()]


def get_cat_id(u_id, c_name):
    cur.execute("SELECT c_id FROM categories WHERE u_id = %s AND c_name = %s", (u_id, c_name))
    res = cur.fetchone()
    return res[0] if res else None


def get_a_cat(u_id, c_name):
    cur.execute("SELECT c_id FROM categories WHERE u_id = %s AND c_name = %s", (u_id, c_name))
    res = cur.fetchone()
    return res[0] if res else False


# --- TYPES ---
def new_ty(c_id, u_id, t_name, deff):
    cur.execute("INSERT INTO types (c_id, u_id, t_name, deff) VALUES (%s, %s, %s, %s) RETURNING t_id",
                (c_id, u_id, t_name, deff))
    t_id = cur.fetchone()[0]
    db.commit()
    return t_id


def get_a_ty(t_name, u_id):
    cur.execute("SELECT t_name FROM types WHERE t_name = %s AND u_id = %s", (t_name, u_id))
    return cur.fetchone() is None


def get_all_ty(c_id, u_id):
    cur.execute("SELECT t_name FROM types WHERE c_id = %s AND u_id = %s", (c_id, u_id))
    return [row[0] for row in cur.fetchall()]


def get_any_ty(u_id):
    cur.execute("SELECT t_name FROM types WHERE u_id = %s", (u_id,))
    return cur.fetchall()


def get_type_id(c_id, u_id, t_name):
    cur.execute("SELECT t_id FROM types WHERE c_id = %s AND u_id = %s AND t_name = %s", (c_id, u_id, t_name))
    res = cur.fetchone()
    return res[0] if res else None


def get_type_info(t_id):
    cur.execute("SELECT t_name, deff FROM types WHERE t_id = %s", (t_id,))
    return cur.fetchone()


# --- SEEDLINGS ---
def new_seedling(u_id, t_id, q1, q2=0, q3=0):
    cur.execute("SELECT s_id FROM seedlings WHERE t_id = %s AND u_id = %s", (t_id, u_id))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE seedlings SET quality_1 = %s, quality_2 = %s, quality_3 = %s WHERE s_id = %s",
                    (q1, q2, q3, row[0]))
    else:
        cur.execute("INSERT INTO seedlings (u_id, t_id, quality_1, quality_2, quality_3) VALUES (%s, %s, %s, %s, %s)",
                    (u_id, t_id, q1, q2, q3))
    db.commit()
    return True


def get_seedling_count(t_id):
    cur.execute("SELECT quality_1, quality_2, quality_3 FROM seedlings WHERE t_id = %s", (t_id,))
    res = cur.fetchone()
    if res:
        return {
            'sifat_1': res[0] if res[0] is not None else 0,
            'sifat_2': res[1] if res[1] is not None else 0,
            'sifat_3': res[2] if res[2] is not None else 0
        }
    return {'sifat_1': 0, 'sifat_2': 0, 'sifat_3': 0}


# --- IMAGES ---
def add_new_img(t_id, photo_id):
    try:
        cur.execute("INSERT INTO img (t_id, i_url) VALUES (%s, %s)", (t_id, photo_id))
        db.commit()
        return True
    except:
        return False


def get_img_url(t_id):
    cur.execute("SELECT i_url FROM img WHERE t_id = %s", (t_id,))
    res = cur.fetchone()
    return res[0] if res else None


# --- SALES ---
def add_sale(u_id, c_id, t_id, q1, q2, q3, price):
    try:
        cur.execute(
            "INSERT INTO sales (u_id, c_id, t_id, q1_sold, q2_sold, q3_sold, price) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (u_id, c_id, t_id, q1, q2, q3, price))
        # TRIGGER ishlaydi, vaqtni o'zi yangilaydi
        cur.execute(
            "UPDATE seedlings SET quality_1 = quality_1 - %s, quality_2 = quality_2 - %s, quality_3 = quality_3 - %s WHERE t_id = %s AND u_id = %s",
            (q1, q2, q3, t_id, u_id))
        db.commit()
        return True
    except:
        return False


# --- UNIVERSAL UPDATE ---
def update_any(table, column, val, where_col, where_val):
    query = f"UPDATE {table} SET {column} = %s WHERE {where_col} = %s"
    cur.execute(query, (val, where_val))
    db.commit()