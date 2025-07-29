# src/submission.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import asyncio
from typing import List, Dict, Any
from streamlit import column_config
import time 

from .submission_utils import (
    initialize_or_clear_session_state, 
    get_task_column_config,
    prepare_tasks_df, 
    update_tasks_from_editor, 
    update_meetings_from_editor, 
    check_existing_submission,
    load_drafts,
    handle_save_or_submit, 
    

)


from .api_client import (
    get_group_activities,
    get_function_activities,
    load_week_submission,
    get_user_details,

)
AUTOSAVE_INTERVAL_SECONDS = 10

@st.dialog("⚠️ Overwrite existing submission?")
def confirm_overwrite_dialog():
    st.write("You already submitted a timesheet for this week. Do you want to permanently overwrite it?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Continue"):
            st.session_state.step = "final"
            st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.step = None
            st.session_state.submit_pressed = False
            st.rerun()


@st.dialog("✅ Confirm Submission")
def confirm_final_dialog():
    st.write("You're about to submit your timesheet for this week. Are you sure?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm and Submit"):
            st.session_state.step = None
            st.session_state.submit_pressed = False
            st.session_state.submitted = True
            st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.step = None
            st.session_state.submit_pressed = False
            st.rerun()

def clean_empty_rows(df):
    """Remove rows where 'Total Weekly Hours' is missing or zero."""
    if "Total Weekly Hours" in df.columns:
        df = df.copy()
        df["Total Weekly Hours"] = pd.to_numeric(df["Total Weekly Hours"], errors="coerce")
        return df[df["Total Weekly Hours"].fillna(0) > 0].reset_index(drop=True)
    return df

# --- State Management and Data Fetching ---
def set_last_thursday():
    today = datetime.today().date()
    last_thursday = today - timedelta(days=(today.weekday() - 3 + 7) % 7)
    st.session_state.selected_date = last_thursday


async def preload_dropdown_options():
    st.session_state.group_activity_options = [ga['name'] for ga in await get_group_activities()]
    team = st.session_state.get("user_team_name", "")
    st.session_state.function_activity_options = await get_function_activities(team)
    st.session_state.status_options = ["Not Started", "In Progress", "On Hold", "Done"]

