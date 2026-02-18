# Structured Agent Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace free-form text agent responses with Pydantic-validated JSON — giving the Tutor structured `response_text + tone_up + tone_down + next_nudge` fields and the Evaluator a typed 7-metric `EvalReport`, then surface both in the Streamlit UI with suggestion chips and a metric card table.

**Architecture:** Two new agents are created once via a setup script and their IDs stored in `.env`. `chat_with_agent()` and `evaluate_session()` return typed Pydantic objects instead of `dict`/`str`. `views/chat.py` reads the typed fields directly — no JSON parsing in view code. Suggestion chips appear below the last assistant message; evaluation renders as a metric row table.

**Tech Stack:** Python, Pydantic v2, lyzr-adk SDK v0.1.5 (`studio.agents.create` with `response_model`), Streamlit, SQLite via auth.py.

---

## Validated Finding (do not re-test)

Runtime `response_model` on an existing plain-text agent **fails** — `ResponseParser` cannot parse free-form text as JSON. Confirmed via live test. Agents must be created fresh with JSON instructions baked in AND `response_model` set at `studio.agents.create()` time. The structured Tutor agent was already created (ID: `6995c12b62eb68d8f676b535`).

---

## Context

- Working directory: `/Users/harshitchoudhary/Documents/lyzr/initiative/lyzr-agentpreneur/streamilt_app`
- Run tests with: `venv/bin/pytest -v` (113 tests currently pass)
- Lyzr API key: `sk-default-gqcFW0hH98hyscbMUp8nS9cfHLEoLCDw`
- Structured Tutor agent already created: ID `6995c12b62eb68d8f676b535`
- Existing EVALUATOR_AGENT_ID in `.env`: `6995b5cb0011f1752bbed247` (plain-text, will be replaced)

---

### Task 1: Create models.py with TutorResponse, Metric, EvalReport

**Files:**
- Create: `models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing tests**

Create `tests/test_models.py`:

```python
"""Tests for Pydantic models in models.py."""
import pytest
from pydantic import ValidationError


class TestTutorResponse:
    def test_valid_tutor_response(self):
        from models import TutorResponse
        r = TutorResponse(
            response_text="What do you think encapsulation means?",
            tone_up="Can you explain how access modifiers enforce encapsulation?",
            tone_down="Imagine a TV remote — which parts are hidden from you?",
            next_nudge="Why might hiding internal state make code easier to change?",
        )
        assert r.response_text == "What do you think encapsulation means?"
        assert len(r.tone_up) > 0
        assert len(r.tone_down) > 0
        assert len(r.next_nudge) > 0

    def test_missing_field_raises(self):
        from models import TutorResponse
        with pytest.raises(ValidationError):
            TutorResponse(response_text="x", tone_up="y", tone_down="z")
            # missing next_nudge

    def test_all_fields_are_strings(self):
        from models import TutorResponse
        r = TutorResponse(response_text="a", tone_up="b", tone_down="c", next_nudge="d")
        for field in ("response_text", "tone_up", "tone_down", "next_nudge"):
            assert isinstance(getattr(r, field), str)


class TestMetric:
    def test_valid_metric(self):
        from models import Metric
        m = Metric(score=4, explanation="Good engagement throughout.")
        assert m.score == 4
        assert m.explanation == "Good engagement throughout."

    def test_missing_field_raises(self):
        from models import Metric
        with pytest.raises(ValidationError):
            Metric(score=5)  # missing explanation


