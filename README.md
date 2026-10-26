# URL Shortener API

A small URL-shortening service built with **FastAPI**, **SQLAlchemy 2.0** and **SQLite**.
Supports custom aliases, optional expiry, redirects and click analytics.

## Features
- Create short links with auto-generated or custom codes
- Optional expiry (`410 Gone` after expiry)
- Redirect with `404` for unknown codes
- Click analytics: total clicks and last-clicked timestamp
- Input validation and clear error messages
- Automated tests with pytest

## Setup

```bash
git clone <your-repo-url>
cd url-shortener
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # optional; defaults work out of the box
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./shortener.db` | Any SQLAlchemy URL (e.g. Postgres) |
| `BASE_URL` | `http://localhost:8000` | Used to build `short_url` |
| `CODE_LENGTH` | `7` | Length of generated codes |

## API Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| POST | `/links` | Create a short link | `201` | `409` alias taken, `422` invalid input |
| GET | `/{code}` | Redirect to the original URL | `302` | `404` unknown, `410` expired |
| GET | `/links/{code}/stats` | Click statistics | `200` | `404` unknown |

### POST /links
Body:
```json
{
  "url": "https://example.com/some/long/path",
  "custom_alias": "my-link",
  "expires_at": "2026-12-31T23:59:59Z"
}
```
`custom_alias` and `expires_at` are optional. Aliases: 3-32 chars of letters, digits, `-`, `_`.
`expires_at` must be in the future (naive timestamps are treated as UTC).

Response `201`:
```json
{
  "code": "my-link",
  "short_url": "http://localhost:8000/my-link",
  "original_url": "https://example.com/some/long/path",
  "created_at": "2026-10-26T10:15:30.123456Z",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### GET /links/{code}/stats
```json
{
  "code": "my-link",
  "original_url": "https://example.com/some/long/path",
  "total_clicks": 3,
  "last_clicked_at": "2026-10-26T10:20:00.456789Z",
  "created_at": "2026-10-26T10:15:30.123456Z",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Error format
All errors return `{"detail": "<human-readable message>"}`, for example:
`{"detail": "Alias 'my-link' is already taken. Please choose a different alias."}`

## Example requests

```bash
# Create with an auto-generated code
curl -X POST http://localhost:8000/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/some/long/path"}'

# Create with a custom alias and expiry
curl -X POST http://localhost:8000/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/docs", "custom_alias": "my-link", "expires_at": "2026-12-31T23:59:59Z"}'

# Duplicate alias -> 409
curl -i -X POST http://localhost:8000/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.org/other", "custom_alias": "my-link"}'

# Follow the redirect (-i shows the 302 and Location header)
curl -i http://localhost:8000/my-link

# Unknown code -> 404
curl -i http://localhost:8000/doesnotexist

# Stats
curl http://localhost:8000/links/my-link/stats
```

## Running the tests

```bash
pytest -v
```
Tests use an isolated in-memory SQLite database and never touch `shortener.db`.

## Design decisions
- **Random base62 codes (7 chars, `secrets`)**: unguessable, ~3.5 trillion combinations. Uniqueness is enforced by a DB `UNIQUE` constraint; collisions on generated codes are retried.
- **302 redirects, not 301**: browsers cache 301s permanently, which would bypass click counting and expiry.
- **410 for expired, 404 for unknown**: lets clients distinguish "never existed" from "existed, now gone".
- **Atomic click counting** (`SET clicks = clicks + 1`) avoids lost updates under concurrent requests.
- **Layered structure**: routers (HTTP) → services (business rules) → models (DB); domain exceptions are mapped to HTTP responses in one place.
- **Only `http`/`https` URLs accepted**, blocking `javascript:` and similar schemes.
- All timestamps are stored and compared in UTC.

## Known limitations / possible next steps
- Schema is created with `create_all`; a production deployment would use Alembic migrations.
- No rate limiting or authentication.
- Clicks are a single counter; a per-click event table would enable richer analytics.
- Shortening URLs that point back at this service is not blocked.

## Project structure
```
app/
  main.py          # app setup and exception handlers
  config.py        # environment-based settings
  database.py      # engine, session, get_db dependency
  models.py        # Link table
  schemas.py       # request/response models and validation
  codegen.py       # short-code generation
  services.py      # business logic
  routers/         # HTTP endpoints
tests/             # pytest suite
```