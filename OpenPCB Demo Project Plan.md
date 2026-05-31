# OpenPCB Demo — Project Plan

**Goal:** A three-page static demo built with Django + HTMX + Tailwind, populated with hardcoded data, suitable for showing to colleagues to validate the concept.

**Total estimated time:** 4–6 focused sessions of 2–3 hours each (~10–15 hours total), spread across 2–3 weeks depending on your availability.

---

## Assumptions & Constraints

- You are comfortable in Python but new to Django and web development
- You are comfortable with Docker and Docker Compose
- You are working on a desktop Linux machine
- No real backend logic, database, auth, or file handling in scope
- "Done" means: looks credible, loads fast, communicates the idea clearly

---

## Sprint 0 — Environment & Scaffolding

**Goal:** A running Django app in Docker that serves a single "hello world" page at `localhost:8000`

**Expected time:** 2–3 hours

### Tasks

- [ ]  Create a project directory: `~/projects/openpcb/`

- [ ]  Initialize a git repo and create a `.gitignore` (use [gitignore.io](https://gitignore.io/) → select Django, Python, Docker)

- [ ]  Write a minimal `Dockerfile`:
  
  dockerfile
  
  `FROM python:3.12-slim WORKDIR /app COPY requirements.txt . RUN pip install -r requirements.txt COPY . .`

- [ ]  Write a `docker-compose.yml` with a single `web` service (no database needed yet), volume-mounting your project directory

- [ ]  Create `requirements.txt` with your initial dependencies:
  
  python
  
  `django>=5.0 whitenoise        # serves static files (CSS, images) without a separate server`

- [ ]  Scaffold the Django project inside the container:
  
  bash
  
  `docker compose run web django-admin startproject openpcb .`

- [ ]  Create a `core` Django app — this will hold all your demo views:
  
  bash
  
  `docker compose run web python manage.py startapp core`

- [ ]  Configure `settings.py`:
  
  - Add `core` and `whitenoise` to `INSTALLED_APPS`
  - Set `STATIC_ROOT` and configure WhiteNoise middleware
  - Set `ALLOWED_HOSTS = ['*']` (fine for local demo)

- [ ]  Wire up a single placeholder view in `core/views.py` that returns `HttpResponse("hello world")`

- [ ]  Confirm it loads at `http://localhost:8000`

- [ ]  First git commit: `initial scaffold`

### Deliverable

A running Django app in Docker, version controlled, serving a response at localhost.

---

## Sprint 1 — Tailwind & Base Template

**Goal:** A styled base HTML template that all pages will inherit from, including a navbar

**Expected time:** 2–3 hours

### Background

Rather than installing Tailwind via Node (which adds a whole new toolchain), use the **Tailwind CSS CDN** for the demo. It's not suitable for production (it loads the full stylesheet), but for a local demo shown to a handful of people it's completely fine and saves hours of setup.

### Tasks

- [ ]  Create your Django template directory structure:
  
  csharp
  
  `core/   templates/     core/       base.html       index.html       explore.html       project_detail.html`

- [ ]  Write `base.html` — the master template every page extends. It should include:
  
  - Tailwind CSS CDN `<script>` tag in `<head>`
  - HTMX CDN `<script>` tag in `<head>` (you won't use it yet, but wire it in now)
  - A `<nav>` with:
    - OpenPCB logo/wordmark (text is fine for now)
    - "Explore" link → `/explore`
    - "Upload" button → dead link, styled as a button
    - "Log In" link → dead link
  - A `{% block content %}{% endblock %}` placeholder for page content
  - A simple footer with "OpenPCB © 2025 — Open hardware for everyone"

- [ ]  Update your placeholder view to render `core/index.html` (which just extends base for now)

- [ ]  Confirm the navbar renders and looks reasonable at `localhost:8000`

### Deliverable

A styled shell that all three pages will live inside. Every subsequent sprint just fills in the `content` block.

### Resources

- [Tailwind CSS CDN docs](https://tailwindcss.com/docs/installation/play-cdn)
- [Django template inheritance docs](https://docs.djangoproject.com/en/5.0/ref/templates/language/#template-inheritance)

---

## Sprint 2 — Seed Data & URL Structure

**Goal:** Define your fake projects as Python data structures and wire up all three URL routes

**Expected time:** 1–2 hours

### Background

Instead of a database, your "data layer" for the demo is a plain Python list of dictionaries defined directly in `views.py`. This is the fastest possible path to something that looks dynamic without any real backend work. It also makes the eventual migration to real models very clean — you're just swapping the hardcoded list for a `Project.objects.all()` query.

### Tasks

- [ ]  Define a `PROJECTS` list in `core/views.py`. Each project should have enough fields to feel realistic:
  
  python
  
  `PROJECTS = [     {         "id": 1,         "title": "RP2040 Breakout Board",         "author": "jsmith",         "description": "A minimal breakout for the RP2040 with USB-C, LiPo charging, and 2MB flash. Designed in KiCad 7.",         "license": "CC BY-SA 4.0",         "tags": ["microcontroller", "rp2040", "breakout"],         "downloads": 142,         "stars": 38,         "uploaded": "2025-03-12",         "files": [             {"name": "rp2040-breakout-gerbers.zip", "type": "Gerber", "size": "48 KB"},             {"name": "rp2040-breakout.kicad_pcb", "type": "KiCad PCB", "size": "210 KB"},             {"name": "bom.csv", "type": "BOM", "size": "4 KB"},             {"name": "schematic.pdf", "type": "Schematic", "size": "312 KB"},         ],         "thumbnail": "https://placehold.co/400x300?text=RP2040+Breakout",     },     # ... 3-4 more projects ]`

- [ ]  Aim for 4–5 projects total. Use realistic names — look at popular designs on [GitHub](https://github.com/topics/kicad) or [Hackaday.io](https://hackaday.io/) for inspiration. Variety helps: mix a microcontroller board, a power supply, an RF board, a sensor board.

- [ ]  Write three views:
  
  python
  
  `def index(request): ...          # landing page def explore(request): ...        # passes PROJECTS to template def project_detail(request, id): # finds one project by id, passes it to template`

- [ ]  Wire up `core/urls.py` and include it from `openpcb/urls.py`:
  
  python
  
  `urlpatterns = [     path('', views.index, name='index'),     path('explore/', views.explore, name='explore'),     path('projects/<int:id>/', views.project_detail, name='project_detail'), ]`

- [ ]  Confirm all three routes return a response (content doesn't matter yet)

### Deliverable

All three URL routes working, fake data defined, no 404s.

---

## Sprint 3 — Landing Page

**Goal:** A compelling homepage that explains the idea in under five seconds

**Expected time:** 2–3 hours

### Design Target

Think: large hero section, one-line value proposition, a call-to-action button, and a brief "how it works" section. You are not designing from scratch — find a Tailwind landing page example you like and adapt it. [Tailwind UI](https://tailwindui.com/components) has free components, as does [Flowbite](https://flowbite.com/).

### Tasks

- [ ]  **Hero section:**
  - Large heading: *"The open library for PCB designs"* (or similar — this is worth iterating on)
  - Subheading: one sentence describing the concept
  - Two CTA buttons: "Explore Designs" → `/explore` and "Upload Your Board" → dead link
- [ ]  **"How it works" section** — three columns, each with an icon and a short label:
  - Upload your design files
  - Share with the community
  - Order direct from your favorite fab (greyed out / "coming soon" badge)
- [ ]  **"Why OpenPCB?" section** — two or three short bullet points differentiating from emailing Gerbers around or using generic file hosts. Think about what you'd actually say to a colleague.
- [ ]  **A preview strip** — show 3 project cards pulled from your `PROJECTS` data (reuse the card component you'll build in Sprint 4 — you may need to do these sprints slightly iteratively)
- [ ]  A link at the bottom of the strip: "See all designs →" to `/explore`

### Deliverable

A landing page that, when shown cold to a colleague, makes them say "oh, I get it" without you explaining anything.

---

## Sprint 4 — Explore / Gallery Page

**Goal:** A browseable grid of all fake projects that feels like a real design library

**Expected time:** 2–3 hours

### Design Target

Look at Printables' explore page or [Hackaday.io](https://hackaday.io/projects) for reference. A clean card grid with a thumbnail, title, author, and a couple of stats is the whole thing.

### Tasks

- [ ]  **Page header** — "Explore Designs" heading, and a row of placeholder filter buttons (All, Microcontrollers, Power, RF, Sensors — dead links for now, but they signal future functionality)
- [ ]  **Project card component** — build this as a reusable template include (`_card.html`) so the landing page preview strip can use the same component:
  - Thumbnail image (use your `placehold.co` URL)
  - Project title
  - Author handle with a small avatar placeholder
  - Download count and star count with icons
  - Tags as small badges
  - The whole card links to `/projects/<id>/`
- [ ]  **Grid layout** — responsive grid using Tailwind: 1 column on mobile, 2 on tablet, 3 on desktop. (Even if you only demo on desktop, responsive design makes it look more serious)
- [ ]  Render all projects from your `PROJECTS` context variable using a `{% for %}` loop

### Deliverable

A grid of 4–5 convincing project cards, all clickable through to the detail page.

---

## Sprint 5 — Project Detail Page

**Goal:** The page that answers "what would I actually get from this site?"

**Expected time:** 2–3 hours

### Design Target

This is your most important page for the demo. It's what a colleague will stare at and imagine uploading their own work to. Reference [Printables project pages](https://printables.com/) and [GitHub releases pages](https://github.com/) for layout ideas.

### Tasks

- [ ]  **Header section:**
  
  - Project title (large)
  - Author handle, upload date, license badge
  - Star button (dead, but visually present) and download count

- [ ]  **Main content area — two column layout:**
  
  - Left/main (wider): project description, tags
  - Right/sidebar: file list, each with filename, type badge, file size, and a "Download" button (dead link — or optionally, link to a real open-source Gerber file on GitHub for extra credibility)

- [ ]  **File list** — this is critical. Make it look like a real, thoughtful file management UI:
  
  css
  
  `📦 rp2040-breakout-gerbers.zip    Gerber    48 KB    [Download] 📄 rp2040-breakout.kicad_pcb      KiCad     210 KB   [Download] 📄 bom.csv                         BOM       4 KB     [Download] 📄 schematic.pdf                   PDF       312 KB   [Download]`

- [ ]  **A "More by this author" strip** at the bottom — 1–2 other project cards (reuse your card component). This makes the site feel like a real browseable community.

- [ ]  **An "Order This Board" placeholder section** — greyed out, with PCBWay and JLC logos, and a "Coming soon" label. This communicates the business model without building anything.

### Deliverable

A project detail page that makes a colleague say "I'd want my boards to look like this."

---

## Sprint 6 — Polish & Demo Prep

**Goal:** Clean up rough edges, verify the demo flow end to end, prepare for conversations

**Expected time:** 1–2 hours

### Tasks

- [ ]  **Favicon** — grab a simple PCB-related SVG icon from [SVG Repo](https://svgrepo.com/) and set it as the favicon. A small detail that makes it feel real.
- [ ]  **Page titles** — make sure each page has a proper `<title>` tag: "OpenPCB — Explore Designs", etc.
- [ ]  **404 page** — Django's default is ugly. Write a one-page custom 404 that matches your design. Ten minutes, high visual impact.
- [ ]  **Dead link audit** — go through every button and link. Anything that goes nowhere should either be removed or visually indicated as "coming soon." Broken navigation interrupts the demo flow.
- [ ]  **Walk the demo yourself three times** — landing → explore → project detail → back to explore. Note anything that feels confusing or broken.
- [ ]  **Write a one-paragraph "About" blurb** — put it in the footer or a `/about` page. Include the vision and a note that it's in early development and you're looking for feedback. Gives colleagues context and an implicit invitation to comment.
- [ ]  **Deploy to your desktop, confirm it runs cleanly after a fresh `docker compose up`**

### Deliverable

A demo you can confidently walk a colleague through in under five minutes.

---

## Summary Timeline

| Sprint | Focus                     | Est. Time | Cumulative |
| ------ | ------------------------- | --------- | ---------- |
| 0      | Environment & scaffolding | 2–3 hrs   | 2–3 hrs    |
| 1      | Tailwind & base template  | 2–3 hrs   | 4–6 hrs    |
| 2      | Seed data & URL structure | 1–2 hrs   | 5–8 hrs    |
| 3      | Landing page              | 2–3 hrs   | 7–11 hrs   |
| 4      | Explore / gallery page    | 2–3 hrs   | 9–14 hrs   |
| 5      | Project detail page       | 2–3 hrs   | 11–17 hrs  |
| 6      | Polish & demo prep        | 1–2 hrs   | 12–19 hrs  |

**Realistic calendar estimate:** 2–3 weekends if you have 3–4 hour blocks available, or ~2 weeks of evening sessions.

---

## Definition of Done

The demo is complete when all three of the following are true:

1. A colleague who knows nothing about the project can land on the homepage and explain back to you what the site does
2. The full flow of landing → explore → project detail works without any broken links or visual errors
3. You can answer the question *"what happens when I click Upload?"* with a credible description of what the experience will be, even if the button doesn't work yet