class TestEvalReport:
    def test_valid_eval_report(self):
        from models import EvalReport, Metric
        m = Metric(score=4, explanation="Good.")
        r = EvalReport(
            engagement=m, clarity=m, guidance=m, encouragement=m,
            real_world_connection=m, conversational_flow=m, learning_progression=m,
        )
        assert r.engagement.score == 4
        assert r.clarity.explanation == "Good."

    def test_all_seven_metrics_required(self):
        from models import EvalReport, Metric
        m = Metric(score=3, explanation="OK.")
        with pytest.raises(ValidationError):
            EvalReport(engagement=m, clarity=m)  # missing 5 metrics

    def test_metrics_are_metric_instances(self):
        from models import EvalReport, Metric
        m = Metric(score=5, explanation="Excellent.")
        r = EvalReport(
            engagement=m, clarity=m, guidance=m, encouragement=m,
            real_world_connection=m, conversational_flow=m, learning_progression=m,
        )
        for field in ("engagement", "clarity", "guidance", "encouragement",
                      "real_world_connection", "conversational_flow", "learning_progression"):
            assert isinstance(getattr(r, field), Metric)
```

**Step 2: Run tests to confirm they fail**

```bash
venv/bin/pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'models'`

**Step 3: Create models.py**

```python
"""Pydantic models for structured agent output."""
from pydantic import BaseModel


class TutorResponse(BaseModel):
    """Structured response from the Tutor agent."""
    response_text: str    # The main teaching content or Socratic question
    tone_up: str          # Follow-up the learner can send to go deeper
    tone_down: str        # Follow-up the learner can send for simpler explanation
    next_nudge: str       # Socratic nudge toward the next concept


class Metric(BaseModel):
    """A single evaluation metric with a 1-5 score and explanation."""
    score: int            # 1 (poor) to 5 (excellent)
    explanation: str      # One-sentence rationale


class EvalReport(BaseModel):
    """Structured 7-metric evaluation report from the Evaluator agent."""
    engagement: Metric
    clarity: Metric
    guidance: Metric
    encouragement: Metric
    real_world_connection: Metric
    conversational_flow: Metric
    learning_progression: Metric
```

**Step 4: Run tests to confirm they pass**

```bash
venv/bin/pytest tests/test_models.py -v
```

Expected: 7 tests PASS.

**Step 5: Run full suite to confirm no regressions**

```bash
venv/bin/pytest -v
```

Expected: 120 tests pass (113 existing + 7 new).

**Step 6: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add TutorResponse, Metric, EvalReport Pydantic models"
```

---

### Task 2: Create one-time agent setup script and update .env

**Files:**
- Create: `scripts/create_agents.py`
- Modify: `.env`

**Step 1: Create `scripts/` directory and setup script**

Create `scripts/create_agents.py`:

