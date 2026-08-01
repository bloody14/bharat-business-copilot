"""Shared test fixtures for the Bharat Business Copilot backend.

Database isolation
------------------
Each test runs inside a PostgreSQL transaction that is rolled back after the
test completes.  Route handlers call ``session.commit()`` internally; we use a
SAVEPOINT so those commits release the savepoint rather than the real
connection-level transaction.

Principal injection
-------------------
The ``as_principal`` fixture returns a callable that sets the active test
principal (organization + role) for subsequent HTTP requests.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.core.database import get_db
from app.core.auth import Principal, get_principal

# Re-use the project database; every test transaction is rolled back.
_engine = create_engine(get_settings().database_url)


@pytest.fixture()
def db():
    """Provide a DB session inside a rolled-back transaction.

    A SAVEPOINT is started so that ``session.commit()`` inside route handlers
    releases the savepoint instead of committing the real transaction.  An
    event listener restarts the savepoint after each commit/rollback so
    subsequent operations in the same test continue to work.

    At teardown the outer transaction is rolled back, leaving the database
    unchanged.
    """
    connection = _engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        """Restart the savepoint after each commit/rollback inside the test."""
        if trans.nested and trans.parent is not None and not trans.parent.nested:
            session.begin_nested()

    def _override_db():
        yield session

    app.dependency_overrides[get_db] = _override_db
    yield session

    # Teardown — remove listener, roll everything back.
    event.remove(session, "after_transaction_end", _restart_savepoint)
    app.dependency_overrides.pop(get_db, None)
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def as_principal():
    """Callable fixture to set the active test principal.

    Call with no arguments for the default (``org_test_a`` / ``owner``).
    Call with keyword arguments to customise::

        as_principal(org_id="org_test_b", role="viewer")
    """

    def _set(
        org_id: str = "org_test_a",
        user_id: str = "user_001",
        role: str = "owner",
    ) -> Principal:
        p = Principal(organization_id=org_id, user_id=user_id, role=role)
        app.dependency_overrides[get_principal] = lambda: p
        return p

    yield _set
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture()
def client(db, as_principal):
    """FastAPI ``TestClient`` authenticated as ``org_test_a`` owner.

    Uses the transactional ``db`` session and injects a default principal.
    Call ``as_principal(...)`` inside the test body to switch role / org.
    """
    as_principal()  # default: org_test_a, user_001, owner
    return TestClient(app)
