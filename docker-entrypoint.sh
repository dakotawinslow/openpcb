#!/usr/bin/env sh
# Production entrypoint: prepare the app, then exec the container CMD (gunicorn).
# Local dev bypasses this entrypoint via the docker-compose override.
set -e

# Postgres may still be starting when the web container boots — retry migrate
# until the database accepts connections.
until uv run python manage.py migrate --noinput; do
  echo "Database unavailable, retrying migrate in 2s..."
  sleep 2
done

# gunicorn (unlike runserver) does not serve static files itself; WhiteNoise
# serves them from STATIC_ROOT, which must be populated here.
uv run python manage.py collectstatic --noinput

exec "$@"