```python
"""
ONE-TIME SETUP SCRIPT — creates the structured Lyzr agents.

Run ONCE: python scripts/create_agents.py
Then paste the printed IDs into .env.

DO NOT run again — it will create duplicate agents on the Lyzr backend.
"""
import os
import sys

# Guard: refuse to run if structured agent IDs already set
from dotenv import load_dotenv
load_dotenv()

existing_tutor = os.getenv("TUTOR_AGENT_ID", "")
# The structured evaluator has a different key from the old one for safety
existing_eval = os.getenv("EVALUATOR_AGENT_ID", "")

STRUCTURED_TUTOR_ID = "6995c12b62eb68d8f676b535"  # Already created
LYZR_API_KEY = os.getenv("LYZR_API_KEY")

if not LYZR_API_KEY:
    print("ERROR: LYZR_API_KEY not set in .env")
    sys.exit(1)

from pydantic import BaseModel
from lyzr import Studio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import EvalReport

TUTOR_INSTRUCTIONS = """You are a Socratic OOP tutor. You teach Object-Oriented Programming by asking
questions — never giving direct answers. Guide learners to discover insights themselves.

ALWAYS respond with valid JSON matching this exact schema (no other text):
{
    "response_text": "<your main teaching response or Socratic question>",
    "tone_up": "<a complete message the learner can send to explore the topic more deeply>",
    "tone_down": "<a complete message the learner can send to get a simpler explanation or analogy>",
    "next_nudge": "<a Socratic question nudging the learner toward the next key concept>"
}

Rules:
- Never respond with plain text. Always return valid JSON only.
- tone_up and tone_down must be complete sentences the learner could copy-paste and send.
- next_nudge naturally leads to the next concept in the learning progression."""

EVALUATOR_INSTRUCTIONS = """You are a learning session evaluator. Analyse a tutoring transcript and
produce a structured assessment of 7 metrics.

ALWAYS respond with valid JSON matching this exact schema (no other text):
{
    "engagement":           {"score": <int 1-5>, "explanation": "<one sentence>"},
    "clarity":              {"score": <int 1-5>, "explanation": "<one sentence>"},
    "guidance":             {"score": <int 1-5>, "explanation": "<one sentence>"},
    "encouragement":        {"score": <int 1-5>, "explanation": "<one sentence>"},
    "real_world_connection":{"score": <int 1-5>, "explanation": "<one sentence>"},
    "conversational_flow":  {"score": <int 1-5>, "explanation": "<one sentence>"},
    "learning_progression": {"score": <int 1-5>, "explanation": "<one sentence>"}
}

Scoring: 1=Poor 2=Below average 3=Average 4=Good 5=Excellent
Never respond with plain text. Always return valid JSON only."""


def main():
    studio = Studio(api_key=LYZR_API_KEY)

    print("Tutor agent already created.")
    print(f"  TUTOR_AGENT_ID = {STRUCTURED_TUTOR_ID}")

    print("\nCreating Evaluator agent...")
    eval_agent = studio.agents.create(
        name="OOP Evaluator (Structured)",
        provider="openai/gpt-4o",
        role="Learning session evaluator",
        goal="Produce a structured 7-metric evaluation of a tutoring session",
        instructions=EVALUATOR_INSTRUCTIONS,
        response_model=EvalReport,
    )
    print(f"  EVALUATOR_AGENT_ID = {eval_agent.id}")

    print("\n--- Paste these into your .env ---")
    print(f"TUTOR_AGENT_ID={STRUCTURED_TUTOR_ID}")
    print(f"EVALUATOR_AGENT_ID={eval_agent.id}")
    print("-----------------------------------")


if __name__ == "__main__":
    main()
```

**Step 2: Run the setup script**

```bash
venv/bin/python scripts/create_agents.py
```

Expected output (note the EVALUATOR_AGENT_ID — it will be a new ID):
```
Tutor agent already created.
  TUTOR_AGENT_ID = 6995c12b62eb68d8f676b535

Creating Evaluator agent...
  EVALUATOR_AGENT_ID = <new-id-here>

--- Paste these into your .env ---
TUTOR_AGENT_ID=6995c12b62eb68d8f676b535
EVALUATOR_AGENT_ID=<new-id-here>
-----------------------------------
```

**Step 3: Update .env with the printed IDs**

Open `.env` and update:
```
TUTOR_AGENT_ID=6995c12b62eb68d8f676b535
EVALUATOR_AGENT_ID=<id printed by the script>
```

**Step 4: Run full test suite to confirm nothing broke**

```bash
venv/bin/pytest -v
```

Expected: 120 tests pass.

**Step 5: Commit**

```bash
git add scripts/create_agents.py .env
git commit -m "feat: add one-time agent creation script and update .env with structured agent IDs"
```

---

### Task 3: Update lyzr_client.py — typed return values + update tests

**Files:**
- Modify: `lyzr_client.py`
- Modify: `tests/test_lyzr_client.py`

**Step 1: Update the failing tests first**

In `tests/test_lyzr_client.py`, find `class TestChatWithAgent` (around line 93).

Replace `test_chat_with_agent_basic` with:

