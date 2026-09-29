from pwdlib import PasswordHash
import secrets

password_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    """
    Hash a plain-text password.
    """
    return password_hasher.hash(password)
def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a plain-text password against a stored hash.
    """
    return password_hasher.verify(password, password_hash)

def generate_secure_token() -> str:
    return secrets.token_urlsafe(48)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)