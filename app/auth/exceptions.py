class AuthError(Exception):
    """
    Base authentication exception.
    """


class EmailAlreadyExistsError(AuthError):
    """
    Raised when an email is already registered.
    """

class InvalidCredentialsError(AuthError):
    """
    Raised when email or password is invalid.
    """


class InvalidTokenError(AuthError):
    """
    Raised when JWT is invalid.
    """


class ExpiredTokenError(AuthError):
    """
    Raised when JWT has expired.
    """

class InvalidRefreshTokenError(AuthError):
    """
    Raised when a refresh token is invalid,
    expired, or revoked.
    """

class PermissionDeniedError(AuthError):
    """
    Raised when a user does not have permission
    to access a resource.
    """

class InvalidCurrentPasswordError(AuthError):
    """
    Raised when the supplied current password is incorrect.
    """
class AccountDisabledError(AuthError):
    """
    Raised when a user account is not active.
    """

class RateLimitExceededError(AuthError):
    """
    Raised when too many attempts (e.g. logins) have been made for
    a given key within the block window.
    """