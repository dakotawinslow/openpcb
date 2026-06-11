FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install dependencies (cached layer — only reruns when lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

# Production default: gunicorn behind the reverse proxy. The entrypoint runs
# migrate + collectstatic first. Local dev overrides both in docker-compose.yml
# to keep runserver's hot-reload. --timeout 120 accommodates large file uploads.
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "openpcb.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
