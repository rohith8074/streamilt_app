# --- 1. SETUP AND TOOLS ---
import streamlit as st  # For the website interface
import os  # For reading environment variables
import uuid  # For creating unique session IDs
import json  # For handling complex data structures
from auth import (  # Importing our database helper functions
    get_user_credits,
    get_user_limit,
    update_user_session,
    save_chat_message,
    save_trace_mapping,
)
from lyzr_client import chat_with_agent_sdk, AGENT_ID  # For talking to the AI via SDK


def show_chat_view():
    """This function builds the main AI conversation screen."""

    # --- 2. THE HEADER ---
    # Spacer so the heading is not clipped at the top of the viewport
    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 🤖 Lyzr AI Chat")
    st.caption("Manager Agent is online. Ready to route your request to specialists.")

    # --- 3. SPECIALIST AGENTS CONFIGURATION ---
    # We define a group of 'Expert Agents' who specialize in different areas.
    # The 'Manager Agent' will choose the best one to answer your question.
    managed_agents = []
    agent_configs = [
        ("ENCAPSULATION_AGENT_ID", "Encapsulation Specialist", "Handles queries about data hiding and bundling."),
        ("INHERITANCE_AGENT_ID", "Inheritance Specialist", "Expert in class hierarchies and code reuse."),
        ("POLYMORPHISM_AGENT_ID", "Polymorphism Specialist", "Explains method overriding and interfaces."),
        ("ABSTRACTION_AGENT_ID", "Abstraction Specialist", "Focuses on abstract classes and simplification."),
    ]

    # We verify which of these experts are actually configured in our system.
    for env_key, name, desc in agent_configs:
        a_id = os.getenv(env_key)
        if a_id:
            managed_agents.append({"id": a_id, "name": name, "usage_description": desc})

    # Show the current Session ID (useful for debugging and tracking).
    if st.session_state.get("session_id"):
        st.caption(f"🆔 Current Session: `{st.session_state.session_id}`")

    # --- 4. DISPLAYING THE CONVERSATION ---
    # We loop through all previous messages and show them in a chat-like format.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 5. HANDLING NEW INPUT ---
    # This is the box where the user types their question.
    sid_hint = f"[{st.session_state.session_id[:8]}] " if st.session_state.get("session_id") else ""
    if prompt := st.chat_input(f"Ask me about OOPs"):

        # A. AUTOMATIC SYNC:
        # Before we check your budget, we quickly download your latest usage from the AI servers.
        # This prevents the "Free Chat" loophole where you could use more credits than allowed.
        from utils.sync import sync_user_activity

        with st.spinner("Verifying your remaining credits..."):
            sync_user_activity(st.session_state.username, st.session_state.session_id)

        # B. BUDGET CHECK: Make sure the user hasn't run out of credits.
        user_credits = get_user_credits(st.session_state.username, agent_id=AGENT_ID)
        max_limit = get_user_limit(st.session_state.username)

        if user_credits >= max_limit and not st.session_state.isAdmin:
            st.error(
                f"⚠️ **Credit Limit Reached**: You have spent ${user_credits:.4f} of your ${max_limit:.2f} allowance. Please contact the administrator."
            )
            return

        # C. SESSION SETUP: Ensure the conversation has a unique ID.
        if not st.session_state.session_id:
            st.session_state.session_id = str(uuid.uuid4())
            if st.session_state.username:
                update_user_session(st.session_state.username, st.session_state.session_id)

        # C. SHOW USER MESSAGE: Display what you just typed and save it to the database.
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_chat_message(st.session_state.username, st.session_state.session_id, "user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        # D. GET AI RESPONSE: Send your question to the Lyzr AI service.
        # Note: The chat response does NOT include trace data. Traces are fetched separately via sync_user_activity().
        with st.spinner("Manager Agent is routing your request to a specialist..."):
            # --- LOG: User Query ---
            print(f"\n[USER QUERY]: {prompt}")
            print(f"[SESSION ID]: {st.session_state.session_id}")

            # This is the actual call to the Lyzr AI service using SDK.
            # Traces must be fetched separately from the traces endpoint.
            api_data = chat_with_agent_sdk(
                message=prompt,
                user_id=st.session_state.username,
                session_id=st.session_state.session_id,
                managed_agents=managed_agents if managed_agents else None,
            )

            # --- LOG: Agent Response ---
            print(f"[AGENT RESPONSE]: {json.dumps(api_data, indent=2) if isinstance(api_data, dict) else api_data}")

            # E. PROCESS THE RESPONSE: Translate the AI's data back into readable text.
            # Note: The chat response does NOT include trace data. Traces must be fetched separately via get_traces().
            if isinstance(api_data, dict):
                response_val = api_data.get("response", "No response from agent.")
                internal_data = {}
                # Sometimes the response is wrapped in extra layers; we dig through them.
                if isinstance(response_val, str):
                    try:
                        internal_data = json.loads(response_val)
                        response = internal_data.get("response_text") or response_val
                    except:
                        response = response_val
                elif isinstance(response_val, dict):
                    internal_data = response_val
                    response = json.dumps(response_val, indent=2)
                else:
                    response = response_val

                # F. TRACKING: Save session mapping for later trace attribution.
                # Since traces are fetched separately via the traces endpoint, we save a timestamp-based
                # mapping to help match traces to this user/session when syncing.
                active_session = api_data.get("session_id") or st.session_state.session_id

                # Save a fuzzy timestamp mapping so we can match traces later (traces API may not have user_id immediately)
                from datetime import datetime

                # 🕒 UTC TIME: We use UTC here to match the cloud receipts from Lyzr traces endpoint.
                timestamp_now = datetime.utcnow().isoformat()
                save_trace_mapping(
                    f"fuzzy_{st.session_state.username}_{timestamp_now}", st.session_state.username, active_session
                )

                # If the AI started a new underlying session, we update our records.
                if api_data.get("session_id") and api_data.get("session_id") != st.session_state.session_id:
                    update_user_session(st.session_state.username, api_data.get("session_id"))
                    st.session_state.session_id = api_data.get("session_id")
            else:
                # If something went wrong, the error message is our response.
                response = api_data

        # G. SHOW AI RESPONSE: Display the AI's answer and save it to the database.
        st.session_state.messages.append({"role": "assistant", "content": response})
        save_chat_message(st.session_state.username, st.session_state.session_id, "assistant", response)
        with st.chat_message("assistant"):
            st.markdown(response)
