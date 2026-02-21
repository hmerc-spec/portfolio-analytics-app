# Project State

## Project Overview
Learning Ops Hub is a single-user ops console for tracking learning sessions, bugs, projects, and feature work with lightweight analytics. It emphasizes quick logging, searchable lists, and a central dashboard for KPIs and trends.

The app is a Flask + Postgres (Supabase) web UI with Bootstrap styling and Chart.js visualizations. It runs on Render and uses environment-based configuration.

## Current Stack
- Render (hosting)
- Supabase Postgres (transaction pooler, port 6543)
- Flask
- Bootstrap 5 (CDN)
- Chart.js
- Codex CLI

## Environments & Secrets
- `DATABASE_URL`
- `SECRET_KEY`
- `APP_PASSWORD`
- Set as Render environment variables (no secrets in repo).

## Database Schema
- `learning_entries`: `id`, `entry_date`, `topic`, `minutes`, `confidence`, `summary`, `notes`, `tags`, `created_at`, `updated_at`
- `bug_entries`: `id`, `bug_date`, `title`, `error_text`, `fix_text`, `minutes_lost`, `status`, `tags`, `created_at`, `updated_at`, `completed_at`
- `projects`: `id`, `created_at`, `name`, `problem_statement`, `status`, `notes`, `tags`, `updated_at`, `completed_at`
- `features`: `id`, `created_at`, `project_id`, `title`, `description`, `priority`, `status`, `effort`, `value`, `tags`, `updated_at`, `completed_at`

## App Modules & Routes
- Learning: list, detail, new, edit
- Bugs: list, detail, new, edit, toggle status
- Projects: list, detail, new, edit
- Features: list, new
- Dashboard: aggregated KPIs + charts
- Auth: login, logout

## Dashboard Behavior
- Section order: Projects, Features, Bugs, Learning.
- Charts: Learning 14-day minutes line chart; Bugs stacked horizontal bar (Open vs Fixed).
- KPI drill-down links to filtered lists; values of 0 are not clickable.
- Status colors are consistent across dashboard and list tables (open/blocked red, in_progress blue, planned purple, done/fixed green, backlog/idea/paused gray).

## Completed Milestones
- Dashboard v1 layout with sections, KPIs, and charts.
- Pagination with filters on list pages (Learning/Bugs/Projects/Features).
- Status color system and clickable KPI filters.
- Manual SQL migration `migrations/003_timestamps.sql` for timestamps.
- Auth flow redirect to `/dashboard` after login.

## Current Known Issues / Tech Debt
- Migrations are manual via Supabase SQL Editor.
- Features edit flow not yet implemented.
- README has some encoding artifacts (smart quotes rendered as mojibake).

## Next Priorities
1. Add Features edit route + template.
2. Wire completed_at usage into UI (e.g., show completed dates).
3. Add automated migration tooling or document sequence.
4. Add tests for filters/pagination.
5. Clean up README encoding artifacts.

## Session Handoff Template
```
Last completed:
Current state:
Next tasks:
Risks:
Commands:
```
