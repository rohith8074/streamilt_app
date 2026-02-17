# Code Audit Report - Lyzr AI Assistant

**Date**: 2026-02-17
**Tools Used**: Pyright, Pylint, Flake8, Manual Code Review

---

## Executive Summary

The codebase is functional and has comprehensive test coverage (77 tests). However, there are several areas for improvement in code quality, security, type safety, and maintainability.

### Priority Breakdown
- 🔴 **Critical** (Security & Bugs): 5 issues
- 🟡 **Medium** (Code Quality): 12 issues
- 🟢 **Low** (Style & Formatting): 50+ issues

---

## 🔴 Critical Issues

### 1. SQL Injection Vulnerability (auth.py)
**Location**: `auth.py:119, 122, 372` and multiple other locations
**Issue**: Direct string formatting in SQL queries
```python
# VULNERABLE - Current code
c.execute(f"ALTER TABLE traces ADD COLUMN {col} TEXT")
```

**Risk**: Potential SQL injection if column names are ever derived from user input

**Fix**: Use parameterized queries or whitelist allowed column names
```python
# SAFE
allowed_cols = ['input', 'output', 'session_id', 'inspect']
if col in allowed_cols:
    c.execute(f"ALTER TABLE traces ADD COLUMN {col} TEXT")
```

**Status**: Low risk currently (hardcoded values), but should be fixed for future-proofing

---

### 2. Bare Exception Handlers (auth.py:167, 365, 390)
**Location**: `auth.py:167`, `auth.py:365`, `auth.py:390`
**Issue**: Using bare `except:` catches system exits and keyboard interrupts
```python
# PROBLEM
try:
    some_operation()
except: return None  # Catches SystemExit, KeyboardInterrupt, etc.
```

**Risk**: Hides critical errors, makes debugging difficult

**Fix**: Catch specific exceptions
```python
except (sqlite3.Error, ValueError) as e:
    logger.error(f"Operation failed: {e}")
    return None
```

---

### 3. Unbound Variable (auth.py:167)
**Location**: `auth.py:163-168`
**Issue**: `conn` may be unbound if exception occurs during connection
```python
def verify_password(username, password):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        # ... code ...
    except: return False  # conn may not exist
    finally: conn.close()  # ERROR: conn potentially unbound
```

**Fix**: Initialize conn before try block or check existence
```python
conn = None
try:
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    # ...
finally:
    if conn:
        conn.close()
```

---

### 4. Broad Exception Catching (auth.py, lyzr_client.py)
**Location**: Multiple locations catching `Exception`
**Issue**: Catching `Exception` is too broad; masks unexpected errors
```python
except Exception as e:  # Too broad
    logger.error(f"Error: {e}")
```

**Fix**: Catch specific exceptions
```python
except (sqlite3.Error, requests.RequestException, ValueError) as e:
    logger.error(f"Expected error: {e}")
```

---

### 5. Password Comparison Timing Attack (auth.py:167)
**Location**: `auth.py:163-168` (`verify_password`)
**Issue**: Direct string comparison for passwords may leak information via timing
```python
if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
```

**Risk**: Low (bcrypt already uses constant-time comparison internally)
**Recommendation**: No change needed; bcrypt.checkpw is secure

---

## 🟡 Medium Priority Issues

### 6. Missing Type Hints
**Location**: All files
**Issue**: No type annotations; reduces IDE support and catches bugs

**Fix**: Add type hints incrementally
```python
# Before
def get_user_credits(username, agent_id=None):

# After
def get_user_credits(username: str, agent_id: Optional[str] = None) -> float:
```

**Recommendation**: Start with public API functions, then expand

---

### 7. Import Organization
**Location**: Multiple files
**Issue**: Imports not following PEP 8 order (stdlib → third-party → local)

**Fix**: Reorganize imports
```python
# Correct order
import os          # stdlib
import uuid        # stdlib

import bcrypt      # third-party
import streamlit   # third-party

from auth import init_db  # local
```

**Tool**: Use `isort` to auto-fix

---

### 8. Unused Imports
**Location**:
- `app.py:4` - `import os` (unused)
- `auth.py:5` - `import uuid` (unused)
- `auth.py:6` - `import os` (unused)

**Fix**: Remove or use them

---

