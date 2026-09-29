"""
Create (or promote) an admin user.

There is intentionally no public API endpoint for this -- letting
people self-register as admin would be a security hole. Run this
script directly against your database instead, once, to bootstrap
your first admin account.

Usage:
    python -m app.commands.create_admin --email admin@example.com --password "SomeStrongPassword123!" --name "Admin"

If a user with that email already exists, they are promoted to
admin (and activated) instead of creating a duplicate account.
"""

import argparse
import sys

from sqlalchemy.orm import Session

from app.auth.constants import UserRole, UserStatus
from app.auth.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User


def create_or_promote_admin(
    session: Session,
    *,
    email: str,
    password: str | None,
    full_name: str,
) -> User:

    user = (
        session.query(User)
        .filter(User.email == email)
        .one_or_none()
    )

    if user is not None:

        user.role = UserRole.ADMIN.value
        user.status = UserStatus.ACTIVE.value

        if password:
            user.password_hash = hash_password(password)

        session.commit()
        session.refresh(user)

        return user

    if not password:
        raise ValueError(
            "A password is required to create a new admin user."
        )

    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        is_verified=True,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Create or promote an admin user.",
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--password",
        required=False,
        help="Required when creating a new user. Optional when "
             "promoting an existing user (leave unset to keep their "
             "current password).",
    )
    parser.add_argument(
        "--name",
        default="Admin",
        help="Full name, used only when creating a new user.",
    )

    args = parser.parse_args()

    session = SessionLocal()

    try:
        user = create_or_promote_admin(
            session,
            email=args.email,
            password=args.password,
            full_name=args.name,
        )

        print(f"OK: {user.email} is now an admin (user id {user.id}).")

    except Exception as exc:
        session.rollback()
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()