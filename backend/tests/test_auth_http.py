from sqlalchemy import select

from app.models.auth_lifecycle import WorkspaceInvitation
from app.models.workspace import WorkspaceMembership
from tests.auth_test_support import CookieSessionTestCase


class InvitationAndTenantHttpTests(CookieSessionTestCase):
    def test_staff_invitation_requires_mobile_verification_and_creates_a_workspace_membership(self):
        owner = self.make_user(username="owner", mobile_e164="+919876543210")
        _, owner_membership = self.make_workspace_membership(owner, role="OWNER")
        self.authenticate_client(owner, owner_membership)

        created = self.client.post(
            "/business/invitations",
            headers=self.csrf_headers(),
            json={"mobile_number": "9123456789", "role": "SALES"},
        )
        self.assertEqual(created.status_code, 201)
        token = created.json()["invitation_token"]
        db = self.db()
        invitation = db.execute(select(WorkspaceInvitation)).scalar_one()
        self.assertNotEqual(invitation.token_hash, token)
        db.close()

        self.client.cookies.clear()
        accepted = self.client.post(
            "/business/invitations/accept",
            json={
                "invitation_token": token,
                "full_name": "Sales Staff",
                "username": "sales-staff",
                "password": "a-secure-staff-password",
                "confirm_password": "a-secure-staff-password",
            },
        )
        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(self.sms.messages[-1][2], "INVITATION")
        joined = self.client.post(
            "/business/invitations/verify-otp",
            json={"challenge_id": accepted.json()["challenge_id"], "code": self.sms.messages[-1][1]},
        )
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.json()["workspace"]["role"], "SALES")
        self.assertIn("orders:write", joined.json()["permissions"])
        self.assertNotIn("users:manage", joined.json()["permissions"])

        db = self.db()
        memberships = db.execute(select(WorkspaceMembership)).scalars().all()
        self.assertEqual(len(memberships), 2)
        self.assertTrue(db.execute(select(WorkspaceInvitation)).scalar_one().accepted_at)
        db.close()

    def test_workspace_session_cannot_read_categories_from_another_workspace(self):
        user = self.make_user()
        _, first_membership = self.make_workspace_membership(user, business_name="First")
        _, second_membership = self.make_workspace_membership(user, business_name="Second")

        self.authenticate_client(user, first_membership)
        created = self.client.post(
            "/categories/",
            headers=self.csrf_headers(),
            json={"category_name": "Private to first workspace"},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(self.client.get("/categories/").json()), 1)

        self.authenticate_client(user, second_membership)
        second_workspace_categories = self.client.get("/categories/")
        self.assertEqual(second_workspace_categories.status_code, 200)
        self.assertEqual(second_workspace_categories.json(), [])

    def test_guessed_supplier_id_is_not_readable_or_mutable_across_workspaces(self):
        user = self.make_user()
        _, first_membership = self.make_workspace_membership(user, business_name="First")
        _, second_membership = self.make_workspace_membership(user, business_name="Second")
        self.authenticate_client(user, first_membership)
        created = self.client.post(
            "/suppliers/",
            headers=self.csrf_headers(),
            json={"supplier_name": "First-only supplier", "address": "Address"},
        )
        self.assertEqual(created.status_code, 201)
        supplier_id = created.json()["supplier_id"]

        self.authenticate_client(user, second_membership)
        read = self.client.get(f"/suppliers/{supplier_id}")
        update = self.client.patch(
            f"/suppliers/{supplier_id}", headers=self.csrf_headers(), json={"supplier_name": "Hijacked"}
        )
        self.assertEqual(read.status_code, 404)
        self.assertEqual(update.status_code, 404)


if __name__ == "__main__":
    import unittest
    unittest.main()