### 9. Magic Numbers and Hardcoded Values
**Location**: Multiple files
**Issue**: Hardcoded values reduce maintainability

**Examples**:
- `auth.py:73` - `max_credits` default value `'2.0'`
- `lyzr_client.py:83` - Default limit `100`
- `utils/sync.py:73` - Credit division by `100.0`

**Fix**: Extract to constants
```python
# At top of file
DEFAULT_MAX_CREDITS = 2.0
CREDIT_CONVERSION_FACTOR = 100.0
DEFAULT_TRACE_LIMIT = 100
```

---

### 10. Long Functions
**Location**: Several functions exceed 50 lines
**Issue**: Reduces readability and testability

**Examples**:
- `sync_user_activity()` - 80+ lines
- `show_chat_view()` - 100+ lines
- `show_dashboard_view()` - 150+ lines

**Fix**: Extract helper functions
```python
# Before: one giant function
def sync_user_activity(username, session_id):
    # 80 lines of logic

# After: break into logical chunks
def sync_user_activity(username, session_id):
    api_traces = fetch_traces_from_api(username)
    validated_traces = validate_and_attribute_traces(api_traces, username)
    save_traces_to_db(validated_traces)
```

---

### 11. Inconsistent Error Handling
**Location**: Across all files
**Issue**: Some functions return error strings, others raise exceptions, some return None

**Examples**:
- `chat_with_agent()` returns error string: `"Error: Missing Lyzr API Credentials"`
- `verify_password()` returns `False` on error
- `get_user_credits()` returns `0.0` on error

**Fix**: Standardize error handling strategy
```python
# Option 1: Raise exceptions (preferred for library code)
def get_user_credits(username: str) -> float:
    if not username:
        raise ValueError("Username cannot be empty")

# Option 2: Return Result type (for user-facing code)
def chat_with_agent(...) -> dict:
    return {"success": True, "data": response}
    # or
    return {"success": False, "error": "Missing API key"}
```

---

### 12. Database Connection Management
**Location**: `auth.py` - throughout
**Issue**: Repetitive connection creation/closing; no connection pooling

**Current Pattern** (repeated 20+ times):
```python
def some_function():
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    # do work
    conn.close()
```

**Fix**: Use context managers
```python
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    try:
        yield conn
    finally:
        conn.close()

# Usage
def some_function():
    with get_db_connection() as conn:
        c = conn.cursor()
        # do work
```

---

### 13. Logging Best Practices
**Location**: `auth.py:268, 393`
**Issue**: Using f-strings in logging calls (inefficient if logging disabled)

```python
# CURRENT (inefficient)
logger.error(f"Error saving traces: {e}")

# BETTER (lazy evaluation)
logger.error("Error saving traces: %s", e)
```

---

### 14. Hard-Coded Admin Credentials
**Location**: `app.py:37`
**Issue**: Default admin password committed to code
```python
create_user("rohith.p@lyzr.ai", "Rohith@123")
```

**Risk**: Security issue if repository is public or shared

**Fix**:
1. Generate random password on first run
2. Store in environment variable
3. Force password change on first login
4. Log the generated password to console only once

```python
# Better approach
import secrets

admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    admin_password = secrets.token_urlsafe(16)
    print(f"🔐 Generated admin password: {admin_password}")
    print("⚠️  Set ADMIN_PASSWORD in .env to persist")

create_user("rohith.p@lyzr.ai", admin_password)
```

---

### 15. API Key Storage Security
**Location**: `auth.py:73`, Settings page
**Issue**: API key stored in plaintext in SQLite

**Risk**: Database file readable = API key exposed

**Fix**: Encrypt sensitive settings
```python
from cryptography.fernet import Fernet

# Generate key once, store in .env (or OS keyring)
ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

def save_encrypted_setting(key, value):
    encrypted = cipher.encrypt(value.encode())
    # save to db

def get_decrypted_setting(key):
    encrypted = # load from db
    return cipher.decrypt(encrypted).decode()
```

---

### 16. No Input Validation
**Location**: Throughout, especially user-facing functions
**Issue**: Missing validation for user inputs

**Examples**:
- Username/password length checks
- Credit limit range validation
- Session ID format validation

**Fix**: Add validation layer
```python
def create_user(username: str, password: str) -> bool:
    # Validate inputs
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
        raise ValueError("Username must be valid email")

    # Proceed with creation
    ...
```

