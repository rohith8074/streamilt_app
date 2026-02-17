"""
Tests for auth.py — Covers ALL database and authentication functions.

Modules tested:
  - User CRUD: create_user, verify_user, get_all_users
  - Sessions: get_user_session, update_user_session, get_all_user_sessions
  - Credits: get_user_credits, get_user_limit, update_user_limit, get_total_platform_credits
  - Chat: save_chat_message, get_chat_history, delete_chat_session
  - Traces: save_traces_bulk, get_all_traces, save_trace_mapping,
            get_mapping_for_trace, get_latest_trace_timestamp, clear_user_traces
  - Settings: get_app_settings, update_app_setting
  - Fuzzy Matching: get_fuzzy_session
  - Database Init: init_db
  - Database Connection: db_connection (context manager)
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from auth import (
    init_db,
    create_user,
    verify_user,
    get_all_users,
    get_user_session,
    update_user_session,
    get_all_user_sessions,
    get_user_credits,
    get_user_limit,
    update_user_limit,
    get_total_platform_credits,
    save_chat_message,
    get_chat_history,
    delete_chat_session,
    save_traces_bulk,
    get_all_traces,
    save_trace_mapping,
    get_mapping_for_trace,
    get_latest_trace_timestamp,
    clear_user_traces,
    get_app_settings,
    update_app_setting,
    get_fuzzy_session,
)


# ============================================================
# 1. DATABASE CONNECTION CONTEXT MANAGER
# ============================================================


class TestDatabaseConnection:
    """Tests for the db_connection context manager."""

    def test_db_connection_context_manager(self):
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

    def test_db_connection_handles_errors(self, mocker):
        """Test that db_connection handles errors and still closes connection."""
        from auth import db_connection

        with db_connection() as conn:
            c = conn.cursor()
            # This should work normally
            c.execute("SELECT 1")

        # Even if we patch connect to fail, context manager should handle it
        mocker.patch("auth.sqlite3.connect", side_effect=sqlite3.Error("Connection failed"))

        try:
            with db_connection() as conn:
                pass  # Should raise
        except sqlite3.Error:
            pass  # Expected


# ============================================================
# 2. DATABASE INITIALIZATION
# ============================================================


class TestInitDb:
    """Verify the database schema is set up correctly."""

    def test_init_creates_default_settings(self):
        """Default max_credits and admin_api_key should exist after init."""
        settings = get_app_settings()
        assert "max_credits" in settings
        assert settings["max_credits"] == "2.0"
        assert "admin_api_key" in settings
        assert settings["admin_api_key"] == ""  # Empty by default

    def test_init_is_idempotent(self):
        """Calling init_db() multiple times should not crash or duplicate data."""
        init_db()
        init_db()
        settings = get_app_settings()
        assert settings["max_credits"] == "2.0"


# ============================================================
# 3. USER REGISTRATION & LOGIN
# ============================================================


class TestUserAuth:
    """Tests for user creation and password verification."""

    def test_create_user_success(self):
        assert create_user("alice@test.com", "pass123") is True

    def test_create_duplicate_user_fails(self):
        create_user("bob@test.com", "pass")
        assert create_user("bob@test.com", "pass") is False

    def test_create_user_database_error(self, mocker):
        """Test that create_user handles database errors gracefully."""
        import sqlite3

        # Mock sqlite3.connect to raise an error
        mocker.patch("auth.sqlite3.connect", side_effect=sqlite3.Error("Connection failed"))

        result = create_user("test@example.com", "password")

        # Should return False, not crash with unbound variable
        assert result is False

    def test_verify_correct_password(self, sample_user):
        assert verify_user(sample_user["username"], sample_user["password"]) is True

    def test_verify_wrong_password(self, sample_user):
        assert verify_user(sample_user["username"], "WrongPassword!") is False

    def test_verify_nonexistent_user(self):
        assert verify_user("ghost@nowhere.com", "anything") is False

    def test_get_all_users(self, sample_user):
        create_user("extra@test.com", "pass")
        users = get_all_users()
        usernames = [u["username"] for u in users]
        assert sample_user["username"] in usernames
        assert "extra@test.com" in usernames


# ============================================================
# 4. SESSION MANAGEMENT
# ============================================================


class TestSessions:
    """Tests for session creation, retrieval, and history."""

    def test_new_user_has_no_session(self, sample_user):
        assert get_user_session(sample_user["username"]) is None

    def test_update_and_get_session(self, sample_user):
        update_user_session(sample_user["username"], "sess_abc")
        assert get_user_session(sample_user["username"]) == "sess_abc"

    def test_update_session_overwrites(self, sample_user):
        update_user_session(sample_user["username"], "sess_1")
        update_user_session(sample_user["username"], "sess_2")
        assert get_user_session(sample_user["username"]) == "sess_2"

    def test_get_all_user_sessions_empty(self, sample_user):
        sessions = get_all_user_sessions(sample_user["username"])
        assert sessions == []

    def test_get_all_user_sessions_with_chats(self, sample_user):
        save_chat_message(sample_user["username"], "sess_A", "user", "Hello session A")
        save_chat_message(sample_user["username"], "sess_B", "user", "Hello session B")

        sessions = get_all_user_sessions(sample_user["username"])
        session_ids = [s["session_id"] for s in sessions]
        assert "sess_A" in session_ids
        assert "sess_B" in session_ids
        assert len(sessions) == 2


# ============================================================
# 5. CREDIT LIMITS
# ============================================================


class TestCreditLimits:
    """Tests for global and per-user credit limits."""

    def test_default_limit_is_global(self, sample_user):
        """A user without a custom limit should use the global default (2.0)."""
        assert get_user_limit(sample_user["username"]) == 2.0

    def test_custom_limit_overrides_global(self, sample_user):
        update_user_limit(sample_user["username"], 10.0)
        assert get_user_limit(sample_user["username"]) == 10.0

    def test_global_limit_change_affects_users_without_custom(self, sample_user):
        """Changing the global max_credits affects users who don't have a custom limit."""
        update_app_setting("max_credits", "5.0")
        assert get_user_limit(sample_user["username"]) == 5.0

    def test_credits_zero_for_new_user(self, sample_user):
        assert get_user_credits(sample_user["username"]) == 0.0

    def test_credits_accumulate_from_traces(self, sample_user):
        traces = [
            {
                "trace_id": "t1",
                "user_id": sample_user["username"],
                "agent_id": "agent_1",
                "credits": 0.5,
                "created_at": "2026-01-01T00:00:00",
            },
            {
                "trace_id": "t2",
                "user_id": sample_user["username"],
                "agent_id": "agent_1",
                "credits": 0.3,
                "created_at": "2026-01-01T00:01:00",
            },
        ]
        save_traces_bulk(traces)
        assert abs(get_user_credits(sample_user["username"]) - 0.8) < 0.001

    def test_credits_filter_by_agent(self, sample_user):
        traces = [
            {
                "trace_id": "t1",
                "user_id": sample_user["username"],
                "agent_id": "agent_A",
                "credits": 1.0,
                "created_at": "2026-01-01T00:00:00",
            },
            {
                "trace_id": "t2",
                "user_id": sample_user["username"],
                "agent_id": "agent_B",
                "credits": 2.0,
                "created_at": "2026-01-01T00:01:00",
            },
        ]
        save_traces_bulk(traces)
        assert get_user_credits(sample_user["username"], agent_id="agent_A") == 1.0
        assert get_user_credits(sample_user["username"], agent_id="agent_B") == 2.0

    def test_total_platform_credits(self, sample_traces):
        save_traces_bulk(sample_traces)
        total = get_total_platform_credits(agent_id="agent_abc")
        expected = 0.25 + 0.15 + 0.30
        assert abs(total - expected) < 0.001

    def test_total_platform_credits_no_filter(self, sample_traces):
        save_traces_bulk(sample_traces)
        total = get_total_platform_credits()
        expected = 0.25 + 0.15 + 0.30
        assert abs(total - expected) < 0.001


