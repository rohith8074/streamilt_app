# --- 1. SETUP AND TOOLS ---
import streamlit as st  # The framework for building the website
import pandas as pd  # A powerful tool for handling tables and lists of data
import plotly.express as px  # Used to create beautiful interactive graphs
import json  # For handling data formats
import os  # For system tasks (like checking settings)
from auth import (  # Importing our database management functions
    clear_user_traces,
    get_latest_trace_timestamp,
    save_traces_bulk,
    get_all_traces,
    get_mapping_for_trace,
    get_fuzzy_session,
)
from lyzr_client import get_traces, AGENT_ID  # Tools to fetch data from the AI service
from utils.ui import TEXT_COLOR, CHART_GRID  # Visual design constants


def show_dashboard_view():
    """This function builds the 'Monitoring' screen with charts and logs."""

    # --- 2. HEADER AND RESET BUTTONS ---
    st.title("📊 Monitoring Dashboard")

    refresh_clicked = False
    if st.button("🔄 Refresh & Sync"):
        refresh_clicked = True

    # --- 3. DATA SYNCHRONIZATION (The 'Sync' process) ---
    # When you click refresh, the app reaches out to the AI servers and downloads
    # the receipt of every question you asked and what it cost.
    if refresh_clicked:
        with st.spinner("Downloading your latest interaction records..."):
            from utils.sync import sync_user_activity

            new_count = sync_user_activity(st.session_state.username, st.session_state.session_id)
            if new_count > 0:
                st.toast(f"✅ Successfully downloaded {new_count} new records!")
            st.rerun()

    # --- 4. DATA RETRIEVAL ---
    # We load all the saved records from our local database.
    current_user = st.session_state.username
    traces_data = get_all_traces(user_id=None if st.session_state.isAdmin else current_user, agent_id=AGENT_ID)

    if not traces_data:
        st.info("💡 **Your dashboard is currently empty.** Start a chat to see your metrics here!")
        df = pd.DataFrame(
            columns=[
                "trace_id",
                "user_id",
                "agent_id",
                "credits",
                "created_at",
                "input",
                "output",
                "session_id",
                "inspect",
            ]
        )
    else:
        df = pd.DataFrame(traces_data)

        # 🕒 TIMEZONE CONVERSION: Convert timestamps from UTC to IST for local accuracy.
        # Lyzr sends UTC (London time), so we add 5.5 hours to match IST.
        try:
            df["created_at"] = pd.to_datetime(df["created_at"])
            if df["created_at"].dt.tz is None:
                df["created_at"] = df["created_at"].dt.tz_localize("UTC")
            df["created_at"] = df["created_at"].dt.tz_convert("Asia/Kolkata")
        except Exception as e:
            # Fallback if timezone data is missing or corrupted
            pass

    # --- 5. ADMIN FILTERS ---
    # Administrators can filter the entire dashboard to look at one specific user's activity.
    if st.session_state.isAdmin and not df.empty:
        st.markdown("### 🔍 Admin Filtering")
        all_users = sorted(df["user_id"].unique().tolist())
        filter_options = ["All Users"] + all_users
        selected_user = st.selectbox("View dashboard as:", options=filter_options, index=0)

        if selected_user != "All Users":
            df = df[df["user_id"] == selected_user].copy()
            st.caption(f"Showing detailed results for: **{selected_user}**")
        else:
            st.caption("Showing global statistics across **All Users**")
        st.divider()

    # --- 6. PREPARE DATA FOR TABLE (same set used for KPIs and table so they match exactly) ---
    # Build the display set first: same sort and limit as the table, so KPIs match the table exactly.
    if df.empty:
        display_df = pd.DataFrame(
            columns=[
                "trace_id",
                "user_id",
                "agent_id",
                "credits",
                "created_at",
                "input",
                "output",
                "session_id",
                "inspect",
            ]
        )
        table_df = pd.DataFrame(columns=["created_at", "credits", "input", "output"])
        total_traces = 0
        total_credits = 0.0
    else:
        # Sort by created_at descending and take top 50
        display_df = df.sort_values(by="created_at", ascending=False).head(50).copy()

        # Ensure credits column exists and is numeric (handle any missing or invalid values)
        if "credits" not in display_df.columns:
            display_df["credits"] = 0.0
        display_df["credits"] = pd.to_numeric(display_df["credits"], errors="coerce").fillna(0.0)

        # Create table_df with only the columns we'll display, ensuring all rows are preserved
        table_df = display_df[["created_at", "credits", "input", "output"]].copy()

        # Fill text columns with "N/A" for display, but keep credits as numeric
        table_df["input"] = table_df["input"].fillna("N/A")
        table_df["output"] = table_df["output"].fillna("N/A")
        # Credits is already numeric from above, but ensure it's still numeric
        table_df["credits"] = pd.to_numeric(table_df["credits"], errors="coerce").fillna(0.0)

        # Calculate KPIs from the EXACT same data that will be in the table
        total_traces = len(table_df)  # Use table_df length to ensure exact match
        total_credits = float(table_df["credits"].sum())  # Sum from table_df to ensure exact match

    # --- 7. KPI CARDS (Big Numbers) — match table below ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Total Interactions</div>
                <div class="metric-value">{total_traces}</div>
                <div class="status-badge">● Table below</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Platform Investment</div>
                <div class="metric-value">${total_credits:.4f}</div>
                <div class="status-badge" style="background-color: #eff6ff; color: #2563eb;">Credits (table)</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    n_display = len(table_df)

    # Verification: Calculate what the table should show (for admin debugging)
    if not table_df.empty:
        table_count = len(table_df)
        table_sum = float(table_df["credits"].sum())
        # Show verification info in collapsed expander for admins
        if st.session_state.isAdmin:
            with st.expander("🔍 Verification (Admin Only)", expanded=False):
                st.write(f"**KPI Total Interactions:** {total_traces}")
                st.write(f"**Table Row Count:** {table_count}")
                st.write(f"**Match:** {'✅ Yes' if total_traces == table_count else '❌ No'}")
                st.write("---")
                st.write(f"**KPI Platform Investment:** ${total_credits:.4f}")
                st.write(f"**Table Credits Sum:** ${table_sum:.4f}")
                st.write(f"**Match:** {'✅ Yes' if abs(total_credits - table_sum) < 0.0001 else '❌ No'}")
                if abs(total_credits - table_sum) >= 0.0001:
                    st.warning(f"⚠️ Difference: ${abs(total_credits - table_sum):.6f}")

    st.caption(f"Metrics reflect the **{n_display}** row(s) in the table below (up to 50 most recent).")
    st.write("")

    # --- 8. USAGE TREND GRAPH ---
    # This chart shows when you spent credits over time.
    st.markdown("### 📈 Usage Over Time")
    if df.empty:
        st.info("No usage data available for the chart yet.")
    else:
        # 📈 THE TREND LINE: Creating the 'Usage Over Time' graph.
        fig_trend = px.line(
            df.sort_values(by="created_at"),
            x="created_at",
            y="credits",
            template="plotly_dark",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#3b82f6"],
        )
        # Style the graph to match our Dark Theme.
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit", color=TEXT_COLOR),
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            hovermode="x unified",
            dragmode=False,  # Disable editing the graph
            xaxis=dict(showgrid=False, color="#64748b", fixedrange=True),
            yaxis=dict(gridcolor=CHART_GRID, color="#64748b", fixedrange=True),
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    # --- 9. DETAILED LOGS TABLE ---
    # table_df was already created above from the same data used for KPIs, ensuring perfect match.
    st.markdown("### 📜 Application Logs")

    st.dataframe(
        table_df,
        column_config={
            "created_at": st.column_config.DatetimeColumn("Timestamp", format="D MMM, HH:mm"),
            "credits": st.column_config.NumberColumn("Cost ($)", format="$%.4f"),
            "input": st.column_config.TextColumn("Your Question", width="medium"),
            "output": st.column_config.TextColumn("AI's Answer", width="large"),
        },
        width="stretch",
        hide_index=True,
    )
