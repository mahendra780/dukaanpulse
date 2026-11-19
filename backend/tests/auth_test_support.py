"""Test-only helpers for cookie-session integration tests.

The production application uses PostgreSQL identities. SQLite is sufficient
for isolated route tests once this helper supplies deterministic identifiers;
it never points at a configured database or reads an environment file.
"""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core.auth import AuthPrincipal
from app.core.config import settings
from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.auth_lifecycle import issue_session
from app.services.sms_provider import get_sms_provider


class SqliteTestSession(Session):
    pass


@event.listens_for(SqliteTestSession, "before_flush")
def assign_sqlite_identity_values(session, _flush_context, _instances):
    """SQLite does not auto-generate BigInteger Identity values."""
    counters = session.info.setdefault("test_identity_counters", {})
    for instance in session.new:
        mapper = inspect(instance).mapper
        if len(mapper.primary_key) != 1:
            continue
        column = mapper.primary_key[0]
        attribute = column.key
        if getattr(instance, attribute) is not None:
            continue
        if mapper.class_ not in counters:
            counters[mapper.class_] = session.scalar(select(func.max(column))) or 0
        next_value = counters[mapper.class_] + 1
        counters[mapper.class_] = next_value
        setattr(instance, attribute, next_value)


class CapturingSmsProvider:
    def __init__(self):
        self.messages: list[tuple[str, str, str]] = []

    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None:
        self.messages.append((mobile_e164, code, purpose))


class CookieSessionTestCase(unittest.TestCase):
    """A clean SQLite database and TestClient for each test."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, class_=SqliteTestSession, expire_on_commit=False)
        self.sms = CapturingSmsProvider()

        def override_get_db():
            db = self.sessions()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_sms_provider] = lambda: self.sms
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def db(self) -> SqliteTestSession:
        return self.sessions()

    def make_user(
        self,
        *,
        username: str = "admin",
        password: str = "correct-horse-battery-staple",
        mobile_e164: str | None = "+919876543210",
    ) -> User:
        db = self.db()
        user = User(
            username=username,
            full_name="Test User",
            password_hash=hash_password(password),
            role="ADMIN",
            status="ACTIVE",
            mobile_e164=mobile_e164,
            mobile_verified_at=datetime.now(timezone.utc) if mobile_e164 else None,
        )
        db.add(user)
        db.commit()
        db.expunge(user)
        db.close()
        return user

    def make_workspace_membership(
        self,
        user: User,
        *,
        role: str = "OWNER",
        business_name: str = "Test Workspace",
    ) -> tuple[Workspace, WorkspaceMembership]:
        db = self.db()
        workspace = Workspace(business_name=business_name, status="ACTIVE")
        db.add(workspace)
        db.flush()
        membership = WorkspaceMembership(
            workspace_id=workspace.workspace_id,
            user_id=user.user_id,
            role=role,
            status="ACTIVE",
        )
        db.add(membership)
        db.commit()
        db.expunge(workspace)
        db.expunge(membership)
        db.close()
        return workspace, membership

    def authenticate_client(self, user: User, membership: WorkspaceMembership,) -> AuthPrincipal:
        db = self.db()
        workspace_id = membership.workspace_id
        session, token, csrf = issue_session(db, user_id=user.user_id, workspace_id=workspace_id)
        db.commit()
        db.expunge(session)
        db.close()
        self.client.cookies.set(settings.COOKIE_NAME, token)
        self.client.cookies.set(settings.CSRF_COOKIE_NAME, csrf)
        return AuthPrincipal(user=user, session=session, membership=membership)

    def csrf_headers(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.client.cookies.get(settings.CSRF_COOKIE_NAME)}
