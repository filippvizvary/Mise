"""Root pytest configuration for Mise test suite.

Sets up a temporary SQLite database with all tables created,
and configures environment variables for isolated testing.
"""

import os
import tempfile

# ─── Environment Setup ─────────────────────────────────────────────────────
# These must be set BEFORE any mise modules are imported.

# Create a temp database file and set DATABASE_URL to point to it
_test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_file.name}"
os.environ["EMAIL_VERIFICATION_REQUIRED"] = "false"
os.environ["MISE_AI_PROVIDER"] = "ollama"
os.environ["NO_COLOR"] = "1"

# ─── Initialize the Database ───────────────────────────────────────────────
# Create all tables in the test database so CLI commands can use them
from mise.db.database import init_db
init_db()


# ─── Pytest Hooks ─────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    """Clean up the temp database file after all tests are done."""
    import os
    try:
        os.unlink(_test_db_file.name)
    except OSError:
        pass