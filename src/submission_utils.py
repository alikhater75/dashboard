# src/submission_utils.py

import streamlit as st
import pandas as pd
import asyncio
from datetime import date, timedelta
# Import the new API client
from streamlit import column_config
import time
from .api_client import (

    load_week_submission,
    load_draft_submission,
    submit_timesheet,
)



def initialize_or_clear_session_state():
    """
    Creates or clears the DataFrames in the session state for the UI data editors.
    """
    if "clear" in st.session_state and st.session_state.clear:
        st.session_state.tasks_df = pd.DataFrame()
        st.session_state.meetings_df = pd.DataFrame()
        
    daily = st.session_state.get("daily_toggle", False)

    columns = [
        "Description", "Group Activity", "Function Activity", "Status",
        "Total Weekly Hours", "Notes"
    ]
    if daily:
        columns = columns[:4] + ["Sun", "Mon", "Tue", "Wed", "Thu"] + columns[4:]
    st.session_state.tasks_df = pd.DataFrame(columns=columns)

    st.session_state.meetings_df = pd.DataFrame(columns=[
        "Description", "Group Activity", "Function Activity",
        "Total Weekly Hours", "Notes"
    ])





def get_task_column_config(daily_toggle: bool) -> tuple[list[str], dict]:
    """Returns column order and editor configuration for the task table."""
    base_cols = ["Description", "Group Activity", "Function Activity", "Status"]
    day_cols = ["Sun", "Mon", "Tue", "Wed", "Thu"]
    end_cols = ["Total Weekly Hours", "Notes"]

    column_order = base_cols + (day_cols if daily_toggle else []) + end_cols

    column_conf = {
        "Description": column_config.TextColumn("Description", required=False),
        "Group Activity": column_config.SelectboxColumn("Group Activity", options=st.session_state.group_activity_options),
        "Function Activity": column_config.SelectboxColumn("Function Activity", options=st.session_state.function_activity_options),
        "Status": column_config.SelectboxColumn("Status", options=st.session_state.status_options),
        "Notes": column_config.TextColumn("Notes"),
        "Total Weekly Hours": column_config.NumberColumn("Total Weekly Hours", disabled=daily_toggle, default=0.0, min_value=0.0, step=0.5),
    }

    if daily_toggle:
        for day in day_cols:
            column_conf[day] = column_config.NumberColumn(day, min_value=0.0, step=0.5)

    return column_order, column_conf


def prepare_tasks_df(original_df: pd.DataFrame, daily_toggle: bool) -> pd.DataFrame:
    """
    Ensures the DataFrame has all the necessary columns for the data editor
    without destructively recalculating loaded data.
    """
    df = original_df.copy()
    
    # Define all columns the editor might need
    expected_cols = ["Description", "Group Activity", "Function Activity", "Status", "Total Weekly Hours", "Notes"]
    day_cols = ["Sun", "Mon", "Tue", "Wed", "Thu"]
    
    if daily_toggle:
        expected_cols.extend(day_cols)

    # For every column the editor expects, add it with a default value
    # ONLY if it doesn't already exist in the loaded DataFrame.
    for col in expected_cols:
        if col not in df.columns:
            # Use an empty string for text columns and 0.0 for numeric columns
            default_value = "" if col in ["Description", "Notes", "Group Activity", "Function Activity", "Status"] else 0.0
            df[col] = default_value

    return df

def apply_editor_changes(df_key, editor_key):
    """Applies changes from a data_editor to the corresponding session state DataFrame."""
    if editor_key not in st.session_state: return

    # Helper function to clean the value from the editor state
    def clean_value(val):
        # The editor returns a list for selectboxes, so we take the first item
        return val[0] if isinstance(val, list) and len(val) > 0 else val

    df_copy = st.session_state[df_key].copy()
    editor_state = st.session_state[editor_key]

    if editor_state.get("deleted_rows"):
        df_copy = df_copy.drop(index=editor_state["deleted_rows"])

    if editor_state.get("added_rows"):
        added_rows = editor_state["added_rows"]
        # FIX: Clean the data *before* creating the DataFrame from new rows
        for row in added_rows:
            if 'Group Activity' in row:
                row['Group Activity'] = clean_value(row['Group Activity'])
            if 'Function Activity' in row:
                row['Function Activity'] = clean_value(row['Function Activity'])
        df_copy = pd.concat([df_copy, pd.DataFrame(added_rows)], ignore_index=True)

    if editor_state.get("edited_rows"):
        for idx, changes in editor_state["edited_rows"].items():
            # FIX: Clean the data in the changes dictionary for edited rows
            if 'Group Activity' in changes:
                changes['Group Activity'] = clean_value(changes['Group Activity'])
            if 'Function Activity' in changes:
                changes['Function Activity'] = clean_value(changes['Function Activity'])

            if idx < len(df_copy):
                for col, val in changes.items():
                    df_copy.loc[idx, col] = val

    st.session_state[df_key] = df_copy.reset_index(drop=True)

