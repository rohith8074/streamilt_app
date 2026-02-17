# Lyzr Agent Dashboard - SQLite Database Documentation

The application uses a local SQLite database (`users.db`) to manage user authentication, session persistence, telemetry storage (traces), and global administrative settings. 

## 🏗️ Schema Overview

### 1. `users` Table
Stores user credentials and current session metadata.
- **username** (TEXT, PK): The user's email or unique identifier.
- **password** (TEXT): Bcrypt-hashed password.
- **session_id** (TEXT): The persistent UUID for the user's current chat session.

### 2. `traces` Table
Stores telemetry logs fetched from the Lyzr Agent API. This data powers the Dashboard visualizations.
- **trace_id** (TEXT, PK): Unique identifier from Lyzr.
- **user_id** (TEXT): Attributed user (Email).
- **agent_id** (TEXT): The ID of the agent that generated the trace.
- **credits** (REAL): The cost of the interaction in USD ($).
- **created_at** (TIMESTAMP): ISO timestamp of the trace.
- **input** (TEXT): The user's query or tokens info.
- **output** (TEXT): The agent's response or tokens info.
- **session_id** (TEXT): The session UUID used during the interaction.
- **inspect** (TEXT): URL to the Lyzr Studio Gantt chart for internal reasoning logs.

### 3. `trace_user_mapping` Table
A critical shim layer for **Fuzzy Time-Based Attribution**. Since Lyzr traces are sometimes generated without a `user_id`, this table anchors local requests to their respective traces.
- **trace_id** (TEXT, PK): Either a real `trace_id` or a local `interaction_uuid`.
- **user_id** (TEXT): The user who initiated the request.
- **session_id** (TEXT): The session active at the time of request.

### 4. `settings` Table
Global application-wide configurations managed by the Administrator.
- **key** (TEXT, PK): Setting name (e.g., `max_credits`, `admin_api_key`).
- **value** (TEXT): The setting value stored as a string.

---

## 🔒 Security & Performance
- **Password Hashing**: Passwords are never stored in plain text. We use `bcrypt` for secure hashing.
- **Concurrency**: The database is initialized with `PRAGMA journal_mode=WAL` (Write-Ahead Logging) to allow simultaneous reads and writes, crucial for a fluid Streamlit experience.
- **Persistence**: Unlike session state, this database ensures that even if the server restarts or the user clears their cookies, their chat history and credit consumption remain intact.

## 🛠️ Management & Migration
The schema is automatically handled by the `init_db()` function in `auth.py`. It performs "soft migrations"—adding missing columns or tables on the fly—ensuring seamless updates as the platform evolves.