def initialize_state():
    """Initializes the session state with default values."""
    if "initialized" in st.session_state:
        return

    st.session_state.projects = []
    st.session_state.group_activities = []
    st.session_state.function_activities = []
    st.session_state.selected_portfolio_id = None
    st.session_state.selected_project_id = None
    st.session_state.daily_toggle = False
    st.session_state.unsaved_changes = False
    st.session_state.last_autosave_time = time.time() # Start the timer now

    if "user_email" in st.session_state:
        try:
            user_info = asyncio.run(get_user_details(st.session_state.user_email))
            st.session_state.user_name = user_info.get("full_name", "Unknown")
            st.session_state.user_team_name = user_info.get("team", "Unknown")
        except Exception as e:
            st.warning(f"Failed to load user info: {e}")
            st.session_state.user_name = "Unknown"
            st.session_state.user_team_name = "Unknown"


    try:

        draft_data = asyncio.run(load_drafts(st.session_state.user_email))
        if draft_data and draft_data.get("tasks"):
            st.session_state.daily_toggle = any(task.get("daily_mode", False) for task in draft_data.get("tasks", []))
            tasks_df = pd.DataFrame(draft_data.get("tasks"))
            tasks_df.rename(columns={"Task Description": "Description"}, inplace=True)
            st.session_state.tasks_df = tasks_df
        else:
            st.session_state.daily_toggle = False

        if draft_data and draft_data.get("meetings"):
            meetings_df = pd.DataFrame(draft_data.get("meetings"))
            meetings_df.rename(columns={"Meeting Description": "Description"}, inplace=True)
            st.session_state.meetings_df = meetings_df

        if draft_data and draft_data.get("week_date"):
            st.session_state.selected_date = date.fromisoformat(draft_data["week_date"])
            st.toast("Loaded your most recent draft.", icon="📄")

        rename_map = {'sun': 'Sun', 'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 'thu': 'Thu'}
        if 'tasks_df' in st.session_state and not st.session_state.tasks_df.empty:
            st.session_state.tasks_df.rename(columns=rename_map, inplace=True)

    except Exception as e:
        # If anything fails (e.g., no drafts found), set defaults.
        if "selected_date" not in st.session_state:
            set_last_thursday()
        initialize_or_clear_session_state()


    asyncio.run(preload_dropdown_options())

    st.session_state.initialized = True




# --- UI Rendering Functions ---

# --- NEW: UI function to display the last save time ---
def render_save_status():
    """Displays the last successful save time."""
    last_save = st.session_state.get('last_autosave_time')
    if last_save:
        last_save_time_str = datetime.fromtimestamp(last_save).strftime("%H:%M:%S")
        st.caption(f"✅ Last saved at {last_save_time_str}")
    else:
        st.caption("No changes saved yet.")

# --- NEW: Logic function to handle the periodic autosave ---
def handle_periodic_autosave():
    """Checks if it's time to perform a periodic, non-blocking autosave."""
    # Only try to save if there are actual changes
    if not st.session_state.get('unsaved_changes'):
        return

    time_since_last_save = time.time() - st.session_state.get('last_autosave_time', 0)
    print(f"Time since last autosave: {time_since_last_save} seconds")
    if time_since_last_save > AUTOSAVE_INTERVAL_SECONDS:
        autosave_success = handle_save_or_submit("draft")
        if autosave_success:
            # If the save succeeds, reset the timer and the change flag
            st.session_state.last_autosave_time = time.time()
            st.session_state.unsaved_changes = False
            # We don't need a toast here, the status indicator is enough
            st.rerun() # Rerun to update the "Last saved at" time



def render_sidebar():
    """Renders the sidebar with all its components."""
    with st.sidebar:
        st.header("👤 Your Details")
        st.write(f"**Name:** {st.session_state.get('user_name', 'N/A')}")
        st.write(f"**Team:** {st.session_state.get('user_team_name', 'N/A')}")
        st.divider()

        st.header("🗓️ Date Selection")
        if "selected_date" not in st.session_state:
            st.session_state.selected_date = date.today()
        st.date_input("Select a date in the submission week", key="selected_date")
        st.button("Select Last Thursday", use_container_width=True, on_click=set_last_thursday)
        st.divider()

        st.header("🔄 Load Previous Submission")
        date_to_load = st.date_input("Select a date from the week to load", date.today() - timedelta(days=7))
        week_to_load = date_to_load - timedelta(days=(date_to_load.weekday() - 3 + 7) % 7)
        st.caption(f"Will load data for week ending: {week_to_load.strftime('%Y-%m-%d')}")
        
        if st.button("Load Selected Week", use_container_width=True):
            user_email = st.session_state.get("user_email")
            if user_email:
                with st.spinner("Loading data..."):
                    loaded_data = asyncio.run(load_week_submission(user_email, week_to_load.isoformat()))

                    if loaded_data.get("tasks"):
                        st.session_state.daily_toggle = loaded_data["tasks"][0].get("daily_mode", False)
                        tasks_df = pd.DataFrame(loaded_data.get('tasks', []))
                        tasks_df.rename(columns={"Task Description": "Description"}, inplace=True)
                        st.session_state.tasks_df = tasks_df
                    else:
                        st.session_state.daily_toggle = False
                    
                    if loaded_data.get("meetings"):
                        meetings_df = pd.DataFrame(loaded_data.get('meetings', []))
                        meetings_df.rename(columns={"Meeting Description": "Description"}, inplace=True)
                        st.session_state.meetings_df = meetings_df

                    rename_map = {'sun': 'Sun', 'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 'thu': 'Thu'}
                    if not st.session_state.tasks_df.empty:
                        st.session_state.tasks_df.rename(columns=rename_map, inplace=True)
                    
                    st.success("Data loaded!")

        st.header("⚙️ Actions")
        if st.button("🧹 Clear All Entries"):
            initialize_or_clear_session_state()
            st.success("All entries cleared!")
            st.rerun()


def render_data_editors():
    """Renders task and meeting editors with support for daily/weekly entry."""

    col1, col2, col3 = st.columns([3, 1, 1]) # Add an extra column for the status
    with col1:
        st.header("Log Your Weekly Activities")
    with col2:
        # The manual save button remains
        if st.button("💾 Save as Draft", use_container_width=True):
            handle_save_or_submit("draft")
    with col3:
        # Render the new status indicator
        render_save_status()

    # Toggle for daily mode
    st.toggle("Enter hours per day", key="daily_toggle")
    daily_toggle = st.session_state.get("daily_toggle", False)

    # --- Tasks ---
    st.subheader("Tasks")

    base_df = st.session_state.get("tasks_df", pd.DataFrame())
    tasks_df = prepare_tasks_df(base_df, daily_toggle)
    column_order, column_conf = get_task_column_config(daily_toggle)

    st.data_editor(
        tasks_df,
        column_config=column_conf,
        column_order=column_order,
        hide_index=True,
        use_container_width=True,
        key="tasks_editor",
        num_rows="dynamic",
        on_change=update_tasks_from_editor,
    )

    # --- Meetings (basic setup for now) ---
    st.subheader("Meetings")

    if "meetings_df" not in st.session_state:
        st.session_state.meetings_df = pd.DataFrame(columns=[
            "Description", "Group Activity", "Function Activity", "Total Weekly Hours", "Notes"
        ])

    st.data_editor(
        st.session_state.meetings_df,
        column_config={
            "Description": column_config.TextColumn("Description", required=False),
            "Group Activity": column_config.SelectboxColumn("Group Activity", options=st.session_state.group_activity_options),
            "Function Activity": column_config.SelectboxColumn("Function Activity", options=st.session_state.function_activity_options),
            "Notes": column_config.TextColumn("Notes"),
            "Total Weekly Hours": column_config.NumberColumn("Total Weekly Hours", min_value=0.0, step=0.5),
        },
        column_order=[
            "Description", "Group Activity", "Function Activity", "Total Weekly Hours", "Notes"
        ],
        hide_index=True,
        use_container_width=True,
        key="meetings_editor",
        num_rows="dynamic",
        on_change=update_meetings_from_editor
    )



def render_live_summary():
    """Calculates and renders the live summary charts."""
    st.header("📊 Live Summary")
    tasks_df = st.session_state.tasks_df.copy().dropna(how='all', subset=['Group Activity'])
    meetings_df = st.session_state.meetings_df.copy().dropna(how='all', subset=['Group Activity'])
    
    tasks_df['Weekly Hours'] = pd.to_numeric(tasks_df['Total Weekly Hours'], errors='coerce').fillna(0)
    meetings_df['Hours'] = pd.to_numeric(meetings_df['Total Weekly Hours'], errors='coerce').fillna(0)
    
    tasks_df = tasks_df[tasks_df['Weekly Hours'] > 0]
    meetings_df = meetings_df[meetings_df['Hours'] > 0]
    
    total_hours = tasks_df['Weekly Hours'].sum() + meetings_df['Hours'].sum()

    combined_df = pd.concat([
        tasks_df[['Function Activity', 'Group Activity', 'Weekly Hours']].rename(columns={'Weekly Hours': 'Hours'}),
        meetings_df[['Function Activity', 'Group Activity', 'Total Weekly Hours']].rename(columns={'Total Weekly Hours': 'Hours'})
    ], ignore_index=True)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Total Hours", f"{total_hours:.1f}")
    metric2.metric("Meeting Hours", f"{meetings_df['Hours'].sum():.1f}")
    metric3.metric("# Tasks/Meetings", str(len(tasks_df) + len(meetings_df)))
    if not combined_df.empty:
        metric4.metric("# Categories", str(combined_df['Function Activity'].nunique()))
    else:
        metric4.metric("# Categories", "0")
    st.markdown("---")

    if not combined_df.empty:
        func_activity_hrs = combined_df.groupby('Function Activity')['Hours'].sum()
        group_activity_hrs = combined_df.groupby('Group Activity')['Hours'].sum()

        col1, col2 = st.columns(2)
        with col1:
            st.header("Function Activities")
            fig_pie_func = go.Figure(data=[go.Pie(labels=func_activity_hrs.index, values=func_activity_hrs.values, hole=.4)])
            fig_pie_func.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie_func, use_container_width=True)
        with col2:
            st.header("Group Activities")
            fig_pie_group = go.Figure(data=[go.Pie(labels=group_activity_hrs.index, values=group_activity_hrs.values, hole=.4)])
            fig_pie_group.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie_group, use_container_width=True)

    else:
        st.info("Enter some hours above to see a live summary dashboard.")
    
    st.divider()

