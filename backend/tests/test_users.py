import os
import unittest
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.roles import ROLES, USER_STATUSES
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.main import app
from app.models.user import User
from app.routers.users import update_user
from app.schemas.user import UserUpdate


class FakeResult:
    def __init__(self, value=None, items=None):
        self.value = value
        self.items = items if items is not None else []

    def scalars(self):
        return self

    def all(self):
        return self.items

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, users: list[User]):
        self.users = {user.user_id: user for user in users}
        self.commit_count = 0
        self.rollback_count = 0

    def execute(self, statement):
        params = statement.compile().params
        if any(key.startswith("lower") for key in params):
            username = next(iter(params.values()))
            user = next(
                (
                    candidate
                    for candidate in self.users.values()
                    if candidate.username.lower() == username.lower()
                ),
                None,
            )
            return FakeResult(value=user)

        return FakeResult(items=list(self.users.values()))

    def get(self, model, user_id: int):
        if model is User:
            return self.users.get(user_id)
        return None

    def scalar(self, statement):
        return sum(
            user.role == ROLES[0] and user.status == USER_STATUSES[0]
            for user in self.users.values()
        )

    def add(self, user: User):
        user.user_id = max(self.users, default=0) + 1
        user.created_at = datetime.now(timezone.utc)
        self.users[user.user_id] = user

    def refresh(self, user: User):
        pass

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        pass


def make_user(
    user_id: int,
    username: str,
    full_name: str,
    password: str,
    role: str,
    user_status: str = USER_STATUSES[0],
) -> User:
    return User(
        user_id=user_id,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        status=user_status,
        created_at=datetime.now(timezone.utc),
    )


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.current_user = make_user(
            1,
            "Admin",
            "Active Administrator",
            "current-password",
            ROLES[0],
        )
        self.target_user = make_user(
            2,
            "Target",
            "Target User",
            "target-password",
            ROLES[-1],
        )
        self.db = FakeSession([self.current_user, self.target_user])

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def _headers(self):
        return {
            "Authorization": f"Bearer {create_access_token(self.current_user.user_id)}"
        }

    def _create_payload(self, **overrides):
        payload = {
            "username": "NewUser",
            "full_name": "New User",
            "role": ROLES[-1],
            "initial_password": "new-user-password",
        }
        payload.update(overrides)
        return payload

    def test_list_create_and_update_never_return_password_hashes(self):
        listed = self.client.get("/users", headers=self._headers())
        created = self.client.post(
            "/users",
            headers=self._headers(),
            json=self._create_payload(),
        )
        updated = self.client.patch(
            "/users/2",
            headers=self._headers(),
            json={
                "full_name": "Updated Target",
                "role": ROLES[1],
                "status": USER_STATUSES[1],
            },
        )

        for response in (listed, created, updated):
            self.assertIn(response.status_code, (200, 201))
            self.assertNotIn("password_hash", str(response.json()))

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["status"], USER_STATUSES[0])
        self.assertEqual(self.target_user.full_name, "Updated Target")
        self.assertEqual(self.target_user.role, ROLES[1])
        self.assertEqual(self.target_user.status, USER_STATUSES[1])

    def test_username_is_case_insensitively_unique_and_immutable(self):
        duplicate = self.client.post(
            "/users",
            headers=self._headers(),
            json=self._create_payload(username="admin"),
        )
        immutable = self.client.patch(
            "/users/2",
            headers=self._headers(),
            json={"username": "Changed"},
        )

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json(), {"detail": "That username is already in use."})
        self.assertEqual(immutable.status_code, 400)
        self.assertEqual(immutable.json(), {"detail": "Username cannot be changed."})
        self.assertEqual(self.target_user.username, "Target")

    def test_password_rules_apply_to_creation_and_reset(self):
        target_headers = {
            "Authorization": f"Bearer {create_access_token(self.target_user.user_id)}"
        }
        short_initial = self.client.post(
            "/users",
            headers=self._headers(),
            json=self._create_payload(initial_password="too-short"),
        )
        short_reset = self.client.post(
            "/users/2/reset-password",
            headers=self._headers(),
            json={"new_password": "too-short"},
        )
        repeated_reset = self.client.post(
            "/users/2/reset-password",
            headers=self._headers(),
            json={"new_password": "target-password"},
        )
        reset = self.client.post(
            "/users/2/reset-password",
            headers=self._headers(),
            json={"new_password": "replacement-password"},
        )

        self.assertEqual(short_initial.status_code, 400)
        self.assertEqual(short_reset.status_code, 400)
        self.assertEqual(repeated_reset.status_code, 400)
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json(), {"message": "Password reset successfully."})
        self.assertTrue(verify_password("replacement-password", self.target_user.password_hash))
        self.assertFalse(verify_password("target-password", self.target_user.password_hash))
        self.assertEqual(self.target_user.token_version, 1)
        self.assertEqual(
            self.client.get("/auth/me", headers=target_headers).status_code,
            401,
        )

    def test_an_admin_cannot_deactivate_or_demote_themselves(self):
        deactivate = self.client.patch(
            "/users/1",
            headers=self._headers(),
            json={"status": USER_STATUSES[1]},
        )
        demote = self.client.patch(
            "/users/1",
            headers=self._headers(),
            json={"role": ROLES[1]},
        )

        self.assertEqual(deactivate.status_code, 400)
        self.assertEqual(
            deactivate.json(),
            {"detail": "You cannot deactivate your own account."},
        )
        self.assertEqual(demote.status_code, 400)
        self.assertEqual(
            demote.json(),
            {"detail": "You cannot change your own administrator role."},
        )

    def test_the_last_active_admin_cannot_be_deactivated_or_demoted(self):
        last_admin = make_user(
            2,
            "LastAdmin",
            "Last Administrator",
            "last-admin-password",
            ROLES[0],
        )
        acting_admin = make_user(
            99,
            "ActingAdmin",
            "Acting Administrator",
            "acting-admin-password",
            ROLES[0],
        )
        db = FakeSession([last_admin])

        for data in (
            UserUpdate(status=USER_STATUSES[1]),
            UserUpdate(role=ROLES[1]),
        ):
            with self.subTest(data=data):
                with self.assertRaises(HTTPException) as context:
                    update_user(2, data, acting_admin, db)

                self.assertEqual(context.exception.status_code, 400)
                self.assertEqual(
                    context.exception.detail,
                    "The last active administrator cannot be deactivated or demoted.",
                )

    def test_non_admins_are_forbidden_from_every_user_management_endpoint(self):
        requests = (
            ("GET", "/users", {}),
            ("POST", "/users", {"json": self._create_payload()}),
            ("PATCH", "/users/2", {"json": {"full_name": "Changed"}}),
            (
                "POST",
                "/users/2/reset-password",
                {"json": {"new_password": "replacement-password"}},
            ),
        )

        for role in ROLES[1:]:
            self.current_user.role = role
            for method, path, options in requests:
                with self.subTest(role=role, method=method, path=path):
                    response = self.client.request(
                        method,
                        path,
                        headers=self._headers(),
                        **options,
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(
                        response.json(),
                        {"detail": "You don't have permission to do this."},
                    )


if __name__ == "__main__":
    unittest.main()
