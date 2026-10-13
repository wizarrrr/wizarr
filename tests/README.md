# Wizarr tests

## Run the tests

```bash
uv sync --dev
uv run pytest                     # all tests, including e2e
uv run pytest --ignore=tests/e2e  # without the browser tests
```

The e2e tests in `tests/e2e/` use Playwright. They need the built static
assets (`npm --prefix app/static ci && npm --prefix app/static run build`)
and `uv run playwright install`.

## Database

`tests/conftest.py` makes one SQLite file per test process and runs the
Alembic migrations on it, so the schema is the same as in production.

## Shared fixtures (`tests/conftest.py`)

- `app`, `client`: the Flask app and its test client.
- `session`: a database session. All tables are empty before and after the test.
- `admin_user`: an admin account (`testadmin` / `TestPass123`).
- `admin_client`: a test client with a logged-in admin session.
- `clear_media_caches`: clears the image proxy and Plex caches before and after the test.
