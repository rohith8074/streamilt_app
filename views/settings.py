# --- 1. SETUP AND TOOLS ---
import streamlit as st  # The framework for building the website interface
from auth import (  # Importing our database and settings functions
    get_app_settings,
    update_app_setting,
    get_all_users,
    update_user_limit,
)


def show_settings_view():
    """This function builds the Admin Control Panel for Managing the platform."""

    st.title("⚙️ Application Settings")
    st.markdown("---")

    # We load all the current global settings from our database.
    settings = get_app_settings()

    # --- 2. GLOBAL CONFIGURATION ---
    with st.container():
        # A. Lyzr API Key Management
        # The API key is never pre-filled; the admin must set it here. All AI calls use this value.
        st.subheader("🔑 Platform Credentials")
        current_api_key = settings.get("admin_api_key", "")

        # If the key is empty or just whitespace, treat it as not set (show empty field).
        # This ensures no old/default values are displayed.
        if current_api_key and current_api_key.strip():
            display_value = current_api_key
            key_status = "✅ Configured"
        else:
            display_value = ""  # Empty string so field shows as empty
            key_status = "⚠️ Not set"

        # Show status indicator
        st.caption(f"Status: {key_status}")

        col1, col2 = st.columns([4, 1])
        with col1:
            new_api_key = st.text_input(
                "Company Lyzr API Key",
                value=display_value,
                type="password",
                placeholder="Enter your Lyzr API key here",
                help="Set your Lyzr API key here. This is the only source used for AI calls.",
                label_visibility="visible",
            )
        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("🗑️ Clear", help="Clear the API key field", use_container_width=True):
                update_app_setting("admin_api_key", "")
                st.success("API key cleared. Please set a new one.")
                st.rerun()

        # B. Default Spending Limits
        # Here, the Admin can set a limit on how many credits/dollars each user can spend by default.
        st.subheader("💰 Platform Spending Limits")
        current_limit = float(settings.get("max_credits", 2.0))
        new_limit = st.number_input(
            "Global Credit Limit (Default for all users) ($)",
            value=current_limit,
            min_value=0.1,
            step=0.1,
            help="If a user reaches this amount, their chat will be disabled until you increase it.",
        )

        # Save these global rules to the database.
        if st.button("💾 Save Platform Settings"):
            update_app_setting("admin_api_key", new_api_key)
            update_app_setting("max_credits", str(new_limit))
            st.success("✅ Platform-wide settings have been updated successfully!")
            st.rerun()

        st.divider()

        # --- 3. INDIVIDUAL USER MANAGEMENT ---
        # Sometimes, you might want a specific user to have more or less credits than everyone else.
        st.subheader("👤 Individual User Quotas")
        all_users_data = get_all_users()
        user_usernames = [u["username"] for u in all_users_data]

        # Select the specific person you want to help.
        target_user = st.selectbox("Search for a user to adjust their specific limit:", options=user_usernames)

        if target_user:
            # Find their current settings.
            user_data = next(u for u in all_users_data if u["username"] == target_user)

            # If they don't have a custom limit, we show them they are currently using the Global Default.
            current_val = (
                user_data["credit_limit"]
                if user_data["credit_limit"] is not None
                else float(settings.get("max_credits", 2.0))
            )

            # Adjust their wallet.
            new_val = st.number_input(
                f"New Wallet Limit for {target_user} ($)", value=float(current_val), min_value=0.1, step=0.1
            )

            # Update only this specific user's record in the filing cabinet.
            if st.button(f"Update Individual Quota for {target_user}"):
                update_user_limit(target_user, new_val)
                st.success(f"✅ User '{target_user}' now has a custom limit of ${new_val:.2f}.")
                st.rerun()
