from datetime import timedelta
from uuid import UUID

from app.core.config import settings
from app.models.auth_lifecycle import OtpChallenge
from tests.auth_test_support import CookieSessionTestCase


class AuthenticationLifecycleTests(CookieSessionTestCase):
    def test_signup_verification_creates_owner_workspace_and_cookie_session(self):
        started = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Business Owner",
                "business_name": "Northwind Traders",
                "mobile_number": "9876543210",
                "username": "owner",
                "password": "twelve-character-password",
                "confirm_password": "twelve-character-password",
            },
        )
        self.assertEqual(started.status_code, 202)
        self.assertEqual(self.sms.messages[0][0], "+919876543210")
        self.assertEqual(self.sms.messages[0][2], "SIGNUP")

        verified = self.client.post(
            "/auth/signup/verify-otp",
            json={"challenge_id": started.json()["challenge_id"], "code": self.sms.messages[0][1]},
        )
        self.assertEqual(verified.status_code, 200)
        payload = verified.json()
        self.assertEqual(payload["workspace"]["business_name"], "Northwind Traders")
        self.assertEqual(payload["workspace"]["role"], "OWNER")
        self.assertIn("users:manage", payload["permissions"])
        self.assertTrue(self.client.cookies.get(settings.COOKIE_NAME))
        self.assertTrue(self.client.cookies.get(settings.CSRF_COOKIE_NAME))
        self.assertNotIn("access_token", payload)
        self.assertNotIn("password", str(payload).lower())

        replay = self.client.post(
            "/auth/signup/verify-otp",
            json={"challenge_id": started.json()["challenge_id"], "code": self.sms.messages[0][1]},
        )
        self.assertEqual(replay.status_code, 400)

    def test_signup_enforces_confirmed_twelve_character_password(self):
        short_password = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Business Owner", "business_name": "Northwind Traders", "mobile_number": "9876543210",
                "username": "owner", "password": "too-short", "confirm_password": "too-short",
            },
        )
        mismatch = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Business Owner", "business_name": "Northwind Traders", "mobile_number": "9876543210",
                "username": "owner", "password": "twelve-character-password", "confirm_password": "a-different-password",
            },
        )
        self.assertEqual(short_password.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(self.sms.messages, [])

    def test_login_accepts_case_insensitive_username_and_verified_mobile(self):
        user = self.make_user(username="Owner")
        self.make_workspace_membership(user)
        by_username = self.client.post(
            "/auth/login", json={"identifier": "OWNER", "password": "correct-horse-battery-staple"}
        )
        self.assertEqual(by_username.status_code, 200)
        self.assertEqual(by_username.json()["username"], "Owner")
        self.assertIn("httponly", by_username.headers["set-cookie"].lower())

        self.client.cookies.clear()
        by_mobile = self.client.post(
            "/auth/login", json={"identifier": "9876543210", "password": "correct-horse-battery-staple"}
        )
        self.assertEqual(by_mobile.status_code, 200)
        self.assertEqual(by_mobile.json()["username"], "Owner")

    def test_login_failures_are_generic_and_lock_after_five_attempts(self):
        user = self.make_user(username="owner")
        self.make_workspace_membership(user)
        failures = [
            self.client.post("/auth/login", json={"identifier": "owner", "password": "wrong-password"})
            for _ in range(settings.FAILED_LOGIN_ATTEMPT_THRESHOLD)
        ]
        unknown = self.client.post("/auth/login", json={"identifier": "unknown", "password": "wrong-password"})
        locked = self.client.post(
            "/auth/login", json={"identifier": "owner", "password": "correct-horse-battery-staple"}
        )
        self.assertTrue(all(response.status_code == 401 for response in failures))
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.json(), failures[0].json())
        self.assertEqual(locked.status_code, 401)
        self.assertEqual(locked.json(), failures[0].json())

    def test_expired_lock_resets_then_a_wrong_password_counts_from_one(self):
        user = self.make_user(username="owner")
        self.make_workspace_membership(user)
        db = self.db()
        stored = db.get(type(user), user.user_id)
        stored.failed_login_count = settings.FAILED_LOGIN_ATTEMPT_THRESHOLD
        from app.services.auth_lifecycle import utc_now
        stored.locked_until = utc_now() - timedelta(seconds=1)
        db.commit()
        db.close()

        response = self.client.post("/auth/login", json={"identifier": "owner", "password": "wrong-password"})
        self.assertEqual(response.status_code, 401)
        db = self.db()
        stored = db.get(type(user), user.user_id)
        self.assertEqual(stored.failed_login_count, 1)
        self.assertIsNone(stored.locked_until)
        db.close()

    def test_cookie_session_requires_csrf_for_logout_and_is_revoked_on_logout(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user)
        self.authenticate_client(user, membership)
        self.assertEqual(self.client.post("/auth/logout").status_code, 403)
        logged_out = self.client.post("/auth/logout", headers=self.csrf_headers())
        self.assertEqual(logged_out.status_code, 200)
        self.assertIn("signed out", logged_out.json()["message"].lower())
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_password_recovery_otp_is_single_use_and_reset_revokes_sessions(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user)
        self.authenticate_client(user, membership)
        started = self.client.post("/auth/forgot-password", json={"mobile_number": "9876543210"})
        self.assertEqual(started.status_code, 202)
        verified = self.client.post(
            "/auth/reset-password/verify-otp",
            json={"challenge_id": started.json()["challenge_id"], "code": self.sms.messages[-1][1]},
        )
        self.assertEqual(verified.status_code, 200)
        reset = self.client.post(
            "/auth/reset-password",
            json={
                "reset_grant": verified.json()["reset_grant"],
                "new_password": "a-new-twelve-character-password",
                "confirm_password": "a-new-twelve-character-password",
            },
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        replay = self.client.post(
            "/auth/reset-password",
            json={
                "reset_grant": verified.json()["reset_grant"],
                "new_password": "another-twelve-character-password",
                "confirm_password": "another-twelve-character-password",
            },
        )
        self.assertEqual(replay.status_code, 400)

    def test_expired_otp_is_rejected(self):
        started = self.client.post(
            "/auth/signup",
            json={
                "full_name": "Business Owner", "business_name": "Northwind", "mobile_number": "9876543210",
                "username": "owner", "password": "twelve-character-password", "confirm_password": "twelve-character-password",
            },
        )
        db = self.db()
        challenge = db.query(OtpChallenge).filter_by(public_id=UUID(started.json()["challenge_id"])).one()
        from app.services.auth_lifecycle import utc_now
        challenge.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        db.close()
        response = self.client.post(
            "/auth/signup/verify-otp",
            json={"challenge_id": started.json()["challenge_id"], "code": self.sms.messages[0][1]},
        )
        self.assertEqual(response.status_code, 400)

    def test_otp_has_five_attempts_and_resend_invalidates_the_previous_code(self):
        payload = {
            "full_name": "Business Owner", "business_name": "Northwind", "mobile_number": "9876543210",
            "username": "owner", "password": "twelve-character-password", "confirm_password": "twelve-character-password",
        }
        started = self.client.post("/auth/signup", json=payload)
        challenge_id = started.json()["challenge_id"]
        original_code = self.sms.messages[-1][1]
        for _ in range(5):
            wrong = self.client.post("/auth/signup/verify-otp", json={"challenge_id": challenge_id, "code": "000000"})
            self.assertEqual(wrong.status_code, 400)
        exhausted = self.client.post("/auth/signup/verify-otp", json={"challenge_id": challenge_id, "code": original_code})
        self.assertEqual(exhausted.status_code, 400)

        fresh = self.client.post("/auth/signup", json={**payload, "username": "owner-two"})
        db = self.db()
        challenge = db.query(OtpChallenge).filter_by(public_id=UUID(fresh.json()["challenge_id"])).one()
        from app.services.auth_lifecycle import utc_now
        challenge.sent_at = utc_now() - timedelta(seconds=31)
        db.commit()
        db.close()
        previous_code = self.sms.messages[-1][1]
        resent = self.client.post("/auth/signup/resend-otp", json={"challenge_id": fresh.json()["challenge_id"]})
        self.assertEqual(resent.status_code, 202)
        self.assertNotEqual(self.sms.messages[-1][1], previous_code)
        invalidated = self.client.post(
            "/auth/signup/verify-otp", json={"challenge_id": fresh.json()["challenge_id"], "code": previous_code}
        )
        self.assertEqual(invalidated.status_code, 400)

    def test_change_password_revokes_the_current_session_and_requires_the_new_password(self):
        user = self.make_user()
        _, membership = self.make_workspace_membership(user)
        self.authenticate_client(user, membership)
        changed = self.client.post(
            "/auth/change-password",
            headers=self.csrf_headers(),
            json={
                "current_password": "correct-horse-battery-staple",
                "new_password": "a-new-twelve-character-password",
                "confirm_password": "a-new-twelve-character-password",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.client.cookies.clear()
        old_password = self.client.post("/auth/login", json={"identifier": "admin", "password": "correct-horse-battery-staple"})
        new_password = self.client.post("/auth/login", json={"identifier": "admin", "password": "a-new-twelve-character-password"})
        self.assertEqual(old_password.status_code, 401)
        self.assertEqual(new_password.status_code, 200)


if __name__ == "__main__":
    import unittest
    unittest.main()
