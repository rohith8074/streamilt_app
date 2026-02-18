# Structured Agent Output Design

## Goal

Replace free-form text responses from the Tutor and Evaluator agents with Pydantic-validated JSON, unlocking type-safe access in the app and richer UI components.

## Key Validation Finding

Runtime `response_model` on an existing plain-text agent **fails** — `ResponseParser` cannot parse free-form text as JSON. New agents must be created with JSON output instructions baked into their `instructions` field AND `response_model` set at `studio.agents.create()` time. Live-tested and confirmed.

---

## Pydantic Models (`models.py`)

```python
from pydantic import BaseModel

class TutorResponse(BaseModel):
    response_text: str    # the teaching content / Socratic question
    tone_up: str          # follow-up suggestion to go deeper
    tone_down: str        # follow-up suggestion for simpler explanation
    next_nudge: str       # Socratic nudge toward the next concept

class Metric(BaseModel):
    score: int            # 1–5
    explanation: str      # one-sentence rationale

class EvalReport(BaseModel):
    engagement: Metric
    clarity: Metric
    guidance: Metric
    encouragement: Metric
    real_world_connection: Metric
    conversational_flow: Metric
    learning_progression: Metric
```

---

## Agent Creation Strategy

### Create-once, store ID in `.env`

Both agents are created **once** via `scripts/create_agents.py`. The script prints the agent IDs; the user pastes them into `.env`. On every subsequent app boot, `studio.agents.get(id, response_model=Model)` fetches the agent with the model injected client-side.

**Tutor agent** (already created, ID: `6995c12b62eb68d8f676b535`):
- `name`: "OOP Tutor (Structured)"
- `instructions`: Socratic teaching instructions + explicit JSON schema requirement
- `response_model`: `TutorResponse`

**Evaluator agent** (to be created by script):
- `name`: "OOP Evaluator (Structured)"
- `instructions`: Session evaluation instructions + explicit JSON schema for 7 metrics
- `response_model`: `EvalReport`

### `.env` keys

```
TUTOR_AGENT_ID=<id from create script>
EVALUATOR_AGENT_ID=<id from create script>
```

---

## lyzr_client.py Changes

### `chat_with_agent()` return type: `TutorResponse | str`

```python
from models import TutorResponse

agent = client.studio.agents.get(agent_id, response_model=TutorResponse)
result = agent.run(message=..., user_id=..., session_id=..., knowledge_bases=...)
return result  # TutorResponse instance, or error string on exception
```

### `evaluate_session()` return type: `EvalReport | str`

```python
from models import EvalReport

agent = client.studio.agents.get(EVALUATOR_AGENT_ID, response_model=EvalReport)
result = agent.run(message=prompt, user_id="evaluator", session_id=uuid4())
return result  # EvalReport instance, or error string on exception
```

---

## views/chat.py Changes

### Message dict extended with suggestion fields

```python
st.session_state.messages.append({
    "role": "assistant",
    "content": result.response_text,
    "tone_up": result.tone_up,
    "tone_down": result.tone_down,
    "next_nudge": result.next_nudge,
    "credits_used": credits_this_msg,
    "credits_remaining": credits_remaining,
})
```

### Suggestion chips — last assistant message only

Below the response of the most recent assistant message, show three `st.button()` chips in one row:

```
[⬆ Go deeper]   [⬇ Simplify]   [➡ Next question]
```

Clicking auto-sends the stored suggestion text via `_handle_send(text)`.

Only the last assistant message shows chips — older messages show response text only (no buttons, reducing clutter).

```python
is_last = (i == len(messages) - 1)
if msg["role"] == "assistant" and is_last and "tone_up" in msg:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⬆ Go deeper", key="tone_up", use_container_width=True):
            _handle_send(msg["tone_up"])
    with c2:
        if st.button("⬇ Simplify", key="tone_down", use_container_width=True):
            _handle_send(msg["tone_down"])
    with c3:
        if st.button("➡ Next question", key="next_nudge", use_container_width=True):
            _handle_send(msg["next_nudge"])
```

### Evaluation report — typed metric cards

Replace the raw `st.markdown()` of the evaluation string with a structured 7-row table:

```python
report: EvalReport = st.session_state.evaluation_result
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
    col_name, col_score, col_bar, col_explain = st.columns([2, 0.5, 1.5, 5])
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

---

## Error Handling

- If `agent.run()` raises `InvalidResponseError` (malformed JSON from agent): catch and return the raw string, fall back to plain text display
- If `studio.agents.get()` raises: return error string — existing budget/send flow is unchanged
- Suggestion chips only rendered if `"tone_up"` key present in message dict (graceful degradation for old messages)

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `models.py` | New — `TutorResponse`, `Metric`, `EvalReport` |
| `scripts/create_agents.py` | New — one-time agent creation script |
| `lyzr_client.py` | Import from models, update `chat_with_agent()` and `evaluate_session()` return types |
| `views/chat.py` | Update `_handle_send()` dict, add suggestion chips, update eval report rendering |
| `tests/test_models.py` | New — Pydantic model validation tests |
| `tests/test_lyzr_client.py` | Update mocks for new return types |
| `.env.example` | Note that TUTOR_AGENT_ID should point to structured agent |

## Files NOT Changing

- `auth.py` — no schema changes
- `app.py` — unchanged
- `utils/sync.py` — unchanged
- `utils/ui.py` — unchanged
- Learning instruction markdown files — unchanged

---

## Verification

1. Run `scripts/create_agents.py` → get evaluator agent ID, update `.env`
2. `streamlit run app.py` → login
3. Start a learning session → send a message → confirm:
   - Response text renders (not raw JSON)
   - Three suggestion chips appear below the last assistant message
   - Clicking a chip auto-sends the suggestion
4. Click "Evaluate Session" → confirm 7 metric rows with score bars render
5. `python -m pytest -v` → all tests pass
