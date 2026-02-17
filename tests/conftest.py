"""
Shared fixtures for all tests.
Every test automatically gets a fresh, isolated temporary database.
"""

import pytest
import os
import sqlite3
from auth import init_db


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    """
    Creates a temporary database for EACH test to ensure full isolation.
    No test can ever affect another test's data.
    """
    db_file = tmp_path / "test_users.db"
    monkeypatch.setattr("auth.DB_PATH", str(db_file))

    # Initialize the temporary database with all tables
    init_db()

    yield str(db_file)


@pytest.fixture
def sample_user():
    """Creates and returns a standard test user for convenience."""
    from auth import create_user

    username = "testuser@example.com"
    password = "SecurePass123"
    create_user(username, password)
    return {"username": username, "password": password}


@pytest.fixture
def admin_user():
    """Creates an admin user (matches the hardcoded admin in app.py)."""
    from auth import create_user

    username = "rohith.p@lyzr.ai"
    password = "Rohith@123"
    create_user(username, password)
    return {"username": username, "password": password}


@pytest.fixture
def sample_traces():
    """Returns a list of realistic trace dicts for bulk-save testing."""
    return [
        {
            "trace_id": "trace_001",
            "user_id": "testuser@example.com",
            "agent_id": "agent_abc",
            "credits": 0.25,
            "created_at": "2026-02-17T10:00:00",
            "input": "What is encapsulation?",
            "output": "Encapsulation is...",
            "session_id": "sess_001",
            "inspect": "https://example.com/trace/001",
        },
        {
            "trace_id": "trace_002",
            "user_id": "testuser@example.com",
            "agent_id": "agent_abc",
            "credits": 0.15,
            "created_at": "2026-02-17T10:05:00",
            "input": "What is inheritance?",
            "output": "Inheritance is...",
            "session_id": "sess_001",
            "inspect": "https://example.com/trace/002",
        },
        {
            "trace_id": "trace_003",
            "user_id": "other_user@example.com",
            "agent_id": "agent_abc",
            "credits": 0.30,
            "created_at": "2026-02-17T10:10:00",
            "input": "What is polymorphism?",
            "output": "Polymorphism is...",
            "session_id": "sess_002",
            "inspect": "https://example.com/trace/003",
        },
    ]
