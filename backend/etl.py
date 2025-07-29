# backend/etl.py
import pandas as pd
from sqlalchemy.orm import joinedload
from datetime import datetime
import uuid
import etl_config as config
from database import Project, TeamMember, TimeEntry, Portfolio, Team, GroupActivity, FunctionActivity, Task
from dotenv import load_dotenv
from etl_database_utils import get_session, create_database_and_tables

load_dotenv()

def populate_portfolios_and_projects(session):
    """
    Populates Portfolios, Projects, and GroupActivities from the project Excel file.
    This function is now designed to handle the new relational structure.
    """
    print("\n--- Populating Portfolios, Projects, and Group Activities ---")
    try:
        print(f"--> Reading from: {config.PROJECTS_EXCEL_FILE_PATH}")
        df = pd.read_excel(config.PROJECTS_EXCEL_FILE_PATH, sheet_name=config.PROJECTS_SHEET_NAME)

        # In-memory maps to avoid duplicate entries and redundant DB queries
        portfolios_map = {}
        projects_map = {}

        # 1. Populate Portfolios
        unique_portfolios = df['Portfolio (Only used in visuallization)'].dropna().unique()
        for name in unique_portfolios:
            if not session.query(Portfolio).filter_by(name=name).first():
                new_portfolio = Portfolio(name=name)
                session.add(new_portfolio)
        session.commit()
        # Load all portfolios into the map
        for p in session.query(Portfolio).all():
            portfolios_map[p.name] = p.id
        print(f"--> Synced {len(portfolios_map)} portfolios.")

        # 2. Populate Projects
        for index, row in df.iterrows():
            project_name = str(row['Project (Only used in visuallization)']).strip()
            if not project_name or project_name.lower() == 'nan':
                continue
            
            if not session.query(Project).filter_by(project_name=project_name).first():
                portfolio_name = row.get('Portfolio (Only used in visuallization)')
                portfolio_id = portfolios_map.get(portfolio_name)
                
                new_project = Project(
                    project_name=project_name,
                    status='Active',
                    portfolio_id=portfolio_id
                )
                session.add(new_project)
        session.commit()
        # Load all projects into the map
        for p in session.query(Project).all():
            projects_map[p.project_name] = p.id
        print(f"--> Synced {len(projects_map)} projects.")

        # 3. Populate Group Activities
        group_activities_count = 0
        for index, row in df.iterrows():
            project_name = str(row['Project (Only used in visuallization)']).strip()
            group_activity_name = str(row.get('Group Activity')).strip()
            
            if not all([project_name, group_activity_name]) or group_activity_name.lower() == 'nan':
                continue

            project_id = projects_map.get(project_name)
            if project_id:
                # Check if this group activity already exists for this project
                exists = session.query(GroupActivity).filter_by(name=group_activity_name, project_id=project_id).first()
                if not exists:
                    new_group_activity = GroupActivity(
                        name=group_activity_name,
                        project_id=project_id
                    )
                    session.add(new_group_activity)
                    group_activities_count += 1
        session.commit()
        print(f"--> Synced {group_activities_count} new group activities.")

    except Exception as e:
        print(f"--> ERROR: An error occurred: {e}")
        session.rollback()

def populate_teams_and_members(session):
    """
    Populates Teams and TeamMembers, correctly handling the manager relationship.
    """
    print("\n--- Populating Teams and Team Members ---")
    try:
        print(f"--> Reading from: {config.MAIN_EXCEL_FILE_PATH}")
        df = pd.read_excel(config.MAIN_EXCEL_FILE_PATH, sheet_name=config.MEMBERS_SHEET_NAME)

        teams_map = {}
        manager_emails = set(df['Manager Email'].dropna().unique()) # <-- ADDED

        # 1. Populate Teams
        unique_teams = df['Team'].dropna().unique()
        for name in unique_teams:
            if not session.query(Team).filter_by(name=name).first():
                new_team = Team(name=name)
                session.add(new_team)
        session.commit()
        for t in session.query(Team).all():
            teams_map[t.name] = t.id
        print(f"--> Synced {len(teams_map)} teams.")

        # 2. Populate Team Members (Pass 1: Create members)
        new_members_count = 0
        for index, row in df.iterrows():
            email = str(row['Email']).strip()
            if not session.query(TeamMember).filter_by(email=email).first():
                team_name = row.get('Team')
                team_id = teams_map.get(team_name)
                
                role = 'manager' if email in manager_emails else 'user' # <-- ADDED

                member = TeamMember(
                    email=email,
                    full_name=str(row.get('Name')).strip(),
                    status='Active',
                    team_id=team_id,
                    role=role # <-- ADDED
                )
                session.add(member)
                new_members_count += 1
        session.commit()
        print(f"--> Added {new_members_count} new team members.")
        
        # 3. Update Managers (Pass 2: Set manager_id)
        updated_managers_count = 0
        all_members = session.query(TeamMember).all()
        member_email_map = {m.email: m.id for m in all_members}
        
        for index, row in df.iterrows():
            email = str(row['Email']).strip()
            manager_email = row.get('Manager Email')
            
            if pd.notna(manager_email):
                member_id = member_email_map.get(email)
                manager_id = member_email_map.get(manager_email.strip())
                
                if member_id and manager_id:
                    member_to_update = session.query(TeamMember).get(member_id)
                    if member_to_update and not member_to_update.manager_id:
                        member_to_update.manager_id = manager_id
                        updated_managers_count += 1
        session.commit()
        print(f"--> Updated manager relationships for {updated_managers_count} members.")

    except Exception as e:
        print(f"--> ERROR: An error occurred: {e}")
        session.rollback()

