# backend/etl_config.py

import os

# --- Project Root ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- Source Data Files ---
# Path to the main file with Time Entries and Team Members
MAIN_EXCEL_FILE_PATH = os.path.join(PROJECT_ROOT, 'Excel data', 'Sensor Technology Workload Report.xlsx')

# Path to the project list file
PROJECTS_EXCEL_FILE_PATH = os.path.join(PROJECT_ROOT, 'Excel data', 'Project List - ST Timesheet - Import.xlsx')


# --- Sheet Names within the Excel Files ---
PROJECTS_SHEET_NAME = 'Sheet1'                # Use 'Sheet1' from the new project file
MEMBERS_SHEET_NAME = 'Team Members'           # From the main file
FORM_RESPONSES_SHEET_NAME = 'Form Responses 1'  # From the main file


