from app.core.security import verify_password
from app.models.user import User
from tests.auth_test_support import CookieSessionTestCase


class UserManagementTests(CookieSessionTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user(username="owner", mobile_e164="+919876543210")
        self.workspace, self.owner_membership = self.make_workspace_membership(self.owner, role="OWNER")
        self.staff = self.make_user(username="staff", mobile_e164="+919876543211")
        db = self.db()
        from app.models.workspace import WorkspaceMembership
        staff_membership = WorkspaceMembership(
            workspace_id=self.workspace.workspace_id,
            user_id=self.staff.user_id,
            role="VIEWER",
            status="ACTIVE",
        )
        db.add(staff_membership)
        db.commit()
        db.expunge(staff_membership)
        db.close()
        self.staff_membership = staff_membership
        self.authenticate_client(self.owner, self.owner_membership)

    def test_listing_and_updating_workspace_staff_never_returns_password_hashes(self):
        listed = self.client.get("/users")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 2)
        self.assertNotIn("password_hash", str(listed.json()))

        updated = self.client.patch(
            f"/users/{self.staff.user_id}",
            headers=self.csrf_headers(),
            json={"full_name": "Updated Staff", "role": "SALES", "status": "ACTIVE"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "SALES")
        self.assertEqual(updated.json()["membership_status"], "ACTIVE")
        self.assertNotIn("password_hash", str(updated.json()))

    def test_direct_user_creation_is_rejected_in_favour_of_invitations(self):
        response = self.client.post(
            "/users",
            headers=self.csrf_headers(),
            json={"username": "new-user", "full_name": "New User", "role": "VIEWER", "initial_password": "not-used"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invite staff", response.json()["detail"])

    def test_owner_cannot_demote_or_deactivate_themselves_and_last_owner_is_preserved(self):
        for payload in ({"status": "INACTIVE"}, {"role": "ADMIN"}):
            with self.subTest(payload=payload):
                response = self.client.patch(
                    f"/users/{self.owner.user_id}", headers=self.csrf_headers(), json=payload
                )
                self.assertEqual(response.status_code, 400)

    def test_owner_reset_revokes_staff_sessions_and_changes_the_password(self):
        self.client.cookies.clear()
        self.authenticate_client(self.staff, self.staff_membership)
        self.assertEqual(self.client.get("/auth/me").status_code, 200)
        self.client.cookies.clear()
        self.authenticate_client(self.owner, self.owner_membership)
        reset = self.client.post(
            f"/users/{self.staff.user_id}/reset-password",
            headers=self.csrf_headers(),
            json={"new_password": "a-replacement-staff-password"},
        )
        self.assertEqual(reset.status_code, 200)
        db = self.db()
        stored = db.get(User, self.staff.user_id)
        self.assertTrue(verify_password("a-replacement-staff-password", stored.password_hash))
        db.close()

    def test_staff_cannot_access_workspace_user_management(self):
        self.client.cookies.clear()
        self.authenticate_client(self.staff, self.staff_membership)
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    import unittest
    unittest.main()
