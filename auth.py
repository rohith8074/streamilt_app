# --- 1. CORE SYSTEM IMPORTS ---
import logging  # The app's diary (Logs everything that happens behind the scenes)
import sqlite3  # The "Filing Cabinet" engine (Our database)
from contextlib import contextmanager

import bcrypt  # Security tool used to scramble (hash) passwords so they are safe

# --- 2. LOGGING SETUP ---
# This part makes sure that if anything goes wrong, we save a record of it.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "users.db" # This is the name of our database file
DB_TIMEOUT = 20      # We wait up to 20 seconds if the database is busy

@contextmanager
def db_connection():
    """
    Context manager for database connections.

    Usage:
        with db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT ...")

    Ensures connection is always closed, even on errors.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        yield conn
    finally:
        if conn:
            conn.close()

# --- 3. DATABASE INITIALIZATION (The Filing Cabinet Setup) ---
# This function creates our tables (drawers) if they don't already exist.
def init_db():
    """Initializes the database and creates all necessary tables for Users, Traces, and Settings."""
    with db_connection() as conn:
        c = conn.cursor()

        # Enable a 'high-performance' mode for our database
        c.execute("PRAGMA journal_mode=WAL")

        # TABLE 1: USERS (Stores usernames and passwords)
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password TEXT, session_id TEXT)''')

        # Update the users table if we added new features (like credit limits)
        c.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in c.fetchall()]
        if 'session_id' not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN session_id TEXT")
        if 'credit_limit' not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN credit_limit REAL")

        # TABLE 2: TRACES (Receipts of AI interactions)
        c.execute('''CREATE TABLE IF NOT EXISTS traces
                     (trace_id TEXT PRIMARY KEY, user_id TEXT, agent_id TEXT,
                      credits REAL, created_at TIMESTAMP)''')

        # Ensure current tables have all the columns needed for new features
        c.execute("PRAGMA table_info(traces)")
        existing_trace_cols = [column[1] for column in c.fetchall()]
        for col in ['input', 'output', 'session_id', 'inspect']:
            if col not in existing_trace_cols:
                c.execute(f"ALTER TABLE traces ADD COLUMN {col} TEXT")

        # TABLE 3: MAPPINGS (Connects anonymous AI records to real users)
        c.execute('''CREATE TABLE IF NOT EXISTS trace_user_mapping
                     (trace_id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT)''')

        # TABLE 4: SETTINGS (Global rules for the entire app)
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')

        # TABLE 5: CHAT HISTORY (Saves your actual conversations)
        c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT,
                      session_id TEXT,
                      role TEXT,
                      content TEXT,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # Set up some default rules if they are missing.
        # Admin API key is left empty so the admin must set it manually in Settings (never pre-filled from .env).
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_credits', '2.0')")

        # Ensure admin_api_key exists and is empty by default (not pre-filled from .env).
        # If it doesn't exist, create it empty. If it exists, check if it needs to be cleared.
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_api_key', '')")

        # Check if there's an existing value that might be from old code (pre-filled from .env).
        # We check if it matches what would be in .env - if so, and if .env has a different value now,
        # we clear it. But actually, we can't reliably detect this, so we just ensure empty values stay empty.
        # The admin must manually set the key in Settings - we never auto-populate it.
        c.execute("UPDATE settings SET value = '' WHERE key = 'admin_api_key' AND (value IS NULL OR value = '' OR trim(value) = '')")

        conn.commit()

# --- 4. TRACKING AND AUDITING FUNCTIONS ---
# These functions help the administrator see exactly what happened in the system.

def save_trace_mapping(trace_id, user_id, session_id):
    """Links an anonymous 'Trace ID' from the AI to a specific User's account."""
    if not trace_id or not user_id: return
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    try:
        conn.execute("INSERT OR REPLACE INTO trace_user_mapping (trace_id, user_id, session_id) VALUES (?, ?, ?)", (trace_id, user_id, session_id))
        conn.commit()
    finally:
        conn.close()

