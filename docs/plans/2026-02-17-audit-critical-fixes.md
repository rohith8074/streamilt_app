# Audit Critical Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix critical security and reliability issues identified in code audit (unbound variables, bare exceptions, unused imports, database connection management)

**Architecture:** Improve error handling robustness, add database connection context manager pattern, clean up imports, apply code formatting standards

**Tech Stack:** Python 3.9+, SQLite3, bcrypt, pytest, black, isort, autoflake

---

## Pre-Implementation Setup

### Task 0: Install Development Tools

**Files:**
- Modify: `requirements.txt`

**Step 1: Add development dependencies**

Add to `requirements.txt`:
```
black
isort
autoflake
pylint
flake8
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All tools installed successfully

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add code quality tools to requirements"
```

---

## Task 1: Fix Unbound Variable in verify_password

**Files:**
- Modify: `auth.py:163-170`
- Test: `tests/test_auth.py`

**Step 1: Write test for exception handling**

Add to `tests/test_auth.py`:

```python
def test_verify_password_database_error(temp_db, mocker):
    """Test that verify_password handles database errors gracefully."""
    # Mock sqlite3.connect to raise an error
    mocker.patch('auth.sqlite3.connect', side_effect=sqlite3.Error("Connection failed"))

    result = verify_password("test@example.com", "password")

    # Should return False, not crash with unbound variable
    assert result is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_verify_password_database_error -v`
Expected: FAIL - Test doesn't exist yet OR passes incorrectly due to bug

**Step 3: Implement the fix**

In `auth.py`, replace lines 163-170:

```python
def verify_password(username, password):
    """Verifies a user's password against the stored hash."""
    conn = None  # Initialize to None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            return True
        return False
    except (sqlite3.Error, ValueError, UnicodeDecodeError) as e:
        logger.error("Password verification failed: %s", e)
        return False
    finally:
        if conn:
            conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_verify_password_database_error -v`
Expected: PASS

**Step 5: Run all auth tests to ensure no regression**

Run: `pytest tests/test_auth.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "fix: prevent unbound variable error in verify_password

- Initialize conn to None before try block
- Replace bare except with specific exceptions
- Add test for database error handling"
```

---

## Task 2: Replace Bare Except in get_mapping_for_trace

**Files:**
- Modify: `auth.py:97-110`
- Test: `tests/test_auth.py`

**Step 1: Write test for exception handling**

Add to `tests/test_auth.py`:

```python
def test_get_mapping_for_trace_handles_database_error(temp_db, mocker):
    """Test that get_mapping_for_trace handles database errors."""
    mocker.patch('auth.sqlite3.connect', side_effect=sqlite3.Error("DB error"))

    result = get_mapping_for_trace("test-trace-id")

    # Should return (None, None) on error
    assert result == (None, None)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_get_mapping_for_trace_handles_database_error -v`
Expected: FAIL - Test doesn't exist yet

**Step 3: Implement the fix**

In `auth.py`, replace lines 97-110 with:

```python
def get_mapping_for_trace(trace_id):
    """Finds out which user owns a specific AI interaction receipt."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        c.execute("SELECT user_id, session_id FROM trace_user_mapping WHERE trace_id=?", (trace_id,))
        result = c.fetchone()
        if result:
            return result[0], result[1]
        return None, None
    except sqlite3.Error as e:
        logger.error("Failed to get mapping for trace %s: %s", trace_id, e)
        return None, None
    finally:
        if conn:
            conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_get_mapping_for_trace_handles_database_error -v`
Expected: PASS

**Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "fix: replace bare except in get_mapping_for_trace

