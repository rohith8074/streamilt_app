# --- 1. SETUP AND CORE CONFIGURATION ---
import json  # For handling complex data formats
import logging
import os  # Used to read secret keys and system settings

import requests  # The tool that allows our app to talk to other computers over the internet
import streamlit as st
from dotenv import load_dotenv  # Loads our 'Secret File' (.env) containing API keys
from lyzr import Studio

# Load the secret keys from the .env file immediately
load_dotenv(override=True)

# Set up logging
logger = logging.getLogger(__name__)

# These are the default identities for our AI agent and API connection.
AGENT_ID = os.getenv("AGENT_ID")
LYZR_API_KEY = os.getenv("LYZR_API_KEY")
LYZR_BASE_URL = os.getenv("LYZR_BASE_URL", "https://api.lyzr.app")

# --- TOPIC TAXONOMY ---
TOPIC_TAXONOMY = {
    "OOP (Object-Oriented Programming)": [
        "Encapsulation",
        "Inheritance",
        "Polymorphism",
        "Abstraction",
    ]
}

TUTOR_AGENT_ID = os.getenv("TUTOR_AGENT_ID") or AGENT_ID
EVALUATOR_AGENT_ID = os.getenv("EVALUATOR_AGENT_ID")


def get_instruction_file(super_topic: str, sub_topic: str) -> str:
    """Return the path to the markdown instruction file for a topic.

    Args:
        super_topic: e.g. "OOP (Object-Oriented Programming)"
        sub_topic: e.g. "Encapsulation"

    Returns:
        Relative file path, e.g. "learning_instructions/oop_encapsulation.md"
    """
    prefix = "oop"  # Only OOP supported; extend here for future super-topics
    return f"learning_instructions/{prefix}_{sub_topic.lower()}.md"


# --- SDK WRAPPER CLASS ---
class LyzrClient:
    """Wrapper class for lyzr-adk SDK Studio."""

    def __init__(self, api_key: str = None, env: str = "prod"):
        """Initialize Lyzr client with SDK.

        Args:
            api_key: Lyzr API key (defaults to get_active_api_key() or LYZR_API_KEY env var)
            env: Environment ('prod' or 'dev', defaults to 'prod')

        Raises:
            ValueError: If API key is not provided
        """
        # Try to get API key from: parameter > get_active_api_key() > env var
        if api_key:
            self.api_key = api_key
        else:
            # Try database first (for runtime), then env var (for tests)
            self.api_key = get_active_api_key() or LYZR_API_KEY

        self.env = env

        if not self.api_key:
            raise ValueError("LYZR_API_KEY environment variable or api_key parameter is required")

        # Initialize Studio with API key and environment
        self.studio = Studio(api_key=self.api_key, env=self.env)
        logger.info(f"Initialized Lyzr SDK client with env: {self.env}")


# --- 2. DYNAMIC API KEY RETRIEVAL ---
def get_active_api_key():
    """Returns the Lyzr API key only from Admin Settings. Admin must set it manually in Settings."""
    try:
        from auth import get_app_settings

        settings = get_app_settings()
        db_key = settings.get("admin_api_key")
        if db_key and db_key.strip():
            return db_key
    except Exception:
        pass
    return None


# Set the active URL endpoints (where we send our messages).
API_URL = os.getenv("LYZR_API_URL", "https://agent-prod.studio.lyzr.ai/v3/inference/chat/")
TRACES_URL = os.getenv("LYZR_TRACES_URL", "https://agent-prod.studio.lyzr.ai/v3/traces")


# --- SDK CHAT FUNCTION ---
def chat_with_agent(
    message: str,
    user_id: str,
    session_id: str,
    agent_id: str = None,
    managed_agents: list = None
):
    """
    Send a chat message using lyzr-adk SDK.

    Args:
        message: User's message
        user_id: User identifier (email)
        session_id: Session UUID string
        agent_id: Agent ID (defaults to AGENT_ID env var)
        managed_agents: List of specialist agents for routing

    Returns:
        dict: Response with 'response' key, or error string

    Raises:
        None: Returns error strings instead of raising exceptions
    """
    agent_id = agent_id or AGENT_ID

    if not agent_id:
        return "Error: Missing Lyzr API Credentials. Please configure AGENT_ID."

    try:
        # Initialize SDK client
        client = LyzrClient()

        # Get agent instance from agent_id
        agent = client.studio.agents.get(agent_id)

        # Build run parameters
        run_kwargs = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id
        }

        # Add managed_agents if provided (for manager agent routing)
        if managed_agents:
            run_kwargs["managed_agents"] = managed_agents

        # Execute chat using SDK
        response = agent.run(**run_kwargs)

        # Convert AgentResponse to dict format matching old API
        result = {
            "response": response.response if hasattr(response, 'response') else str(response)
        }

        logger.info(f"SDK chat successful for user {user_id}, session {session_id}")
        return result

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        return f"Error: Missing Lyzr API Credentials. Please check your settings."
    except Exception as e:
        logger.error(f"SDK chat error: {e}")
        return f"AI Connection Error: {e}. Please try again."


# --- SDK TRACES FUNCTION ---
def get_traces(
    agent_id: str = None,
    user_id: str = None,
    session_id: str = None,
    limit: int = 100,
    offset: int = 0,
    start_time: str = None
):
    """
    Retrieve traces from Lyzr using SDK's HTTP client.

    Note: The SDK doesn't have a public traces API, so we use the internal HTTP client
    to call the /v3/traces endpoint directly.

    Args:
        agent_id: Filter by agent ID (defaults to AGENT_ID env var)
        user_id: Filter by user ID
        session_id: Filter by session ID
        limit: Maximum number of traces to retrieve
        offset: Number of traces to skip
        start_time: ISO timestamp to fetch traces after

    Returns:
        list: List of trace dictionaries

    Raises:
        None: Returns empty list on errors
    """
    agent_id = agent_id or AGENT_ID

    if not agent_id:
        logger.warning("Cannot fetch traces: Missing AGENT_ID")
        return []

    try:
        # Initialize SDK client
        client = LyzrClient()

        # Build query parameters
        params = {
            "limit": limit,
            "offset": offset
        }

        if user_id:
            params["user_id"] = user_id
        if session_id:
            params["session_id"] = session_id
        if start_time:
            # Optimization: Look slightly before start time to avoid missing data
            try:
                from datetime import datetime, timedelta
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                params["start_time"] = (dt - timedelta(seconds=1)).isoformat()
            except:
                params["start_time"] = start_time

        # Call traces endpoint using SDK's HTTP client
        # Note: Using internal _http client since SDK doesn't expose public traces API
        response = client.studio._http.get("/v3/traces", params=params)

        # Handle response format (could be dict with 'traces' key or list directly)
        traces = response.get("traces", []) if isinstance(response, dict) else response

        # Local filter by agent_id (API may not support this param)
        if agent_id:
            traces = [t for t in traces if t.get("agent_id") == agent_id or not t.get("agent_id")]

        logger.info(f"Retrieved {len(traces)} traces from SDK")
        return traces

    except Exception as e:
        logger.error(f"Failed to fetch traces via SDK: {e}")
        return []


# --- LEGACY FUNCTIONS REMOVED ---
# Old requests-based chat_with_agent() and get_traces() functions have been removed.
# Use chat_with_agent_sdk() and get_traces_sdk() instead (see above).
