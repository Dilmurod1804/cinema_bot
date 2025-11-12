# database.py
import sqlite3
import random
from config import DB_NAME

def connect():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            genre TEXT,
            year INTEGER,
            description TEXT,
            file_id TEXT,
            code TEXT UNIQUE,
            views INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE
        )
    """)

    conn.commit()
    conn.close()

def add_user(user_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def list_users():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    return users

def _generate_code(cur):
    while True:
        new_code = str(random.randint(1000, 9999))
        cur.execute("SELECT id FROM movies WHERE code = ?", (new_code,))
        if not cur.fetchone():
            return new_code

def add_movie(title, genre, year, description, file_id, code=None):
    conn = connect()
    cur = conn.cursor()
    if code is None:
        code = _generate_code(cur)
    cur.execute("""
        INSERT INTO movies (title, genre, year, description, file_id, code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, genre, year, description, file_id, code))
    conn.commit()
    movie_id = cur.lastrowid
    conn.close()
    return movie_id, code

def get_movie_by_code(code):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT title, genre, year, description, file_id, views FROM movies WHERE code = ?
    """, (code,))
    row = cur.fetchone()
    conn.close()
    return row  # None or tuple

def search_movies_by_title(query):
    conn = connect()
    cur = conn.cursor()
    q = f"%{query}%"
    cur.execute("SELECT id, title, genre, year, code FROM movies WHERE title LIKE ? ORDER BY id DESC", (q,))
    rows = cur.fetchall()
    conn.close()
    return rows

def list_movies():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, title, genre, year, code FROM movies ORDER BY id DESC")
    movies = cur.fetchall()
    conn.close()
    return movies

def delete_movie_by_id(movie_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted > 0

def update_movie(movie_id, title=None, genre=None, year=None, description=None):
    conn = connect()
    cur = conn.cursor()
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?"); params.append(title)
    if genre is not None:
        fields.append("genre = ?"); params.append(genre)
    if year is not None:
        fields.append("year = ?"); params.append(year)
    if description is not None:
        fields.append("description = ?"); params.append(description)
    if not fields:
        conn.close()
        return False
    params.append(movie_id)
    sql = f"UPDATE movies SET {', '.join(fields)} WHERE id = ?"
    cur.execute(sql, tuple(params))
    conn.commit()
    conn.close()
    return True

def increment_views_by_code(code):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def add_channel(username):
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO channels (username) VALUES (?)", (username,))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok

def remove_channel(username):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE username = ?", (username,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted > 0

def list_channels():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT username FROM channels")
    channels = [row[0] for row in cur.fetchall()]
    conn.close()
    return channels