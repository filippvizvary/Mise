"""Authentication logic for Mise – register, login, logout, whoami.

Auth state is stored locally in ~/.mise/auth as a JSON file containing
the current user's ID and username. This is CLI-only auth (no JWT yet;
JWT will be added when the web API is built in Phase 7).
"""

import json
import os
from typing import NamedTuple, Optional

import bcrypt

from mise.config import AUTH_FILE
from mise.db.database import SessionLocal
from mise.db.crud import create_user, get_user_by_username, get_user_by_email
from mise.db.models import User


class RegisterResult(NamedTuple):
    """Result of a registration attempt."""
    user: User
    verification_code: Optional[str] = None


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _read_auth_file() -> Optional[dict]:
    """Read the auth file. Returns None if it doesn't exist or is invalid."""
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _write_auth_file(data: dict) -> None:
    """Write auth data to the auth file."""
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f)


def _delete_auth_file() -> None:
    """Delete the auth file (logout)."""
    try:
        os.remove(AUTH_FILE)
    except FileNotFoundError:
        pass


def register(username: str, email: str, password: str) -> RegisterResult:
    """Register a new user.

    Returns a RegisterResult containing the user and optionally a verification code.
    Raises ValueError if username or email is already taken.
    If email verification is required, sends a verification code.
    """
    session = SessionLocal()
    try:
        # Check if username is taken
        existing = get_user_by_username(session, username)
        if existing:
            raise ValueError(f"Username '{username}' is already taken.")

        # Check if email is taken
        existing = get_user_by_email(session, email)
        if existing:
            raise ValueError(f"Email '{email}' is already registered.")

        # Create user with hashed password
        password_hash = _hash_password(password)
        user = create_user(session, username=username, email=email, password_hash=password_hash)

        # Send verification email if required
        verification_code = None
        from mise.email.verification import create_verification_code, is_verification_required
        if is_verification_required():
            verification_code = create_verification_code(user.id, user.email, user.username)
            # In development mode (no SMTP), the code is printed to console
            # In production, it's sent via email

        return RegisterResult(user=user, verification_code=verification_code)
    finally:
        session.close()


def login(username: str, password: str) -> User:
    """Log in a user.

    Returns the User object if credentials are valid.
    Raises ValueError if credentials are invalid.
    Also saves auth state to ~/.mise/auth.
    """
    session = SessionLocal()
    try:
        user = get_user_by_username(session, username)
        if user is None:
            raise ValueError(f"User '{username}' not found.")

        if not _verify_password(password, user.password_hash):
            raise ValueError("Invalid password.")

        # Save auth state
        _write_auth_file({
            "user_id": user.id,
            "username": user.username,
        })

        return user
    finally:
        session.close()


def logout() -> None:
    """Log out the current user by deleting the auth file."""
    _delete_auth_file()


def get_current_user() -> Optional[User]:
    """Get the currently logged-in user from the auth file.

    Returns None if no user is logged in.
    """
    auth_data = _read_auth_file()
    if auth_data is None:
        return None

    user_id = auth_data.get("user_id")
    if user_id is None:
        # Auth file is corrupt — remove it and require re-login
        _delete_auth_file()
        return None

    session = SessionLocal()
    try:
        from mise.db.crud import get_user_by_id
        user = get_user_by_id(session, user_id)
        return user
    finally:
        session.close()


def require_current_user() -> User:
    """Get the currently logged-in user, raising an error if not logged in.

    Raises RuntimeError if no user is logged in.
    """
    user = get_current_user()
    if user is None:
        raise RuntimeError(
            "No user logged in. Run 'mise auth login' first."
        )
    return user