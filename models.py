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