def populate_function_activities(session):
    """Populates the function_activities table from the project Excel file."""
    print("\n--- Populating Function Activities ---")
    try:
        df = pd.read_excel(config.PROJECTS_EXCEL_FILE_PATH, sheet_name=config.PROJECTS_SHEET_NAME)
        
        # Get team map from DB
        teams_map = {t.name: t.id for t in session.query(Team).all()}
        
        main_cols = ['Group Activity', 'Project (Only used in visuallization)', 'Portfolio (Only used in visuallization)']
        team_cols = [col for col in df.columns if col not in main_cols and 'Unnamed' not in col]
        
        new_activities_count = 0
        for team_name in team_cols:
            team_id = teams_map.get(team_name.strip())
            if not team_id: continue
            
            activities = df[team_name].dropna().unique()
            for activity_name in activities:
                # Check if this activity already exists for this team
                exists = session.query(FunctionActivity).filter_by(name=str(activity_name).strip(), team_id=team_id).first()
                if not exists:
                    new_activity = FunctionActivity(
                        name=str(activity_name).strip(),
                        team_id=team_id # Use the team_id foreign key
                    )
                    session.add(new_activity)
                    new_activities_count +=1
        
        session.commit()
        print(f"--> Synced {new_activities_count} new function activities.")
    except Exception as e:
        print(f"--> ERROR: An error occurred: {e}")
        session.rollback()

def _load_reference_maps(session):
    print("--> Loading reference data into memory...")
    members_map = {m.email.strip(): m.id for m in session.query(TeamMember).all()}
    projects_map = {p.project_name: p.id for p in session.query(Project).all()}
    group_activities_map = {(ga.project_id, ga.name): ga.id for ga in session.query(GroupActivity).all()}
    func_activities_map = {(fa.team_id, fa.name): fa.id for fa in session.query(FunctionActivity).all()}
    teams_name_to_id_map = {t.name.strip(): t.id for t in session.query(Team).all()}
    return members_map, projects_map, group_activities_map, func_activities_map, teams_name_to_id_map


# New helper function to process a single Excel row and create Task/TimeEntry objects
def _process_single_timesheet_row(session, row, submission_id, maps):
    members_map, projects_map, group_activities_map, func_activities_map, teams_name_to_id_map = maps

    # --- Find or Create Inactive TeamMember for orphaned records ---
    email_from_row = str(row['email']).strip()
    owner_id = members_map.get(email_from_row)
    if not owner_id and email_from_row:
        print(f"--> Found orphaned email: {email_from_row}. Creating inactive member.")
        new_member = TeamMember(
            email=email_from_row,
            full_name=f"Orphaned User ({email_from_row})",
            status='Inactive'
        )
        session.add(new_member)
        session.flush() # Flush to get the ID and update map for subsequent lookups
        owner_id = new_member.id
        members_map[email_from_row] = owner_id # Update map for subsequent rows in the same ETL run

    # --- Find or Create Inactive Project for orphaned records ---
    project_name_from_row = str(row.get('Project')).strip()
    if not project_name_from_row or project_name_from_row.lower() == 'nan':
        return None, None # Skip this row if no valid project name
    
    project_id = projects_map.get(project_name_from_row)
    if not project_id and project_name_from_row:
        print(f"--> Found orphaned project: {project_name_from_row}. Creating inactive project.")
        new_project = Project(
            project_name=project_name_from_row,
            status='Inactive',
            portfolio_id=None # No way to know the portfolio, so leave it null
        )
        session.add(new_project)
        session.flush() # Flush to get the ID and update map
        project_id = new_project.id
        projects_map[project_name_from_row] = project_id # Update map

    # If after all checks, we still don't have an owner, we must skip.
    if not owner_id:
        return None, None

    group_activity_id = group_activities_map.get((project_id, str(row.get('Group Activity')).strip()))

    team_name_from_row = str(row.get('Team')).strip()
    current_team_id = teams_name_to_id_map.get(team_name_from_row) 

    function_activity_id = None
    if current_team_id is not None: 
        function_activity_id = func_activities_map.get((current_team_id, str(row.get('Function Activity')).strip())) 
    else:
        print(f"Warning: Team '{team_name_from_row}' not found for function activity lookup. Function Activity will be NULL for this task.")

    status_val = row.get('Current Status')
    if pd.isna(status_val):
        status_val = 'Done' 

    task = Task(
        type=str(row.get('Task')).strip(),
        description=None,
        status=status_val, 
        owner_id=owner_id,
        group_activity_id=group_activity_id,
        function_activity_id=function_activity_id 
    )
    
    entry = TimeEntry(
        hours=row.get('Hours'),
        notes=row.get('Notes'),
        date_of_work=row.get('Date'),
        submission_id=submission_id,
        team_member_id=owner_id,
        task=task,
        timestamp=row.get('Timestamp'),

    )

    return task, entry


