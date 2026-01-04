import sqlite3 as sq

db = sq.connect('users.db')
cur = db.cursor()

async def db_start():
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
                        u_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_name text,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
              )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS categories(
                        c_id INTEGER PRIMARY KEY,
                        u_id INTEGER,
                        c_name TEXT,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute('''CREATE TABLE IF NOT EXISTS types (
                        t_id INTEGER PRIMARY KEY,
                        u_id INTEGER,
                        c_id INTEGER,
                        t_name TEXT,
                        deff TEXT,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                   )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seedlings (
                        s_id INTEGER PRIMARY KEY,
                        u_id INTEGER,
                        t_id INTEGER,
                        quality_1 INTEGER,
                        quality_2 INTEGER,z
                        quality_3 INTEGER,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP  
                   )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS img (
                       i_id INTEGER PRIMARY KEY,
                       t_id INTEGER,
                       i_url TEXT,
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                   )''')

    db.commit()

# Users table commits
def new_user(user_id, name):
    cur.execute("SELECT u_id FROM users WHERE u_id = ?", (user_id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (u_id, u_name) VALUES (?, ?)", (user_id, name))
        db.commit()
        return True
    else:
        return False

def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE u_id = ?", (user_id,))
    row = cur.fetchone()

    if row:
        return row
    else:
        return None
def delete_one(user_id):
    cur.execute("DELETE from users_data WHERE user_id = (?)", (user_id,))
    db.commit()

def get_all_users():
    cur.execute("SELECT * FROM users_data")
    users = cur.fetchall()
    return users

def search_by_name(name):
    cur.execute("SELECT * FROM users_data WHERE name = (?)", (name)) 
    user = cur.fetchall()
    return user

# Categories table commits

def new_cat(c_id, u_id, c_name):
    cur.execute("SELECT c_name FROM categories WHERE c_name = ? AND u_id = ?", (c_name, u_id))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO categories (c_id, u_id, c_name) VALUES (?, ?, ?)", (c_id, u_id, c_name))
        db.commit()
        return True
    else:
        return False

def get_all_cat(u_id):
    cur.execute("SELECT c_name FROM categories WHERE u_id = ?", (u_id,))
    results = cur.fetchall()

    cat_arr = [row[0] for row in results]
    return cat_arr

def get_cat_id(u_id, c_name):
    cur.execute("SELECT c_id FROM categories WHERE u_id = ? AND c_name = ?", (u_id, c_name))
    return cur.fetchone()[0]

def get_a_cat(u_id, c_name):
    cur.execute("SELECT c_id FROM categories WHERE u_id = ? AND c_name = ?", (u_id, c_name))
    if cur.fetchone() is None:
        return False
    else:
        return cur.fetchone()[0]

# The Types table commits
def new_ty(t_id, c_id, u_id, t_name, deff):
    cur.execute("INSERT INTO types (t_id, c_id, u_id, t_name, deff) VALUES (?, ?, ?,?,?)", (t_id,c_id, u_id, t_name, deff))
    db.commit()

def get_a_ty(t_name, u_id):
    cur.execute("SELECT t_name FROM types WHERE t_name = ? AND u_id = ?", (t_name, u_id))
    if cur.fetchone() is None:
        return True
    else: return False

def get_all_ty(c_id,u_id):
    cur.execute("SELECT t_name FROM types WHERE c_id = ? AND u_id = ?", (c_id, u_id))
    results = cur.fetchall()
    ty_arr = [row[0] for row in results]
    return ty_arr
def get_any_ty(u_id):
    cur.execute("SELECT t_name FROM types WHERE u_id = ?", (u_id,))
    results = cur.fetchall()

    return results

def get_type_id(c_id, u_id, t_name):
    cur.execute("SELECT t_id FROM types WHERE c_id = ? AND u_id = ? AND t_name = ?", (c_id, u_id, t_name))
    result = cur.fetchone()
    if result:
        return result[0]
    return None
def get_type_info(t_id):
    """Nav IDsi (t_id) bo'yicha Nav nomi va Tafsilotini olish."""
    cur.execute("SELECT t_name, deff FROM types WHERE t_id = ?", (t_id,))
    result = cur.fetchone()
    if result:
        # result quyidagi kortejni qaytaradi: (t_name, deff)
        return result
    return None


def get_type_id(c_id, u_id, t_name):

    cur.execute('''SELECT t_id FROM types WHERE c_id = ? AND u_id = ? AND t_name = ?''', (c_id, u_id, t_name))

    result = cur.fetchone()

    if result:
        return result[0]
    else:
        return None

# Seedlings table commits

def new_seedling(u_id, t_id, q1_count, q2_count=0, q3_count=0):

    cur.execute("SELECT s_id FROM seedlings WHERE t_id = ? AND u_id = ?", (t_id, u_id))
    existing_row = cur.fetchone()

    if existing_row:
        s_id = existing_row[0]
        cur.execute('''UPDATE seedlings SET quality_1 = ?, quality_2 = ?,quality_3 = ? WHERE s_id = ?''', (q1_count, q2_count, q3_count, s_id))

    else:
        cur.execute('''
                    INSERT INTO seedlings (u_id, t_id, quality_1, quality_2, quality_3)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (u_id, t_id, q1_count, q2_count, q3_count))

    db.commit()
    return True



def get_seedling_count(t_id):
    cur.execute('''
                SELECT quality_1,
                       quality_2,
                       quality_3
                FROM seedlings
                WHERE t_id = ?
                ''', (t_id,))

    result = cur.fetchone()

    if result:
        return {
            'sifat_1': result[0] if result[0] is not None else 0,
            'sifat_2': result[1] if result[1] is not None else 0,
            'sifat_3': result[2] if result[2] is not None else 0
        }
    else:
        return {'sifat_1': 0, 'sifat_2': 0, 'sifat_3': 0}