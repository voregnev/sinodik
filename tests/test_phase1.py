import os
import pytest
from pydantic import ValidationError
from config import Settings
from models.models import Order
from sqlalchemy import inspect as sa_inspect
from database import Base
from datetime import datetime


def test_jwt_secret_required(monkeypatch):
    """Test that importing Settings() without SINODIK_JWT_SECRET in env raises pydantic ValidationError"""
    monkeypatch.delenv("SINODIK_JWT_SECRET", raising=False)
    with pytest.raises(Exception):  # pydantic ValidationError
        Settings()


def test_admin_emails_config(monkeypatch):
    """Test that SINODIK_ADMIN_EMAILS is parsed correctly"""
    monkeypatch.setenv("SINODIK_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SINODIK_ADMIN_EMAILS", "Admin@Example.com, other@example.com ")
    s = Settings()
    assert s.admin_emails == ["admin@example.com", "other@example.com"]

    # Test with no SINODIK_ADMIN_EMAILS env var
    monkeypatch.delenv("SINODIK_ADMIN_EMAILS", raising=False)
    s2 = Settings()
    assert s2.admin_emails == []


def test_order_user_email_exists():
    """Test that Order.user_email column is present and nullable=True"""
    from sqlalchemy import inspect as sa_inspect
    cols = {c.key: c for c in Order.__table__.columns}
    assert "user_email" in cols
    assert cols["user_email"].nullable is True


def test_anonymous_order_unaffected():
    """Test that Order model can be instantiated without user_email (field accepts None)"""
    o = Order(
        source_channel="form",
        order_type="здравие",
        period_type="разовое",
        ordered_at=datetime.utcnow()
    )
    assert o.user_email is None