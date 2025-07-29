# submit_timesheet.py

import streamlit as st
from dotenv import load_dotenv
import asyncio

from src.login_page import show_login_page, handle_login_redirect
from src.submission import get_submission_page
from dashboard_app import admin_main # Import the admin dashboard main function

# Load environment variables
load_dotenv()

"""
Main application flow.
- Handles login
- Switches between user submission view and admin dashboard view.
"""
st.set_page_config(layout="wide")

# Initialize view state if it doesn't exist
if "view" not in st.session_state:
    st.session_state.view = "submission"

# Handle Google OAuth callback
handle_login_redirect()

if not st.session_state.get("logged_in"):
    show_login_page()
else:
    # If the user is an admin, show the view-toggle button
    if st.session_state.get("user_role") == "admin":
        if st.session_state.view == "submission":
            if st.sidebar.button("Switch to Admin View"):
                st.session_state.view = "admin"
                st.rerun()
        else:
            if st.sidebar.button("Switch to Submission View"):
                st.session_state.view = "submission"
                st.rerun()

    # Render the appropriate view based on session state
    if st.session_state.view == "submission":
        get_submission_page()
    else:
        admin_main() # Run the admin dashboard
