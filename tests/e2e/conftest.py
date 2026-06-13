"""E2E test fixtures — fresh DB per test, CLI runner, auth helpers, AI mocks."""

import os
import json
import tempfile
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mise.db.database import Base, get_db
from mise.db.models import User, UserProfile, UserPreference, Discount, MealPlan, Recipe
from mise.auth.auth import register as auth_register, login as auth_login, logout as auth_logout
from mise.auth.auth import _write_auth_file, _delete_auth_file


# ─── Database Fixtures ────────────────────────────────────────────────────
# The root conftest.py sets up a temporary SQLite database with all tables
# created and DATABASE_URL pointing to it. CLI commands use this database
# via SessionLocal. Our fixtures clean up data between tests.

from mise.db.database import SessionLocal as _SessionLocal, init_db as _init_db


@pytest.fixture(scope="function")
def db_engine():
    """Provide the test database engine (from root conftest's temp file DB)."""
    from mise.db.database import engine
    return engine


@pytest.fixture(scope="function")
def db_session():
    """Provide a database session from the global test database."""
    session = _SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def db_session_committed():
    """Provide a DB session with committed data."""
    session = _SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def patched_db(monkeypatch):
    """Patch init_db to be a no-op (tables already created by root conftest)."""
    monkeypatch.setattr("mise.db.database.init_db", lambda: None)
    return _SessionLocal


@pytest.fixture(scope="function")
def fresh_db(patched_db):
    """Provide a session factory connected to the test database.

    Also cleans all data from tables to ensure test isolation.
    """
    # Clean all data from tables for test isolation
    session = _SessionLocal()
    try:
        # Delete data from all tables in reverse dependency order
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    return _SessionLocal