```python
def test_chat_with_agent_basic(self, mocker):
    """Test chat_with_agent returns TutorResponse from SDK."""
    from lyzr_client import chat_with_agent
    from models import TutorResponse

    mock_agent = MagicMock()
    mock_agent.run.return_value = TutorResponse(
        response_text="What do you think encapsulation means?",
        tone_up="Can you explain access modifiers?",
        tone_down="Think of a TV remote — what is hidden?",
        next_nudge="Why hide internal state at all?",
    )

    mock_client = MagicMock()
    mock_client.studio.agents.get.return_value = mock_agent

    mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
    mocker.patch("lyzr_client.AGENT_ID", "test-agent-123")
    mocker.patch("lyzr_client.get_active_api_key", return_value="test-key")

    result = chat_with_agent(
        message="Hello SDK",
        user_id="user@test.com",
        session_id="session-123"
    )

    assert isinstance(result, TutorResponse)
    assert result.response_text == "What do you think encapsulation means?"
    mock_agent.run.assert_called_once_with(
        message="Hello SDK",
        user_id="user@test.com",
        session_id="session-123"
    )
```

Also replace `test_chat_with_agent_with_managed_agents` to check that `agents.get` is still called:

```python
def test_chat_with_agent_with_managed_agents(self, mocker):
    """Test chat_with_agent passes managed_agents to agent.run()."""
    from lyzr_client import chat_with_agent
    from models import TutorResponse

    mock_agent = MagicMock()
    mock_agent.run.return_value = TutorResponse(
        response_text="Routed response",
        tone_up="go deeper",
        tone_down="simplify",
        next_nudge="next concept",
    )

    mock_client = MagicMock()
    mock_client.studio.agents.get.return_value = mock_agent

    mocker.patch("lyzr_client.LyzrClient", return_value=mock_client)
    mocker.patch("lyzr_client.AGENT_ID", "manager-agent")
    mocker.patch("lyzr_client.get_active_api_key", return_value="test-key")

    managed_agents = [{"id": "agent-1", "name": "Specialist 1"}]

    result = chat_with_agent(
        message="Route this",
        user_id="user@test.com",
        session_id="session-123",
        managed_agents=managed_agents
    )

    call_kwargs = mock_agent.run.call_args.kwargs
    assert "managed_agents" in call_kwargs
    assert call_kwargs["managed_agents"] == managed_agents
```

**Step 2: Run failing tests to confirm the current code fails**

```bash
venv/bin/pytest tests/test_lyzr_client.py::TestChatWithAgent -v
```

Expected: Tests fail (current code returns `dict`, not `TutorResponse`).

**Step 3: Update lyzr_client.py**

At the top of `lyzr_client.py`, add the models import after the existing imports:

```python
from models import EvalReport, TutorResponse
```

Replace `chat_with_agent()` (lines 149–217) with:

```python
def chat_with_agent(
    message: str,
    user_id: str,
    session_id: str,
    agent_id: str = None,
    managed_agents: list = None,
    knowledge_bases: list = None,
):
    """
    Send a chat message using lyzr-adk SDK.

    Returns:
        TutorResponse: Structured Pydantic response on success
        str: Error message string on failure
    """
    agent_id = agent_id or AGENT_ID

    if not agent_id:
        return "Error: Missing Lyzr API Credentials. Please configure AGENT_ID."

    try:
        client = LyzrClient()
        agent = client.studio.agents.get(agent_id, response_model=TutorResponse)

        run_kwargs = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id,
        }

        if managed_agents:
            run_kwargs["managed_agents"] = managed_agents

        if knowledge_bases:
            run_kwargs["knowledge_bases"] = knowledge_bases

        response = agent.run(**run_kwargs)
        logger.info("SDK chat successful for user %s, session %s", user_id, session_id)
        return response  # TutorResponse instance

    except ValueError as ve:
        logger.error("Configuration error: %s", ve)
        return "Error: Missing Lyzr API Credentials. Please check your settings."
    except Exception as e:
        logger.error("SDK chat error: %s", e)
        return f"AI Connection Error: {e}. Please try again."
```

Replace `evaluate_session()` (lines 297–353) with:

```python
def evaluate_session(messages: list, super_topic: str, sub_topic: str):
    """Evaluate a completed tutoring session using the structured evaluator agent.

    Returns:
        EvalReport: Structured 7-metric Pydantic report on success
        str: Error message string on failure
    """
    if not EVALUATOR_AGENT_ID:
        return "Error: EVALUATOR_AGENT_ID is not configured. Set it in Settings or .env."

    transcript_lines = []
    for msg in messages:
        label = "Student" if msg["role"] == "user" else "Tutor"
        content = msg.get("content", "")
        transcript_lines.append(f"{label}: {content}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "(No messages exchanged.)"

    prompt = (
        f"Evaluate this tutoring session on {super_topic} > {sub_topic}.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        client = LyzrClient()
        agent = client.studio.agents.get(EVALUATOR_AGENT_ID, response_model=EvalReport)
        response = agent.run(
            message=prompt,
            user_id="evaluator",
            session_id=str(uuid.uuid4()),
        )
        return response  # EvalReport instance
    except Exception as e:
        logger.error("Session evaluation failed: %s", e)
        return f"Evaluation failed: {e}"
```

**Step 4: Run tests to confirm they now pass**

```bash
venv/bin/pytest tests/test_lyzr_client.py::TestChatWithAgent -v
```

Expected: PASS.

**Step 5: Run full suite**

```bash
venv/bin/pytest -v
```

Expected: All 120 tests pass.

**Step 6: Commit**

```bash
git add lyzr_client.py tests/test_lyzr_client.py
git commit -m "feat: update chat_with_agent and evaluate_session to return typed Pydantic objects"
```

---

### Task 4: Update _handle_send() — handle TutorResponse, extend message dict

**Files:**
- Modify: `views/chat.py`

**Step 1: Remove `import json` from the top of views/chat.py**

Find line 2:
```python
import json  # For handling complex data structures
```

Delete it — `json` is no longer used in this file.

**Step 2: Add models import**

After the existing `from lyzr_client import (...)` block (around line 27), add:

```python
from models import EvalReport, TutorResponse
```

**Step 3: Replace steps F and G in _handle_send()**

Find lines 148–181 (the logging line + step F + step G block):

```python
        logger.info(
            "[AGENT RESPONSE]: %s",
            json.dumps(api_data, indent=2) if isinstance(api_data, dict) else api_data,
        )

    # F. PARSE RESPONSE.
    if isinstance(api_data, dict):
        response_val = api_data.get("response", "No response from agent.")
        if isinstance(response_val, str):
            try:
                internal_data = json.loads(response_val)
                response = internal_data.get("response_text") or response_val
            except (json.JSONDecodeError, ValueError):
                response = response_val
        elif isinstance(response_val, dict):
            response = json.dumps(response_val, indent=2)
        else:
            response = response_val

        # G. TRACE MAPPING: Save fuzzy timestamp mapping for later attribution.
        active_session = api_data.get("session_id") or st.session_state.session_id
        timestamp_now = datetime.utcnow().isoformat()
        save_trace_mapping(
            f"fuzzy_{st.session_state.username}_{timestamp_now}",
            st.session_state.username,
            active_session,
        )

        # If the API returned a new session ID, persist it.
        if api_data.get("session_id") and api_data["session_id"] != st.session_state.session_id:
            update_user_session(st.session_state.username, api_data["session_id"])
            st.session_state.session_id = api_data["session_id"]
    else:
        response = api_data  # Error string from SDK wrapper
```

Replace with:

```python
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
```

**Step 4: Extend the message dict in step I**

Find the message dict in step I (around line 192):

```python
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "credits_used": credits_this_msg,
        "credits_remaining": credits_remaining,
    })
```

Replace with:

```python
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "tone_up": tone_up,
        "tone_down": tone_down,
        "next_nudge": next_nudge,
        "credits_used": credits_this_msg,
        "credits_remaining": credits_remaining,
    })
```

**Step 5: Run full test suite**