---

### 17. Session ID Collision Risk
**Location**: `app.py:163`, multiple files using `uuid.uuid4()`
**Issue**: UUIDs generated without checking for collisions

**Risk**: Extremely low (~zero) for UUID4, but good practice to verify

**Fix**: Add collision check
```python
def generate_unique_session_id(username: str) -> str:
    """Generate session ID and ensure uniqueness."""
    max_attempts = 5
    for _ in range(max_attempts):
        session_id = str(uuid.uuid4())
        existing = get_user_session(username)  # Check DB
        if existing != session_id:
            return session_id
    raise RuntimeError("Failed to generate unique session ID")
```

---

## 🟢 Low Priority (Style & Formatting)

### 18. Code Formatting Issues
**Findings**:
- 50+ trailing whitespace violations
- 20+ lines exceeding 120 characters
- Inconsistent spacing around operators
- Multiple statements on one line (e.g., `if x: return y`)

**Fix**: Run auto-formatters
```bash
# Install formatters
pip install black isort flake8

# Format all code
black app.py auth.py lyzr_client.py utils/ views/
isort app.py auth.py lyzr_client.py utils/ views/

# Check style
flake8 . --max-line-length=120
```

**Recommendation**: Add to pre-commit hooks

---

### 19. Documentation Gaps
**Location**: All files
**Issue**: Many functions lack docstrings

**Fix**: Add comprehensive docstrings
```python
def sync_user_activity(username: str, session_id: str) -> int:
    """
    Synchronizes user activity traces from Lyzr API to local database.

    Fetches traces since last sync, attributes them to users via three-way
    matching (direct/mapping/fuzzy), converts credits, and saves to DB.

    Args:
        username: User's email identifier
        session_id: Current chat session UUID

    Returns:
        Number of traces successfully synced

    Raises:
        sqlite3.Error: If database operation fails
        requests.RequestException: If API call fails
    """
    ...
```

---

### 20. Magic Strings
**Location**: Throughout
**Issue**: Repeated string literals reduce maintainability

**Examples**:
- `"rohith.p@lyzr.ai"` appears 3+ times
- Database column names repeated in multiple functions
- Error messages duplicated

**Fix**: Use constants
```python
# At top of auth.py
ADMIN_EMAIL = "rohith.p@lyzr.ai"
DEFAULT_SESSION_ID_COLUMN = "session_id"
DEFAULT_CREDIT_LIMIT_COLUMN = "credit_limit"

# Error messages
ERR_MISSING_API_KEY = "Error: Missing Lyzr API Credentials"
ERR_NETWORK_FAILURE = "AI Connection Error: {err}. Please try again."
```

---

## Performance Considerations

### 21. Database Query Optimization
**Location**: `auth.py` - various functions
**Issue**: Missing indexes on frequently queried columns

**Recommendation**: Add indexes
```sql
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_session
    ON chat_messages(username, session_id);

CREATE INDEX IF NOT EXISTS idx_traces_user_agent
    ON traces(user_id, agent_id);

CREATE INDEX IF NOT EXISTS idx_traces_created_at
    ON traces(created_at DESC);
```

---

### 22. Inefficient Queries
**Location**: `auth.py:389` - `get_all_user_sessions()`
**Issue**: Loads entire chat history just to get preview

**Current**:
```python
# Loads ALL messages, then processes in Python
messages = get_chat_history(username, session_id)
```

**Optimized**:
```sql
-- Get just the first message for preview
SELECT content FROM chat_messages
WHERE username=? AND session_id=?
ORDER BY timestamp ASC LIMIT 1
```

---

## Testing Gaps

### 23. Missing Test Coverage
**Areas not fully tested**:
- Error handling paths in `sync.py`
- Edge cases in fuzzy session matching
- Dashboard filtering with invalid user
- Settings validation (negative credit limits, etc.)
- Concurrent access scenarios (SQLite WAL mode)

**Recommendation**: Add integration tests
```python
# tests/test_concurrent.py
def test_concurrent_chat_saves(temp_db):
    """Test that WAL mode handles concurrent writes."""
    import threading

    def save_message(user_id):
        save_chat_message(f"user{user_id}", "session1", "user", "test")

    threads = [threading.Thread(target=save_message, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Verify all 10 messages saved
    assert count_messages("session1") == 10
```

