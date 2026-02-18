"""
ONE-TIME SETUP SCRIPT — creates the structured Lyzr agents.

Run ONCE: python scripts/create_agents.py
Then paste the printed IDs into .env.

DO NOT run again — it will create duplicate agents on the Lyzr backend.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

LYZR_API_KEY = os.getenv("LYZR_API_KEY")
STRUCTURED_TUTOR_ID = "6995c12b62eb68d8f676b535"  # Already created

if not LYZR_API_KEY:
    print("ERROR: LYZR_API_KEY not set in .env")
    sys.exit(1)

from lyzr import Studio
from models import EvalReport

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
