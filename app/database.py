import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config['DB_PATH'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        conn = sqlite3.connect(app.config['DB_PATH'])
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS queue_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prefix TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_number TEXT NOT NULL,
                queue_type_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting',
                created_at TEXT NOT NULL,
                called_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (queue_type_id) REFERENCES queue_types (id)
            );

            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            """
        )
        cur.execute("SELECT COUNT(*) FROM staff")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO staff (username, password_hash) VALUES (?, ?)",
                (app.config['DEFAULT_ADMIN_USERNAME'], generate_password_hash(app.config['DEFAULT_ADMIN_PASSWORD'])),
            )
        cur.execute("SELECT COUNT(*) FROM queue_types")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO queue_types (name, prefix) VALUES (?, ?)",
                [("ซักประวัติ / วัดความดัน", "A"), ("ตรวจโรคทั่วไป", "B"), ("เจาะเลือด / เอกซเรย์", "C"), ("รับยา / การเงิน", "D"), ("ทันตกรรม", "E")],
            )
        conn.commit()
        conn.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)
