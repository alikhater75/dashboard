# app.py

import streamlit as st
from src.edit_projects import show_edit_projects_page
from src.edit_team_members import show_edit_team_members_page
from src.edit_function_activities import show_edit_function_activities_page

def admin_main():
    """
    The main function for the Admin Dashboard.
    It controls navigation between different admin pages.
    """
    st.title("Sensor Tech Admin Dashboard")

    st.sidebar.title("Admin Menu")
    page_options = {
        "Edit Projects & Activities": show_edit_projects_page,
        "Edit Team Members": show_edit_team_members_page,
        "Edit Function Activities": show_edit_function_activities_page,
        # We will add Reports and Static Views here later
    }
    
    page_selection = st.sidebar.radio("Actions", list(page_options.keys()))
    
    # Render the selected page
    page_to_render = page_options[page_selection]
    page_to_render()