import os
import math
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


def build_pagination_window(page: int, total_pages: int):
    if total_pages <= 1:
        return []
    pages = {1, total_pages}
    for p in range(page - 2, page + 3):
        if 1 <= p <= total_pages:
            pages.add(p)
    ordered = sorted(pages)
    window = []
    last = None
    for p in ordered:
        if last is not None and p - last > 1:
            window.append("…")
        window.append(p)
        last = p
    return window


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
            return redirect(url_for("dashboard"))

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


@app.get("/bugs")
@login_required
def bugs_list():
    q = request.args.get("q", "").strip()
    page_text = request.args.get("page", "1").strip()
    try:
        page = int(page_text)
    except ValueError:
        page = 1
    if page < 1:
        page = 1
    per_page = 20

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """
                    select count(*)
                    from bug_entries
                    where title ilike %s
                       or error_text ilike %s
                       or fix_text ilike %s
                       or tags ilike %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, bug_date, title, minutes_lost, status, tags
                    from bug_entries
                    where title ilike %s
                       or error_text ilike %s
                       or fix_text ilike %s
                       or tags ilike %s
                    order by bug_date desc, created_at desc
                    limit %s
                    offset %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", per_page, offset),
                )
            else:
                cur.execute(
                    """
                    select count(*)
                    from bug_entries
                    """
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, bug_date, title, minutes_lost, status, tags
                    from bug_entries
                    order by bug_date desc, created_at desc
                    limit %s
                    offset %s
                    """,
                    (per_page, offset),
                )

            rows = cur.fetchall()

    has_prev = page > 1
    has_next = page < total_pages
    page_numbers = build_pagination_window(page, total_pages)
    bugs = [
        {
            "id": r[0],
            "bug_date": r[1],
            "title": r[2],
            "minutes_lost": r[3],
            "status": r[4],
            "tags": r[5],
        }
        for r in rows
    ]

    return render_template(
        "bugs_list.html",
        bugs=bugs,
        q=q,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        page_numbers=page_numbers,
    )


@app.route("/bugs/new", methods=["GET", "POST"])
@login_required
def bugs_new():
    if request.method == "POST":
        bug_date = request.form.get("bug_date", "").strip()
        title = request.form.get("title", "").strip()
        status = request.form.get("status", "open").strip()
        tags = request.form.get("tags", "").strip() or None

        error_text = request.form.get("error_text", "").strip() or None
        fix_text = request.form.get("fix_text", "").strip() or None

        minutes_lost_text = request.form.get("minutes_lost", "0").strip()

        errors = []
        if not title:
            errors.append("Title is required.")

        if status not in ("open", "fixed"):
            errors.append("Status must be open or fixed.")

        try:
            minutes_lost = int(minutes_lost_text)
            if minutes_lost < 0:
                errors.append("Minutes lost must be 0 or more.")
        except ValueError:
            errors.append("Minutes lost must be a whole number.")

        if errors:
            return render_template("bugs_new.html", errors=errors, form=request.form), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into bug_entries
                      (bug_date, title, error_text, fix_text, minutes_lost, status, tags)
                    values
                      (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (bug_date or None, title, error_text, fix_text, minutes_lost, status, tags),
                )

        return redirect(url_for("bugs_list"))

    return render_template("bugs_new.html", errors=[], form={})


