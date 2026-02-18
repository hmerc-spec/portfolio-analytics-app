import os
from functools import wraps

import psycopg
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-secret")  # set SECRET_KEY in env (Render)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


@app.get("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = os.environ.get("APP_PASSWORD")

        if not expected:
            return render_template("login.html", error="APP_PASSWORD is not set on the server."), 500

        if password == expected:
            session["logged_in"] = True
            return redirect(url_for("app_home"))

        return render_template("login.html", error="Invalid password"), 401

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/app")
@login_required
def app_home():
    return render_template("app_home.html")


@app.get("/db")
def db_check():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return "DATABASE_URL is not set", 500

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            value = cur.fetchone()[0]

    return f"DB OK: {value}"


@app.get("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(debug=True)
