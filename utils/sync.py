import os
from auth import get_latest_trace_timestamp, save_traces_bulk, get_mapping_for_trace, get_fuzzy_session
from lyzr_client import get_traces_sdk, AGENT_ID


def sync_user_activity(username, session_id):
    """
    Downloads the latest AI interaction records from Lyzr and saves them locally.
    This ensures that credit calculations are always up-to-date.
    """
    # 1. We look for work done since our last local record across the whole platform.
    # We remove the 'agent_id' filter here so we don't miss specialist agent work.
    last_sync_time = get_latest_trace_timestamp(user_id=username)

    # 2. Fetch the latest receipts (traces) from the Lyzr cloud using SDK.
    api_traces = get_traces_sdk(start_time=last_sync_time, limit=500)

    if not api_traces:
        return 0

    traces_to_save = []
    for t in api_traces:
        trace_id = t.get("trace_id") or t.get("id") or t.get("traceId")

        # --- INITIAL DATA RETRIEVAL ---
        # We check multiple possible names (user_id, userId) for compatibility.
        cloud_user_id = t.get("user_id") or t.get("userId") or t.get("query_user_id") or "unknown"
        cloud_session_id = t.get("session_id") or t.get("sessionId") or "unknown"
        created_at_val = t.get("trace_start_time") or t.get("created_at") or t.get("start_time")

        # --- STRICT USER ATTRIBUTION ---
        is_owner = False
        final_user_id = cloud_user_id
        final_session_id = cloud_session_id

        # Check A: Direct Match
        if cloud_user_id == username:
            is_owner = True

        # Check B: Local Memory Match
        mapped_user, mapped_session = get_mapping_for_trace(trace_id)
        if mapped_user == username:
            is_owner = True
            final_user_id = username
            final_session_id = mapped_session or final_session_id

        # Check C: Fuzzy Detective (Match by Time)
        if not is_owner and (cloud_user_id == "unknown" or cloud_user_id is None):
            fuzzy_session = get_fuzzy_session(username, created_at_val)
            if fuzzy_session:
                is_owner = True
                final_user_id = username
                final_session_id = fuzzy_session
                print(f"🕵️ Fuzzy Match Found for Trace {trace_id} -> User {username}")

        # Final Verification
        # SECURITY: If we cannot prove this trace belongs to the current user, we SKIP it.
        # This stops new users (like 'r4') from inheriting logs from previous users.
        if not is_owner:
            print(f"🚫 [SYNC SKIP]: Record {trace_id[:8]}... belongs to another user ({cloud_user_id}).")
            continue

        print(f"📊 Syncing verified trace: {trace_id} for user {final_user_id}")

        # --- RECORD PREPARATION ---
        # We fetch the cost and divide by 100 to convert to our local unit format.
        raw_credits = t.get("action_cost") or t.get("total_credits") or 0.0
        credits_spent = float(raw_credits) / 100.0

        # If the actual chat text is missing, show the Token Count for consistency.
        user_message = t.get("message") or t.get("input") or f"Tokens: {t.get('llm_input_tokens', 'N/A')}"
        agent_response = t.get("response") or t.get("output") or f"Tokens: {t.get('llm_output_tokens', 'N/A')}"

        if trace_id:
            base_trace_url = os.getenv("LYZR_TRACES_URL", "https://agent-prod.studio.lyzr.ai/v3/traces").replace(
                "/v3/traces", ""
            )
            inspect_url = f"{base_trace_url}/v3/traces/{trace_id}/gantt"

            traces_to_save.append(
                {
                    "trace_id": trace_id,
                    "user_id": final_user_id,
                    "session_id": final_session_id,
                    "agent_id": AGENT_ID,
                    "credits": credits_spent,
                    "created_at": created_at_val,
                    "input": user_message,
                    "output": agent_response,
                    "inspect": inspect_url,
                }
            )

    # 3. Save only the verified records back to the database.
    return save_traces_bulk(traces_to_save)