def get_mapping_for_trace(trace_id):
    """Finds out which user owns a specific AI interaction receipt."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        c.execute("SELECT user_id, session_id FROM trace_user_mapping WHERE trace_id=?", (trace_id,))
        result = c.fetchone()
        if result:
            return result[0], result[1]
        return None, None
    except sqlite3.Error as e:
        logger.error("Failed to get mapping for trace %s: %s", trace_id, e)
        return None, None
    finally:
        if conn:
            conn.close()

def save_traces_bulk(traces_list):
    """Saves many receipts (traces) into the database at once. Very efficient."""
    if not traces_list: return 0
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    count = 0
    try:
        for trace_data in traces_list:
            # Logic: If we already have the receipt, we update it; otherwise, we create a new one.
            c.execute("SELECT user_id FROM traces WHERE trace_id = ?", (trace_data['trace_id'],))
            existing = c.fetchone()
            if existing:
                c.execute("UPDATE traces SET user_id=?, credits=?, created_at=?, input=?, output=?, session_id=?, inspect=? WHERE trace_id=?",
                          (trace_data['user_id'], trace_data['credits'], trace_data['created_at'], trace_data.get('input'), trace_data.get('output'), trace_data.get('session_id'), trace_data.get('inspect'), trace_data['trace_id']))
            else:
                c.execute("INSERT INTO traces (trace_id, user_id, agent_id, credits, created_at, input, output, session_id, inspect) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (trace_data['trace_id'], trace_data['user_id'], trace_data['agent_id'], trace_data['credits'], trace_data['created_at'], trace_data.get('input'), trace_data.get('output'), trace_data.get('session_id'), trace_data.get('inspect')))
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count

def get_all_traces(user_id=None, agent_id=None):
    """Retrieves all chat logs. Admins see everything, normal users see only their own."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM traces"
    params = []
    conditions = []
    
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    
    if agent_id:
        conditions.append("agent_id = ?")
        params.append(agent_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- 5. USER AND CREDIT MANAGEMENT ---
# These functions handle your money (credits) and your account security.

def create_user(username, password):
    """Registers a new person. We scramble the password immediately for security."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = None  # Initialize to None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except (sqlite3.Error, ValueError, UnicodeDecodeError) as e:
        logger.error("User creation failed: %s", e)
        return False
    finally:
        if conn:
            conn.close()

def verify_user(username, password):
    """Checks if the password provided matches the scrambled password in our drawer."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        # The password in the database might be 'text' or 'bytes' depending on your system.
        # We safely ensure both are converted to the format needed for the security check.
        p_bytes = password.encode('utf-8') if isinstance(password, str) else password
        h_bytes = result[0].encode('utf-8') if isinstance(result[0], str) else result[0]
        return bcrypt.checkpw(p_bytes, h_bytes)
    return False

def get_user_credits(user_id, agent_id=None):
    """Calculates how many total dollars/credits a specific user has used."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    if agent_id:
        query = "SELECT SUM(credits) FROM traces WHERE user_id=? AND agent_id=?"
        c.execute(query, (user_id, agent_id))
    else:
        query = "SELECT SUM(credits) FROM traces WHERE user_id=?"
        c.execute(query, (user_id,))
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0.0

def get_user_limit(username):
    """Finds out the 'Spending Limit' for a user. If they don't have a custom one, use the Global rule."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    c.execute("SELECT credit_limit FROM users WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    if res and res[0] is not None: return float(res[0])
    
    # Fallback to general platform limit
    settings = get_app_settings()
    return float(settings.get("max_credits", 2.0))

# --- 6. CHAT HISTORY PERSISTENCE ---
# This part saves your conversations so you can read them tomorrow.

def save_chat_message(username, session_id, role, content):
    """Saves a single sentence (message) to the database."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    try:
        from datetime import datetime

        # 🕒 UTC TIME: We save the message with a UTC timestamp to match Lyzr's cloud clocks.
        now_utc = datetime.utcnow().isoformat()
        conn.execute("INSERT INTO chat_messages (username, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)", 
                     (username, session_id, role, content, now_utc))
        conn.commit()
    finally: conn.close()

def get_chat_history(username, session_id=None):
    """Retrieves all previous messages for a user so the chat isn't empty on login."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT role, content FROM chat_messages WHERE username=?"
    params = [username]
    if session_id:
        query += " AND session_id=?"
        params.append(session_id)
    query += " ORDER BY timestamp ASC"
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    return [{"role": row['role'], "content": row['content']} for row in rows]

def get_all_user_sessions(username):
    """Retrieves a list of all unique chat sessions this user has participated in."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    # We find unique Session IDs and the first message sent in that session to use as a title.
    c.execute("""
        SELECT session_id, MIN(content), MAX(timestamp) 
        FROM chat_messages 
        WHERE username=? AND role='user'
        GROUP BY session_id 
        ORDER BY MAX(timestamp) DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    return [{"session_id": row[0], "preview": row[1][:30] + "..." if row[1] else "New Chat"} for row in rows]

def delete_chat_session(username, session_id):
    """Permanently deletes all messages from a specific chat session."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    try:
        conn.execute("DELETE FROM chat_messages WHERE username=? AND session_id=?", (username, session_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return False
    finally:
        conn.close()

# --- 7. UTILITY FUNCTIONS ---
# Specialized helpers for various internal tasks.

def get_app_settings():
    """Reads the 'Global Rules' (like API keys) from the database."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def update_app_setting(key, value):
    """Changes a global rule (like increasing the default user limit)."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_latest_trace_timestamp(user_id=None, agent_id=None):
    """Finds the timestamp of the very last record we have, to help synchronize with the cloud."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    c.execute("SELECT MAX(created_at) FROM traces")
    res = c.fetchone()[0]
    conn.close()
    return res if res else None

def get_user_session(username):
    """Checks if the user already has an active session from an earlier visit."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    c.execute("SELECT session_id FROM users WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res and res[0] else None

def update_user_session(username, session_id):
    """Saves the user's current session ID so they can stay in the same conversation."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.execute("UPDATE users SET session_id=? WHERE username=?", (session_id, username))
    conn.commit()
    conn.close()

def clear_user_traces(user_id=None, agent_id=None):
    """Wipes the interaction history from the local filing cabinet."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.execute("DELETE FROM traces WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_total_platform_credits(agent_id=None):
    """Calculates the total platform health by checking total spent credits by everyone."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    if agent_id:
        query = "SELECT SUM(credits) FROM traces WHERE agent_id = ?"
        res = c.execute(query, (agent_id,)).fetchone()[0]
    else:
        res = c.execute("SELECT SUM(credits) FROM traces").fetchone()[0]
    conn.close()
    return res if res else 0.0

def get_all_users():
    """Lists every registered user so the admin can manage them."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    rows = conn.execute("SELECT username, credit_limit FROM users").fetchall()
    conn.close()
    return [{"username": row[0], "credit_limit": row[1]} for row in rows]

def update_user_limit(username, limit):
    """Sets a special spending limit for one specific person."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.execute("UPDATE users SET credit_limit=? WHERE username=?", (limit, username))
    conn.commit()
    conn.close()

def get_fuzzy_session(user_id, timestamp_str):
    """
    A clever detective function that finds a session ID by matching a user
    and a nearby timestamp. Used when the AI receipt doesn't have an ID yet.
    """
    if not user_id or not timestamp_str:
        return None

    conn = None
    try:
        from datetime import datetime

        # 1. Parse the time from the cloud receipt
        try:
            # Lyzr usually sends time in ISO format (e.g., 2026-02-17T...)
            trace_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            # Fall back to strptime for non-ISO formats
            trace_time = datetime.strptime(timestamp_str[:19], "%Y-%m-%dT%H:%M:%S")

        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()

        # 2. Look for our 'fuzzy' breadcrumbs for this user
        c.execute("SELECT trace_id, session_id FROM trace_user_mapping WHERE user_id = ? AND trace_id LIKE 'fuzzy_%'", (user_id,))
        fuzzy_entries = c.fetchall()

        for entry_id, session_id in fuzzy_entries:
            try:
                time_part = entry_id.split("_")[-1]
                map_time = datetime.fromisoformat(time_part).replace(tzinfo=None)

                # 3. If the chat happened within 120 seconds of the receipt, it's a match!
                # We increased this to 120s to account for slight cloud delays.
                time_diff = abs((trace_time - map_time).total_seconds())
                if time_diff < 120:
                    return session_id

                # Log slight misses to help find the right window
                if time_diff < 3600: # only log if within an hour
                    print(f"⌛ [FUZZY NEAR MISS]: Diff {time_diff:.1f}s between Cloud({trace_time.strftime('%H:%M:%S')}) and Local({map_time.strftime('%H:%M:%S')})")
            except (ValueError, IndexError, AttributeError):
                # Skip entries with malformed timestamps
                continue

        return None

    except (sqlite3.Error, ValueError, ImportError) as e:
        logger.error("Fuzzy session lookup failed for %s: %s", user_id, e)
        return None
    finally:
        if conn:
            conn.close()
