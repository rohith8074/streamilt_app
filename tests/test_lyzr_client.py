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
            "traces": [{"trace_id": "t1", "action_cost": 10}, {"trace_id": "t2", "action_cost": 20}]
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
        mock_response.json.return_value = [{"trace_id": "t1"}, {"trace_id": "t2"}]
        mock_response.raise_for_status = MagicMock()
        mocker.patch("lyzr_client.requests.get", return_value=mock_response)

        traces = get_traces()
        assert len(traces) == 2


class TestLyzrSDKImport:
    """Tests for lyzr-adk SDK availability."""

    def test_lyzr_adk_import(self):
        """Verify lyzr-adk SDK can be imported."""
        try:
            from lyzr import Studio, Agent
            assert Studio is not None
            assert Agent is not None
        except ImportError:
            pytest.fail("lyzr-adk not installed")


class TestLyzrClient:
    """Tests for LyzrClient wrapper class."""

    def test_lyzr_client_initialization(self, mocker):
        """Test LyzrClient initializes with API key from parameter."""
        from lyzr_client import LyzrClient

        # Mock get_active_api_key to return None (so it uses parameter)
        mocker.patch("lyzr_client.get_active_api_key", return_value=None)

        client = LyzrClient(api_key="test-key-123")
        assert client.studio is not None
        assert client.api_key == "test-key-123"
        assert client.env == "prod"

    def test_lyzr_client_missing_api_key(self, mocker):
        """Test LyzrClient raises error when API key is missing."""
        from lyzr_client import LyzrClient

        # Mock both get_active_api_key and LYZR_API_KEY to return None
        mocker.patch("lyzr_client.get_active_api_key", return_value=None)
        mocker.patch("lyzr_client.LYZR_API_KEY", None)

        with pytest.raises(ValueError, match="LYZR_API_KEY"):
            LyzrClient()

    def test_lyzr_client_with_custom_env(self):
        """Test LyzrClient accepts API key and env as parameters."""
        from lyzr_client import LyzrClient

        client = LyzrClient(api_key="custom-key", env="dev")
        assert client.api_key == "custom-key"
        assert client.env == "dev"
        assert client.studio is not None

    def test_lyzr_client_from_database(self, mocker):
        """Test LyzrClient uses get_active_api_key() when no parameter provided."""
        from lyzr_client import LyzrClient

        # Mock get_active_api_key to return a key from database
        mocker.patch("lyzr_client.get_active_api_key", return_value="db-key-456")

        client = LyzrClient()
        assert client.api_key == "db-key-456"
        assert client.studio is not None


class TestChatWithAgentSDK:
    """Tests for chat_with_agent_sdk function using SDK."""

    def test_chat_with_agent_sdk_basic(self, mocker):
        """Test chat_with_agent_sdk uses SDK's agent.run() method."""
        from lyzr_client import chat_with_agent_sdk

        # Mock the Agent instance and its run method
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="Test SDK response")

        # Mock studio.agents.get to return our mock agent
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent

        # Mock LyzrClient to return our mock client
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent-123")
        mocker.patch("lyzr_client.get_active_api_key", return_value="test-key")

        result = chat_with_agent_sdk(
            message="Hello SDK",
            user_id="user@test.com",
            session_id="session-123"
        )

        assert "response" in result
        assert result["response"] == "Test SDK response"
        mock_agent.run.assert_called_once_with(
            message="Hello SDK",
            user_id="user@test.com",
            session_id="session-123"
        )

    def test_chat_with_agent_sdk_missing_agent_id(self, mocker):
        """Test chat_with_agent_sdk returns error when AGENT_ID is missing."""
        from lyzr_client import chat_with_agent_sdk

        mocker.patch("lyzr_client.AGENT_ID", None)

        result = chat_with_agent_sdk(
            message="Hello",
            user_id="user@test.com",
            session_id="session-123"
        )

        assert "Error" in result
        assert "Missing" in result

    def test_chat_with_agent_sdk_with_managed_agents(self, mocker):
        """Test chat_with_agent_sdk passes managed_agents via kwargs."""
        from lyzr_client import chat_with_agent_sdk

        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="Routed response")

        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent

        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "manager-agent")
        mocker.patch("lyzr_client.get_active_api_key", return_value="test-key")

        managed_agents = [
            {"id": "agent-1", "name": "Specialist 1"},
            {"id": "agent-2", "name": "Specialist 2"}
        ]

        result = chat_with_agent_sdk(
            message="Route this",
            user_id="user@test.com",
            session_id="session-123",
            managed_agents=managed_agents
        )

        # Verify agent.run() was called with managed_agents in kwargs
        call_kwargs = mock_agent.run.call_args.kwargs
        assert "managed_agents" in call_kwargs
        assert call_kwargs["managed_agents"] == managed_agents


class TestGetTracesSDK:
    """Tests for get_traces_sdk function using SDK."""

    def test_get_traces_sdk_basic(self, mocker):
        """Test get_traces_sdk retrieves traces from SDK HTTP client."""
        from lyzr_client import get_traces_sdk

        # Mock HTTP response
        mock_response = [
            {
                "trace_id": "trace-1",
                "user_id": "user@test.com",
                "agent_id": "test-agent-123",
                "session_id": "session-abc",
                "action_cost": 150,
                "created_at": "2026-02-17T10:30:00Z",
                "input_data": {"query": "Hello"},
                "output_data": {"response": "Hi"}
            }
        ]

        # Mock the HTTP client's get method
        mock_http_get = mocker.Mock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.studio._http.get.return_value = mock_response

        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent-123")

        result = get_traces_sdk(
            agent_id="test-agent-123",
            user_id="user@test.com",
            limit=100
        )

        assert len(result) == 1
        assert result[0]["trace_id"] == "trace-1"
        assert result[0]["action_cost"] == 150

    def test_get_traces_sdk_with_filters(self, mocker):
        """Test get_traces_sdk passes filter parameters correctly."""
        from lyzr_client import get_traces_sdk

        mock_response = []
        mock_client = MagicMock()
        mock_client.studio._http.get.return_value = mock_response

        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent")

        get_traces_sdk(
            agent_id="test-agent",
            user_id="user@test.com",
            session_id="session-123",
            limit=50,
            since_timestamp="2026-02-17T10:00:00Z"
        )

        # Verify HTTP client was called with correct endpoint and params
        call_args = mock_client.studio._http.get.call_args
        assert "/v3/traces" in str(call_args)

    def test_get_traces_sdk_missing_agent_id(self, mocker):
        """Test get_traces_sdk returns empty list when agent_id is missing."""
        from lyzr_client import get_traces_sdk

        mocker.patch("lyzr_client.AGENT_ID", None)

        result = get_traces_sdk()
        assert result == []
