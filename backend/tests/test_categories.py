import os
import unittest

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.roles import ROLES, USER_STATUSES
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.category import Category
from app.models.user import User


class FakeSession:
    def __init__(self, user: User, categories: list[Category] | None = None):
        self.user = user
        self.categories = categories or []
        self.pending_category: Category | None = None
        self.commit_count = 0
        self.rollback_count = 0

    def get(self, model, record_id: int):
        if model is User and record_id == self.user.user_id:
            return self.user
        return None

    def add(self, record):
        if isinstance(record, Category):
            self.pending_category = record

    def commit(self):
        if self.pending_category is not None:
            if any(
                category.category_name == self.pending_category.category_name
                for category in self.categories
            ):
                raise IntegrityError("INSERT", {}, Exception("duplicate category"))

            self.pending_category.category_id = max(
                (category.category_id for category in self.categories),
                default=0,
            ) + 1
            self.categories.append(self.pending_category)
            self.pending_category = None
        self.commit_count += 1

    def refresh(self, record):
        pass

    def rollback(self):
        self.pending_category = None
        self.rollback_count += 1

    def close(self):
        pass


class CategoryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.user = User(
            user_id=1,
            username="Admin",
            full_name="Active Administrator",
            password_hash=hash_password("current-password"),
            role="ADMIN",
            status=USER_STATUSES[0],
        )
        self.db = FakeSession(self.user)

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def _headers(self):
        return {"Authorization": f"Bearer {create_access_token(self.user.user_id)}"}

    def test_create_category_returns_the_list_item_shape(self):
        response = self.client.post(
            "/categories/",
            headers=self._headers(),
            json={"category_name": "Hardware", "status": "ACTIVE"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"category_id": 1, "category_name": "Hardware", "status": "ACTIVE"},
        )
        self.assertEqual(self.db.commit_count, 1)

    def test_create_category_validates_the_model_fields(self):
        cases = (
            {"category_name": ""},
            {"category_name": "x" * 101},
            {"category_name": "Hardware", "status": "ARCHIVED"},
        )

        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/categories/",
                    headers=self._headers(),
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

        self.assertEqual(self.db.commit_count, 0)

    def test_create_category_rejects_a_duplicate_name(self):
        self.db.categories.append(
            Category(
                category_id=1,
                category_name="Hardware",
                status="ACTIVE",
            )
        )

        response = self.client.post(
            "/categories/",
            headers=self._headers(),
            json={"category_name": "Hardware"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"detail": "A category with that name already exists."},
        )
        self.assertEqual(self.db.rollback_count, 1)

    def test_create_category_requires_categories_write_permission(self):
        unauthenticated = self.client.post(
            "/categories/",
            json={"category_name": "Hardware"},
        )
        self.assertEqual(unauthenticated.status_code, 401)

        for role in ("SALES", "ACCOUNTS", "VIEWER"):
            with self.subTest(role=role):
                self.user.role = role
                response = self.client.post(
                    "/categories/",
                    headers=self._headers(),
                    json={"category_name": "Hardware"},
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json(),
                    {"detail": "You don't have permission to do this."},
                )

        self.user.role = "WAREHOUSE"
        response = self.client.post(
            "/categories/",
            headers=self._headers(),
            json={"category_name": "Hardware"},
        )
        self.assertEqual(response.status_code, 201)


if __name__ == "__main__":
    unittest.main()