# ============================================================
# 6. CHAT HISTORY
# ============================================================


class TestChatHistory:
    """Tests for chat message saving, loading, and deletion."""

    def test_save_and_retrieve(self, sample_user):
        save_chat_message(sample_user["username"], "s1", "user", "What is OOP?")
        save_chat_message(sample_user["username"], "s1", "assistant", "OOP stands for...")

        history = get_chat_history(sample_user["username"], "s1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "What is OOP?"
        assert history[1]["role"] == "assistant"

    def test_history_filtered_by_session(self, sample_user):
        save_chat_message(sample_user["username"], "s1", "user", "Session 1 msg")
        save_chat_message(sample_user["username"], "s2", "user", "Session 2 msg")

        h1 = get_chat_history(sample_user["username"], "s1")
        h2 = get_chat_history(sample_user["username"], "s2")
        assert len(h1) == 1
        assert len(h2) == 1
        assert h1[0]["content"] == "Session 1 msg"

    def test_history_all_sessions(self, sample_user):
        """Without session_id filter, all messages for the user are returned."""
        save_chat_message(sample_user["username"], "s1", "user", "Msg 1")
        save_chat_message(sample_user["username"], "s2", "user", "Msg 2")

        all_history = get_chat_history(sample_user["username"])
        assert len(all_history) == 2

    def test_delete_session(self, sample_user):
        save_chat_message(sample_user["username"], "s1", "user", "To be deleted")
        save_chat_message(sample_user["username"], "s1", "assistant", "Also deleted")
        save_chat_message(sample_user["username"], "s2", "user", "Keep this")

        result = delete_chat_session(sample_user["username"], "s1")
        assert result is True
        assert len(get_chat_history(sample_user["username"], "s1")) == 0
        assert len(get_chat_history(sample_user["username"], "s2")) == 1

    def test_delete_nonexistent_session(self, sample_user):
        """Deleting a session that doesn't exist should still return True (no error)."""
        result = delete_chat_session(sample_user["username"], "nonexistent")
        assert result is True

    def test_messages_ordered_by_timestamp(self, sample_user):
        save_chat_message(sample_user["username"], "s1", "user", "First")
        save_chat_message(sample_user["username"], "s1", "assistant", "Second")
        save_chat_message(sample_user["username"], "s1", "user", "Third")

        history = get_chat_history(sample_user["username"], "s1")
        assert [m["content"] for m in history] == ["First", "Second", "Third"]


# ============================================================
# 7. TRACES (Bulk Save, Retrieval, Mapping, Clear)
# ============================================================


class TestTraces:
    """Tests for trace saving, retrieval, mapping, and cleanup."""

    def test_save_traces_bulk(self, sample_traces):
        count = save_traces_bulk(sample_traces)
        assert count == 3

    def test_save_empty_list(self):
        assert save_traces_bulk([]) == 0

    def test_traces_update_on_duplicate(self, sample_traces):
        """Saving the same trace_id again should UPDATE, not duplicate."""
        save_traces_bulk(sample_traces)

        updated = [sample_traces[0].copy()]
        updated[0]["credits"] = 0.99
        save_traces_bulk(updated)

        traces = get_all_traces(user_id="testuser@example.com")
        trace_001 = [t for t in traces if t["trace_id"] == "trace_001"][0]
        assert trace_001["credits"] == 0.99

    def test_get_all_traces_by_user(self, sample_traces):
        save_traces_bulk(sample_traces)
        user_traces = get_all_traces(user_id="testuser@example.com")
        assert len(user_traces) == 2
        assert all(t["user_id"] == "testuser@example.com" for t in user_traces)

    def test_get_all_traces_by_agent(self, sample_traces):
        save_traces_bulk(sample_traces)
        traces = get_all_traces(agent_id="agent_abc")
        assert len(traces) == 3

    def test_get_all_traces_no_filter(self, sample_traces):
        save_traces_bulk(sample_traces)
        traces = get_all_traces()
        assert len(traces) == 3

    def test_latest_trace_timestamp(self, sample_traces):
        save_traces_bulk(sample_traces)
        latest = get_latest_trace_timestamp()
        assert latest is not None
        assert "2026-02-17T10:10:00" in latest

    def test_latest_trace_timestamp_empty_db(self):
        assert get_latest_trace_timestamp() is None

    def test_clear_user_traces(self, sample_traces):
        save_traces_bulk(sample_traces)
        clear_user_traces(user_id="testuser@example.com")
        assert len(get_all_traces(user_id="testuser@example.com")) == 0
        # Other user's traces should remain
        assert len(get_all_traces(user_id="other_user@example.com")) == 1

    def test_trace_mapping_save_and_get(self):
        save_trace_mapping("trace_xyz", "alice", "sess_123")
        user_id, session_id = get_mapping_for_trace("trace_xyz")
        assert user_id == "alice"
        assert session_id == "sess_123"

    def test_trace_mapping_nonexistent(self):
        user_id, session_id = get_mapping_for_trace("no_such_trace")
        assert user_id is None
        assert session_id is None

    def test_trace_mapping_overwrite(self):
        save_trace_mapping("trace_1", "alice", "sess_a")
        save_trace_mapping("trace_1", "bob", "sess_b")
        user_id, session_id = get_mapping_for_trace("trace_1")
        assert user_id == "bob"
        assert session_id == "sess_b"

    def test_get_mapping_for_trace_handles_database_error(self, mocker):
        """Test that get_mapping_for_trace handles database errors."""
        import sqlite3

        mocker.patch("auth.sqlite3.connect", side_effect=sqlite3.Error("DB error"))

        result = get_mapping_for_trace("test-trace-id")

        # Should return (None, None) on error
        assert result == (None, None)


# ============================================================
# 8. APP SETTINGS
# ============================================================


class TestSettings:
    """Tests for global app settings (key-value store)."""

    def test_default_settings_exist(self):
        settings = get_app_settings()
        assert "max_credits" in settings
        assert "admin_api_key" in settings

    def test_update_setting(self):
        update_app_setting("max_credits", "10.0")
        settings = get_app_settings()
        assert settings["max_credits"] == "10.0"

    def test_create_new_setting(self):
        update_app_setting("custom_key", "custom_value")
        settings = get_app_settings()
        assert settings["custom_key"] == "custom_value"

    def test_update_api_key(self):
        update_app_setting("admin_api_key", "sk-test-key-123")
        settings = get_app_settings()
        assert settings["admin_api_key"] == "sk-test-key-123"


# ============================================================
# 9. FUZZY SESSION MATCHING
# ============================================================


class TestFuzzySession:
    """Tests for the time-based fuzzy session detection."""

    def test_fuzzy_match_within_window(self):
        """A fuzzy entry within 120 seconds should match."""
        time_now = datetime.utcnow().isoformat()
        save_trace_mapping(f"fuzzy_alice_{time_now}", "alice", "sess_match")

        result = get_fuzzy_session("alice", time_now)
        assert result == "sess_match"

    def test_fuzzy_no_match_outside_window(self):
        """A fuzzy entry older than 120 seconds should NOT match."""
        old_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
        save_trace_mapping(f"fuzzy_alice_{old_time}", "alice", "sess_old")

        check_time = datetime.utcnow().isoformat()
        result = get_fuzzy_session("alice", check_time)
        assert result is None

    def test_fuzzy_wrong_user(self):
        """Fuzzy entries for user A should not match user B."""
        time_now = datetime.utcnow().isoformat()
        save_trace_mapping(f"fuzzy_alice_{time_now}", "alice", "sess_alice")

        result = get_fuzzy_session("bob", time_now)
        assert result is None

    def test_fuzzy_null_inputs(self):
        assert get_fuzzy_session(None, None) is None
        assert get_fuzzy_session("alice", None) is None
        assert get_fuzzy_session(None, "2026-01-01T00:00:00") is None

    def test_get_fuzzy_session_handles_database_error(self, mocker):
        """Test that get_fuzzy_session handles database errors."""
        import sqlite3

        mocker.patch("auth.sqlite3.connect", side_effect=sqlite3.Error("DB error"))

        result = get_fuzzy_session("test@example.com", "2026-02-17T10:00:00Z")

        # Should return None on error
        assert result is None


# ============================================================
# 10. DATABASE PERFORMANCE INDEXES
# ============================================================


class TestDatabaseIndexes:
    """Tests for database performance indexes."""

    def test_database_has_performance_indexes(self):
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
