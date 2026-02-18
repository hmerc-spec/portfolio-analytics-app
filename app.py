import os

import psycopg
from flask import Flask

app = Flask(__name__)


@app.get("/")
def home():
    return "Hello from Flask! 🚀"


@app.get("/db")
def db_check():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return "DATABASE_URL is not set", 500

    # Simple connectivity test
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            value = cur.fetchone()[0]

    return f"DB OK: {value}"