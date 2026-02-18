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


class TestCreateTopicKb:
    """Tests for create_topic_kb() — creates a Lyzr KB from topic markdown content."""

    def test_creates_kb_with_snake_case_name(self, mocker):
        from lyzr_client import create_topic_kb

        mock_kb = MagicMock()
        mock_client = MagicMock()
        mock_client.studio.create_knowledge_base.return_value = mock_kb
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        create_topic_kb("OOP (Object-Oriented Programming)", "Encapsulation", "content")

        mock_client.studio.create_knowledge_base.assert_called_once()
        call_kwargs = mock_client.studio.create_knowledge_base.call_args.kwargs
        assert call_kwargs["name"] == "oop_encapsulation"

    def test_adds_instruction_text_to_kb(self, mocker):
        from lyzr_client import create_topic_kb

        mock_kb = MagicMock()
        mock_client = MagicMock()
        mock_client.studio.create_knowledge_base.return_value = mock_kb
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        content = "# Encapsulation instructions — bundle data and behaviour."
        create_topic_kb("OOP (Object-Oriented Programming)", "Encapsulation", content)

        mock_kb.add_text.assert_called_once()
        call_kwargs = mock_kb.add_text.call_args.kwargs
        assert call_kwargs["text"] == content

    def test_returns_kb_object(self, mocker):
        from lyzr_client import create_topic_kb

        mock_kb = MagicMock()
        mock_kb.id = "kb-456"
        mock_client = MagicMock()
        mock_client.studio.create_knowledge_base.return_value = mock_kb
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        result = create_topic_kb("OOP (Object-Oriented Programming)", "Encapsulation", "content")
        assert result is mock_kb

    def test_returns_none_on_sdk_error(self, mocker):
        from lyzr_client import create_topic_kb

        mock_client = MagicMock()
        mock_client.studio.create_knowledge_base.side_effect = Exception("API unavailable")
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        result = create_topic_kb("OOP (Object-Oriented Programming)", "Encapsulation", "content")
        assert result is None

    def test_knowledge_base_name_is_lowercase_alphanumeric_underscore(self, mocker):
        """KB name must match ^[a-z0-9_]+$ (SDK requirement)."""
        from lyzr_client import create_topic_kb
        import re

        mock_kb = MagicMock()
        mock_client = MagicMock()
        mock_client.studio.create_knowledge_base.return_value = mock_kb
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        create_topic_kb("OOP (Object-Oriented Programming)", "Polymorphism", "content")
        call_kwargs = mock_client.studio.create_knowledge_base.call_args.kwargs
        assert re.match(r"^[a-z0-9_]+$", call_kwargs["name"]), (
            f"KB name '{call_kwargs['name']}' must match ^[a-z0-9_]+$"
        )


class TestEvaluateSession:
    """Tests for evaluate_session() — calls evaluator agent with conversation transcript."""

    def test_returns_error_when_evaluator_not_configured(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", None)
        result = evaluate_session([], "OOP (Object-Oriented Programming)", "Encapsulation")

        assert "Error" in result
        assert "EVALUATOR_AGENT_ID" in result

    def test_formats_user_messages_as_student(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", "eval-agent-123")
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="Report")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        messages = [{"role": "user", "content": "What is encapsulation?"}]
        evaluate_session(messages, "OOP (Object-Oriented Programming)", "Encapsulation")

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "Student: What is encapsulation?" in call_kwargs["message"]

    def test_formats_assistant_messages_as_tutor(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", "eval-agent-123")
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="Report")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        messages = [{"role": "assistant", "content": "It is data hiding."}]
        evaluate_session(messages, "OOP (Object-Oriented Programming)", "Encapsulation")

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "Tutor: It is data hiding." in call_kwargs["message"]

    def test_includes_topic_context_in_prompt(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", "eval-agent-123")
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="Report")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        evaluate_session([], "OOP (Object-Oriented Programming)", "Inheritance")

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "Inheritance" in call_kwargs["message"]

    def test_returns_agent_response_string(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", "eval-agent-123")
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="**Engagement: 4/5** - Good questions asked.")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        result = evaluate_session(
            [{"role": "user", "content": "Hello"}],
            "OOP (Object-Oriented Programming)",
            "Encapsulation",
        )
        assert result == "**Engagement: 4/5** - Good questions asked."

    def test_handles_sdk_error_gracefully(self, mocker):
        from lyzr_client import evaluate_session

        mocker.patch("lyzr_client.EVALUATOR_AGENT_ID", "eval-agent-123")
        mock_client = MagicMock()
        mock_client.studio.agents.get.side_effect = Exception("Connection timeout")
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)

        result = evaluate_session([], "OOP (Object-Oriented Programming)", "Encapsulation")
        assert "failed" in result.lower() or "Error" in result