- Use specific sqlite3.Error exception
- Initialize conn to None for safe cleanup
- Add error logging with context"
```

---

## Task 3: Replace Bare Except in get_fuzzy_session

**Files:**
- Modify: `auth.py:358-395`
- Test: `tests/test_auth.py`

**Step 1: Write test for exception handling**

Add to `tests/test_auth.py`:

```python
def test_get_fuzzy_session_handles_database_error(temp_db, mocker):
    """Test that get_fuzzy_session handles database errors."""
    mocker.patch('auth.sqlite3.connect', side_effect=sqlite3.Error("DB error"))

    result = get_fuzzy_session("test@example.com", "2026-02-17T10:00:00Z")

    # Should return None on error
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_get_fuzzy_session_handles_database_error -v`
Expected: FAIL - Test doesn't exist yet

**Step 3: Implement the fix**

In `auth.py`, replace the `get_fuzzy_session` function (lines 358-395) with:

```python
def get_fuzzy_session(username, trace_timestamp):
    """
    Fuzzy detective work: Matches a trace to a user session based on timing.

    If a trace has no user_id, we check if the user was active around that time
    (within ±2 minutes) and attribute the trace to their session.
    """
    if not trace_timestamp:
        return None

    conn = None
    try:
        from datetime import datetime, timedelta

        # Parse the timestamp
        if isinstance(trace_timestamp, str):
            trace_time = datetime.fromisoformat(trace_timestamp.replace("Z", "+00:00"))
        else:
            trace_time = trace_timestamp

        # Define the fuzzy window (±2 minutes)
        window_start = (trace_time - timedelta(minutes=2)).isoformat()
        window_end = (trace_time + timedelta(minutes=2)).isoformat()

        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()

        # Find messages from this user within the time window
        c.execute("""
            SELECT session_id FROM chat_messages
            WHERE username=? AND timestamp BETWEEN ? AND ?
            ORDER BY ABS(julianday(timestamp) - julianday(?))
            LIMIT 1
        """, (username, window_start, window_end, trace_timestamp))

        result = c.fetchone()
        if result:
            logger.info("Fuzzy matched trace at %s to user %s session %s",
                       trace_timestamp, username, result[0])
            return result[0]
        return None

    except (sqlite3.Error, ValueError, ImportError) as e:
        logger.error("Fuzzy session lookup failed for %s: %s", username, e)
        return None
    finally:
        if conn:
            conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_get_fuzzy_session_handles_database_error -v`
Expected: PASS

**Step 5: Run all auth tests**

Run: `pytest tests/test_auth.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "fix: replace bare excepts in get_fuzzy_session

- Use specific exceptions (sqlite3.Error, ValueError, ImportError)
- Initialize conn to None for safe cleanup
- Improve error logging with context
- Remove unnecessary else after return"
```

---

## Task 4: Create Database Connection Context Manager

**Files:**
- Modify: `auth.py:1-20` (add at top after constants)
- Test: `tests/test_auth.py`

**Step 1: Write test for context manager**

Add to `tests/test_auth.py`:

```python
def test_db_connection_context_manager(temp_db):
    """Test that db_connection context manager works correctly."""
    from auth import db_connection

    # Should successfully connect and execute query
    with db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        assert len(tables) > 0  # Should have at least 'users' table

    # Connection should be closed after context
    # (No way to test this directly, but if no error raised, it worked)

def test_db_connection_handles_errors(temp_db, mocker):
    """Test that db_connection handles errors and still closes connection."""
    from auth import db_connection

    with db_connection() as conn:
        c = conn.cursor()
        # This should work normally
        c.execute("SELECT 1")

    # Even if we patch connect to fail, context manager should handle it
    mocker.patch('auth.sqlite3.connect', side_effect=sqlite3.Error("Connection failed"))

    try:
        with db_connection() as conn:
            pass  # Should raise
    except sqlite3.Error:
        pass  # Expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_db_connection_context_manager -v`
Expected: FAIL - ImportError: cannot import name 'db_connection'

**Step 3: Implement the context manager**

Add after line 14 in `auth.py` (after DB_TIMEOUT constant):

```python
from contextlib import contextmanager

@contextmanager
def db_connection():
    """
    Context manager for database connections.

    Usage:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT ...")

    Ensures connection is always closed, even on errors.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        yield conn
    finally:
        if conn:
            conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_db_connection_context_manager -v`
Expected: PASS

**Step 5: Run test for error handling**

Run: `pytest tests/test_auth.py::test_db_connection_handles_errors -v`
Expected: PASS

**Step 6: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add database connection context manager