def update_tasks_from_editor():
    """Callback to update task data and recalculate daily hours if needed."""

    apply_editor_changes("tasks_df", "tasks_editor")
    df = st.session_state.tasks_df

    if 'Group Activity' in df.columns:
        df['Group Activity'] = df['Group Activity'].apply(lambda x: x[0] if isinstance(x, list) and x else x)

    if st.session_state.get("daily_toggle", False):
        day_cols = ["Sun", "Mon", "Tue", "Wed", "Thu"]
        
        # FIX: Add the day columns if they don't exist when the toggle is switched on
        for col in day_cols:
            if col not in df.columns:
                df[col] = 0.0

        df[day_cols] = df[day_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        df["Total Weekly Hours"] = df[day_cols].sum(axis=1) 
    
    st.session_state.tasks_df = df
    st.session_state.unsaved_changes = True

def update_meetings_from_editor():
    """Callback to update meeting data."""

    apply_editor_changes("meetings_df", "meetings_editor")
    df = st.session_state.meetings_df

    # FIX: Clean the 'Group Activity' column to ensure it contains strings, not lists
    if 'Group Activity' in df.columns:
        df['Group Activity'] = df['Group Activity'].apply(lambda x: x[0] if isinstance(x, list) and x else x)
    st.session_state.meetings_df = df

    st.session_state.unsaved_changes = True

def reset_modal_state():
    """Resets session state variables related to modal control."""
    st.session_state.force_submit = False
    st.session_state.show_overwrite_modal = False
    st.session_state.show_final_modal = False
    st.session_state.show_simple_modal = False

async def check_existing_submission(user_email: str, week_date: date) -> bool:
    """Checks if a submission for the given week already exists using the API."""
    try:
        loaded_data = await load_week_submission(user_email, week_date.isoformat())
        # A submission exists if either tasks or meetings list is not empty
        return bool(loaded_data.get('tasks') or loaded_data.get('meetings'))
    except Exception as e:
        # Assuming an exception (e.g., 404 Not Found) means no submission exists
        return False
    

async def load_drafts(user_email: str):

    """
    Checks for and loads draft data for the current user and week into session_state.
    """
    user_email = st.session_state.get("user_email")
    if not user_email:
        raise ValueError("User email cannot be empty.")


    try:
        draft_data = await load_draft_submission(user_email)
        return draft_data
    except Exception:
        # If no drafts are found (404 error) or other issue, initialize empty dataframes
        initialize_or_clear_session_state()


# --- NEW: Moved from submission.py ---
def clean_empty_rows(df):
    """Remove rows where 'Total Weekly Hours' is missing or zero."""
    if "Total Weekly Hours" in df.columns:
        df = df.copy()
        df["Total Weekly Hours"] = pd.to_numeric(df["Total Weekly Hours"], errors="coerce")
        return df[df["Total Weekly Hours"].fillna(0) > 0].reset_index(drop=True)
    return df

def is_valid_entry(df: pd.DataFrame, check_status: bool = False) -> pd.Series:
    if df.empty:
        return False
    checks = (
        df["Group Activity"].astype(str).str.strip().ne("") &
        df["Function Activity"].astype(str).str.strip().ne("") &
        df["Total Weekly Hours"].fillna(0) > 0
    )

    if check_status:
        checks &= df["Status"].astype(str).str.strip().ne("")

    return checks

# --- NEW: Moved from submission.py ---
def handle_save_or_submit(status: str):
    """
    Gathers data, cleans it for JSON and Pydantic compatibility, and sends it to the backend.
    """ 
    user_email = st.session_state.get("user_email")
    user_name = st.session_state.get("user_name")
    user_team = st.session_state.get("user_team_name")
    week_ending_date = st.session_state.selected_date - timedelta(days=(st.session_state.selected_date.weekday() - 3 + 7) % 7)

    tasks_df = st.session_state.tasks_df.copy()
    meetings_df = st.session_state.meetings_df.copy()

    if not (is_valid_entry(tasks_df, check_status=True) | is_valid_entry(meetings_df)).all():
        return True
    
    tasks_df.rename(columns={"Description": "Task Description"}, inplace=True)
    meetings_df.rename(columns={"Description": "Meeting Description"}, inplace=True)
   
    # --- START OF FIX ---
    # Rename the capitalized columns from the UI ('Sun') to lowercase ('sun') for the API payload.
    rename_map = {'Sun': 'sun', 'Mon': 'mon', 'Tue': 'tue', 'Wed': 'wed', 'Thu': 'thu'}
    if not tasks_df.empty:
        tasks_df.rename(columns=rename_map, inplace=True)

    # Clean NaN and None values as before
    string_columns = ["Task Description", "Meeting Description", "Notes", "Group Activity", "Function Activity", "Status"]
    for col in string_columns:
        if col in tasks_df.columns:
            tasks_df[col] = tasks_df[col].fillna("")
        if col in meetings_df.columns:
            meetings_df[col] = meetings_df[col].fillna("")

    # Convert to dictionary using the cleaned and correctly named data
    tasks = clean_empty_rows(tasks_df).to_dict("records")
    meetings = clean_empty_rows(meetings_df).to_dict("records")
    # --- END OF FIX ---

    payload = {
        "user_email": user_email,
        "user_name": user_name,
        "user_team": user_team,
        "week_date": week_ending_date.isoformat(),
        "daily_mode": st.session_state.daily_toggle,
        "overwrite": True,
        "tasks": tasks,
        "meetings": meetings,
        "status": status,
    }

    with st.spinner(f"Saving as {status}..."):
        try:
            result = asyncio.run(submit_timesheet(payload))
            if status == "draft":
                success_message = "Draft saved successfully!"
            else:
                success_message = "Timesheet submitted successfully!"
            st.toast(success_message, icon="✅")

            return True
        except Exception as e:
            st.error(f"❌ Save failed: {str(e)}")
