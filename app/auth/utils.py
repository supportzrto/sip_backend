import hashlib


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token before storing it.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()