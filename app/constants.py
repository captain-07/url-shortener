"""Single source of truth for size limits and reserved names.

Both the SQLAlchemy columns (`app/models.py`) and the Pydantic schemas
(`app/schemas.py`) import these values, so validation rules can never drift
away from the database schema.
"""

MAX_URL_LENGTH = 2048
MIN_ALIAS_LENGTH = 3
MAX_ALIAS_LENGTH = 32

DEFAULT_CODE_LENGTH = 7
CODE_COLUMN_LENGTH = 32

# Paths this service serves itself. A custom alias with one of these names
# would be shadowed by a real route, so they are rejected at creation time.
RESERVED_ALIASES = frozenset({"links", "docs", "redoc", "openapi.json", "health"})
