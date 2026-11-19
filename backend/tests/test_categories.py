from tests.auth_test_support import CookieSessionTestCase


class CategoryEndpointTests(CookieSessionTestCase):
    def test_create_category_is_workspace_scoped_and_returns_the_existing_shape(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user, role="OWNER")
        self.authenticate_client(user, membership)

        response = self.client.post(
            "/categories/",
            headers=self.csrf_headers(),
            json={"category_name": "Hardware", "status": "ACTIVE"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"category_id": 1, "category_name": "Hardware", "status": "ACTIVE"},
        )
        self.assertEqual(self.client.get("/categories/").json(), [response.json()])

    def test_create_category_requires_csrf_and_categories_write_permission(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user, role="SALES")
        self.authenticate_client(user, membership)

        no_csrf = self.client.post("/categories/", json={"category_name": "Hardware"})
        forbidden = self.client.post(
            "/categories/", headers=self.csrf_headers(), json={"category_name": "Hardware"}
        )
        self.assertEqual(no_csrf.status_code, 403)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json(), {"detail": "You don't have permission to do this."})

    def test_duplicate_category_returns_the_existing_human_readable_conflict(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user, role="OWNER")
        self.authenticate_client(user, membership)
        payload = {"category_name": "Hardware"}
        self.assertEqual(self.client.post("/categories/", headers=self.csrf_headers(), json=payload).status_code, 201)
        duplicate = self.client.post("/categories/", headers=self.csrf_headers(), json=payload)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json(), {"detail": "A category with that name already exists."})


if __name__ == "__main__":
    import unittest
    unittest.main()
