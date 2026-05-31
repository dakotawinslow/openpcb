# CLAUDE.md — OpenPCB Project Context

This file gives you context about the project, the current phase, the tech
stack, and the conventions to follow. Read this before making any changes.

---

## What This Project Is

OpenPCB (openpcb.com) is a community platform for sharing open-source PCB
designs — think Printables or Thingiverse, but for PCB design files (Gerbers,
KiCad, Eagle, etc.). Users will eventually be able to upload designs, browse a
public library, and order boards directly through partner integrations with
fabs like PCBWay and JLC.

The domain is already owned. The project is in early pre-launch development.

---

## Current Phase: Proof of Concept Demo

We are NOT building a full product yet. The current goal is a static
three-page demo with hardcoded data, good enough to show to colleagues and
validate the concept. There is no database, no authentication, no file
uploads, and no backend logic in scope for this phase.

**In scope for the demo:**
- A landing page (`/`)
- A gallery/explore page (`/explore`)
- A project detail page (`/projects/<id>/`)
- Hardcoded fake project data defined as a Python list in `views.py`
- A convincing, polished UI using Tailwind CSS

**Explicitly out of scope for the demo:**
- Authentication of any kind
- Database models or migrations
- File upload or storage
- Any backend logic beyond rendering templates
- Mobile optimization (nice to have, not required)
- Real download links (dead buttons are fine)

When the demo is validated, we will move to a real MVP with Django models,
auth, and file uploads. Do not get ahead of that phase.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend framework | Django 5.x |
| Frontend interaction | HTMX |
| Styling | Tailwind CSS (CDN for demo, not compiled) |
| Language | Python 3.12 |
| Package management | uv (`pyproject.toml` + `uv.lock`) |
| Containerization | Docker + Docker Compose |
| Version control | Git / GitHub |

**Not in the stack:**
- No React, Vue, or any JS framework
- No Node.js or npm/webpack toolchain
- No JavaScript written by hand unless absolutely necessary — prefer HTMX
- No Celery, Redis, or any task queue (post-MVP concerns)
- No database yet (demo phase)

---

## Project Structure

```
openpcb/                        ← repo root, also Django project root
├── CLAUDE.md                   ← this file
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml              ← dependencies (edit this to add packages)
├── uv.lock                     ← auto-generated, never edit by hand
├── manage.py
├── openpcb/                    ← Django project package
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/                       ← main (and currently only) Django app
    ├── views.py                ← all views + hardcoded PROJECTS data
    ├── urls.py
    └── templates/
        └── core/
            ├── base.html       ← master template, all pages extend this
            ├── index.html      ← landing page
            ├── explore.html    ← gallery grid
            ├── project_detail.html
            └── _card.html      ← reusable project card include
```

---

## Data Model (Demo Phase)

There is no database. All project data lives as a hardcoded `PROJECTS` list
of dictionaries in `core/views.py`. This is intentional — it is the fastest
path to a working demo and will be replaced with real Django models in the
next phase.

Each project dict has the following shape:

```python
{
    "id": int,
    "title": str,
    "author": str,
    "description": str,
    "license": str,          # e.g. "CC BY-SA 4.0"
    "tags": list[str],
    "downloads": int,
    "stars": int,
    "uploaded": str,         # ISO date string, e.g. "2025-03-12"
    "files": [
        {
            "name": str,     # e.g. "gerbers.zip"
            "type": str,     # e.g. "Gerber", "KiCad PCB", "BOM", "Schematic"
            "size": str,     # e.g. "48 KB"
        }
    ],
    "thumbnail": str,        # placehold.co URL for demo
}
```

When we move to real models, this structure directly informs the schema for
`Project` and `File` models. Do not diverge from this shape without good
reason.

---

## URL Structure

```
/                        → core.views.index           (landing page)
/explore/                → core.views.explore          (gallery grid)
/projects/<int:id>/      → core.views.project_detail   (detail page)
```

These are the only routes for the demo. Do not add routes unless asked.

---

## Django Conventions

- **Fat models, thin views** — business logic belongs in models, not views.
  (Not relevant in the demo phase since there are no models, but follow this
  when models are introduced.)
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

---

## Tailwind Conventions

- Using the **Tailwind CDN** for the demo. This is intentional and acceptable
  for this phase. Do not introduce a Node/npm build pipeline.
- Prefer Tailwind utility classes directly in HTML. Do not write custom CSS
  unless there is genuinely no Tailwind equivalent.
- Responsive classes are welcome but not required for the demo. Desktop layout
  is the primary target.

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

Because `clip-path` clips box shadows, use CSS `filter: drop-shadow()` instead
of Tailwind `shadow-*` classes on elements that need a shadow.

### Soldermask Green Theme

The brand color palette is defined in `base.html`'s Tailwind config under
`brand`. Key values:
- `brand-600` — primary soldermask green, main action color
- `brand-400` — lighter accent for dark mode
- `brand-50/brand-900` — tag/badge backgrounds (light/dark)

### PCB Trace Background

A subtle `repeating-linear-gradient` at −45° runs across the page body,
evoking PCB trace routing. Defined in `base.html`'s `<style>` block. Do not
remove or override this on individual pages.

---

## HTMX Conventions

HTMX is included in `base.html` but is not actively used in the demo phase.
It is wired in now so it is available when we need it. Do not add HTMX
interactions until the real MVP phase unless a specific interaction is
explicitly requested.

---

## Development Environment

- The developer is working on a **desktop Linux machine**.
- Docker and Docker Compose are the only runtime requirements. Nothing should
  require a local Python install or manual setup steps outside of Docker.
- The app runs at `http://localhost:8000`.
- `docker compose up` should always be the single command needed to start the
  full environment.
- There is no database container in the demo phase. The `docker-compose.yml`
  has a single `web` service.
- Static files are served by **WhiteNoise** — no separate static file server
  or Nginx is needed in development or demo deployment.

---

## What Good Looks Like (Definition of Done for the Demo)

The demo is complete when:

1. A colleague who knows nothing about the project can land on the homepage
   and explain back what the site does without prompting.
2. The full flow of `/` → `/explore` → `/projects/<id>/` works with no broken
   links, no Django error pages, and no visual anomalies.
3. The project detail page makes a colleague say "I'd want my board listed
   here."

---

## What Comes After the Demo

For context — do not build any of this yet:

- **Phase 2 (Real MVP):** Django models for `User`, `Project`, and `File`.
  Auth via `django-allauth`. File upload to cloud storage. Real Postgres
  database added to Docker Compose.
- **Phase 3:** In-browser Gerber viewer (WebGL/JS, backend-agnostic).
  Search and tagging. User profiles.
- **Phase 4:** Partner integrations (PCBWay, JLC, Digi-Key). "Order this
  board" button. Revenue model.

If a request seems to be heading toward Phase 2+ concerns while we are in the
demo phase, flag it and confirm before proceeding.

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
```

---

A few notes on what's in here and why:

- **The "out of scope" sections are the most important part.** Claude Code is eager and will happily build you a full auth system if you ask an ambiguous question. Being explicit about phase boundaries prevents that.
- **The Questions & Decisions log** at the bottom is worth maintaining as the project evolves. When you make a meaningful architectural call, add a row. It gives future-you (and future Claude sessions) the *reasoning*, not just the outcome.
- **The "What Comes After" section** tells the model what the future looks like without inviting it to build there prematurely.

As you move into new phases, update this file before starting work in that phase — it's more valuable than any comment in the code.