# Refactored sync_tasks_and_time_entries
def sync_tasks_and_time_entries(session):
    """
    Reads the main form responses, creates central Task records, and then creates
    lean TimeEntry records linked to those tasks.
    Refactored for better readability and maintainability.
    """
    print("\n--- Syncing Tasks and Time Entries ---")
    try:
        print(f"--> Reading time entries from: {config.MAIN_EXCEL_FILE_PATH}")
        df = pd.read_excel(config.MAIN_EXCEL_FILE_PATH, sheet_name=config.FORM_RESPONSES_SHEET_NAME)
        
        # Clean column names and preprocess dates
        df.columns = df.columns.str.strip()
        df.rename(columns={'Email Address': 'email'}, inplace=True)
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df.dropna(subset=['Date'], inplace=True)
        
        # Calculate the Thursday of the current week (Sunday-Thursday week) for grouping
        # pandas dayofweek: Monday=0, Sunday=6.
        # To find the most recent Sunday: subtract (dayofweek + 1) % 7 days
        # Then add 4 days to get Thursday
        df['week_ending_thursday'] = (
            df['Date'] - pd.to_timedelta((df['Date'].dt.dayofweek + 1) % 7, unit='D')
        ) + pd.to_timedelta(4, unit='D')

        # Load all necessary reference data into memory maps
        members_map, projects_map, group_activities_map, func_activities_map, teams_name_to_id_map = _load_reference_maps(session)
        all_maps = (members_map, projects_map, group_activities_map, func_activities_map, teams_name_to_id_map)

        new_tasks = []
        new_entries = []
        
        print(f"\n--> Preparing {len(df)} records for processing...")
        
        # Group by email and the consistent week-ending Thursday date
        for _, group in df.groupby(['email', 'week_ending_thursday']):
            submission_id = str(uuid.uuid4())
            
            for index, row in group.iterrows():
                task, entry = _process_single_timesheet_row(session, row, submission_id, all_maps)
                if task and entry:
                    new_tasks.append(task)
                    new_entries.append(entry)

        if new_tasks:
            print(f"--> Inserting {len(new_tasks)} new Task records...")
            session.add_all(new_tasks)
            session.commit()
            
            print(f"--> Inserting {len(new_entries)} new TimeEntry records...")
            session.add_all(new_entries)
            session.commit()

        print(f"--> Success: Database is now up to date.")

    except Exception as e:
        print(f"--> ERROR: An error occurred while syncing: {e}")
        session.rollback()



def run_full_etl_pipeline():
    """
    Runs the entire ETL process from start to finish in the correct order.
    Returns a tuple: (success_boolean, message_string)
    """
    session = get_session()
    try:
        print("--- Starting Full Data Sync ---")
        
        # Ensure the database and tables exist
        create_database_and_tables()
        
        # Populate tables in an order that respects foreign key constraints
        populate_portfolios_and_projects(session)
        populate_teams_and_members(session)
        populate_function_activities(session)
        
        # Finally, sync the main data which depends on all previous tables
        sync_tasks_and_time_entries(session)
        
        print("\n--- ETL Sync Complete ---")
        return (True, "✅ Data synchronization complete! The database is now up to date.")
    
    except Exception as e:
        error_message = f"An error occurred during the ETL process: {e}"
        print(f"ERROR: {error_message}")
        session.rollback()
        return (False, f"❌ {error_message}")
    finally:
        session.close()

if __name__ == "__main__":
    run_full_etl_pipeline()