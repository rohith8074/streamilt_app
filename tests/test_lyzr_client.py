"""
Tests for lyzr_client.py — Covers the Lyzr SDK client functions.

Modules tested:
  - get_active_api_key
  - LyzrClient (SDK wrapper)
  - chat_with_agent (SDK-based chat)
  - get_traces (SDK-based traces)
"""

import pytest
from unittest.mock import MagicMock
from auth import update_app_setting
from lyzr_client import get_active_api_key


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


# Old TestChatWithAgent and TestGetTraces classes removed
# Legacy functions have been replaced with SDK-based implementations
# See TestChatWithAgent and TestGetTraces below


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


class TestChatWithAgent:
    """Tests for chat_with_agent function using SDK."""

    def test_chat_with_agent_basic(self, mocker):
        """Test chat_with_agent uses SDK's agent.run() method."""
        from lyzr_client import chat_with_agent

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

        result = chat_with_agent(
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

    def test_chat_with_agent_missing_agent_id(self, mocker):
        """Test chat_with_agent returns error when AGENT_ID is missing."""
        from lyzr_client import chat_with_agent

        mocker.patch("lyzr_client.AGENT_ID", None)

        result = chat_with_agent(
            message="Hello",
            user_id="user@test.com",
            session_id="session-123"
        )

        assert "Error" in result
        assert "Missing" in result

    def test_chat_with_agent_with_managed_agents(self, mocker):
        """Test chat_with_agent passes managed_agents via kwargs."""
        from lyzr_client import chat_with_agent

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

        result = chat_with_agent(
            message="Route this",
            user_id="user@test.com",
            session_id="session-123",
            managed_agents=managed_agents
        )

        # Verify agent.run() was called with managed_agents in kwargs
        call_kwargs = mock_agent.run.call_args.kwargs
        assert "managed_agents" in call_kwargs
        assert call_kwargs["managed_agents"] == managed_agents


class TestFinalFunctionNames:
    """Tests to verify SDK functions use clean names without _sdk suffix."""

    def test_final_function_names(self):
        """Verify SDK functions use clean names without _sdk suffix."""
        import lyzr_client

        # Final clean names should exist (SDK-based implementations)
        assert hasattr(lyzr_client, "chat_with_agent")
        assert hasattr(lyzr_client, "get_traces")

        # SDK suffix versions should not exist
        assert not hasattr(lyzr_client, "chat_with_agent_sdk")
        assert not hasattr(lyzr_client, "get_traces_sdk")


class TestGetTraces:
    """Tests for get_traces function using SDK."""

    def test_get_traces_basic(self, mocker):
        """Test get_traces retrieves traces from SDK HTTP client."""
        from lyzr_client import get_traces

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

        result = get_traces(
            agent_id="test-agent-123",
            user_id="user@test.com",
            limit=100
        )

        assert len(result) == 1
        assert result[0]["trace_id"] == "trace-1"
        assert result[0]["action_cost"] == 150

    def test_get_traces_with_filters(self, mocker):
        """Test get_traces passes filter parameters correctly."""
        from lyzr_client import get_traces

        mock_response = []
        mock_client = MagicMock()
        mock_client.studio._http.get.return_value = mock_response

        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent")

        get_traces(
            agent_id="test-agent",
            user_id="user@test.com",
            session_id="session-123",
            limit=50,
            start_time="2026-02-17T10:00:00Z"
        )

        # Verify HTTP client was called with correct endpoint and params
        call_args = mock_client.studio._http.get.call_args
        assert "/v3/traces" in str(call_args)

    def test_get_traces_missing_agent_id(self, mocker):
        """Test get_traces returns empty list when agent_id is missing."""
        from lyzr_client import get_traces

        mocker.patch("lyzr_client.AGENT_ID", None)

        result = get_traces()
        assert result == []


class TestTopicTaxonomy:
    """Tests for TOPIC_TAXONOMY constant."""

    def test_oop_super_topic_exists(self):
        from lyzr_client import TOPIC_TAXONOMY
        assert "OOP (Object-Oriented Programming)" in TOPIC_TAXONOMY

    def test_oop_has_four_subtopics(self):
        from lyzr_client import TOPIC_TAXONOMY
        subtopics = TOPIC_TAXONOMY["OOP (Object-Oriented Programming)"]
        assert set(subtopics) == {"Encapsulation", "Inheritance", "Polymorphism", "Abstraction"}


class TestAgentIdConstants:
    """Tests for TUTOR_AGENT_ID and EVALUATOR_AGENT_ID module constants."""

    def test_tutor_and_evaluator_agent_ids_defined(self):
        import lyzr_client
        assert hasattr(lyzr_client, "TUTOR_AGENT_ID")
        assert hasattr(lyzr_client, "EVALUATOR_AGENT_ID")

    def test_tutor_agent_id_fallback_expression(self):
        """Verify that TUTOR_AGENT_ID uses the or-AGENT_ID fallback pattern."""
        import lyzr_client, inspect, textwrap
        # Read the source and confirm the fallback is in the module
        source = inspect.getsource(lyzr_client)
        assert "TUTOR_AGENT_ID = os.getenv" in source
        assert "or AGENT_ID" in source


class TestGetInstructionFile:
    """Tests for get_instruction_file() helper."""

    def test_encapsulation_returns_correct_path(self):
        from lyzr_client import get_instruction_file
        result = get_instruction_file("OOP (Object-Oriented Programming)", "Encapsulation")
        assert result == "learning_instructions/oop_encapsulation.md"

    def test_inheritance_returns_correct_path(self):
        from lyzr_client import get_instruction_file
        result = get_instruction_file("OOP (Object-Oriented Programming)", "Inheritance")
        assert result == "learning_instructions/oop_inheritance.md"

    def test_polymorphism_returns_correct_path(self):
        from lyzr_client import get_instruction_file
        result = get_instruction_file("OOP (Object-Oriented Programming)", "Polymorphism")
        assert result == "learning_instructions/oop_polymorphism.md"

    def test_abstraction_returns_correct_path(self):
        from lyzr_client import get_instruction_file
        result = get_instruction_file("OOP (Object-Oriented Programming)", "Abstraction")
        assert result == "learning_instructions/oop_abstraction.md"

    def test_sub_topic_is_lowercased(self):
        from lyzr_client import get_instruction_file
        result = get_instruction_file("OOP (Object-Oriented Programming)", "POLYMORPHISM")
        assert result == "learning_instructions/oop_polymorphism.md"

    def test_uses_prefix_from_super_topic_lookup(self):
        from lyzr_client import get_instruction_file, _SUPER_TOPIC_PREFIX
        # Verify the lookup dict exists and has the OOP entry
        assert "OOP (Object-Oriented Programming)" in _SUPER_TOPIC_PREFIX
        assert _SUPER_TOPIC_PREFIX["OOP (Object-Oriented Programming)"] == "oop"
        # Verify function output uses the prefix
        result = get_instruction_file("OOP (Object-Oriented Programming)", "Encapsulation")
        assert result.startswith("learning_instructions/oop_")