```bash
venv/bin/pytest -v
```

Expected: All 120 tests pass.

**Step 6: Commit**

```bash
git add views/chat.py
git commit -m "feat: update _handle_send to extract fields from TutorResponse"
```

---

### Task 5: Add suggestion chips to the message history loop

**Files:**
- Modify: `views/chat.py` — update `show_chat_view()` message loop

**Step 1: Find the message history loop in show_chat_view()**

Find (around line 263):

```python
    # Display conversation history
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "credits_used" in msg:
                st.caption(
                    f"💳 ${msg['credits_used']:.4f} used this message  ·  "
                    f"${msg['credits_remaining']:.4f} remaining"
                )
```

Replace with:

```python
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
```

**Step 2: Run full test suite**

```bash
venv/bin/pytest -v
```

Expected: All 120 tests pass.

**Step 3: Manual smoke test — suggestion chips**

```bash
streamlit run app.py
```

- Log in → start a topic session → send one message
- Confirm three buttons appear below the assistant response: ⬆ Go deeper / ⬇ Simplify / ➡ Next question
- Click one — confirm it auto-sends that text and a new response appears
- Confirm chips only appear on the latest message (not old ones after new messages arrive)

**Step 4: Commit**

```bash
git add views/chat.py
git commit -m "feat: add suggestion chips (tone-up, tone-down, next nudge) below last assistant message"
```

---

### Task 6: Update evaluation report — typed metric card table

**Files:**
- Modify: `views/chat.py` — add `_render_eval_report()` helper and update report rendering

**Step 1: Add _render_eval_report() helper**

In `views/chat.py`, add this function just before `show_chat_view()` (around line 230):

```python
def _render_eval_report(report):
    """Render a structured EvalReport as a 7-row metric table."""
    metrics = [
        ("Engagement",          report.engagement),
        ("Clarity",             report.clarity),
        ("Guidance",            report.guidance),
        ("Encouragement",       report.encouragement),
        ("Real-world Connect.", report.real_world_connection),
        ("Conversational Flow", report.conversational_flow),
        ("Learning Progression",report.learning_progression),
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
```

**Step 2: Update the evaluation report block in show_chat_view()**

Find (around line 273):

```python
    # --- EVALUATION REPORT ---
    if st.session_state.get("evaluation_result"):
        with st.expander("Session Evaluation Report", expanded=True):
            st.markdown(st.session_state.evaluation_result)
```

Replace with:

```python
    # --- EVALUATION REPORT ---
    if st.session_state.get("evaluation_result"):
        report = st.session_state.evaluation_result
        with st.expander("Session Evaluation Report", expanded=True):
            if isinstance(report, EvalReport):
                _render_eval_report(report)
            else:
                st.markdown(str(report))  # Fallback for error strings
```

**Step 3: Run full test suite**

```bash
venv/bin/pytest -v
```

Expected: All 120 tests pass.

**Step 4: Manual smoke test — evaluation report**

```bash
streamlit run app.py
```

- Log in → start a session → exchange 3–4 messages → click "Evaluate Session"
- Confirm the expander shows 7 metric rows with score bars, not raw markdown
- Each row: bold metric name | score/5 | `████░` bar | explanation caption

**Step 5: Commit**

```bash
git add views/chat.py
git commit -m "feat: render EvalReport as typed metric card table instead of raw markdown"
```

---

## Final Verification

```bash
venv/bin/pytest -v 2>&1 | tail -3
```

Expected: `120 passed`

Manual end-to-end:
- [ ] Topic card grid appears → click a card → chat area loads
- [ ] Send a message → TutorResponse fields populate the message dict
- [ ] Three suggestion chips appear below last assistant message
- [ ] Clicking a chip auto-sends that follow-up
- [ ] "Evaluate Session" → 7-row metric table with score bars renders
- [ ] Credits caption still shows under each assistant message
- [ ] "↩ New Topic" clears state correctly
