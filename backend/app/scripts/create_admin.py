import getpass
import sys

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.roles import ROLES, USER_STATUSES
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User


def _validate_username(username: str) -> str | None:
    if not username:
        return "Username is required."
    if len(username) > 50:
        return "Username must be 50 characters or fewer."
    return None


def _validate_full_name(full_name: str) -> str | None:
    if not full_name:
        return "Full name is required."
    if len(full_name) > 100:
        return "Full name must be 100 characters or fewer."
    return None


def _username_exists(username: str) -> bool:
    db = SessionLocal()
    try:
        return db.execute(
            select(User.user_id).where(
                func.lower(User.username) == username.lower()
            )
        ).scalar_one_or_none() is not None
    finally:
        db.close()


def main() -> int:
    try:
        username = input("Username: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("Admin creation cancelled.")
        return 1

    username_error = _validate_username(username)
    if username_error:
        print(username_error)
        return 1

    try:
        if _username_exists(username):
            print("A user with that username already exists.")
            return 1
    except SQLAlchemyError:
        print("Unable to check whether that username already exists.")
        return 1

    try:
        full_name = input("Full name: ").strip()
        password = getpass.getpass("Password: ")
        password_confirmation = getpass.getpass("Confirm password: ")
    except (EOFError, KeyboardInterrupt):
        print("Admin creation cancelled.")
        return 1

    full_name_error = _validate_full_name(full_name)
    if full_name_error:
        print(full_name_error)
        return 1

    if len(password) < 10:
        print("Password must be at least 10 characters long.")
        return 1

    if password != password_confirmation:
        print("Passwords do not match.")
        return 1

    db = SessionLocal()
    try:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=hash_password(password),
            role=ROLES[0],
            status=USER_STATUSES[0],
        )
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        print("A user with that username already exists.")
        return 1
    except SQLAlchemyError:
        db.rollback()
        print("Unable to create the admin user.")
        return 1
    finally:
        db.close()

    print(f"Admin user '{username}' created successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
