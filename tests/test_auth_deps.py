"""Import and export verification for app.api.deps (get_current_user, require_admin)."""

import inspect
import sys
import os

# Support both: run from project root (app as package) and from container (PYTHONPATH=/app)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from app.api.deps import get_current_user, require_admin
except ImportError:
    from api.deps import get_current_user, require_admin


def test_get_current_user_importable_and_callable():
    """get_current_user is importable from app.api.deps and is a coroutine function."""
    assert callable(get_current_user)
    assert inspect.iscoroutinefunction(get_current_user)


def test_require_admin_importable_and_callable():
    """require_admin is importable from app.api.deps and is a coroutine function."""
    assert callable(require_admin)
    assert inspect.iscoroutinefunction(require_admin)
