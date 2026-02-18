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


def get_db_connection():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(dsn)


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


@app.route("/learning/new", methods=["GET", "POST"])
@login_required
def learning_new():
    if request.method == "POST":
        entry_date = request.form.get("entry_date", "").strip()
        topic = request.form.get("topic", "").strip()
        minutes_text = request.form.get("minutes", "").strip()
        confidence_text = request.form.get("confidence", "").strip()
        summary = request.form.get("summary", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        tags = request.form.get("tags", "").strip() or None

        # Basic validation
        errors = []
        if not topic:
            errors.append("Topic is required.")

        try:
            minutes = int(minutes_text)
            if minutes < 0:
                errors.append("Minutes must be 0 or more.")
        except ValueError:
            errors.append("Minutes must be a whole number.")

        try:
            confidence = int(confidence_text)
            if confidence < 1 or confidence > 5:
                errors.append("Confidence must be between 1 and 5.")
        except ValueError:
            errors.append("Confidence must be a whole number between 1 and 5.")

        if errors:
            return render_template(
                "learning_new.html",
                errors=errors,
                form=request.form,
            ), 400

        # Insert into DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into learning_entries
                      (entry_date, topic, minutes, confidence, summary, notes, tags)
                    values
                      (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (entry_date or None, topic, minutes, confidence, summary, notes, tags),
                )

        return redirect(url_for("app_home"))

    # GET
    return render_template("learning_new.html", form={})


@app.route("/learning/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def learning_edit(entry_id: int):
    if request.method == "POST":
        entry_date = request.form.get("entry_date", "").strip()
        topic = request.form.get("topic", "").strip()
        minutes_text = request.form.get("minutes", "").strip()
        confidence_text = request.form.get("confidence", "").strip()
        summary = request.form.get("summary", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        tags = request.form.get("tags", "").strip() or None

        errors = []
        if not topic:
            errors.append("Topic is required.")

        try:
            minutes = int(minutes_text)
            if minutes < 0:
                errors.append("Minutes must be 0 or more.")
        except ValueError:
            errors.append("Minutes must be a whole number.")

        try:
            confidence = int(confidence_text)
            if confidence < 1 or confidence > 5:
                errors.append("Confidence must be between 1 and 5.")
        except ValueError:
            errors.append("Confidence must be a whole number between 1 and 5.")

        if errors:
            # Re-render form with entered data
            return render_template(
                "learning_edit.html",
                errors=errors,
                entry_id=entry_id,
                form=request.form,
            ), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update learning_entries
                    set entry_date = coalesce(%s, entry_date),
                        topic = %s,
                        minutes = %s,
                        confidence = %s,
                        summary = %s,
                        notes = %s,
                        tags = %s
                    where id = %s
                    """,
                    (entry_date or None, topic, minutes, confidence, summary, notes, tags, entry_id),
                )

        return redirect(url_for("learning_detail", entry_id=entry_id))

    # GET: load existing data
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select entry_date, topic, minutes, confidence, summary, notes, tags
                from learning_entries
                where id = %s
                """,
                (entry_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    form = {
        "entry_date": str(row[0]) if row[0] else "",
        "topic": row[1] or "",
        "minutes": row[2] if row[2] is not None else "",
        "confidence": row[3] if row[3] is not None else "",
        "summary": row[4] or "",
        "notes": row[5] or "",
        "tags": row[6] or "",
    }

    return render_template("learning_edit.html", entry_id=entry_id, form=form, errors=[])


@app.get("/learning/<int:entry_id>")
@login_required
def learning_detail(entry_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, entry_date, topic, minutes, confidence, summary, notes, tags, created_at
                from learning_entries
                where id = %s
                """,
                (entry_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    entry = {
        "id": row[0],
        "entry_date": row[1],
        "topic": row[2],
        "minutes": row[3],
        "confidence": row[4],
        "summary": row[5],
        "notes": row[6],
        "tags": row[7],
        "created_at": row[8],
    }

    return render_template("learning_detail.html", entry=entry)


@app.get("/learning")
@login_required
def learning_list():
    q = request.args.get("q", "").strip()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """
                    select id, entry_date, topic, minutes, confidence, summary, tags
                    from learning_entries
                    where topic ilike %s
                       or summary ilike %s
                       or notes ilike %s
                       or tags ilike %s
                    order by entry_date desc, created_at desc
                    limit 200
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
                )
            else:
                cur.execute(
                    """
                    select id, entry_date, topic, minutes, confidence, summary, tags
                    from learning_entries
                    order by entry_date desc, created_at desc
                    limit 200
                    """
                )

            rows = cur.fetchall()

    entries = [
        {
            "id": r[0],
            "entry_date": r[1],
            "topic": r[2],
            "minutes": r[3],
            "confidence": r[4],
            "summary": r[5],
            "tags": r[6],
        }
        for r in rows
    ]

    return render_template("learning_list.html", entries=entries, q=q)


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
