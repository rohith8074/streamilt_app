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
