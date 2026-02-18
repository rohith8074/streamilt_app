# --- 1. SETUP AND TOOLS ---
import logging
import uuid  # For creating unique session IDs
from datetime import datetime

logger = logging.getLogger(__name__)

import streamlit as st  # For the website interface

from auth import (  # Importing our database helper functions
    get_user_credits,
    get_user_limit,
    save_chat_message,
    save_trace_mapping,
    update_user_session,
)
from lyzr_client import (
    TOPIC_DESCRIPTIONS,
    TOPIC_TAXONOMY,
    TUTOR_AGENT_ID,
    chat_with_agent,
    create_topic_kb,
    evaluate_session,
    get_instruction_file,
)
from models import EvalReport, TutorResponse
from utils.sync import sync_user_activity


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _reset_session():
    """Clear all session-related state and return to the topic selector."""
    for key in ("session_started", "selected_super_topic", "selected_sub_topic",
                "learning_kb", "evaluation_result"):
        st.session_state.pop(key, None)
    st.session_state.messages = []
    st.rerun()


def _show_topic_selector():
    """Render the pre-session topic-picker UI as a 2-column card grid."""
    st.markdown("#### Select a topic to begin your learning session")

    for super_topic, sub_topics in TOPIC_TAXONOMY.items():
        st.markdown(f"**{super_topic}**")
        cols = st.columns(2)
        for i, sub_topic in enumerate(sub_topics):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{sub_topic}**")
                    st.caption(TOPIC_DESCRIPTIONS.get(sub_topic, ""))
                    if st.button(
                        "▶ Start Learning",
                        key=f"start_{sub_topic}",
                        use_container_width=True,
                        type="primary",
                    ):
                        _start_session(super_topic, sub_topic)


def _start_session(super_topic: str, sub_topic: str):
    """Load instruction file, create KB, and initialise session state."""
    instruction_file = get_instruction_file(super_topic, sub_topic)

    try:
        with open(instruction_file, "r", encoding="utf-8") as fh:
            content = fh.read()
    except FileNotFoundError:
        st.error(
            f"Instruction file not found: `{instruction_file}`. "
            "Please add the file and try again."
        )
        return
    except OSError as exc:
        st.error(f"Could not read instruction file `{instruction_file}`: {exc}")
        return

    with st.spinner(f"Setting up your {sub_topic} learning session…"):
        kb = create_topic_kb(super_topic, sub_topic, content)

    if kb is None:
        st.warning("Could not create knowledge base — session will proceed without RAG.")

    # Build a fresh session ID and persist it
    new_session_id = str(uuid.uuid4())
    st.session_state.session_id = new_session_id
    if st.session_state.get("username"):
        update_user_session(st.session_state.username, new_session_id)

    st.session_state.selected_super_topic = super_topic
    st.session_state.selected_sub_topic = sub_topic
    st.session_state.learning_kb = kb
    st.session_state.session_started = True
    st.session_state.evaluation_result = None
    st.session_state.messages = []
    st.rerun()


def _handle_send(prompt: str):
    """Validate credits, send message to tutor agent, save to DB."""
    # A. AUTOMATIC SYNC: Refresh usage before the credit check.
    with st.spinner("Verifying your remaining credits…"):
        sync_user_activity(st.session_state.username, st.session_state.session_id)

    # B. BUDGET CHECK: Block non-admins who have hit their limit.
    user_credits = get_user_credits(st.session_state.username, agent_id=TUTOR_AGENT_ID)
    max_limit = get_user_limit(st.session_state.username)

    if user_credits >= max_limit and not st.session_state.isAdmin:
        st.error(
            f"**Credit Limit Reached**: You have spent ${user_credits:.4f} of your "
            f"${max_limit:.2f} allowance. Please contact the administrator."
        )
        return

    # C. SNAPSHOT CREDITS BEFORE INFERENCE (reuse value already fetched in step B).
    credits_before = user_credits

    # D. SHOW USER MESSAGE and persist.
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_chat_message(
        st.session_state.username,
        st.session_state.session_id,
        "user",
        prompt,
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    # E. CALL TUTOR AGENT.
    kb = st.session_state.get("learning_kb")
    with st.spinner("Thinking…"):
        logger.info("[USER QUERY]: %s", prompt)
        logger.info("[SESSION ID]: %s", st.session_state.session_id)

        api_data = chat_with_agent(
            message=prompt,
            user_id=st.session_state.username,
            session_id=st.session_state.session_id,
            agent_id=TUTOR_AGENT_ID,
            knowledge_bases=[kb] if kb is not None else None,
        )

        logger.info("[AGENT RESPONSE]: %s", api_data)

    # F. EXTRACT FIELDS FROM TYPED RESPONSE.
    if isinstance(api_data, TutorResponse):
        response = api_data.response_text
        tone_up = api_data.tone_up
        tone_down = api_data.tone_down
        next_nudge = api_data.next_nudge

        # G. TRACE MAPPING: Save fuzzy timestamp mapping for later attribution.
        timestamp_now = datetime.utcnow().isoformat()
        save_trace_mapping(
            f"fuzzy_{st.session_state.username}_{timestamp_now}",
            st.session_state.username,
            st.session_state.session_id,
        )
    else:
        response = api_data  # Error string from SDK wrapper
        tone_up = tone_down = next_nudge = ""

    # H. POST-INFERENCE SYNC: capture the new trace so credit delta is accurate.
    with st.spinner("Updating credit usage…"):
        sync_user_activity(st.session_state.username, st.session_state.session_id)

    credits_after = get_user_credits(st.session_state.username, agent_id=TUTOR_AGENT_ID)
    credits_this_msg = max(0.0, credits_after - credits_before)
    credits_remaining = max(0.0, max_limit - credits_after)

    # I. SHOW AND SAVE ASSISTANT RESPONSE (with credit metadata on the dict).
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "tone_up": tone_up,
        "tone_down": tone_down,
        "next_nudge": next_nudge,
        "credits_used": credits_this_msg,
        "credits_remaining": credits_remaining,
    })
    save_chat_message(
        st.session_state.username,
        st.session_state.session_id,
        "assistant",
        response,
    )
    with st.chat_message("assistant"):
        st.markdown(response)
        st.caption(
            f"💳 ${credits_this_msg:.4f} used this message  ·  "
            f"${credits_remaining:.4f} remaining"
        )