---

## Recommendations Summary

### Immediate Actions (This Week)
1. ✅ Fix unbound variable in `auth.py:167` (5 min)
2. ✅ Replace bare excepts with specific exceptions (30 min)
3. ✅ Remove unused imports (5 min)
4. ✅ Run `black` and `isort` for code formatting (10 min)
5. ✅ Add database connection context manager (1 hour)

### Short Term (This Month)
6. Add type hints to public API functions
7. Extract magic numbers to constants
8. Add input validation layer
9. Improve error handling consistency
10. Add database indexes

### Long Term (Next Quarter)
11. Encrypt sensitive settings in database
12. Refactor long functions (>50 lines)
13. Add comprehensive integration tests
14. Set up pre-commit hooks with linters
15. Consider migrating to async database driver (aiosqlite)

---

## Automated Fixes

The following can be auto-fixed:

```bash
# 1. Format code
pip install black isort
black .
isort .

# 2. Remove unused imports
pip install autoflake
autoflake --remove-all-unused-imports --in-place --recursive .

# 3. Sort imports
isort .

# 4. Fix common issues
pip install autopep8
autopep8 --in-place --aggressive --recursive .
```

---

## Conclusion

The codebase is well-structured with good test coverage. The main areas for improvement are:
- **Security**: Encrypt API keys, validate inputs, fix exception handling
- **Maintainability**: Add type hints, extract constants, refactor long functions
- **Performance**: Add database indexes, optimize queries
- **Code Quality**: Fix formatting, improve error handling consistency

**Estimated effort**: ~2-3 days to address critical and medium priority issues.

---

## Lyzr SDK Migration (2026-02-17)

**Status:** ✅ Complete

**Summary:** Successfully migrated from direct HTTP API calls to the official lyzr-adk SDK (version 0.1.5).

### Changes Implemented

**Dependencies:**
- Added `lyzr-adk>=0.1.5,<1.0.0` to requirements.txt
- SDK provides `Studio` class and `Agent.run()` for chat operations
- Import path: `from lyzr import Studio, Agent`

**Code Changes:**
- Created `LyzrClient` wrapper class for SDK initialization
- Migrated `chat_with_agent()` to use `agent.run()` method
- Migrated `get_traces()` to use SDK's internal HTTP client (workaround for missing public API)
- Updated `views/chat.py` to use SDK-based chat function
- Updated `utils/sync.py` to use SDK-based trace retrieval
- Removed legacy requests-based functions

**Test Updates:**
- Updated all test mocks to reference SDK functions
- Added SDK-specific test classes
- All 86 tests passing (previously 77)
- Maintained 97%+ code coverage

**Documentation:**
- Updated CLAUDE.md with SDK usage patterns
- Updated .env.example with SDK configuration
- Documented SDK limitations and workarounds

### Benefits

- **Official SDK support** with built-in error handling
- **Better maintainability** as SDK evolves
- **Future-ready** for streaming, memory, knowledge bases, RAI guardrails
- **Reduced maintenance burden** compared to direct API calls

### SDK Limitations & Workarounds

1. **No public traces API**: Used SDK's internal `_http.get("/v3/traces")` client
2. **Response format**: Converted `AgentResponse` to dict for backward compatibility
3. **Limited versions**: Only 0.1.x available (not 1.0.0+ as originally planned)

### Breaking Changes

**None** - All API signatures maintained for backward compatibility. Migration was transparent to end users.

### Git Commits

1. `44e0c57` - feat: add lyzr-adk SDK dependency
2. `28e7ae7` - feat: create LyzrClient wrapper class for SDK
3. `f476b7d` - feat: implement chat_with_agent_sdk using SDK
4. `7df214e` - feat: implement get_traces_sdk using SDK HTTP client
5. `b34bc96` - feat: migrate chat view to use SDK
6. `07dcec2` - feat: migrate sync to use SDK and fix parameter naming
7. `593360b` - refactor: remove legacy requests-based API functions
8. `d79a9ec` - refactor: remove _sdk suffix from function names

### Next Steps (Optional Future Enhancements)

- Enable streaming with `agent.run_stream()` for real-time chat responses
- Integrate knowledge bases for enhanced context
- Enable RAI guardrails for responsible AI checks
- Explore SDK's built-in memory management features
