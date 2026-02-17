# --- 1. SETUP AND IMPORTS ---
# These lines bring in the necessary "tools" (libraries) for the app to run.
import uuid  # Generates unique IDs for chat sessions

import streamlit as st  # The main framework for building the website interface
from dotenv import \
    load_dotenv  # Loads secret configurations from a hidden file (.env)

# --- 2. CONNECTING TO THE "BRAIN" (Auth & Logic) ---
# We are importing functions we wrote in other files to handle things like users and database work.
from auth import create_user  # Function to register a new person
from auth import delete_chat_session  # Deletes a specific session
from auth import get_chat_history  # Retrieves old messages from the database
from auth import \
    get_total_platform_credits  # Total cost spent by everyone on the platform
from auth import \
    get_user_credits  # Checks how much money/credits a person has spent
from auth import \
    get_user_limit  # Finds out how much a user is allowed to spend
from auth import get_user_session  # Finds a user's previous active chat
from auth import init_db  # Initializes the database (the app's filing cabinet)
from auth import update_user_session  # Saves a user's current chat ID
from lyzr_client import \
    AGENT_ID  # The specific ID of the AI agent we are talking to
# --- 3. CONNECTING TO THE "FACE" (UI & Views) ---
# These are the different screens and styling of our application.
from utils.ui import (  # Handles the beautiful design and branding
    BORDER_COLOR, CARD_BG, SECONDARY_TEXT, TEXT_COLOR, get_logo_base64,
    inject_custom_css)
from views.chat import show_chat_view  # The main AI chat screen
from views.dashboard import \
    show_dashboard_view  # The monitoring and charts screen
from views.login import show_login_page  # The screen for Sign In/Sign Up
from views.settings import show_settings_view  # The admin control panel

# --- 4. STARTUP SEQUENCE ---
# This part runs every time the app starts to make sure everything is ready.
load_dotenv(override=True)  # Refresh secret keys
init_db()                   # Make sure the "filing cabinet" (database) exists and is ready

# We create a default Administrator account so you can log in immediately.
create_user("rohith.p@lyzr.ai", "Rohith@123")

# Set up the website's basic information (Tab title, Icon, and Layout)
st.set_page_config(
    page_title="Lyzr AI Assistant",
    page_icon="🤖",
    layout="wide",
)

# Apply our custom "Glassmorphism" design to make the app look premium and modern.
inject_custom_css()

# --- 5. MANAGING THE USER'S "STATE" (Session Management) ---
# This part remembers if you are logged in or what page you are currently viewing.

# If the app doesn't know who you are, it checks if you were just here (via URL link).
if "logged_in" not in st.session_state:
    user_param = st.query_params.get("user")
    if user_param:
        st.session_state.logged_in = True
        st.session_state.username = user_param
        st.session_state.session_id = get_user_session(user_param)
        st.session_state.page = "Chat"
        st.session_state.isAdmin = (user_param == "rohith.p@lyzr.ai")
    else:
        # If you are not in the URL and not logged in, show the login screen.
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.session_id = None
        st.session_state.page = "Chat"
        st.session_state.isAdmin = False

# This part loads your old messages so your conversation doesn't disappear when you refresh.
if "messages" not in st.session_state:
    if st.session_state.get("logged_in") and st.session_state.get("username"):
        st.session_state.messages = get_chat_history(st.session_state.username, st.session_state.get("session_id"))
    else:
        st.session_state.messages = []

# Default starting page is always the Chat.
if "page" not in st.session_state:
    st.session_state.page = "Chat"

