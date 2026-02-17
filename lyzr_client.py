# --- 1. SETUP AND CORE CONFIGURATION ---
import requests  # The tool that allows our app to talk to other computers over the internet
import os        # Used to read secret keys and system settings
import json      # For handling complex data formats
import streamlit as st
from dotenv import load_dotenv  # Loads our 'Secret File' (.env) containing API keys

# Load the secret keys from the .env file immediately
load_dotenv(override=True)

# These are the default identities for our AI agent and API connection.
AGENT_ID = os.getenv("AGENT_ID")

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

# --- 3. THE 'CHAT' ENGINE ---
# This function sends your question to the Lyzr chat endpoint and gets an AI response.
# IMPORTANT: The chat response does NOT include trace data. Traces must be fetched separately
# via the get_traces() function which calls the traces endpoint.
def chat_with_agent(message, user_id, session_id, managed_agents=None):
    """Sends the user's message to the Lyzr AI chat endpoint and gets an answer back.
    
    Note: This returns only the chat response. To get trace/usage data, call get_traces() separately.
    """
    
    # 1. Get our secure authorization key.
    api_key = get_active_api_key()
    if not api_key or not AGENT_ID:
        return "Error: Missing Lyzr API Credentials. Please check your settings."

    # 2. Prepare the envelope (Headers) with the secret key.
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    # 3. Prepare the package (Payload) with your question and identity.
    payload = {
        "user_id": user_id,
        "agent_id": AGENT_ID,
        "session_id": session_id if session_id else "",
        "message": message
    }
    
    # 4. DEBUG LOGGING: Print what we are sending to the AI.
    print("\n--- 📤 LYZR API REQUEST ---")
    print(f"URL: {API_URL}")
    # Mask API key for security in logs
    masked_headers = headers.copy()
    if "x-api-key" in masked_headers:
        key = masked_headers["x-api-key"]
        masked_headers["x-api-key"] = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
    print(f"Headers: {json.dumps(masked_headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("---------------------------\n")

    # 5. SEND THE PACKAGE: We post this data to the Lyzr servers.
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() # Check if the servers are working correctly
        return response.json()      # Open the response package and return the data
    except Exception as err:
        return f"AI Connection Error: {err}. Please try again in a few minutes."

# --- 4. THE 'TRACES' ENGINE ---
# This function fetches trace/usage data from the Lyzr traces endpoint.
# Traces are NOT included in the chat response - they must be fetched separately via this endpoint.
def get_traces(user_id=None, session_id=None, agent_id=None, limit=100, offset=0, start_time=None):
    """Fetches trace/usage records from the Lyzr traces endpoint.
    
    IMPORTANT: Traces are NOT returned in the chat response. This separate endpoint must be called
    to retrieve trace data including costs, timestamps, and interaction details.
    """
    
    api_key = get_active_api_key()
    if not api_key: return []
    
    headers = {"x-api-key": api_key}
    
    # We specify which records we are looking for (e.g., only for a specific person).
    params = {
        "limit": limit,
        "offset": offset
    }
    
    if user_id: params["user_id"] = user_id
    if session_id: params["session_id"] = session_id
    if start_time:
        # Optimization: We look slightly before the start time to ensure no overlapping data is missed.
        try:
            from datetime import datetime, timedelta
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            params["start_time"] = (dt - timedelta(seconds=1)).isoformat()
        except:
            params["start_time"] = start_time

    # REACH OUT TO CLOUD: Download the interaction logs.
    try:
        response = requests.get(TRACES_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # --- DEBUG LOG: Cloud Traces ---
        print(f"☁️ [CLOUD SYNC]: Received {len(data.get('traces', [])) if isinstance(data, dict) else len(data)} records from cloud.")
        # ------------------------------

        # We clean up the data and turn it into a standard list format our dashboard can read.
        traces = data.get("traces", []) if isinstance(data, dict) else data
        
        # Local Filter by agent_id if requested (Lyzr API doesn't always support this param)
        if agent_id:
            traces = [t for t in traces if t.get("agent_id") == agent_id or not t.get("agent_id")]
            
        return traces
    except:
        return []