@app.post("/bugs/<int:bug_id>/toggle")
@login_required
def bugs_toggle_status(bug_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update bug_entries
                set status = case when status = 'open' then 'fixed' else 'open' end
                where id = %s
                """,
                (bug_id,),
            )
    return redirect(url_for("bugs_detail", bug_id=bug_id))


@app.get("/dashboard")
@login_required
def dashboard():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # total minutes last 7 days
            cur.execute(
                """
                select coalesce(sum(minutes), 0)
                from learning_entries
                where entry_date >= current_date - interval '6 days'
                """
            )
            minutes_7d = cur.fetchone()[0]

            # sessions count last 7 days
            cur.execute(
                """
                select count(*)
                from learning_entries
                where entry_date >= current_date - interval '6 days'
                """
            )
            sessions_7d = cur.fetchone()[0]

            # average confidence last 7 days
            cur.execute(
                """
                select coalesce(avg(confidence), 0)
                from learning_entries
                where entry_date >= current_date - interval '6 days'
                """
            )
            avg_conf_7d = cur.fetchone()[0]

            # minutes per day (last 14 days) - include missing dates as 0
            cur.execute(
                """
                with days as (
                  select generate_series(
                    current_date - interval '13 days',
                    current_date,
                    interval '1 day'
                  )::date as day
                )
                select
                  days.day,
                  coalesce(sum(le.minutes), 0) as total_minutes
                from days
                left join learning_entries le
                  on le.entry_date = days.day
                group by days.day
                order by days.day
                """
            )
            daily_rows = cur.fetchall()

    # Current streak: consecutive days (ending today) with minutes > 0
    streak_days = 0
    for day, total_minutes in reversed(daily_rows):  # start from today backwards
        if int(total_minutes) > 0:
            streak_days += 1
        else:
            break


    labels = [r[0].strftime("%b %d") for r in daily_rows]  # e.g., "Feb 19"
    values = [int(r[1]) for r in daily_rows]

    return render_template(
        "dashboard.html",
        minutes_7d=minutes_7d,
        sessions_7d=sessions_7d,
        avg_conf_7d=avg_conf_7d,
        streak_days=streak_days,
        labels=labels,
        values=values,
    )


@app.get("/projects")
@login_required
def projects_list():
    q = request.args.get("q", "").strip()
    page_text = request.args.get("page", "1").strip()
    try:
        page = int(page_text)
    except ValueError:
        page = 1
    if page < 1:
        page = 1
    per_page = 20

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """
                    select count(*)
                    from projects
                    where name ilike %s
                       or problem_statement ilike %s
                       or notes ilike %s
                       or tags ilike %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, created_at, name, status, tags
                    from projects
                    where name ilike %s
                       or problem_statement ilike %s
                       or notes ilike %s
                       or tags ilike %s
                    order by created_at desc
                    limit %s
                    offset %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", per_page, offset),
                )
            else:
                cur.execute(
                    """
                    select count(*)
                    from projects
                    """
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, created_at, name, status, tags
                    from projects
                    order by created_at desc
                    limit %s
                    offset %s
                    """,
                    (per_page, offset),
                )
            rows = cur.fetchall()

    has_prev = page > 1
    has_next = page < total_pages
    page_numbers = build_pagination_window(page, total_pages)
    projects = [
        {
            "id": r[0],
            "created_at": r[1],
            "name": r[2],
            "status": r[3],
            "tags": r[4],
        }
        for r in rows
    ]

    return render_template(
        "projects_list.html",
        projects=projects,
        q=q,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        page_numbers=page_numbers,
    )


@app.get("/projects/<int:project_id>")
@login_required
def projects_detail(project_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, created_at, name, status, tags, problem_statement, notes
                from projects
                where id = %s
                """,
                (project_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    project = {
        "id": row[0],
        "created_at": row[1],
        "name": row[2],
        "status": row[3],
        "tags": row[4],
        "problem_statement": row[5],
        "notes": row[6],
    }

    return render_template("projects_detail.html", project=project)


@app.route("/projects/new", methods=["GET", "POST"])
@login_required
def projects_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        problem_statement = request.form.get("problem_statement", "").strip()
        status = request.form.get("status", "idea").strip()
        notes = request.form.get("notes", "").strip() or None
        tags = request.form.get("tags", "").strip() or None

        errors = []
        if not name:
            errors.append("Project name is required.")
        if not problem_statement:
            errors.append("Problem statement is required.")
        if status not in ("idea", "planned", "in_progress", "paused", "done"):
            errors.append("Invalid status.")

        if errors:
            return render_template("projects_new.html", errors=errors, form=request.form), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into projects (name, problem_statement, status, notes, tags)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (name, problem_statement, status, notes, tags),
                )

        return redirect(url_for("projects_list"))

    return render_template("projects_new.html", errors=[], form={})


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def projects_edit(project_id: int):
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        problem_statement = request.form.get("problem_statement", "").strip()
        status = request.form.get("status", "idea").strip()
        notes = request.form.get("notes", "").strip() or None
        tags = request.form.get("tags", "").strip() or None

        errors = []
        if not name:
            errors.append("Project name is required.")
        if not problem_statement:
            errors.append("Problem statement is required.")
        if status not in ("idea", "planned", "in_progress", "paused", "done"):
            errors.append("Invalid status.")

        if errors:
            return render_template(
                "projects_edit.html",
                errors=errors,
                project_id=project_id,
                form=request.form,
            ), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update projects
                    set name=%s, problem_statement=%s, status=%s, notes=%s, tags=%s
                    where id=%s
                    """,
                    (name, problem_statement, status, notes, tags, project_id),
                )

        return redirect(url_for("projects_detail", project_id=project_id))

    # GET: load existing project
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select name, problem_statement, status, notes, tags
                from projects
                where id=%s
                """,
                (project_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    form = {
        "name": row[0] or "",
        "problem_statement": row[1] or "",
        "status": row[2] or "idea",
        "notes": row[3] or "",
        "tags": row[4] or "",
    }

    return render_template("projects_edit.html", errors=[], project_id=project_id, form=form)


@app.get("/features")
@login_required
def features_list():
    q = request.args.get("q", "").strip()
    project_id = request.args.get("project_id", "").strip()
    status = request.args.get("status", "").strip()
    page_text = request.args.get("page", "1").strip()
    try:
        page = int(page_text)
    except ValueError:
        page = 1
    if page < 1:
        page = 1
    per_page = 20

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch projects for filter dropdown
            cur.execute("select id, name from projects order by name;")
            projects = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

            # Build query dynamically but safely
            where = []
            params = []

            if q:
                where.append("(f.title ilike %s or f.description ilike %s or f.tags ilike %s)")
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

            if project_id:
                where.append("f.project_id = %s")
                params.append(project_id)

            if status:
                where.append("f.status = %s")
                params.append(status)

            where_sql = ("where " + " and ".join(where)) if where else ""

            cur.execute(
                f"""
                select count(*)
                from features f
                {where_sql}
                """,
                params,
            )
            total_count = cur.fetchone()[0]
            total_pages = max(1, math.ceil(total_count / per_page))
            if page > total_pages:
                page = total_pages
            offset = (page - 1) * per_page

            cur.execute(
                f"""
                select f.id, f.created_at, f.project_id, p.name as project_name,
                       f.title, f.priority, f.status, f.effort, f.value, f.tags
                from features f
                join projects p on p.id = f.project_id
                {where_sql}
                order by
                  case f.status
                    when 'in_progress' then 1
                    when 'blocked' then 2
                    when 'planned' then 3
                    when 'backlog' then 4
                    when 'done' then 5
                    else 6
                  end,
                  f.priority asc,
                  f.created_at desc
                limit %s
                offset %s
                """,
                params + [per_page, offset],
            )
            rows = cur.fetchall()

    has_prev = page > 1
    has_next = page < total_pages
    page_numbers = build_pagination_window(page, total_pages)
    features = [
        {
            "id": r[0],
            "created_at": r[1],
            "project_id": r[2],
            "project_name": r[3],
            "title": r[4],
            "priority": r[5],
            "status": r[6],
            "effort": r[7],
            "value": r[8],
            "tags": r[9],
        }
        for r in rows
    ]

    return render_template(
        "features_list.html",
        features=features,
        projects=projects,
        q=q,
        project_id=project_id,
        status=status,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        page_numbers=page_numbers,
    )


@app.route("/features/new", methods=["GET", "POST"])
@login_required
def features_new():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, name from projects order by name;")
            projects = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

    if request.method == "POST":
        project_id = request.form.get("project_id", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        tags = request.form.get("tags", "").strip() or None

        status = request.form.get("status", "backlog").strip()

        priority_text = request.form.get("priority", "3").strip()
        effort_text = request.form.get("effort", "3").strip()
        value_text = request.form.get("value", "3").strip()

        errors = []
        if not project_id:
            errors.append("Project is required.")
        if not title:
            errors.append("Title is required.")
        if status not in ("backlog", "planned", "in_progress", "blocked", "done"):
            errors.append("Invalid status.")

        try:
            priority = int(priority_text)
            if not (1 <= priority <= 5):
                errors.append("Priority must be between 1 and 5.")
        except ValueError:
            errors.append("Priority must be a whole number.")

        try:
            effort = int(effort_text)
            if not (1 <= effort <= 5):
                errors.append("Effort must be between 1 and 5.")
        except ValueError:
            errors.append("Effort must be a whole number.")

        try:
            value = int(value_text)
            if not (1 <= value <= 5):
                errors.append("Value must be between 1 and 5.")
        except ValueError:
            errors.append("Value must be a whole number.")

        if errors:
            return render_template(
                "features_new.html",
                projects=projects,
                errors=errors,
                form=request.form,
            ), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into features
                      (project_id, title, description, priority, status, effort, value, tags)
                    values
                      (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (project_id, title, description, priority, status, effort, value, tags),
                )

        return redirect(url_for("features_list"))

    return render_template("features_new.html", projects=projects, errors=[], form={})



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
    page_text = request.args.get("page", "1").strip()
    try:
        page = int(page_text)
    except ValueError:
        page = 1
    if page < 1:
        page = 1
    per_page = 20

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """
                    select count(*)
                    from learning_entries
                    where topic ilike %s
                       or summary ilike %s
                       or notes ilike %s
                       or tags ilike %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, entry_date, topic, minutes, confidence, summary, tags
                    from learning_entries
                    where topic ilike %s
                       or summary ilike %s
                       or notes ilike %s
                       or tags ilike %s
                    order by entry_date desc, created_at desc
                    limit %s
                    offset %s
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", per_page, offset),
                )
            else:
                cur.execute(
                    """
                    select count(*)
                    from learning_entries
                    """
                )
                total_count = cur.fetchone()[0]
                total_pages = max(1, math.ceil(total_count / per_page))
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page
                cur.execute(
                    """
                    select id, entry_date, topic, minutes, confidence, summary, tags
                    from learning_entries
                    order by entry_date desc, created_at desc
                    limit %s
                    offset %s
                    """,
                    (per_page, offset),
                )

            rows = cur.fetchall()

    has_prev = page > 1
    has_next = page < total_pages
    page_numbers = build_pagination_window(page, total_pages)
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

    return render_template(
        "learning_list.html",
        entries=entries,
        q=q,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        page_numbers=page_numbers,
    )


@app.get("/bugs/<int:bug_id>")
@login_required
def bugs_detail(bug_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, bug_date, title, status, minutes_lost, tags, error_text, fix_text, created_at
                from bug_entries
                where id = %s
                """,
                (bug_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    bug = {
        "id": row[0],
        "bug_date": row[1],
        "title": row[2],
        "status": row[3],
        "minutes_lost": row[4],
        "tags": row[5],
        "error_text": row[6],
        "fix_text": row[7],
        "created_at": row[8],
    }

    return render_template("bugs_detail.html", bug=bug)


@app.route("/bugs/<int:bug_id>/edit", methods=["GET", "POST"])
@login_required
def bugs_edit(bug_id: int):
    if request.method == "POST":
        bug_date = request.form.get("bug_date", "").strip()
        title = request.form.get("title", "").strip()
        status = request.form.get("status", "open").strip()
        tags = request.form.get("tags", "").strip() or None

        error_text = request.form.get("error_text", "").strip() or None
        fix_text = request.form.get("fix_text", "").strip() or None

        minutes_lost_text = request.form.get("minutes_lost", "0").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if status not in ("open", "fixed"):
            errors.append("Status must be open or fixed.")

        try:
            minutes_lost = int(minutes_lost_text)
            if minutes_lost < 0:
                errors.append("Minutes lost must be 0 or more.")
        except ValueError:
            errors.append("Minutes lost must be a whole number.")

        if errors:
            return render_template(
                "bugs_edit.html",
                errors=errors,
                bug_id=bug_id,
                form=request.form,
            ), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update bug_entries
                    set bug_date = coalesce(%s, bug_date),
                        title = %s,
                        error_text = %s,
                        fix_text = %s,
                        minutes_lost = %s,
                        status = %s,
                        tags = %s
                    where id = %s
                    """,
                    (bug_date or None, title, error_text, fix_text, minutes_lost, status, tags, bug_id),
                )

        return redirect(url_for("bugs_detail", bug_id=bug_id))

    # GET: load existing
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select bug_date, title, error_text, fix_text, minutes_lost, status, tags
                from bug_entries
                where id = %s
                """,
                (bug_id,),
            )
            row = cur.fetchone()

    if not row:
        return "Not found", 404

    form = {
        "bug_date": str(row[0]) if row[0] else "",
        "title": row[1] or "",
        "error_text": row[2] or "",
        "fix_text": row[3] or "",
        "minutes_lost": row[4] if row[4] is not None else 0,
        "status": row[5] or "open",
        "tags": row[6] or "",
    }

    return render_template("bugs_edit.html", errors=[], bug_id=bug_id, form=form)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/app")
@login_required
def app_home():
    return redirect(url_for("dashboard"))


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
