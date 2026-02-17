# 🤖 Lyzr AI Assistant — OOP Specialist

**A friendly AI learning platform that teaches Object-Oriented Programming (OOP) using one Lyzr AI agent.**  
Whether you're a student, teacher, or curious learner, this app lets you chat with the AI about **Encapsulation**, **Inheritance**, **Polymorphism**, and **Abstraction** — with secure accounts, spending limits, and a clean dark-themed interface.

---

## 📖 Table of Contents

1. [What Is This App?](#-what-is-this-app)
2. [Who Is It For?](#-who-is-it-for)
3. [What Can You Do? (Features)](#-what-can-you-do-features)
4. [How Does It Look and Feel?](#-how-does-it-look-and-feel)
5. [What Do You Need to Run It?](#-what-do-you-need-to-run-it)
6. [Step-by-Step: Getting Started](#-step-by-step-getting-started)
7. [Project Structure (Where Everything Lives)](#-project-structure-where-everything-lives)
8. [Database and Data Storage](#-database-and-data-storage)
9. [Testing](#-testing)
10. [Technology Used (For the Curious)](#-technology-used-for-the-curious)
11. [Troubleshooting](#-troubleshooting)
12. [License & Credits](#-license--credits)

---

## 🎯 What Is This App?

Think of it as a **web-based chatbot** that:

- **Teaches OOP concepts** — You ask questions about Object-Oriented Programming; the app sends your message to one Lyzr AI agent, which answers about OOP topics (e.g. Encapsulation, Inheritance, Polymorphism, Abstraction).
- **Remembers who you are** — You sign in with a username and password. Your chat history and usage are saved under your account.
- **Keeps spending under control** — Each user has a "credit limit" (like a budget). The app shows how much you've used and stops you from chatting when the limit is reached (unless you're the administrator).
- **Lets admins manage everything** — One special account (the administrator) can change the main API key, set default and per-user limits, and see usage across all users.

The app runs in your **web browser**. You don't need to install anything on your phone; you open a link (for example `http://localhost:8501`) after someone starts the app on a computer.

---

## 👥 Who Is It For?

| Audience | How they use it |
|----------|------------------|
| **Learners** | Sign up, log in, ask OOP questions in the chat, and get answers from the Lyzr AI agent. |
| **Teachers / Trainers** | Use it as a demo or lab environment; can create accounts for students. |
| **Administrators** | Log in with the admin account to set API keys, credit limits, and view platform-wide usage. |
| **Developers** | Run the app locally, read the code, or extend it (e.g. add new agents or change the UI). |

---

## ✨ What Can You Do? (Features)

### For Everyone (Users)

| Feature | What it means in simple terms |
|--------|--------------------------------|
| **Sign In / Create Account** | Log in with username and password, or register a new account. Passwords are stored in a secure, scrambled form (never in plain text). |
| **Chat with AI** | Type questions about OOP in a chat box. Your message is sent to the Lyzr AI agent, and you get an answer in the same chat. |
| **Credit meter** | In the left sidebar you see how much "credit" (cost in dollars) you've used. The app uses this to enforce your spending limit. |
| **Progress bar** | A bar shows how close you are to your credit limit. When you hit the limit, you see a message and cannot send new messages until the admin raises your limit. |
| **Chat history** | Your past conversations are saved. In the sidebar you see a list of "Recent Chats" — click one to open that conversation again. |
| **New Chat** | Start a brand-new conversation with a single click; the current one stays in history. |
| **Dashboard** | A page with charts and a table: total number of interactions, total credits spent, a "Usage Over Time" graph, and a log of your questions and the AI's answers. You can also click "Refresh & Sync" to pull the latest usage data from the AI service. |
| **Logout** | Safely sign out. Your data stays saved for the next time you log in. |

### For Administrators Only

| Feature | What it means in simple terms |
|--------|--------------------------------|
| **Platform usage** | In the sidebar, instead of "Credits Used" you see "Platform Usage" — the total amount spent by *all* users. |
| **Settings page** | A separate screen (gear icon in the sidebar) where you can: (1) set or change the **Lyzr API Key** used for all AI calls, and (2) set the **global default credit limit** for every user. |
| **Per-user limits** | In Settings you can pick a user and give them a custom credit limit (higher or lower than the default). |
| **View as user** | On the Dashboard, admins can choose "View dashboard as: [user]" to see that user's usage and logs only. |
| **No credit cap** | The administrator account is not blocked by the credit limit; they can keep chatting even when the limit would normally apply. |

---

## 🎨 How Does It Look and Feel?

- **Dark theme** — The app uses a dark background (charcoal / navy tones) so it’s easy on the eyes.
- **Glassmorphism style** — Cards and panels look slightly translucent with soft borders, like frosted glass.
- **Font** — A modern, readable font (Outfit) is used for titles and text.
- **Layout** — Wide layout: a **sidebar on the left** (logo, user name, credits, navigation, recent chats, New Chat, Settings for admin, Logout) and the **main area** on the right (Chat, Dashboard, or Settings).
- **Charts** — The Dashboard uses interactive Plotly charts (you can hover to see exact values).

---

## 📋 What Do You Need to Run It?

- **Python** — Version **3.9 or higher** must be installed on the computer where the app will run.  
  - *If you're not sure:* Open a terminal/command prompt and type `python --version` or `python3 --version`. You should see something like `Python 3.11.x`.
- **Internet** — The app talks to Lyzr’s servers for AI responses and for syncing usage data.
- **Lyzr account** — You need a Lyzr API key and one Lyzr agent (created in Lyzr). The app uses that single agent for all chat responses.

---

## 🚀 Step-by-Step: Getting Started

### Step 1: Get the project on your computer

- If you have the project as a folder, open that folder in your file manager or in Cursor/VS Code.
- If you use Git, clone the repository into a folder and open that folder.

### Step 2: Open a terminal in the project folder

- On Mac/Linux: open Terminal and run `cd` to go to the project folder, e.g.  
  `cd /path/to/Streamlit_app`
- On Windows: open Command Prompt or PowerShell and do the same.

### Step 3: Create a virtual environment (recommended)

This keeps the app’s dependencies separate from other Python projects.

```bash
python3 -m venv venv
```

Then turn it on:

- **Mac/Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

You should see `(venv)` at the start of your command line.

### Step 4: Install dependencies

Run:

```bash
pip install -r requirements.txt
```

This installs: Streamlit (web framework), requests (to call Lyzr API), python-dotenv (to load `.env`), bcrypt (password hashing), pandas and plotly (for the dashboard).

### Step 5: Create and fill the `.env` file

In the **same folder** as `app.py`, create a file named `.env` (no name before the dot, extension is `env`).

Copy the contents from `.env.example` and replace the placeholder values with your real values:

```env
LYZR_API_KEY=your_lyzr_api_key_here
AGENT_ID=your_lyzr_agent_id
LYZR_API_URL=https://agent-prod.studio.lyzr.ai/v3/inference/chat/
LYZR_TRACES_URL=https://agent-prod.studio.lyzr.ai/v3/traces
```

- **LYZR_API_KEY** — Your Lyzr API key (required).
- **AGENT_ID** — Your single Lyzr agent’s ID (required). All chat messages are sent to this agent.
- **LYZR_API_URL** and **LYZR_TRACES_URL** — Usually you can leave these as in the example unless Lyzr gives you different URLs.

Save the file. **Do not share your `.env` file or put it in public places** — it contains secrets.

### Step 6: Run the app

In the same terminal (with `venv` activated), run:

```bash
streamlit run app.py
```

You should see a line like:

```text
Local URL: http://localhost:8501
```

### Step 7: Open the app in your browser

- Open a web browser (Chrome, Firefox, Safari, Edge, etc.).
- In the address bar type: `http://localhost:8501` and press Enter.

You should see the Lyzr Assistant login screen.

### Step 8: Log in for the first time

The app creates a **default administrator** account when it starts (see `app.py`). The default is:

- **Username:** `rohith.p@lyzr.ai`
- **Password:** `Rohith@123`

Use these to log in as admin, or use "Create Account" to register a new user. **For production or sharing, you should change the default admin password or create a new admin account and remove this default.**

---

## 📂 Project Structure (Where Everything Lives)

Below is a simple map of the main files and folders. You don’t need to edit these to use the app; this is for understanding and for developers.

```text
Streamlit_app/
├── app.py                 # Main entry: starts the app, loads login/chat/dashboard/settings
├── auth.py                # Database and security: users, passwords, sessions, credits, traces, settings
├── lyzr_client.py         # Talks to Lyzr: send chat messages, fetch usage (traces)
├── .env                   # Your secrets (API key, agent IDs) — you create this from .env.example
├── .env.example            # Template showing which variables to set
├── .gitignore             # Files excluded from Git (venv, .env, database, caches)
├── requirements.txt       # List of Python packages to install
├── pytest.ini             # Pytest configuration (test paths, verbosity)
├── users.db               # SQLite database (created automatically): users, chats, traces, settings
├── utils/
│   ├── ui.py              # Styling: colors, fonts, glassmorphism CSS, logo
│   └── sync.py            # Syncs usage data from Lyzr to the local database (credits, logs)
├── views/
│   ├── login.py           # Login and registration page
│   ├── chat.py            # Chat screen: send messages, show history, call Lyzr, save messages/traces
│   ├── dashboard.py      # Dashboard: charts, usage table, refresh/sync, admin filter
│   └── settings.py       # Admin-only: API key, global limit, per-user limits
├── tests/                 # Automated test suite (pytest)
│   ├── conftest.py        # Shared fixtures: temp database, sample users, sample traces
│   ├── test_auth.py       # Tests for auth.py (47 tests: users, sessions, credits, chat, traces, settings)
│   ├── test_sync.py       # Tests for sync.py (12 tests: credit division, attribution, security, edge cases)
│   ├── test_lyzr_client.py # Tests for lyzr_client.py (12 tests: API key, chat, traces — all HTTP mocked)
│   └── test_ui.py         # Tests for ui.py (5 tests: base64 encoding, CSS injection smoke test)
```

- **app.py** — What runs when you type `streamlit run app.py`. It sets up the database, loads styling, and shows either the login page or the main app (sidebar + Chat/Dashboard/Settings).
- **auth.py** — All database operations: create/verify users, save/load chat messages, save/load traces, credit limits, settings. Uses SQLite and bcrypt for passwords.
- **lyzr_client.py** — Sends your message to Lyzr chat endpoint and gets the AI reply; also fetches "traces" (usage receipts) from the separate Lyzr traces endpoint.
- **utils/sync.py** — Takes traces from Lyzr, figures out which user each trace belongs to, converts cost to credits, and saves them into `users.db` so the dashboard and credit meter are correct.

<<<<<<< HEAD

---
=======
>>>>>>> a83a7bf (updated Readme)

## 🗄️ Database and Data Storage

The app uses a single **SQLite** file: **`users.db`**. It is created automatically in the project folder when you first run the app.

- **users** — Username, hashed password, current session ID, optional per-user credit limit.
- **chat_messages** — Every message in every chat: username, session ID, role (user/assistant), content, timestamp.
- **traces** — Synced usage records: trace ID, user ID, agent ID, credits, timestamp, and optional input/output/inspect URL.
- **trace_user_mapping** — Links trace IDs (or temporary IDs) to users and sessions for attribution.
- **settings** — Key-value store: e.g. `max_credits` (default limit), `admin_api_key` (Lyzr API key from Settings page).

Passwords are hashed with **bcrypt**; they are never stored in plain text. The database uses WAL (Write-Ahead Logging) for better concurrency. For more detail, see **DATABASE.md**. 

---

## 🧪 Testing

The project includes a comprehensive **pytest** test suite with **77 tests** covering all core modules. Tests run against an isolated temporary database — your real `users.db` is **never** touched.

### How to Run Tests

```bash
# 1. Make sure you have pytest installed (inside your venv)
pip install pytest pytest-mock

# 2. Run all tests with verbose output
./venv/bin/python -m pytest -v

# 3. Run a specific test file
./venv/bin/python -m pytest tests/test_auth.py -v

# 4. Run a specific test class or function
./venv/bin/python -m pytest tests/test_auth.py::TestCreditLimits -v
./venv/bin/python -m pytest tests/test_sync.py::TestCreditDivision::test_action_cost_divided_by_100 -v
```

### Test Structure

```text
tests/
├── conftest.py           # Shared fixtures (auto-creates temp DB for every test)
├── test_auth.py          # 47 tests — Database, authentication, and business logic
├── test_sync.py          # 12 tests — Lyzr-to-local sync pipeline
├── test_lyzr_client.py   # 12 tests — Lyzr API client (all HTTP mocked)
└── test_ui.py            #  6 tests — UI helpers and CSS smoke test
```

### What Each File Tests

| Test File | Module Under Test | What It Covers |
|-----------|------------------|----------------|
| `test_auth.py` | `auth.py` | User registration & login, duplicate prevention, session management, credit limits (global/custom), chat history (save/load/delete/order), trace bulk saving & retrieval, trace mapping, app settings, fuzzy session matching, database initialization |
| `test_sync.py` | `utils/sync.py` | Credit division by 100, all three attribution methods (direct/mapping/fuzzy), security skip for other users' traces, edge cases (empty/null API responses, missing fields, duplicates) |
| `test_lyzr_client.py` | `lyzr_client.py` | API key retrieval, chat request/response (success, missing key, network error), trace fetch (dict & list formats, agent filtering, network error) |
| `test_ui.py` | `utils/ui.py` | Base64 file encoding, image-to-data-URI conversion, missing file handling, CSS injection smoke test (prevents NameError regressions) |

### Key Design Decisions

- **Database Isolation**: Every test gets its own temporary SQLite database via `conftest.py`. Tests can run in parallel without interference.
- **No Real API Calls**: All Lyzr API calls in `test_sync.py` and `test_lyzr_client.py` are mocked with `pytest-mock`. Tests run offline and fast (~5 seconds total).
- **CSS Smoke Test**: The `test_ui.py` suite includes a regression test to ensure the CSS f-string in `inject_custom_css()` has no Python syntax errors (curly brace escaping).

---

## 🛠️ Technology Used (For the Curious)

| Layer | Technology | Purpose |
|-------|------------|--------|
| **Frontend / UI** | Streamlit | Builds the web interface (pages, forms, chat, sidebar). |
| **Styling** | Custom CSS (in `utils/ui.py`) | Dark theme, glassmorphism, Outfit font, buttons, inputs, tables. |
| **Backend logic** | Python 3.x | All app logic: auth, chat, dashboard, sync. |
| **AI** | Lyzr Agent API | Sends messages to your single Lyzr agent; fetches traces for usage tracking. |
| **Database** | SQLite + WAL | Stores users, chat history, traces, settings. |
| **Security** | Bcrypt, UUID | Password hashing; unique session IDs. |
| **Charts** | Plotly Express | Interactive "Usage Over Time" and dashboard visuals. |

---

## ❓ Troubleshooting

| Problem | What to try |
|--------|-------------|
| **"Python not found" / "streamlit not found"** | Make sure Python 3.9+ is installed and you ran `pip install -r requirements.txt` inside the same environment (e.g. `venv`) you’re using to run `streamlit run app.py`. |
| **"Missing Lyzr API Credentials"** | Create a `.env` file in the project root with `LYZR_API_KEY` and `AGENT_ID` at least. Restart the app after changing `.env`. |
| **Blank or error page in browser** | Confirm the app is still running in the terminal and that you’re opening the URL it prints (e.g. `http://localhost:8501`). Try a different browser or clear cache. |
| **Credits don’t update** | Click "Refresh & Sync" on the Dashboard. If you’re an admin, ensure the API key in Settings is correct and that Lyzr is returning traces. |
| **"Quota Reached"** | Your account has hit its credit limit. Ask an administrator to increase your limit in Settings → Individual User Quotas. |
| **Can’t log in** | Check username and password. For the default admin, use the credentials in Step 8 above. If you changed the code that creates the default user, ensure that still runs on startup. |
| **Logo or image missing** | The app expects a logo at the path in `utils/ui.py` (e.g. `lyzr.png` in the project folder). If the path is wrong or the file is missing, the logo area may be empty; the app still runs. |

---

## 📄 License & Credits

- Built for **educational use** with the **Lyzr.ai** Agent framework.
- Default admin account is for initial setup only; change or remove it before sharing or production use.

---

**You’re all set.** For a quick start: install Python 3.9+, run `pip install -r requirements.txt`, create `.env` with your Lyzr key and agent ID, then run `streamlit run app.py` and open `http://localhost:8501` in your browser.
