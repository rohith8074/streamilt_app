# --- 1. SETUP AND IMPORTS ---
# These tools allow us to create the screen, handle security, and use our custom designs.
import streamlit as st  # The framework for building the website
import uuid             # Generates unique identity codes
from auth import verify_user, create_user, update_user_session  # Database functions for users
from utils.ui import get_logo_base64, SECONDARY_TEXT              # Visual styling helpers

def show_login_page():
    """This function builds the 'Entry' screen where users sign in or sign up."""
    
    # --- 2. LAYOUT: CENTERING THE CONTENT ---
    # We create three columns and put our content in the middle one (the [1, 2, 1] ratio).
    # This keeps the login box from being too wide on large screens.
    _, col, _ = st.columns([1, 2, 1])
    logo_base64 = get_logo_base64()
    
    with col:
        # --- 3. BRANDING: THE HEADER ---
        # We display the logo and a welcoming title with a nice blue gradient effect.
        st.markdown(f"""
            <div class="login-header-section">
                <img src="{logo_base64}" width="100">
                <h1 style="font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0; background: linear-gradient(135deg, #60a5fa 0%, #2563eb 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Lyzr Assistant</h1>
                <p style="color: {SECONDARY_TEXT}; font-size: 1rem;">Specialized AI Agents Workspace</p>
            </div>
        """, unsafe_allow_html=True)
        
        # --- 4. NAVIGATION: TABS ---
        # We provide two simple tabs: one for returning users and one for new registrations.
        tab1, tab2 = st.tabs(["🔒 Sign In", "🤝 Create Account"])
        
        # --- 5. THE 'SIGN IN' FORM ---
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Your username")
                password = st.text_input("Password", type="password", placeholder="Your password")
                submitted = st.form_submit_button("Authenticate →", use_container_width=True)
                
                if submitted:
                    # We check if the username and password match our database records.
                    if verify_user(username, password):
                        # SUCCESS: We tell the app who you are.
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.query_params["user"] = username
                        
                        # We generate a fresh 'Session ID'. Think of this as a temporary 
                        # ID card for your current visit so we can track the AI's answers.
                        st.session_state.session_id = str(uuid.uuid4())
                        
                        # Identify if the user is the administrator.
                        st.session_state.isAdmin = (username == "rohith.p@lyzr.ai")
                        
                        # Save your visit info in the database.
                        update_user_session(username, st.session_state.session_id)
                        
                        st.success("Welcome back! Entering workspace...")
                        st.rerun() # Refresh the page to show the Chat screen
                    else:
                        st.error("Invalid credentials. Please check your username and password.")
                        
        # --- 6. THE 'CREATE ACCOUNT' FORM ---
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("New Username", placeholder="e.g., john_doe")
                new_password = st.text_input("New Password", type="password", placeholder="Choose a strong password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat your password")
                signup_submitted = st.form_submit_button("Register Account", use_container_width=True)
                
                if signup_submitted:
                    # Basic checks to ensure the user didn't make a mistake.
                    if new_password != confirm_password:
                        st.error("Passwords do not match. Please try again.")
                    elif not new_username or not new_password:
                        st.error("All fields are required to create an account.")
                    else:
                        # Attempt to save the new user in the database.
                        if create_user(new_username, new_password):
                            st.success("Account created successfully! You can now Sign In.")
                        else:
                            st.error("That username is already taken. Please try another one.")
