import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

import jwt
from fastapi import HTTPException

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.permissions import permissions_for_role
from app.core.roles import USER_STATUSES
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.routers.auth import change_password, get_me, login
from app.schemas.auth import ChangePasswordRequest, CurrentUserResponse


class FakeResult:
    def __init__(self, user: User | None):
        self.user = user

    def scalar_one_or_none(self) -> User | None:
        return self.user


class FakeSession:
    def __init__(self, users: list[User]):
        self.users = {user.user_id: user for user in users}
        self.commit_count = 0
        self.rollback_count = 0

    def execute(self, statement):
        username = next(iter(statement.compile().params.values()))
        user = next(
            (
                candidate
                for candidate in self.users.values()
                if candidate.username.lower() == username
            ),
            None,
        )
        return FakeResult(user)

    def get(self, model, user_id: int) -> User | None:
        return self.users.get(user_id)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        pass


class AuthenticationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.active_user = User(
            user_id=1,
            username="Admin",
            full_name="Active Administrator",
            password_hash=hash_password("current-password"),
            role="ADMIN",
            status=USER_STATUSES[0],
            failed_login_count=0,
            locked_until=None,
        )
        self.inactive_user = User(
            user_id=2,
            username="Inactive",
            full_name="Inactive User",
            password_hash=hash_password("current-password"),
            role="VIEWER",
            status=USER_STATUSES[1],
            failed_login_count=0,
            locked_until=None,
        )
        self.db = FakeSession([self.active_user, self.inactive_user])

    def _login(self, username: str, password: str):
        return login(
            SimpleNamespace(username=username, password=password),
            self.db,
        )

    def _login_error(self, username: str, password: str) -> HTTPException:
        with self.assertRaises(HTTPException) as context:
            self._login(username, password)
        return context.exception

    def test_login_success_sets_last_login_and_returns_bearer_token(self):
        response = self._login("ADMIN", "current-password")

        self.assertEqual(response["token_type"], "bearer")
        self.assertEqual(
            response["expires_in"],
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        self.assertEqual(
            response["access_token"].count("."),
            2,
        )
        self.assertIsNotNone(self.active_user.last_login_at)
        self.assertEqual(self.db.commit_count, 1)

    def test_failed_login_threshold_locks_an_active_user(self):
        for attempt in range(1, settings.FAILED_LOGIN_ATTEMPT_THRESHOLD + 1):
            error = self._login_error("Admin", "wrong-password")

            self.assertEqual(error.status_code, 401)
            self.assertEqual(error.detail, "Incorrect username or password.")
            self.assertEqual(self.active_user.failed_login_count, attempt)
            if attempt < settings.FAILED_LOGIN_ATTEMPT_THRESHOLD:
                self.assertIsNone(self.active_user.locked_until)

        self.assertIsNotNone(self.active_user.locked_until)
        self.assertGreater(self.active_user.locked_until, datetime.now(timezone.utc))
        self.assertEqual(
            self.db.commit_count,
            settings.FAILED_LOGIN_ATTEMPT_THRESHOLD,
        )

    def test_locked_account_rejects_a_correct_password_generically(self):
        self.active_user.failed_login_count = settings.FAILED_LOGIN_ATTEMPT_THRESHOLD
        self.active_user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )

        error = self._login_error("Admin", "current-password")

        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Incorrect username or password.")
        self.assertEqual(
            self.active_user.failed_login_count,
            settings.FAILED_LOGIN_ATTEMPT_THRESHOLD,
        )
        self.assertEqual(self.db.commit_count, 0)

    def test_expired_lock_allows_successful_login_and_resets_state(self):
        self.active_user.failed_login_count = settings.FAILED_LOGIN_ATTEMPT_THRESHOLD
        self.active_user.locked_until = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )

        response = self._login("Admin", "current-password")

        self.assertEqual(response["token_type"], "bearer")
        self.assertEqual(self.active_user.failed_login_count, 0)
        self.assertIsNone(self.active_user.locked_until)
        self.assertEqual(self.db.commit_count, 1)

    def test_successful_login_resets_prior_failed_attempts(self):
        self.active_user.failed_login_count = 2
        self.active_user.locked_until = None

        self._login("Admin", "current-password")

        self.assertEqual(self.active_user.failed_login_count, 0)
        self.assertIsNone(self.active_user.locked_until)
        self.assertEqual(self.db.commit_count, 1)

    def test_unknown_username_response_matches_wrong_password_response(self):
        wrong_password_error = self._login_error("Admin", "wrong-password")
        unknown_username_error = self._login_error("unknown-user", "wrong-password")

        self.assertEqual(
            unknown_username_error.status_code,
            wrong_password_error.status_code,
        )
        self.assertEqual(
            unknown_username_error.detail,
            wrong_password_error.detail,
        )
        self.assertEqual(
            wrong_password_error.status_code,
            401,
        )
        self.assertEqual(
            wrong_password_error.detail,
            "Incorrect username or password.",
        )
        self.assertEqual(self.active_user.failed_login_count, 1)
        self.assertEqual(self.db.commit_count, 1)

    def test_inactive_user_response_matches_wrong_password_response(self):
        wrong_password_error = self._login_error("Admin", "wrong-password")
        inactive_user_error = self._login_error("Inactive", "current-password")

        self.assertEqual(inactive_user_error.status_code, 401)
        self.assertEqual(inactive_user_error.detail, wrong_password_error.detail)
        self.assertEqual(self.inactive_user.failed_login_count, 0)
        self.assertIsNone(self.inactive_user.locked_until)

    def test_unknown_user_does_not_change_known_user_lockout_state(self):
        error = self._login_error("unknown-user", "wrong-password")

        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Incorrect username or password.")
        self.assertEqual(self.active_user.failed_login_count, 0)
        self.assertIsNone(self.active_user.locked_until)
        self.assertEqual(self.db.commit_count, 0)

    def test_get_me_with_a_valid_token_returns_only_current_user_fields(self):
        current_user = get_current_user(
            token=create_access_token(1),
            db=self.db,
        )
        response = CurrentUserResponse.model_validate(get_me(current_user)).model_dump()

        self.assertEqual(
            response,
            {
                "user_id": 1,
                "username": "Admin",
                "full_name": "Active Administrator",
                "role": "ADMIN",
                "status": "ACTIVE",
                "permissions": permissions_for_role("ADMIN"),
            },
        )

    def test_get_me_without_a_token_is_rejected_with_a_bearer_challenge(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(token=None, db=self.db)
        error = context.exception

        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.headers, {"WWW-Authenticate": "Bearer"})
        self.assertEqual(
            error.detail,
            "Authentication is required. Please sign in.",
        )

    def test_get_me_with_an_expired_token_is_rejected(self):
        now = datetime.now(timezone.utc)
        expired_token = jwt.encode(
            {
                "sub": "1",
                "iat": now - timedelta(minutes=2),
                "exp": now - timedelta(minutes=1),
                "token_version": 0,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        with self.assertRaises(HTTPException) as context:
            get_current_user(token=expired_token, db=self.db)
        error = context.exception

        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.headers, {"WWW-Authenticate": "Bearer"})
        self.assertEqual(
            error.detail,
            "Your session has expired. Please sign in again.",
        )

    def test_get_me_rejects_missing_or_inactive_users(self):
        for user_id in (99, 2):
            with self.subTest(user_id=user_id):
                with self.assertRaises(HTTPException) as context:
                    get_current_user(token=create_access_token(user_id), db=self.db)
                error = context.exception

                self.assertEqual(error.status_code, 401)
                self.assertEqual(
                    error.detail,
                    "Your session is no longer active. Please sign in again.",
                )

    def test_change_password_success(self):
        response = change_password(
            ChangePasswordRequest(
                current_password="current-password",
                new_password="new-secure-password",
            ),
            self.active_user,
            self.db,
        )

        self.assertEqual(response, {"message": "Password changed successfully."})
        self.assertTrue(
            verify_password("new-secure-password", self.active_user.password_hash)
        )
        self.assertFalse(verify_password("current-password", self.active_user.password_hash))
        self.assertEqual(self.active_user.token_version, 1)
        self.assertEqual(self.db.commit_count, 1)

    def test_change_password_rejects_each_invalid_request(self):
        cases = (
            (
                {"current_password": "wrong-password", "new_password": "new-password"},
                "Current password is incorrect.",
            ),
            (
                {
                    "current_password": "current-password",
                    "new_password": "current-password",
                },
                "New password must differ from the current password.",
            ),
            (
                {"current_password": "current-password", "new_password": "too-short"},
                "New password must be at least 10 characters long.",
            ),
            (
                {"current_password": "", "new_password": "new-password"},
                "Current password is required.",
            ),
        )

        for data, detail in cases:
            with self.subTest(detail=detail):
                with self.assertRaises(HTTPException) as context:
                    change_password(
                        ChangePasswordRequest(**data),
                        self.active_user,
                        self.db,
                    )
                error = context.exception

                self.assertEqual(error.status_code, 400)
                self.assertEqual(error.detail, detail)

        self.assertEqual(self.db.commit_count, 0)


if __name__ == "__main__":
    unittest.main()
