# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lyzr AI Assistant** — A Streamlit-based educational chatbot platform for teaching Object-Oriented Programming (OOP) concepts using a single Lyzr AI agent. Features user authentication, credit limits, usage tracking, and admin controls.

## Quick Start

### Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
# Edit .env and set: LYZR_API_KEY, AGENT_ID

# Start the Streamlit app
streamlit run app.py
# Opens at http://localhost:8501

# Default admin login:
# Username: rohith.p@lyzr.ai
# Password: Rohith@123
```

### Running Tests

```bash
# Run all tests (77 tests total)
python -m pytest -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run specific test class or function
python -m pytest tests/test_auth.py::TestCreditLimits -v
python -m pytest tests/test_sync.py::TestCreditDivision::test_action_cost_divided_by_100 -v
```

## Architecture

### Entry Point & Navigation Flow

**app.py** is the entry point and orchestrator:
1. Initializes database (`init_db()`)
2. Creates default admin user
3. Loads custom CSS styling
4. Manages session state (`logged_in`, `username`, `session_id`, `page`)
5. Routes to views: Login → Chat/Dashboard/Settings

### Core Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| **app.py** | Entry point, navigation, sidebar (chat history, new chat, metrics, logout) |
| **auth.py** | All database operations: users, sessions, chat history, traces, settings (SQLite + bcrypt) |
| **lyzr_client.py** | API client for Lyzr: `chat_with_agent()`, `get_traces()` |
| **utils/sync.py** | Syncs cloud traces → local DB with three-way attribution (direct/mapping/fuzzy) |
| **utils/ui.py** | Custom CSS (dark theme, glassmorphism), logo base64 encoding |
| **views/login.py** | Login/registration UI |
| **views/chat.py** | Chat interface: message input, AI response, history, quota checks |
| **views/dashboard.py** | Usage charts, credit logs, admin user filter, sync button |
| **views/settings.py** | Admin-only: API key management, global/per-user credit limits |

### Critical Data Flow: Chat → Trace Attribution

1. **User sends message** (views/chat.py)
   - Calls `chat_with_agent(message, user_id, session_id)` (lyzr_client.py)
   - Saves temporary trace mapping: `save_trace_mapping(interaction_uuid, username, session_id)` (auth.py)
   - Saves message to `chat_messages` table

2. **Lyzr API processes request**
   - Returns chat response (no trace data in response)
   - Trace is created on Lyzr backend independently

3. **User clicks "Refresh & Sync"** (views/dashboard.py)
   - Calls `sync_user_activity(username, session_id)` (utils/sync.py)
   - Fetches traces from `get_traces()` (lyzr_client.py) — separate API endpoint
   - Attributes traces using **three-way attribution logic**:
     - **Direct Match**: `trace.user_id == username`
     - **Mapping Match**: Checks `trace_user_mapping` table for saved interaction UUIDs
     - **Fuzzy Match**: Time-based matching if user_id is unknown (matches traces within ±2 min of user activity)
   - Divides `action_cost` by 100 to convert to dollars
   - Saves traces to `traces` table via `save_traces_bulk()`

### Database Schema (SQLite + WAL mode)

Created/migrated in `auth.init_db()`:

- **users**: username (PK), password (bcrypt hashed), session_id, credit_limit (optional per-user limit)
- **chat_messages**: username, session_id, role (user/assistant), content, timestamp
- **traces**: trace_id (PK), user_id, agent_id, credits (USD), created_at, input, output, session_id, inspect (URL)
- **trace_user_mapping**: trace_id (PK, can be interaction_uuid), user_id, session_id (critical for fuzzy attribution)
- **settings**: key-value store (e.g., `max_credits` default limit, `admin_api_key`)

**Key Pattern**: Database uses `PRAGMA journal_mode=WAL` (Write-Ahead Logging) for concurrent read/write operations in Streamlit's multi-request environment.

## Key Patterns & Decisions

### Session State Management

Streamlit session state stores:
- `logged_in`, `username`, `isAdmin`
- `session_id` (persistent chat UUID, stored in DB)
- `messages` (current chat, loaded from `chat_messages` table)
- `page` (Chat/Dashboard/Settings navigation)

Session ID persists across refreshes via `get_user_session()` / `update_user_session()`.

### Credit Limit System

- Global limit: `settings.max_credits` (default $2.00)
- Per-user override: `users.credit_limit` (nullable)
- Admins bypass all limits (`isAdmin` flag)
- Enforcement in `views/chat.py`: blocks message send if `user_credits >= limit`

### API Key Security

- **Admin must manually set API key** in Settings page
- Never auto-populated from `.env` to database
- Retrieved dynamically via `get_active_api_key()` (lyzr_client.py)
- Masked in debug logs

### Test Isolation

- Every test gets isolated temp SQLite database via `conftest.py` fixtures
- All Lyzr API calls mocked with `pytest-mock` (no real network calls)
- Tests run in ~5 seconds total

## Common Tasks

### Adding a New View

1. Create `views/new_view.py` with `show_new_view()` function
2. Import in `app.py`
3. Add navigation button in sidebar (app.py lines 110-117)
4. Add route in view router (app.py lines 186-191)

### Modifying Database Schema

1. Update `init_db()` in `auth.py`
2. Add migration logic with `PRAGMA table_info()` checks (see existing patterns)
3. Create/update relevant getter/setter functions
4. Add tests in `tests/test_auth.py`

### Adding New Test

1. Add test function in appropriate `tests/test_*.py` file
2. Use `temp_db` fixture for database isolation
3. Mock external API calls with `mocker.patch`
4. Follow existing naming: `TestClassName::test_specific_case`

## Important Notes

- **Traces are NOT in chat response**: Must call `get_traces()` separately (lyzr_client.py)
- **Credit division**: `action_cost` from Lyzr is divided by 100 (utils/sync.py line 73)
- **Fuzzy attribution**: Matches traces without user_id to users based on ±2min activity window
- **WAL mode**: Required for Streamlit concurrency (database locked errors otherwise)
- **Default admin**: Created on startup (`rohith.p@lyzr.ai` / `Rohith@123`) — change in production
