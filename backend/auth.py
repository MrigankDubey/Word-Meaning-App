import bcrypt
from .db import get_conn

def create_user(username, password, email=None, is_admin=False):
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO users(username, email, password_hash, is_admin) VALUES(?,?,?,?)",
                    (username, email, password_hash, 1 if is_admin else 0))
        con.commit()
        return cur.lastrowid

def find_user(username):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT id, username, email, password_hash, is_admin FROM users WHERE username=?",
                    (username,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "username": row[1], "email": row[2], "password_hash": row[3], "is_admin": bool(row[4])}

def verify_password(username, password):
    user = find_user(username)
    if not user:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
        return user
    return None