- Create @contextmanager for safe DB connections
- Ensures connections always closed via finally block
- Add comprehensive tests for normal and error cases"
```

---

## Task 5: Refactor init_db to Use Context Manager

**Files:**
- Modify: `auth.py:18-83`

**Step 1: Refactor init_db**

Replace `init_db()` function in `auth.py`:

```python
def init_db():
    """Initializes the database and creates all necessary tables for Users, Traces, and Settings."""
    with db_connection() as conn:
        c = conn.cursor()

        # Enable a 'high-performance' mode for our database
        c.execute("PRAGMA journal_mode=WAL")

        # TABLE 1: USERS (Stores usernames and passwords)
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password TEXT, session_id TEXT)''')

        # Update the users table if we added new features (like credit limits)
        c.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in c.fetchall()]
        if 'session_id' not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN session_id TEXT")
        if 'credit_limit' not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN credit_limit REAL")

        # TABLE 2: TRACES (Receipts of AI interactions)
        c.execute('''CREATE TABLE IF NOT EXISTS traces
                     (trace_id TEXT PRIMARY KEY, user_id TEXT, agent_id TEXT,
                      credits REAL, created_at TIMESTAMP)''')

        # Ensure current tables have all the columns needed for new features
        c.execute("PRAGMA table_info(traces)")
        existing_trace_cols = [column[1] for column in c.fetchall()]
        for col in ['input', 'output', 'session_id', 'inspect']:
            if col not in existing_trace_cols:
                c.execute(f"ALTER TABLE traces ADD COLUMN {col} TEXT")

        # TABLE 3: MAPPINGS (Connects anonymous AI records to real users)
        c.execute('''CREATE TABLE IF NOT EXISTS trace_user_mapping
                     (trace_id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT)''')

        # TABLE 4: SETTINGS (Global rules for the entire app)
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')

        # TABLE 5: CHAT HISTORY (Saves your actual conversations)
        c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT,
                      session_id TEXT,
                      role TEXT,
                      content TEXT,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Set up some default rules if they are missing.
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_credits', '2.0')")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_api_key', '')")
        c.execute("UPDATE settings SET value = '' WHERE key = 'admin_api_key' AND (value IS NULL OR value = '' OR trim(value) = '')")

        conn.commit()
```

**Step 2: Run all tests to ensure no regression**

Run: `pytest tests/test_auth.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add auth.py
git commit -m "refactor: use db_connection context manager in init_db

- Replace manual connection management
- Automatic cleanup on success or failure
- Cleaner, more maintainable code"
```

---

## Task 6: Remove Unused Imports

**Files:**
- Modify: `app.py`
- Modify: `auth.py`

**Step 1: Run autoflake to identify unused imports**

Run: `autoflake --check --remove-all-unused-imports app.py auth.py`
Expected: Shows unused imports in both files

**Step 2: Remove unused imports from app.py**

In `app.py`, remove line 4:
```python
import os  # REMOVE THIS LINE
```

**Step 3: Remove unused imports from auth.py**

In `auth.py`, remove lines 5-6:
```python
import uuid  # REMOVE THIS LINE
import os    # REMOVE THIS LINE
```

**Step 4: Run tests to ensure no regression**

Run: `pytest -v`
Expected: All 77 tests PASS

**Step 5: Commit**

```bash
git add app.py auth.py
git commit -m "chore: remove unused imports

- Remove unused 'os' import from app.py
- Remove unused 'uuid' and 'os' imports from auth.py
- Identified via autoflake static analysis"
```

---

## Task 7: Fix Import Order (PEP 8)

**Files:**
- Modify: `app.py`
- Modify: `auth.py`
- Modify: `lyzr_client.py`

**Step 1: Run isort in check mode**

Run: `isort --check-only --diff app.py auth.py lyzr_client.py`
Expected: Shows import order violations

**Step 2: Auto-fix import order**

Run: `isort app.py auth.py lyzr_client.py`
Expected: Imports reordered according to PEP 8 (stdlib → third-party → local)

**Step 3: Verify changes**

In `app.py`, imports should now be:
```python
# Standard library
import uuid

# Third-party
import streamlit as st
from dotenv import load_dotenv

# Local
from auth import (
    init_db,
    create_user,
    ...
)
from lyzr_client import AGENT_ID
from utils.ui import inject_custom_css, ...
from views.login import show_login_page
...
```

**Step 4: Run tests to ensure no regression**

Run: `pytest -v`
Expected: All 77 tests PASS

**Step 5: Commit**

```bash
git add app.py auth.py lyzr_client.py
git commit -m "style: fix import order per PEP 8

- Reorder imports: stdlib → third-party → local
- Applied via isort
- No functional changes"
```

---

## Task 8: Apply Code Formatting with Black

**Files:**
- Modify: All `.py` files

**Step 1: Run black in check mode**

Run: `black --check --line-length 120 .`
Expected: Shows files that would be reformatted

**Step 2: Apply black formatting**

Run: `black --line-length 120 .`
Expected: Reformats all Python files

**Step 3: Review changes**

Run: `git diff`
Expected: See formatting changes (mostly whitespace, line breaks)

**Step 4: Run tests to ensure no regression**

Run: `pytest -v`
Expected: All 77 tests PASS

**Step 5: Commit**

```bash
git add .
git commit -m "style: apply black code formatting

- Line length: 120 characters
- Removes trailing whitespace
- Standardizes string quotes and spacing
- No functional changes"
```

---

## Task 9: Add Database Indexes for Performance

**Files:**
- Modify: `auth.py:init_db()`
- Test: `tests/test_auth.py`

**Step 1: Write test to verify indexes exist**

Add to `tests/test_auth.py`:

```python
def test_database_has_performance_indexes(temp_db):
    """Test that performance indexes are created."""
    from auth import db_connection

    with db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in c.fetchall()]

        # Check for our custom indexes (exclude auto-created primary key indexes)
        expected_indexes = [
            'idx_chat_messages_user_session',
            'idx_traces_user_agent',
            'idx_traces_created_at'
        ]

        for idx in expected_indexes:
            assert idx in indexes, f"Missing index: {idx}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_database_has_performance_indexes -v`
Expected: FAIL - Indexes don't exist yet

**Step 3: Add indexes to init_db**

In `auth.py`, add before the final `conn.commit()` in `init_db()`:

```python
        # Create performance indexes
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_user_session
            ON chat_messages(username, session_id)
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_traces_user_agent
            ON traces(user_id, agent_id)
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_traces_created_at
            ON traces(created_at DESC)
        """)

        conn.commit()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_database_has_performance_indexes -v`
Expected: PASS

**Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "perf: add database indexes for common queries

- Index on (username, session_id) for chat history lookups
- Index on (user_id, agent_id) for trace filtering
- Index on created_at DESC for chronological queries
- Add test to verify indexes exist"
```

---

## Task 10: Update CLAUDE.md with New Patterns

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add context manager pattern to CLAUDE.md**

Add to the "Key Patterns & Decisions" section in `CLAUDE.md`:

```markdown
### Database Connection Pattern

All database operations use the `db_connection()` context manager:
```python
from auth import db_connection

with db_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT ...")
    result = c.fetchone()
# Connection automatically closed, even on errors
```

**Benefits**:
- Automatic cleanup (finally block)
- Exception-safe
- Consistent error handling
- Reduces boilerplate

**Do not** manually open/close connections except in special cases.
```

**Step 2: Add error handling guidelines**

Add to "Key Patterns & Decisions":

```markdown
### Exception Handling Standards

**Use specific exceptions:**
```python
# ✅ Good - Specific exceptions
try:
    conn = sqlite3.connect(DB_PATH)
except (sqlite3.Error, ValueError) as e:
    logger.error("Database operation failed: %s", e)

# ❌ Bad - Bare except or too broad
try:
    conn = sqlite3.connect(DB_PATH)
except:  # Catches SystemExit, KeyboardInterrupt!
    pass
```

**Always initialize resources before try:**
```python
conn = None
try:
    conn = sqlite3.connect(DB_PATH)
    # use conn
finally:
    if conn:
        conn.close()
```
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add database and error handling patterns to CLAUDE.md

- Document db_connection context manager usage
- Add exception handling best practices
- Provide good/bad examples for future reference"
```

---

## Verification & Cleanup

### Task 11: Final Test Suite Run

**Step 1: Run complete test suite**

Run: `pytest -v --tb=short`
Expected: All 77+ tests PASS (may be more if new tests added)

**Step 2: Check test coverage**

Run: `pytest --cov=. --cov-report=term-missing tests/`
Expected: Coverage report showing improved coverage in auth.py

**Step 3: Document results**

Create `docs/audit-fixes-results.md`:

```markdown
# Audit Fixes - Results

**Date**: 2026-02-17
**Tests**: [X]/[Y] passing
**Coverage**: XX%

## Fixed Issues
- ✅ Unbound variable in verify_password
- ✅ Bare except handlers (3 locations)
- ✅ Unused imports (3 files)
- ✅ Database connection management
- ✅ Code formatting (black + isort)
- ✅ Performance indexes added

## Metrics
- Lines changed: ~XXX
- Files modified: 5
- New tests added: 6
- Commits: 11
```

**Step 4: Commit**

```bash
git add docs/audit-fixes-results.md
git commit -m "docs: add audit fixes results summary"
```

---

## Related Skills

- @superpowers:executing-plans - Execute this plan task-by-task
- @superpowers:subagent-driven-development - Execute with fresh subagents per task
- @superpowers:verification-before-completion - Verify all tests pass before claiming done
- @superpowers:systematic-debugging - If any tests fail during implementation

---

## Notes

- All changes maintain backward compatibility
- Test suite must pass at each commit
- Database migrations are safe (CREATE IF NOT EXISTS, ALTER TABLE ADD)
- Code formatting is style-only, no functional changes

**Estimated Time**: 2-3 hours total (if following TDD steps carefully)
