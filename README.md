# Learning Ops Hub

Learning Ops Hub is a lightweight, single-user operations hub for tracking what you learn, the bugs you hit, and the work you ship. It’s designed to keep day-to-day execution visible: log learning sessions, capture bug context, manage projects and features, and review progress on a compact dashboard.

## Features
- **Learning Log**: record sessions with date, minutes, confidence, topics, and notes.
- **Bug Vault**: capture bugs (what happened, fix, minutes lost), search, and mark fixed/open.
- **Project Vault**: track projects with status, tags, and notes.
- **Features Vault**: manage feature ideas with priority/effort/value and status, linked to a project.
- **Dashboard**: basic KPIs + charting (Chart.js).

## Tech Stack
- **Backend:** Flask (Python)
- **Database:** Postgres (Supabase)
- **Hosting:** Render
- **UI:** Bootstrap
- **Charts:** Chart.js

## Repo Structure
- `app.py` — Flask routes + DB queries
- `templates/` — Jinja templates (Bootstrap UI)
- `static/` — CSS

## Authentication
Single-user password login:
- Visit `/login`
- Password comes from `APP_PASSWORD`

## Environment Variables
Set these in your shell or hosting provider. Examples below use placeholders (no real secrets).

- `SECRET_KEY` — Flask session secret
- `DATABASE_URL` — Postgres connection string
- `APP_PASSWORD` — app login password

## Local Setup (Windows PowerShell)
1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

## Migrations (Supabase SQL Editor)
To apply manual migrations, copy the contents of a file in `migrations/` and run it in the Supabase SQL Editor.

1. Open your Supabase project and go to SQL Editor.
2. Create a new query and paste the contents of `migrations/003_timestamps.sql`.
3. Run the query and confirm it completes successfully.
