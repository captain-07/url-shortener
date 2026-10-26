import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # base62


def generate_code(length: int = 7) -> str:
    # `secrets` is cryptographically secure; `random` is predictable,
    # which would let someone guess other users' links.
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