# ─── Auth File Isolation ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_auth_file(tmp_path, monkeypatch):
    """Ensure each test uses its own auth file in a temp directory.

    This prevents tests from interfering with the real ~/.mise/auth file
    and with each other.
    """
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("mise.config.AUTH_FILE", str(auth_file))
    monkeypatch.setattr("mise.auth.auth.AUTH_FILE", str(auth_file))
    yield str(auth_file)
    # Cleanup is automatic since tmp_path is cleaned up


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Set up isolated config for testing — no email verification, temp paths."""
    monkeypatch.setattr("mise.config.EMAIL_VERIFICATION_REQUIRED", False)
    monkeypatch.setattr("mise.email.verification.EMAIL_VERIFICATION_REQUIRED", False)


# ─── CLI Runner ────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def cli_runner():
    """Provide a Typer CLI test runner."""
    runner = CliRunner()
    return runner


@pytest.fixture(scope="function")
def app():
    """Provide the Mise Typer app instance for testing."""
    from mise.cli.main import app
    return app


# ─── User Creation Helpers ─────────────────────────────────────────────────

@pytest.fixture
def make_user(fresh_db):
    """Factory fixture to create users in the test database.

    Usage:
        user = make_user(username="alice", email="alice@test.com", password="pass123")
    """
    created_users = []

    def _make_user(
        username: str = "testuser",
        email: str = "testuser@example.com",
        password: str = "TestPass123!",
        **kwargs,
    ):
        session = fresh_db()
        try:
            result = auth_register(username=username, email=email, password=password)
            user = result.user
            # If is_verified should be True, update directly
            if kwargs.get("verified", False):
                user.is_verified = True
                session.commit()
            created_users.append(user)
            return user
        finally:
            session.close()

    yield _make_user

    # Cleanup auth state
    _delete_auth_file()


@pytest.fixture
def logged_in_user(make_user, tmp_path, monkeypatch):
    """Create a user and log them in. Returns the user object.

    The auth file is set up so get_current_user() will find them.
    """
    def _logged_in_user(
        username: str = "testuser",
        email: str = "testuser@example.com",
        password: str = "TestPass123!",
        verified: bool = True,
    ):
        user = make_user(username=username, email=email, password=password)
        if verified:
            session = make_user.__code__.co_freevars  # introspection hack - won't work
            # We'll verify directly in the DB
        # Login to set auth state
        auth_login(username=username, password=password)
        return user

    return _logged_in_user


@pytest.fixture
def authenticated_user(fresh_db, make_user):
    """Create a verified, logged-in user and return (user, session).

    This is the most commonly needed fixture for authenticated commands.
    """
    from mise.db.crud import get_user_by_username

    session = fresh_db()
    try:
        result = auth_register(username="testuser", email="test@example.com", password="TestPass123!")
        # Re-fetch the user from DB (auth_register returns an expunged object)
        user = get_user_by_username(session, "testuser")
        # Verify the user directly in DB
        user.is_verified = True
        session.commit()

        # Login
        auth_login(username="testuser", password="TestPass123!")
        yield user
    finally:
        session.close()
        auth_logout()


@pytest.fixture
def second_user(fresh_db, make_user):
    """Create a second verified, logged-in user for multi-user tests.

    Returns (user_b, session_b). The first user is set up via authenticated_user.
    """
    session = fresh_db()
    try:
        result = auth_register(username="user_b", email="userb@example.com", password="TestPass456!")
        user_b = result.user
        user_b.is_verified = True
        session.commit()
        yield user_b
    finally:
        session.close()


# ─── Sample Data Helpers ──────────────────────────────────────────────────

@pytest.fixture
def sample_discounts(fresh_db):
    """Insert sample discounts and return them."""
    from mise.db.crud import insert_discounts

    session = fresh_db()
    try:
        discounts = [
            {"store": "Lidl", "product": "Chicken Breast 500g", "category": "Meat", "original_price": 5.99, "discount_price": 3.99},
            {"store": "Lidl", "product": "Greek Yogurt 500g", "category": "Dairy", "original_price": 2.49, "discount_price": 1.49},
            {"store": "Kaufland", "product": "Pork Shoulder 1kg", "category": "Meat", "original_price": 6.99, "discount_price": 4.49},
            {"store": "Tesco", "product": "Salmon Fillet 200g", "category": "Fish", "original_price": 7.99, "discount_price": 5.49},
            {"store": "Kaufland", "product": "Orange Juice 1L", "category": "Drinks", "original_price": 1.99, "discount_price": 0.99},
        ]
        insert_discounts(session, discounts)
        session.commit()
        yield discounts
    finally:
        session.close()


@pytest.fixture
def sample_preferences(fresh_db, authenticated_user):
    """Set up sample preferences for the authenticated user."""
    from mise.user.preferences import add_allergy, add_dislike, add_liked_cuisine, add_preferred_store, add_meal_slot

    user = authenticated_user
    add_allergy(user.id, "peanuts")
    add_dislike(user.id, "celery")
    add_liked_cuisine(user.id, "Italian")
    add_preferred_store(user.id, "Lidl")
    add_meal_slot(user.id, "breakfast")
    add_meal_slot(user.id, "lunch")
    add_meal_slot(user.id, "dinner")

    return user


@pytest.fixture
def sample_profile(fresh_db, authenticated_user):
    """Set up a sample profile for the authenticated user."""
    from mise.user.profile import update_profile

    user = authenticated_user
    update_profile(
        user.id,
        household_size=2,
        preferred_units="metric",
        currency="EUR",
        cooking_skill="intermediate",
        max_cook_time_min=60,
    )
    return user


# ─── AI Mock ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ai():
    """Mock the AI provider to return deterministic responses.

    This patches the AI registry to return fake responses without
    actually calling Ollama or OpenAI.
    """
    from mise.ai.base import AIResponse

    fake_response = AIResponse(
        provider="mock",
        model="mock-model",
        content="Mock AI response: Suggest pasta with tomato sauce.",
    )

    class MockProvider:
        name = "mock"
        default_model = "mock-model"

        def generate(self, prompt, system=None, model=None):
            return fake_response

        def health_check(self):
            return True

    mock_provider = MockProvider()

    with patch("mise.ai.ai_registry.get", return_value=mock_provider):
        with patch("mise.ai.ai_registry.list_available", return_value=["mock"]):
            yield mock_provider, fake_response


@pytest.fixture
def mock_ai_suggestions():
    """Mock the AI to return structured meal suggestions."""
    from mise.meal.suggestions import MealSuggestion

    sample_suggestions = [
        MealSuggestion(
            title="Pasta Carbonara",
            reason="A classic Italian dish that's quick to prepare",
            recipe_id="recipe-pasta-carbonara",
            prep_time_min=25,
            difficulty="easy",
            cuisine="Italian",
            ingredient_overlap=["eggs", "cheese"],
            discount_match="Pasta on sale at Lidl",
        ),
        MealSuggestion(
            title="Chicken Stir-Fry",
            reason="Healthy and uses discounted chicken breast",
            recipe_id="recipe-chicken-stirfry",
            prep_time_min=30,
            difficulty="easy",
            cuisine="Asian",
            ingredient_overlap=["chicken", "vegetables"],
            discount_match="Chicken Breast 500g on sale at Lidl",
        ),
        MealSuggestion(
            title="Greek Salad",
            reason="Fresh and light, uses discounted yogurt",
            recipe_id="recipe-greek-salad",
            prep_time_min=10,
            difficulty="easy",
            cuisine="Mediterranean",
            ingredient_overlap=["cucumber", "tomatoes"],
            discount_match="Greek Yogurt 500g on sale at Lidl",
        ),
    ]

    with patch("mise.meal.suggestions.get_suggestions", return_value=sample_suggestions):
        yield sample_suggestions


@pytest.fixture
def mock_ai_for_planning(mock_ai_suggestions):
    """Full AI mock for meal planning commands (suggestions + provider)."""
    from mise.ai.base import AIResponse
    from mise.meal.suggestions import MealSuggestion

    # mock_ai_suggestions already patches get_suggestions
    # We also need the AI registry patched
    fake_response = AIResponse(
        provider="mock",
        model="mock-model",
        content="Mock AI response: Suggest pasta with tomato sauce.",
    )

    class MockProvider:
        name = "mock"
        default_model = "mock-model"

        def generate(self, prompt, system=None, model=None):
            return fake_response

        def health_check(self):
            return True

    mock_provider = MockProvider()

    with patch("mise.ai.ai_registry.get", return_value=mock_provider):
        with patch("mise.ai.ai_registry.list_available", return_value=["mock"]):
            yield mock_provider


# ─── Scraper Mock ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_scraper():
    """Mock the scraper registry to return fake discount data.

    Methods are async because the CLI uses asyncio.run() to call them.
    """
    import asyncio
    from mise.scraper.base import DiscountItem

    sample_items = [
        DiscountItem(
            store="Lidl",
            product="Chicken Breast 500g",
            category="Meat",
            original_price=5.99,
            discount_price=3.99,
            discount_percent=33,
        ),
        DiscountItem(
            store="Kaufland",
            product="Pork Shoulder 1kg",
            category="Meat",
            original_price=6.99,
            discount_price=4.49,
            discount_percent=36,
        ),
        DiscountItem(
            store="Tesco",
            product="Salmon Fillet 200g",
            category="Fish",
            original_price=7.99,
            discount_price=5.49,
            discount_percent=31,
        ),
    ]

    class MockScraperRegistry:
        async def run_one(self, store):
            return [item for item in sample_items if item.store.lower() == store.lower()]

        async def run_all(self):
            return sample_items

        def list_available(self):
            return ["lidl", "kaufland", "tesco"]

    mock_registry = MockScraperRegistry()

    with patch("mise.scraper.scraper_registry", mock_registry):
        yield mock_registry, sample_items


@pytest.fixture
def mock_scraper_empty():
    """Mock the scraper registry to return no discounts.

    Methods are async because the CLI uses asyncio.run() to call them.
    """
    import asyncio

    class MockScraperRegistry:
        async def run_one(self, store):
            return []

        async def run_all(self):
            return []

        def list_available(self):
            return ["lidl", "kaufland", "tesco"]

    mock_registry = MockScraperRegistry()

    with patch("mise.scraper.scraper_registry", mock_registry):
        yield mock_registry


# ─── Email Mock ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_email():
    """Mock email sending so tests don't try to connect to SMTP."""
    with patch("mise.email.sender.EmailSender.send", return_value=None):
        with patch("mise.email.verification.VerificationEmailSender.send_verification", return_value=None):
            yield


# ─── Date Helpers ───────────────────────────────────────────────────────────

@pytest.fixture
def today():
    """Return today's date."""
    return date.today()


@pytest.fixture
def tomorrow():
    """Return tomorrow's date."""
    return date.today() + timedelta(days=1)


@pytest.fixture
def next_week():
    """Return dates for the next 7 days."""
    start = date.today() + timedelta(days=1)
    return [start + timedelta(days=i) for i in range(7)]