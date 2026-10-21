import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.permissions import permissions_for_role
from app.core.roles import USER_STATUSES
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.user import User


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


class AuthenticationHttpTests(unittest.TestCase):
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

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def _login(self, username: str, password: str):
        return self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
        )

    def _headers_for(self, user_id: int = 1) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def _assert_bearer_unauthorized(self, response):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_login_success_uses_a_form_encoded_body(self):
        response = self._login("ADMIN", "current-password")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"access_token", "token_type", "expires_in"})
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertEqual(
            response.json()["expires_in"],
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        self.assertEqual(response.json()["access_token"].count("."), 2)

    def test_login_failures_have_the_same_status_and_body(self):
        wrong_password = self._login("Admin", "wrong-password")
        unknown_username = self._login("unknown-user", "wrong-password")
        inactive_user = self._login("Inactive", "current-password")

        for response in (wrong_password, unknown_username, inactive_user):
            self.assertEqual(response.status_code, 401)

        self.assertEqual(unknown_username.status_code, wrong_password.status_code)
        self.assertEqual(inactive_user.status_code, wrong_password.status_code)
        self.assertEqual(unknown_username.json(), wrong_password.json())
        self.assertEqual(inactive_user.json(), wrong_password.json())

    def test_locked_login_has_the_same_response_as_other_login_failures(self):
        self.active_user.failed_login_count = settings.FAILED_LOGIN_ATTEMPT_THRESHOLD
        self.active_user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )

        locked_user = self._login("Admin", "current-password")
        unknown_user = self._login("unknown-user", "wrong-password")

        self.assertEqual(locked_user.status_code, 401)
        self.assertEqual(locked_user.json(), unknown_user.json())
        self.assertEqual(self.db.commit_count, 0)

    def test_get_me_with_a_valid_token_returns_no_password_hash(self):
        response = self.client.get("/auth/me", headers=self._headers_for())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password_hash", response.json())
        self.assertEqual(
            response.json(),
            {
                "user_id": 1,
                "username": "Admin",
                "full_name": "Active Administrator",
                "role": "ADMIN",
                "status": "ACTIVE",
                "permissions": permissions_for_role("ADMIN"),
            },
        )

    def test_get_me_without_a_token_is_unauthorized(self):
        response = self.client.get("/auth/me")

        self._assert_bearer_unauthorized(response)

    def test_get_me_with_a_malformed_token_is_unauthorized(self):
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-token"},
        )

        self._assert_bearer_unauthorized(response)

    def test_get_me_with_an_expired_token_is_unauthorized(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "1",
                "iat": now - timedelta(minutes=2),
                "exp": now - timedelta(minutes=1),
                "token_version": 0,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self._assert_bearer_unauthorized(response)

    def test_get_me_with_a_token_signed_by_a_different_key_is_unauthorized(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "1",
                "iat": now,
                "exp": now + timedelta(minutes=1),
                "token_version": 0,
            },
            "different-test-jwt-secret-key-that-is-long-enough",
            algorithm=settings.ALGORITHM,
        )

        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self._assert_bearer_unauthorized(response)

    def test_get_me_with_a_non_numeric_subject_is_unauthorized_not_an_error(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "not-a-user-id",
                "iat": now,
                "exp": now + timedelta(minutes=1),
                "token_version": 0,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self._assert_bearer_unauthorized(response)

    def test_get_me_with_a_missing_user_is_unauthorized(self):
        response = self.client.get("/auth/me", headers=self._headers_for(user_id=99))

        self._assert_bearer_unauthorized(response)

    def test_get_me_rejects_a_user_deactivated_after_token_issue(self):
        token = create_access_token(self.active_user.user_id)
        self.active_user.status = USER_STATUSES[1]

        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self._assert_bearer_unauthorized(response)

    def test_change_password_success_invalidates_the_old_password(self):
        headers = self._headers_for()
        response = self.client.post(
            "/auth/change-password",
            headers=headers,
            json={
                "current_password": "current-password",
                "new_password": "changed-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Password changed successfully."})
        self.assertEqual(self._login("Admin", "current-password").status_code, 401)
        self.assertEqual(self._login("Admin", "changed-password").status_code, 200)
        self._assert_bearer_unauthorized(
            self.client.get("/auth/me", headers=headers)
        )

    def test_change_password_with_a_wrong_current_password_returns_bad_request(self):
        response = self.client.post(
            "/auth/change-password",
            headers=self._headers_for(),
            json={
                "current_password": "wrong-password",
                "new_password": "changed-password",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_change_password_rejects_an_equal_or_short_new_password(self):
        cases = (
            ("current-password", "current-password"),
            ("current-password", "too-short"),
        )

        for current_password, new_password in cases:
            with self.subTest(new_password=new_password):
                response = self.client.post(
                    "/auth/change-password",
                    headers=self._headers_for(),
                    json={
                        "current_password": current_password,
                        "new_password": new_password,
                    },
                )

                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
