"""
Tests for utils/sync.py — Covers the Lyzr-to-local sync pipeline.

Modules tested:
  - Credit division (/100)
  - User attribution (direct match, mapping match, fuzzy match)
  - Security: traces from other users are skipped
  - Edge cases: zero cost, missing fields, empty API response
"""
import pytest
from datetime import datetime
from utils.sync import sync_user_activity
from auth import (
    get_all_traces, save_trace_mapping, save_traces_bulk,
    get_user_credits
)


class TestCreditDivision:
    """Verify that raw API costs are correctly divided by 100."""

    def test_action_cost_divided_by_100(self, mocker):
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_div",
            "user_id": "alice",
            "session_id": "s1",
            "action_cost": 50.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert len(traces) == 1
        assert traces[0]["credits"] == 0.5  # 50.0 / 100

    def test_total_credits_field_divided(self, mocker):
        """Some API responses use 'total_credits' instead of 'action_cost'."""
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_tc",
            "user_id": "alice",
            "total_credits": 200.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert traces[0]["credits"] == 2.0  # 200 / 100

    def test_zero_cost_trace(self, mocker):
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_zero",
            "user_id": "alice",
            "action_cost": 0.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert traces[0]["credits"] == 0.0

    def test_missing_cost_defaults_to_zero(self, mocker):
        """If neither action_cost nor total_credits is present, credits should be 0."""
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_nocost",
            "user_id": "alice",
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert traces[0]["credits"] == 0.0


class TestUserAttribution:
    """Verify traces are correctly attributed to the right user."""

    def test_direct_user_match(self, mocker):
        """Traces where user_id matches the calling user should be saved."""
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_direct",
            "user_id": "alice",
            "action_cost": 10.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        count = sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert len(traces) == 1

    def test_mapping_match(self, mocker):
        """Traces matched via saved trace_user_mapping should be attributed."""
        save_trace_mapping("t_mapped", "bob", "sess_bob")

        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_mapped",
            "user_id": "unknown",
            "action_cost": 5.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("bob", "sess_bob")

        traces = get_all_traces(user_id="bob")
        assert len(traces) == 1
        assert traces[0]["user_id"] == "bob"

    def test_fuzzy_match(self, mocker):
        """Traces with 'unknown' user_id should match via fuzzy timestamp."""
        time_now = datetime.utcnow().isoformat()
        save_trace_mapping(f"fuzzy_carol_{time_now}", "carol", "sess_carol")

        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_fuzzy",
            "user_id": "unknown",
            "action_cost": 7.0,
            "trace_start_time": time_now
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("carol", "sess_carol")

        traces = get_all_traces(user_id="carol")
        assert len(traces) == 1
        assert traces[0]["user_id"] == "carol"


class TestSecuritySkip:
    """Verify traces belonging to OTHER users are correctly skipped."""

    def test_other_user_trace_skipped(self, mocker):
        """A trace with user_id='bob' should NOT be saved when syncing for 'alice'."""
        mocker.patch("utils.sync.get_traces", return_value=[{
            "trace_id": "t_bobs",
            "user_id": "bob",
            "action_cost": 99.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        assert len(get_all_traces(user_id="alice")) == 0
        assert len(get_all_traces(user_id="bob")) == 0  # NOT saved at all

    def test_mixed_traces_only_own_saved(self, mocker):
        """Only the current user's traces should be saved from a mixed batch."""
        mocker.patch("utils.sync.get_traces", return_value=[
            {"trace_id": "t_mine", "user_id": "alice", "action_cost": 10.0,
             "trace_start_time": "2026-02-17T10:00:00Z"},
            {"trace_id": "t_other", "user_id": "bob", "action_cost": 20.0,
             "trace_start_time": "2026-02-17T10:01:00Z"},
        ])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        assert len(get_all_traces(user_id="alice")) == 1
        assert len(get_all_traces(user_id="bob")) == 0


class TestEdgeCases:
    """Edge cases and error handling for sync."""

    def test_empty_api_response(self, mocker):
        mocker.patch("utils.sync.get_traces", return_value=[])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        count = sync_user_activity("alice", "s1")
        assert count == 0

    def test_none_api_response(self, mocker):
        mocker.patch("utils.sync.get_traces", return_value=None)
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        count = sync_user_activity("alice", "s1")
        assert count == 0

    def test_trace_without_trace_id_skipped(self, mocker):
        """A trace missing a trace_id should be skipped gracefully."""
        mocker.patch("utils.sync.get_traces", return_value=[{
            "user_id": "alice",
            "action_cost": 10.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
            # No trace_id at all
        }])
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")

        assert len(get_all_traces(user_id="alice")) == 0

    def test_duplicate_sync_updates_not_duplicates(self, mocker):
        """Running sync twice with the same data should UPDATE, not duplicate."""
        trace_data = [{
            "trace_id": "t_dup",
            "user_id": "alice",
            "action_cost": 10.0,
            "trace_start_time": "2026-02-17T10:00:00Z"
        }]
        mocker.patch("utils.sync.get_traces", return_value=trace_data)
        mocker.patch("utils.sync.get_latest_trace_timestamp", return_value=None)

        sync_user_activity("alice", "s1")
        sync_user_activity("alice", "s1")

        traces = get_all_traces(user_id="alice")
        assert len(traces) == 1  # NOT 2
