# CLAUDE.md — OpenPCB Project Context

This file gives you context about the project, the current phase, the tech
stack, and the conventions to follow. Read this before making any changes.

---

## What This Project Is

OpenPCB (openpcb.com) is a community platform for sharing open-source PCB
designs — think Printables or Thingiverse, but for PCB design files (Gerbers,
KiCad, Eagle, etc.). Users can create projects, upload design files and
photos, browse a public library, and (eventually) order boards directly
through partner integrations with fabs like PCBWay and JLC.

The domain is already owned. The project is in a **limited alpha**: a small
group of real testers is using the live site and filing bug/feedback issues
on GitHub.

---

## Current Phase: Limited Alpha — Hardening

The core product loop is built and live: real accounts, real projects, real
file/photo uploads to object storage, all backed by Postgres. The current
focus is **not new features** — it's taking the codebase from "built fast to
validate the idea" to "responsible enough to keep running and to build on
confidently." Concretely, that means:

- Closing test-coverage gaps (the app currently has none)
- CI that runs lint + tests on every PR
- Lint/format tooling (ruff) and pre-commit hooks
- Production observability (logging, error visibility, health checks)
- Fixing rough edges found during this review (e.g. validation edge cases)
- Triaging and fixing bugs/feedback filed by alpha testers (tracked as
  GitHub issues)

**What's already live (do not redo or "rebuild from scratch"):**
- Accounts/auth via django-allauth (signup, login, password reset)
- Django models backed by Postgres: `Profile`, `Tag`, `Project`,
  `ProjectFile`, `ProjectPhoto` (see `core/models.py`)
- Project CRUD, owner-only edit/delete
- File and photo upload/delete to Cloudflare R2, with extension/size
  validation (`core/constants.py`, `core/forms.py`)
- Auto-generated thumbnails from a "featured" photo (signal-driven, see
  `core/models.py`)
- Explore page: search, tag filter, sort, pagination
- User profile pages
- Session-deduplicated download counting, pre-signed (60s) R2 download URLs

