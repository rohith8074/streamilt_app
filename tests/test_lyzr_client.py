"""
Tests for lyzr_client.py — Covers the Lyzr API client functions.

Modules tested:
  - get_active_api_key
  - chat_with_agent (mocked HTTP)
  - get_traces (mocked HTTP)
"""
import pytest
from unittest.mock import MagicMock
from auth import update_app_setting
from lyzr_client import get_active_api_key, chat_with_agent, get_traces


class TestGetActiveApiKey:
    """Tests for API key retrieval from the database settings."""

    def test_returns_none_when_empty(self):
        """Default admin_api_key is empty, so should return None."""
        assert get_active_api_key() is None

    def test_returns_none_for_whitespace(self):
        update_app_setting("admin_api_key", "   ")
        assert get_active_api_key() is None

    def test_returns_key_when_set(self):
        update_app_setting("admin_api_key", "sk-real-key-123")
        assert get_active_api_key() == "sk-real-key-123"


class TestChatWithAgent:
    """Tests for the chat_with_agent function (all HTTP calls are mocked)."""

    def test_returns_error_when_no_api_key(self, mocker):
        """If no API key is set, should return an error string."""
        mocker.patch("lyzr_client.get_active_api_key", return_value=None)
        result = chat_with_agent("Hello", "user1", "sess1")
        assert "Error" in result
        assert "Missing" in result

    def test_returns_error_when_no_agent_id(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")
        mocker.patch("lyzr_client.AGENT_ID", None)
        result = chat_with_agent("Hello", "user1", "sess1")
        assert "Error" in result

    def test_successful_chat(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")
        mocker.patch("lyzr_client.AGENT_ID", "agent_test")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "OOP is great!"}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("lyzr_client.requests.post", return_value=mock_response)

        result = chat_with_agent("What is OOP?", "user1", "sess1")
        assert result["response"] == "OOP is great!"

    def test_network_error_returns_error_string(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")
        mocker.patch("lyzr_client.AGENT_ID", "agent_test")
        mocker.patch("lyzr_client.requests.post", side_effect=Exception("Connection timeout"))

        result = chat_with_agent("Hello", "user1", "sess1")
        assert "AI Connection Error" in result


class TestGetTraces:
    """Tests for the get_traces function (all HTTP calls are mocked)."""

    def test_returns_empty_when_no_api_key(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value=None)
        assert get_traces() == []

    def test_successful_trace_fetch(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "traces": [
                {"trace_id": "t1", "action_cost": 10},
                {"trace_id": "t2", "action_cost": 20}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mocker.patch("lyzr_client.requests.get", return_value=mock_response)

        traces = get_traces()
        assert len(traces) == 2
        assert traces[0]["trace_id"] == "t1"

    def test_trace_fetch_with_agent_filter(self, mocker):
        """When agent_id is passed, only matching traces should be returned."""
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "traces": [
                {"trace_id": "t1", "agent_id": "agent_A"},
                {"trace_id": "t2", "agent_id": "agent_B"},
                {"trace_id": "t3"},  # No agent_id — should also pass
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mocker.patch("lyzr_client.requests.get", return_value=mock_response)

        traces = get_traces(agent_id="agent_A")
        trace_ids = [t["trace_id"] for t in traces]
        assert "t1" in trace_ids
        assert "t3" in trace_ids  # No agent_id passes the filter
        assert "t2" not in trace_ids

    def test_network_error_returns_empty(self, mocker):
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")
        mocker.patch("lyzr_client.requests.get", side_effect=Exception("Network error"))

        assert get_traces() == []

    def test_list_response_format(self, mocker):
        """Some API versions return a list instead of {'traces': [...]}'."""
        mocker.patch("lyzr_client.get_active_api_key", return_value="sk-key")

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"trace_id": "t1"},
            {"trace_id": "t2"}
        ]
        mock_response.raise_for_status = MagicMock()
        mocker.patch("lyzr_client.requests.get", return_value=mock_response)

        traces = get_traces()
        assert len(traces) == 2
