#!/usr/bin/env sh
# Run every quality check used by CI, in the same order, so local runs and CI
# can never silently diverge. Run inside the app container, e.g.:
#
#   docker compose exec web-dev sh scripts/check.sh   (dev profile)
#   docker compose exec web sh scripts/check.sh       (prod profile)
set -e

echo '==> ruff check'
uv run ruff check .

echo '==> ruff format --check'
uv run ruff format --check .

echo '==> manage.py check'
uv run python manage.py check

echo '==> manage.py test'
uv run python manage.py test