# --- 6. MAIN NAVIGATION (The Sidebar) ---
# This code builds the menu on the left side of the screen.
if st.session_state.logged_in:
    with st.sidebar:
        # Show your logo or branding at the top (compact).
        logo_base64 = get_logo_base64()
        st.markdown(f'<div style="text-align: center; padding: 0.4rem 0;"><img src="{logo_base64}" width="88"></div>', unsafe_allow_html=True)
        
        # Display the current user's name (compact card).
        st.markdown(f'<div style="background: {CARD_BG}; padding: 0.4rem 0.6rem; border-radius: 8px; border: 1px solid {BORDER_COLOR}; margin: 0.2rem 0;"><span style="color: {SECONDARY_TEXT}; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.04em;">User</span><br><span style="color: {TEXT_COLOR}; font-weight: 600; font-size: 0.85rem;">{st.session_state.username}</span></div>', unsafe_allow_html=True)
        
        st.divider()

        # --- Wallet & Usage Info ---
        # Admins see total platform usage; normal users see their own credits.
        if st.session_state.isAdmin:
            val = get_total_platform_credits(agent_id=AGENT_ID)
            st.metric("Platform Usage", f"${val:.4f}")
        else:
            val = get_user_credits(st.session_state.username, agent_id=AGENT_ID)
            st.metric("Credits Used", f"${val:.4f}")
            
        # Show a progress bar of how much quota is left for the user.
        max_limit = get_user_limit(st.session_state.username)
        if not st.session_state.isAdmin:
            st.progress(min(val / max_limit, 1.0), text=f"Limit: ${max_limit:.2f}")
            if val >= max_limit:
                st.error("Quota Reached - Contact Admin")
        
        st.divider()
        st.caption("NAVIGATION")
        # Buttons to switch between different sections.
        if st.button("💬 Chat", use_container_width=True, key="nav_chat"):
            st.session_state.page = "Chat"
            st.rerun()
        if st.button("📊 Dashboard", use_container_width=True, key="nav_dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()

        # --- CHAT HISTORY ---
        # This section shows your previous conversations so you can jump back into them.
        st.divider()
        st.caption("RECENT CHATS")
        from auth import get_all_user_sessions

        # We fetch all the unique chat sessions this user has started.
        past_sessions = get_all_user_sessions(st.session_state.username)
        
        if not past_sessions:
            st.markdown(f'<div style="color: {SECONDARY_TEXT}; font-size: 0.78rem; text-align: center; padding: 0.35rem 0; font-style: italic;">No past chats yet</div>', unsafe_allow_html=True)
        else:
            # We use a container with a fixed height to create a scrollable area for history
            # This ensures even with 50+ chats, the sidebar remains usable.
            with st.container(height=300):
                for session in past_sessions:
                    # Create two columns: one for the chat preview, one for the delete button
                    cols = st.columns([0.85, 0.15])
                    
                    preview_text = session['preview'][:40] + "..." if len(session['preview']) > 40 else session['preview']
                    
                    with cols[0]:
                        if st.button(f"📄 {preview_text}", key=f"hist_{session['session_id']}", use_container_width=True):
                            st.session_state.session_id = session["session_id"]
                            st.session_state.messages = get_chat_history(st.session_state.username, session["session_id"])
                            update_user_session(st.session_state.username, session["session_id"])
                            st.session_state.page = "Chat"
                            st.rerun()
                    
                    with cols[1]:
                        if st.button("🗑️", key=f"del_{session['session_id']}", help="Delete this chat"):
                            if delete_chat_session(st.session_state.username, session["session_id"]):
                                # If we deleted the CURRENT active session, reset it
                                if st.session_state.session_id == session["session_id"]:
                                    st.session_state.session_id = str(uuid.uuid4())
                                    st.session_state.messages = []
                                    update_user_session(st.session_state.username, st.session_state.session_id)
                                st.rerun()
            
        st.divider()
        st.caption("ACTIONS")
        # Start a fresh conversation with a new Unique ID.
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            if st.session_state.username:
                update_user_session(st.session_state.username, st.session_state.session_id)
            st.session_state.page = "Chat"
            st.rerun()
            
        # Only show the Settings gear to administrators.
        if st.session_state.get('isAdmin'):
            if st.button("⚙️ Settings", use_container_width=True, key="nav_settings"):
                st.session_state.page = "Settings"
                st.rerun()

        st.divider()
        # Securely log out and clear your current state.
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.query_params.clear()
            st.rerun()

    # --- 7. VIEW ROUTER (The Content Area) ---
    # Based on what button you clicked on the left, we show the corresponding screen here.
    if st.session_state.page == "Chat":
        show_chat_view()
    elif st.session_state.page == "Settings" and st.session_state.isAdmin:
        show_settings_view()
    else:
        show_dashboard_view()
else:
    # If not logged in, always show the login/entry page.
    show_login_page()
