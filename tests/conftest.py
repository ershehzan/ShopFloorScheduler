# tests/conftest.py
"""
Shared Pytest fixtures for ShopFloorScheduler tests.

Provides reusable test data and a test DB session that uses
an in-memory SQLite database isolated from production data.
"""
import sys
import os
import copy
import pytest

# Ensure project root is on sys.path so imports like `from models import Job` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Job, Operation, Machine


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_machines():
    """3 machines: M0 (no downtime), M1 (maintenance 7-12), M2 (no downtime)."""
    return [
        Machine(machine_id=0, unavailable_periods=[]),
        Machine(machine_id=1, unavailable_periods=[(7, 12)]),
        Machine(machine_id=2, unavailable_periods=[]),
    ]


@pytest.fixture
def fresh_machines(sample_machines):
    """Deep copy of sample_machines — safe for mutation by scheduling algorithms."""
    return copy.deepcopy(sample_machines)


@pytest.fixture
def sample_jobs():
    """
    5 jobs mirroring the data.json fixture:
      Job 0: M0(3) → M1(2) → M2(2), due=15, prio=2
      Job 1: M0(2) → M2(1) → M1(4), due=20, prio=3
      Job 2: M1(4) → M0(3),          due=25, prio=2
      Job 3: M2(8) → M0(5),          due=30, prio=1
      Job 4: M1(2) → M2(2),          due=10, prio=2
    """
    return [
        Job(0, [Operation(0, 3), Operation(1, 2), Operation(2, 2)], due_date=15, priority=2),
        Job(1, [Operation(0, 2), Operation(2, 1), Operation(1, 4)], due_date=20, priority=3),
        Job(2, [Operation(1, 4), Operation(0, 3)], due_date=25, priority=2),
        Job(3, [Operation(2, 8), Operation(0, 5)], due_date=30, priority=1),
        Job(4, [Operation(1, 2), Operation(2, 2)], due_date=10, priority=2),
    ]


@pytest.fixture
def simple_jobs():
    """2 simple jobs for minimal tests."""
    return [
        Job(1, [Operation(0, 5), Operation(1, 3)], due_date=20, priority=1),
        Job(2, [Operation(1, 4), Operation(0, 2)], due_date=15, priority=2),
    ]


@pytest.fixture
def simple_machines():
    """2 clean machines with no downtime."""
    return [
        Machine(machine_id=0, unavailable_periods=[]),
        Machine(machine_id=1, unavailable_periods=[]),
    ]


@pytest.fixture
def sample_schedule():
    """
    A deterministic pre-computed schedule for metric tests.
    Format: (job_id, op_index, machine_id, start_time, end_time)
    """
    return [
        (1, 0, 0, 0, 5),
        (1, 1, 1, 5, 8),
        (2, 0, 1, 0, 4),
        (2, 1, 0, 5, 7),
    ]


# ---------------------------------------------------------------------------
# API / DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def _test_engine():
    """
    Creates an in-memory SQLite engine with all tables.
    Uses StaticPool so all connections share the same in-memory database.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from core.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import models so they register with Base
    import core.models_db  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(_test_engine):
    """Yields a session from the in-memory test engine."""
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_test_engine):
    """
    FastAPI TestClient that uses the in-memory test database.
    Overrides the `get_db` dependency to create sessions from the test engine.
    """
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient
    from api.main import app
    from core.database import get_db, init_db

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    # Ensure the production DB file also has tables (for on_startup event)
    init_db()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
