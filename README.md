# URL Shortener API

A small URL-shortening service built with **FastAPI**, **SQLAlchemy 2.0** and **SQLite**.
Supports custom aliases, optional expiry, redirects and click analytics.

## Features
- Create short links with auto-generated or custom codes
- Optional expiry (`410 Gone` after expiry)
- Redirect with `404` for unknown codes
- Click analytics: total clicks and last-clicked timestamp
- Consistent, documented error bodies and input validation
- Health endpoint for deployments
- 41 automated tests, ~97% branch coverage

## Setup

Requires **Python 3.11+**.

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
| `BASE_URL` | `http://localhost:8000` | Used to build `short_url` and to reject self-referential links |
| `CODE_LENGTH` | `7` | Length of generated codes (4-32) |

## API Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| POST | `/links` | Create a short link | `201` | `409` alias taken, `422` invalid input |
| GET | `/{code}` | Redirect to the original URL | `302` | `404` unknown, `410` expired |
| GET | `/links/{code}/stats` | Click statistics | `200` | `404` unknown |
| GET | `/health` | Readiness probe (pings the DB) | `200` | — |

### POST /links
Body:
```json
{
  "url": "https://example.com/some/long/path",
  "custom_alias": "my-link",
  "expires_at": "2026-12-31T23:59:59Z"
}
```
`custom_alias` and `expires_at` are optional. Aliases: 3-32 chars of letters, digits, `-`, `_`,
**case-sensitive**. `expires_at` must be in the future (naive timestamps are treated as UTC).
Unknown fields are rejected, so a typo like `custom_alais` fails with `422` instead of silently
creating a different link.

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
Statistics remain readable after a link expires.
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
Every error returns a human-readable `detail` string:

```json
{"detail": "Alias 'my-link' is already taken. Please choose a different alias."}
```

Validation failures (`422`) additionally include a machine-readable `errors` array:

```json
{
  "detail": "url: Input should be a valid URL, relative URL without a base",
  "errors": [{"type": "url_parsing", "loc": ["body", "url"], "msg": "..."}]
}
```

### Status code rationale
- `404` — the code was never issued
- `410` — the code existed but has expired (clients can distinguish the two)
- `409` — the requested custom alias is taken; retrying with the same alias will not help
- `422` — the request itself is invalid (bad URL, alias, or expiry)

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

# Health
curl http://localhost:8000/health
```

## Running the tests

```bash
pytest -v
pytest --cov=app --cov-report=term-missing   # 41 tests, ~97% branch coverage
```

Tests use an isolated in-memory SQLite database and never touch `shortener.db`.
The concurrency test uses a temporary file-backed database, because several
connections must write at once.

Linting and type checking:

```bash
ruff check .
ruff format --check .
mypy app
```

## Requirement traceability

| Requirement | Covered by |
|---|---|
| Create link with generated code | `test_create_link_returns_generated_code` |
| Custom alias used as code | `test_custom_alias_is_used_as_code`, `test_valid_alias_boundaries_are_accepted` |
| Invalid URLs rejected | `test_invalid_urls_are_rejected`, `test_too_long_url_is_rejected` |
| Duplicate alias → helpful `409` | `test_duplicate_alias_returns_409_with_helpful_message`, `test_409_body_matches_documented_shape` |
| Redirect → `302` | `test_redirect_returns_302_to_original_url` |
| Unknown code → `404` | `test_unknown_code_returns_404`, `test_404_body_matches_documented_shape` |
| Expired link → `410` | `test_expired_link_returns_410_and_is_not_counted`, `test_410_body_matches_documented_shape` |
| Click counting + last click | `test_clicks_are_counted_and_last_click_recorded`, `test_concurrent_redirects_count_every_click` |
| Stats endpoint | `test_stats_for_unknown_code_returns_404`, `test_timestamps_are_utc_and_monotonic` |
| Validation/error contract | `test_422_detail_is_a_human_readable_string`, `test_unknown_fields_are_rejected` |
| Health probe | `test_health_endpoint` |
| Startup creates schema | `test_lifespan_creates_schema` |

## Design decisions
- **Random base62 codes (7 chars, `secrets`)**: unguessable, ~3.5 trillion combinations. Uniqueness is enforced by a DB `UNIQUE` constraint; collisions on generated codes are retried up to 5 times.
- **302 redirects, not 301**: browsers cache 301s permanently, which would bypass click counting and expiry. Responses also send `Cache-Control: no-store` so proxies don't cache them either.
- **410 for expired, 404 for unknown**: lets clients distinguish "never existed" from "existed, now gone".
- **Atomic click counting** (`SET clicks = clicks + 1`) avoids lost updates under concurrent requests; a test drives 20 parallel redirects to prove it.
- **Layered structure**: routers (HTTP) → services (business rules) → models (DB); domain exceptions own their HTTP status and are mapped in one handler.
- **Schemas never import models**: response serialisation goes through a structural `Protocol`, keeping the Pydantic layer independent of SQLAlchemy.
- **Only `http`/`https` URLs accepted**, blocking `javascript:` and similar schemes. URLs pointing back at this service are rejected to prevent redirect loops.
- **One limits module** (`app/constants.py`) shared by validation and column definitions, so they cannot drift.
- All timestamps are stored as naive UTC and emitted with an explicit `Z`.

## Known limitations / possible next steps
- Schema is created with `create_all`; a production deployment would use Alembic migrations.
- No rate limiting or authentication: anyone can create links and read any link's stats.
- Clicks are a single counter; a per-click event table would enable richer analytics.
- Aliases are case-sensitive, so `Promo` and `promo` are distinct links (documented above).
- No abuse protection (Safe Browsing checks, domain blocklists); a public deployment needs it.

## Project structure
```
app/
  main.py          # app setup, exception handlers, /health
  config.py        # environment-based settings
  constants.py     # shared size limits and reserved aliases
  database.py      # engine, session, get_db dependency
  models.py        # Link table
  schemas.py       # request/response models and validation
  clock.py         # UTC helpers
  codegen.py       # short-code generation
  exceptions.py    # domain errors with HTTP status/message
  services.py      # business logic
  routers/         # HTTP endpoints
tests/             # pytest suite
```