def _handle_evaluate():
    """Call the evaluator agent and store the result in session state."""
    messages = st.session_state.get("messages", [])
    if not messages:
        st.warning("No conversation to evaluate yet.")
        return

    super_topic = st.session_state.get("selected_super_topic", "")
    sub_topic = st.session_state.get("selected_sub_topic", "")

    with st.spinner("Evaluating your session…"):
        result = evaluate_session(messages, super_topic, sub_topic)

    st.session_state.evaluation_result = result
    st.rerun()


def _render_eval_report(report):
    """Render a structured EvalReport as a 7-row metric table."""
    metrics = [
        ("Engagement",           report.engagement),
        ("Clarity",              report.clarity),
        ("Guidance",             report.guidance),
        ("Encouragement",        report.encouragement),
        ("Real-world Connect.",  report.real_world_connection),
        ("Conversational Flow",  report.conversational_flow),
        ("Learning Progression", report.learning_progression),
    ]
    for name, metric in metrics:
        col_name, col_score, col_bar, col_explain = st.columns([2, 0.6, 1.5, 5])
        with col_name:
            st.markdown(f"**{name}**")
        with col_score:
            st.markdown(f"**{metric.score}/5**")
        with col_bar:
            filled = "█" * metric.score + "░" * (5 - metric.score)
            st.markdown(f"`{filled}`")
        with col_explain:
            st.caption(metric.explanation)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def show_chat_view():
    """Build the main AI conversation screen."""

    st.markdown("### Lyzr AI Tutor")

    # --- PRE-SESSION: show topic selector ---
    if not st.session_state.get("session_started"):
        _show_topic_selector()
        return

    # --- ACTIVE SESSION HEADER ---
    super_topic = st.session_state.get("selected_super_topic", "")
    sub_topic = st.session_state.get("selected_sub_topic", "")
    messages = st.session_state.get("messages", [])

    col_topic, col_count, col_eval, col_new = st.columns([4, 1, 2, 2])
    with col_topic:
        st.markdown(f"**{super_topic}** › **{sub_topic}**")
    with col_count:
        msg_count = len(messages)
        st.caption(f"{msg_count} msg{'s' if msg_count != 1 else ''}")
    with col_eval:
        if st.button("Evaluate Session", use_container_width=True):
            _handle_evaluate()
    with col_new:
        if st.button("↩ New Topic", use_container_width=True):
            _reset_session()
    st.divider()

    # Display conversation history
    last_idx = len(messages) - 1
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if "credits_used" in msg:
                    st.caption(
                        f"💳 ${msg['credits_used']:.4f} used this message  ·  "
                        f"${msg['credits_remaining']:.4f} remaining"
                    )
                # Suggestion chips — only on the last assistant message
                if i == last_idx and msg.get("tone_up"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button(
                            "⬆ Go deeper",
                            key="chip_tone_up",
                            use_container_width=True,
                        ):
                            _handle_send(msg["tone_up"])
                    with c2:
                        if st.button(
                            "⬇ Simplify",
                            key="chip_tone_down",
                            use_container_width=True,
                        ):
                            _handle_send(msg["tone_down"])
                    with c3:
                        if st.button(
                            "➡ Next question",
                            key="chip_next_nudge",
                            use_container_width=True,
                        ):
                            _handle_send(msg["next_nudge"])

    # --- EVALUATION REPORT ---
    if st.session_state.get("evaluation_result"):
        report = st.session_state.evaluation_result
        with st.expander("Session Evaluation Report", expanded=True):
            if isinstance(report, EvalReport):
                _render_eval_report(report)
            else:
                st.markdown(str(report))  # Fallback for error strings

    # --- CHAT INPUT (native sticky bottom) ---
    if prompt := st.chat_input("Ask a question or share your thoughts…"):
        _handle_send(prompt)