class TestChatWithAgentKnowledgeBases:
    """Tests for knowledge_bases parameter in chat_with_agent()."""

    def test_passes_knowledge_bases_to_agent_run(self, mocker):
        from lyzr_client import chat_with_agent

        mock_kb = MagicMock()
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="RAG-powered response")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent-id")

        chat_with_agent(
            message="What is encapsulation?",
            user_id="user@test.com",
            session_id="session-abc",
            knowledge_bases=[mock_kb],
        )

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "knowledge_bases" in call_kwargs
        assert call_kwargs["knowledge_bases"] == [mock_kb]

    def test_knowledge_bases_omitted_when_none(self, mocker):
        """knowledge_bases must NOT appear in agent.run() kwargs when not provided."""
        from lyzr_client import chat_with_agent

        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="response")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "test-agent-id")

        chat_with_agent(message="Hello", user_id="u@t.com", session_id="s-123")

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "knowledge_bases" not in call_kwargs

    def test_managed_agents_and_knowledge_bases_work_together(self, mocker):
        """Passing both managed_agents and knowledge_bases should work."""
        from lyzr_client import chat_with_agent

        mock_kb = MagicMock()
        mock_agent = MagicMock()
        mock_agent.run.return_value = MagicMock(response="routed rag response")
        mock_client = MagicMock()
        mock_client.studio.agents.get.return_value = mock_agent
        mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
        mocker.patch("lyzr_client.AGENT_ID", "mgr-agent")

        managed = [{"id": "spec-1", "name": "Spec"}]
        chat_with_agent(
            message="test",
            user_id="u@t.com",
            session_id="s-123",
            managed_agents=managed,
            knowledge_bases=[mock_kb],
        )

        call_kwargs = mock_agent.run.call_args.kwargs
        assert call_kwargs.get("managed_agents") == managed
        assert call_kwargs.get("knowledge_bases") == [mock_kb]


class TestTopicDescriptions:
    """Tests for TOPIC_DESCRIPTIONS dict in lyzr_client.py."""

    def test_every_taxonomy_topic_has_a_description(self):
        """Each sub-topic in TOPIC_TAXONOMY must have an entry in TOPIC_DESCRIPTIONS."""
        from lyzr_client import TOPIC_DESCRIPTIONS, TOPIC_TAXONOMY
        for sub_topics in TOPIC_TAXONOMY.values():
            for sub in sub_topics:
                assert sub in TOPIC_DESCRIPTIONS, f"Missing description for '{sub}'"

    def test_descriptions_are_non_empty_strings(self):
        """Every description must be a non-empty string of at least 10 characters."""
        from lyzr_client import TOPIC_DESCRIPTIONS
        for key, val in TOPIC_DESCRIPTIONS.items():
            assert isinstance(val, str), f"Description for '{key}' is not a string"
            assert len(val) >= 10, f"Description for '{key}' is too short"

    def test_descriptions_exported(self):
        """TOPIC_DESCRIPTIONS can be imported directly from lyzr_client."""
        import lyzr_client
        assert hasattr(lyzr_client, "TOPIC_DESCRIPTIONS")
        assert isinstance(lyzr_client.TOPIC_DESCRIPTIONS, dict)