**Still explicitly out of scope (Phase 3/4 — do not build unless asked):**
- In-browser Gerber viewer (tracked as issue #17)
- Full-text/fuzzy search (issue #11)
- Profile editing — avatar/username/bio (issue #12)
- Partner fab integrations / "order this board" (issue #18)
- Embedded circuit simulator (issue #19)
- Payments/revenue model
- Mobile optimization (nice to have, not required)

If a request seems to be heading toward one of these, flag it and confirm
before proceeding.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend framework | Django 6.x |
| Auth | django-allauth |
| Database | Postgres 16 |
| Object storage | Cloudflare R2 (via django-storages / boto3, S3-compatible) |
| Images | Pillow (thumbnail generation) |
| Frontend interaction | HTMX (included, not yet actively used) |
| Styling | Tailwind CSS (CDN, not compiled) |
| Language | Python 3.12 |
| Package management | uv (`pyproject.toml` + `uv.lock`) |
| Containerization | Docker + Docker Compose |
| Static files | WhiteNoise |
| Version control | Git / GitHub |

**Not in the stack:**
- No React, Vue, or any JS framework
- No Node.js or npm/webpack toolchain
- No JavaScript written by hand unless absolutely necessary — prefer HTMX
- No Celery, Redis, or any task queue

---

## Project Structure

```
openpcb/                        ← repo root, also Django project root
├── CLAUDE.md                   ← this file
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh        ← prod entrypoint: migrate + collectstatic, then exec CMD
├── pyproject.toml              ← dependencies + ruff config (edit this to add packages)
├── uv.lock                     ← auto-generated, never edit by hand
├── manage.py
├── .env.example                ← copy to .env before first run
├── .pre-commit-config.yaml     ← optional local ruff hooks (see "Running tests and lint")
├── .github/workflows/ci.yml    ← runs scripts/check.sh on push/PR to main
├── scripts/check.sh            ← lint + format check + manage.py check + tests, run by CI
├── assets/                      ← source images (logo, palette) used as static files
├── openpcb/                     ← Django project package
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/                        ← main (and currently only) Django app
│   ├── models.py                ← Profile, Tag, Project, ProjectFile, ProjectPhoto
│   │                                + thumbnail-management signals
│   ├── views.py
│   ├── forms.py                 ← ProjectForm, ProjectFileForm, ProjectPhotoForm
│   ├── constants.py             ← upload allowlists/size limits, file-type detection
│   ├── checks.py                ← Django system checks (e.g. prod email backend)
│   ├── admin.py
│   ├── urls.py
│   ├── tests/                   ← test_forms.py, test_models.py, test_views.py,
│   │                                test_auth.py, test_checks.py
│   ├── migrations/
│   └── templates/
│       ├── 404.html / 500.html
│       └── core/
│           ├── base.html        ← master template, all pages extend this
│           ├── index.html        ← landing page
│           ├── explore.html      ← gallery grid
│           ├── project_detail.html
│           ├── project_form.html
│           ├── project_confirm_delete.html
│           ├── profile.html
│           └── _card.html        ← reusable project card include
└── templates/account/           ← django-allauth templates (login, signup, password reset)
```

---

## Data Model

Real Django models, backed by Postgres. `core/models.py` is the source of
truth — do not duplicate the schema here; this is just an orientation map.

- **`Profile`** — one-to-one with `User`. Auto-created via a `post_save`
  signal on `User`. Bio/website fields (avatar editing not yet built —
  issue #12).
- **`Tag`** — simple unique slug, M2M on `Project`.
- **`Project`** — the core entity. `owner` is `SET_NULL` (deleting a user
  doesn't delete their shared designs). Has a stable `uuid` (used in URLs)
  and a decorative `slug` (auto-generated from title, canonicalised via
  301 redirect if stale). `thumbnail` is server-managed — generated from
  the featured `ProjectPhoto`, never set directly.
- **`ProjectFile`** — design files (Gerbers, KiCad, etc.), one project to
  many. Stored in R2 under `projects/<project.id>/...`. Validation
  (extension allowlist, 100MB cap, 20 files/project) lives in
  `core/constants.py` and `ProjectFileForm.clean_file`.
- **`ProjectPhoto`** — gallery photos, one project to many. Stored in R2
  under `projects/<project.id>/photos/...`. The featured photo drives
  `Project.thumbnail` via `post_save`/`post_delete` signals (fill-and-crop
  JPEG, see `_generate_thumbnail`/`_reassign_thumbnail`). Validation
  (extension allowlist, 20MB cap, 20 photos/project) lives in
  `core/constants.py` and `ProjectPhotoForm.clean_photo`.

`Project.id` (integer PK) remains the canonical FK target and the R2 path
key; `Project.uuid` is scoped to public-facing URLs only (see decisions log).

---

## URL Structure

```
/                                                  → index (landing page)
/healthz/                                          → healthz (DB connectivity check, JSON)
/explore/                                          → explore (gallery grid, search/sort/tags)
/users/<username>/                                 → profile
/admin/                                            → Django admin
/accounts/...                                      → django-allauth (login, signup, password reset)
/projects/new/                                     → ProjectCreateView
/projects/<uuid>/<slug>/                           → project_detail
/projects/<uuid>/<slug>/edit/                      → ProjectUpdateView (owner only)
/projects/<uuid>/<slug>/delete/                    → ProjectDeleteView (owner only)
/projects/<uuid>/<slug>/photos/upload/             → photo_upload (owner only)
/projects/<uuid>/<slug>/photos/<id>/delete/        → photo_delete (owner only)
/projects/<uuid>/<slug>/photos/<id>/feature/       → photo_set_featured (owner only)
/projects/<uuid>/<slug>/photos/reorder/            → photo_reorder (owner only)
/projects/<uuid>/<slug>/files/upload/              → file_upload (owner only)
/projects/<uuid>/<slug>/files/<id>/delete/         → file_delete (owner only)
/projects/<uuid>/<slug>/files/<id>/download/       → file_download
```

Do not add routes unless asked.

---

## Django Conventions

- **Fat models, thin views** — business logic belongs in models (see the
  thumbnail-management signals in `core/models.py` as the pattern to
  follow), not views.
- **Template inheritance** — every page template must extend `core/base.html`
  using `{% extends "core/base.html" %}` and fill in the `{% block content %}`
  block. Never write standalone HTML pages.
- **Template includes** — reusable components like the project card live in
  their own file prefixed with an underscore (e.g. `_card.html`) and are
  included with `{% include "core/_card.html" %}`.
- **No logic in templates** — templates should only contain display logic
  (loops, conditionals on passed context). Data shaping and lookups happen
  in the view.
- **Named URLs** — always use `{% url 'name' %}` in templates, never
  hardcoded paths.
- **Tests are required for new features** — any new model, form, view, or
  signal needs corresponding tests in `core/tests/` (`test_models.py`,
  `test_forms.py`, `test_views.py`, or a new module for a new area). At
  minimum, cover the happy path, permission/ownership checks, and validation
  edge cases. A feature without tests is not done — CI enforces this on every
  PR.

---

## Tailwind Conventions

- Using the **Tailwind CDN**. This is intentional. Do not introduce a
  Node/npm build pipeline.
- Prefer Tailwind utility classes directly in HTML. Do not write custom CSS
  unless there is genuinely no Tailwind equivalent.
- Responsive classes are welcome but not required. Desktop layout is the
  primary target.

---

## Design Motifs (Core Principles)

These are non-negotiable visual decisions that define the OpenPCB aesthetic.
Apply them consistently across all new UI elements.

### 45° Chamfered Corners

**Never use `rounded-*` Tailwind classes.** All corners are chamfered at 45°
using `clip-path` utility classes defined in `base.html`:

| Class | Chamfer size | Use for |
|---|---|---|
| `chamfer-sm` | 5px | Tags, badges, small buttons, avatars |
| `chamfer` | 8px | Standard buttons, inputs |
| `chamfer-lg` | 14px | Cards, panels, large containers |

**Never use `border-*` or `shadow-*` Tailwind classes on chamfered elements.**
`clip-path` clips everything including CSS borders and box-shadows, so they
will not follow the chamfer shape.

Instead, use the `ds-*` drop-shadow utilities defined in `base.html`. Because
`filter: drop-shadow()` is composited *after* `clip-path`, it correctly traces
the chamfer outline:

| Class | Use for |
|---|---|
| `ds-outline` | Panels, outlined buttons — subtle gray border glow |
| `ds-outline-brand` | Tags, badges, brand-coloured buttons |
| `ds-card` | Cards — includes both border glow and elevation shadow with hover state |

### Soldermask Green Theme

The brand color palette is defined in `base.html`'s Tailwind config under
`brand`. Key values:
- `brand-600` — primary soldermask green, main action color
- `brand-400` — lighter accent for dark mode
- `brand-50/brand-900` — tag/badge backgrounds (light/dark)

**CSS custom properties (`--brand-*-rgb`, `--copper-*-rgb`) are derived
automatically** from the Tailwind config by an inline `<script>` in
`base.html`'s `<head>`. Do not add a manual `:root {}` block — update the
Tailwind config only. The script converts hex values to RGB tuples and sets
them on `document.documentElement.style` synchronously, so they are available
before first paint.

### PCB Trace Background

A subtle `repeating-linear-gradient` at −45° runs across the page body,
evoking PCB trace routing. Defined in `base.html`'s `<style>` block. Do not
remove or override this on individual pages.

---

## HTMX Conventions

HTMX is included in `base.html` but is not actively used yet. It is wired in
so it is available when we need it. Do not add HTMX interactions unless a
specific interaction is explicitly requested.

**JavaScript in templates must be wrapped in an IIFE.** Any `<script>` block
inside a template that could be re-executed by an HTMX content swap must wrap
all its declarations in an immediately-invoked function expression to avoid
`SyntaxError: Identifier already declared` on re-swap:

```js
(function () {
  const foo = ...;   // safe — scoped to the IIFE
  window.myHandler = function () { ... };  // exposed for onclick= attrs
}());
```

Functions called from inline `onclick=` attributes must be explicitly assigned
to `window`; declarations inside an IIFE are not visible in global scope.

---

## Development Environment

- The developer is working on a **desktop Linux machine**.
- Docker and Docker Compose are the only runtime requirements. Nothing should
  require a local Python install or manual setup steps outside of Docker.
- The app runs at `http://localhost:8000`.
- `docker compose up` should always be the single command needed to start the
  full environment.
- `docker-compose.yml` has a `web`/`web-dev` service pair (Postgres 16 is
  `db`). `COMPOSE_PROFILES` in `.env` selects which `web` variant runs —
  `dev` for hot-reloading `runserver`, `prod` for gunicorn + migrate +
  collectstatic. `docker compose up` is the same command either way; only
  `.env` differs. Copy `.env.example` to `.env` before first run (defaults to
  `dev`) — settings are loaded via `django-environ` from that file.
- Static files are served by **WhiteNoise** — no separate static file server
  or Nginx is needed in development or production.

### Running tests and lint

- **`scripts/check.sh`** is the single source of truth for "is this change
  good to commit?" — it runs `ruff check`, `ruff format --check`,
  `manage.py check`, and `manage.py test`, in that order, and is also what CI
  runs. Run it with `docker compose exec web sh scripts/check.sh` (or
  `web-dev` if running the dev profile). Don't hand-roll a subset of these
  commands when checking your work — run the script so local and CI results
  can't drift apart.
- Test mode (`'test' in sys.argv`) switches `STORAGES['default']` to
  in-memory storage and static files to the non-manifest backend, so no R2
  credentials or `collectstatic` run are needed for `manage.py test`.
- To auto-fix lint/format issues rather than just check them:
  `docker compose exec web uv run ruff check --fix .` and
  `uv run ruff format .`.
- A `.pre-commit-config.yaml` is provided for the lint/format portion —
  install with `uvx pre-commit install` on the host (requires `uv` on the
  host, not just in Docker). It runs on `git commit` and auto-fixes via
  ruff; it does not run `manage.py test` (no DB access from the host), so
  `scripts/check.sh` is still the full check before pushing.
- CI (`.github/workflows/ci.yml`) runs `scripts/check.sh` against a Postgres
  service container on every push/PR to `main`.

### Branching policy

- **Default working branch is `dev`.** When not on a feature-specific branch,
  all work happens on `dev`. Never commit directly to `main`.
- **Feature branches** branch off `dev` and merge back into `dev` via PR.
- **`dev` → `main` merges only on explicit request.** Do not merge `dev` into
  `main` unless the user specifically asks for it. `main` is the production
  branch — only tested, approved work lands there.
- If the current branch is `main` and the task is not a `dev` → `main` merge,
  switch to `dev` (or a feature branch off `dev`) before making changes.

---

## What Good Looks Like (Definition of Done for Alpha Hardening)

This stage of work is complete when:

1. `core/tests.py` has real coverage of ownership/permission checks, form
   validation, and the thumbnail signals — and CI runs it on every PR.
2. A lint/format check (ruff) runs in CI and locally via pre-commit.
3. Production errors are visible (logging configured, not just default
   Django behavior) without waiting for a tester to report them.
4. The codebase has a README a new contributor or tester can follow.

---

## What Comes After This

For context — do not build any of this yet unless a specific issue asks for
it:

- **Phase 3:** In-browser Gerber viewer (issue #17). Full-text/fuzzy search
  (issue #11). Profile editing (issue #12). License expansion (issue #16).
  Photo crop fix (issue #15).
- **Phase 4:** Partner integrations (PCBWay, JLC, Digi-Key) and "order this
  board" (issue #18). Embedded circuit simulator (issue #19). Revenue model.

---

## Questions & Decisions Log

| Date | Question | Decision |
|---|---|---|
| 2026-05-30 | Framework choice | Django + HTMX. Python familiarity outweighs JS ecosystem benefits for this developer. Option to migrate to Next.js preserved. |
| 2026-05-30 | Demo vs. MVP | Starting with a proof-of-concept demo (hardcoded data, no backend) before building a real MVP. Validate the idea first. |
| 2026-05-30 | Dev environment | Docker Compose on local desktop Linux machine. No cloud dev environment. |
| 2026-05-30 | Tailwind setup | CDN only for demo phase. No Node toolchain until it becomes necessary. |
| 2026-05-30 | Package manager | uv instead of pip/requirements.txt. Modern standard, faster installs, reproducible builds via uv.lock. |
| 2026-05-30 | Sprint 0 complete | Django scaffold running in Docker at localhost:8000. Repo live at github.com/dakotawinslow/openpcb. |
| 2026-05-31 | Corner style | 45° chamfered corners (clip-path) chosen over rounded corners as a core PCB-aesthetic motif. Applied to all UI elements. Never use rounded-* classes. |
| 2026-05-31 | Sprints 1–4 complete | Base template, seed data, explore page, and card component done. Sprint 3 (landing page) intentionally deferred — doing detail page next. |
| 2026-05-31 | Sprint 5 complete | Project detail page done. |
| 2026-05-31 | Chamfer borders | CSS border-* is clipped by clip-path and cannot follow the chamfer. Use filter: drop-shadow() (ds-* utilities) instead — it composites after clip-path and traces the shape correctly. |
| 2026-05-31 | Infrastructure sprint | Postgres 16 + Cloudflare R2 + django-environ wired in. docker-compose now has a `db` service. Settings read from `.env` via django-environ. Copy `.env.example` to `.env` before first run. |
| 2026-05-31 | CSS custom properties | `--brand-*-rgb` / `--copper-*-rgb` vars are now derived from the Tailwind config via an inline script in `base.html`. Never duplicate hex values in a manual `:root` block — the Tailwind config is the single source of truth. |
| 2026-05-31 | Gallery JS scoping | All `<script>` blocks in templates must be wrapped in an IIFE. Functions called from inline `onclick=` must be assigned to `window`. Prevents SyntaxError on HTMX re-swap. |
| 2026-05-31 | Bug sweep | 10 GitHub issues filed and resolved: hardcoded hrefs → `{% url %}`, gallery thumbnail hover state, JS globals, palette duplication, prev/next button visibility, redundant inline styles, duplicate image URL array. All merged to main. |
| 2026-06-11 | File Uploads sprint | Photo/file upload, delete, and download views added. First photo a user uploads is auto-marked featured (so a thumbnail exists as soon as a project has one photo). Photo/file management lives in owner-only panels on `project_detail.html` (grid with "Set featured"/delete controls), not in `ProjectForm`. Validation (extension allowlist + size caps) lives in `core/constants.py` and `forms.py` `clean_*` methods. Downloads are session-deduplicated and redirect to pre-signed R2 URLs (`expire=60`). |
| 2026-06-11 | Dual ID system kept | `Project.id` (integer PK) remains the canonical identifier for all FKs (ProjectFile, ProjectPhoto, tags M2M) and R2 storage paths (`projects/<id>/...`). `Project.uuid` remains scoped to public-facing identifiers (URLs only). Considered consolidating to a UUID-only PK; rejected — integer PK keeps FKs/indexes compact, and `id` is not vestigial since it's the real PK, not a parallel unused field. |
| 2026-06-12 | Dev/prod compose split | First prod deploy (`styx`) used the dev `web` service unmodified — it bypassed `docker-entrypoint.sh`, so `migrate`/`collectstatic` never ran and the site 500'd on every page (missing staticfiles manifest). Fixed by splitting `docker-compose.yml` into `web` (prod, gunicorn + entrypoint) and `web-dev` (hot-reload `runserver` + bind mount), selected via `COMPOSE_PROFILES` in `.env`. `docker compose up` is unchanged for both; only `.env` differs — see issue #13. |
| 2026-06-12 | Alpha hardening kickoff | Codebase moved from "demo" to "limited alpha" framing in this file — auth, Postgres, R2 uploads, and CRUD are all live, so prior demo-phase scope language was stale and misleading. Current focus: tests, CI, lint, observability (see "Current Phase" above). |
| 2026-06-12 | Lint/format tooling | Added ruff (lint + format) as a dev dependency, configured via `[tool.ruff]` in `pyproject.toml`. `quote-style = "single"` preserves the existing single-quote convention to avoid a repo-wide quote-churn diff. DJ012 (Django model member ordering — Meta before `__str__`/`save`) is enforced; reordered the 4 affected models once. The 3 long marketing-copy strings in `WHY_ITEMS` (`core/views.py`) are `# noqa: E501` rather than split, since splitting would hurt readability/grep-ability. `.pre-commit-config.yaml` added for local use (optional — see "Running tests and lint"). |
| 2026-06-12 | Initial test suite | Added `core/tests/` package (forms, models/signals, view permissions — 26 tests). `STORAGES['default']` switches to `django.core.files.storage.InMemoryStorage` and staticfiles to the non-manifest backend when `'test' in sys.argv` (`TESTING` flag in `settings.py`) — avoids needing R2 credentials or a `collectstatic` run to test thumbnail-signal/file-upload code paths. Fixed a real bug found while writing form tests: tags that slugify to `''` (e.g. `"!!!"`) no longer create an empty-named `Tag` — `ProjectForm.save` now drops empty slugs and dedupes via `dict.fromkeys`. |
| 2026-06-12 | CI added | `.github/workflows/ci.yml` runs ruff (check + format) and `manage.py test` against a `postgres:16` service container on push/PR to `main`. Uses dummy `DJANGO_SECRET_KEY`/`DATABASE_URL` env vars — no R2 or email secrets needed since test mode avoids those backends. |
| 2026-06-12 | Test coverage required for new features | Added a rule to "Django Conventions": new models/forms/views/signals must ship with tests in `core/tests/`. CI enforces this on every PR. |
| 2026-06-12 | Observability (Phase B) | Added `LOGGING` config in `settings.py` — structured stdout logging (Django's request/error logs included), picked up by `docker compose logs`. Added a `/healthz` endpoint (`core/views.py:healthz`, checks DB connectivity via `connection.ensure_connection()`) for container/uptime health checks. For error tracking, chose **GlitchTip** (self-hosted, Sentry-API-compatible) over hosted Sentry — fits the "no extra managed services" bias, and the developer already stood up an instance. Wired via `sentry-sdk` (Sentry's official client works against GlitchTip's API) — `SENTRY_DSN` env var; empty/unset in dev and CI skips `sentry_sdk.init` entirely (gated on `TESTING`). |
| 2026-06-12 | Auth rate limiting (Phase C) | Investigated rate-limiting login/signup — django-allauth 65.x already enables `ACCOUNT_RATE_LIMITS` by default (`login_failed`: 5/5min per username + 10/min per IP; `signup`, `reset_password`, etc. similarly limited), backed by Django's default cache (`LocMemCache`, no `CACHES` config needed). No code change required; added `core/tests/test_auth.py` to lock in this behavior so it isn't silently disabled by a future settings change. |
| 2026-06-12 | Prod email backend check (Phase C) | Added `core/checks.py` (`email_backend_check`, registered via `CoreConfig.ready()`): warns (`core.W001`) if `DEBUG=False` and `EMAIL_BACKEND` is still the console backend — password resets would otherwise be silently written to logs instead of emailed. Runs on every `manage.py` invocation (incl. `migrate` in `docker-entrypoint.sh`), so it's visible in prod logs without waiting for a tester to report broken password resets. Skipped when `TESTING` to avoid CI noise (CI doesn't set `EMAIL_BACKEND`). Documented in `.env.example`. |
| 2026-06-12 | Single quality-check script | Added `scripts/check.sh` (ruff check, ruff format --check, manage.py check, manage.py test, in that order) as the one canonical "is this ready to commit?" command, run via `docker compose exec web sh scripts/check.sh`. CI now runs this same script instead of duplicating the steps inline, so local and CI checks can't drift apart. Required adding dummy `R2_*` env vars to CI — `manage.py check` (unlike `manage.py test`) builds the real-storage `STORAGES` dict (TESTING is false), which raises if the R2 env vars are unset, even though no network call is made. |

---

A few notes on what's in here and why:

- **The "out of scope" sections are the most important part.** Claude Code is eager and will happily build you a full feature set if you ask an ambiguous question. Being explicit about phase boundaries prevents that.
- **The Questions & Decisions log** at the bottom is worth maintaining as the project evolves. When you make a meaningful architectural call, add a row. It gives future-you (and future Claude sessions) the *reasoning*, not just the outcome.
- **The "What Comes After" section** tells the model what the future looks like without inviting it to build there prematurely.

As you move into new phases, update this file before starting work in that phase — it's more valuable than any comment in the code.