# --- Main Page Rendering Function ---

def get_submission_page():
    """The main entry point for rendering the complete submission page."""
    st.set_page_config(layout="wide", page_title="Submit Timesheet")

    if "step" not in st.session_state:
        st.session_state.step = None
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "submit_pressed" not in st.session_state:
        st.session_state.submit_pressed = False
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    initialize_state()
    handle_periodic_autosave()  # Check for periodic autosave
    render_sidebar()


    user_name = st.session_state.get('user_name', 'User')
    week_ending_date = st.session_state.selected_date - timedelta(days=(st.session_state.selected_date.weekday() - 3 + 7) % 7)

    st.title(f"Timesheet for {user_name} 📝")
    st.info(f"You are submitting for the week ending on Thursday, **{week_ending_date.strftime('%Y-%m-%d')}**")
    st.markdown("---")

    user_email = st.session_state.get("user_email")
    existing_entry = asyncio.run(check_existing_submission(user_email, week_ending_date))

    if existing_entry:
        st.warning("⚠️ A submission for this week already exists. Submitting again will **overwrite** the previous one.")

    render_data_editors()
    st.markdown("---")
    render_live_summary()
    st.markdown("---")

    # Submit button triggers confirmation dialogs
    if st.button("Submit Timesheet", type="primary", use_container_width=True):
        st.session_state.submit_pressed = True
        st.session_state.step = "overwrite" if existing_entry else "final"
        st.rerun()

    # Dialog triggers
    if st.session_state.step == "overwrite":
        confirm_overwrite_dialog()
    elif st.session_state.step == "final":
        confirm_final_dialog()

    # Final submission (after dialog confirms)
    if st.session_state.submitted:
        st.session_state.submitted = False
        handle_save_or_submit("submitted")