# backend/services.py

from datetime import datetime, timedelta
import uuid
from sqlalchemy import select, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from database import TimeEntry, TeamMember, Task, GroupActivity, FunctionActivity
from schemas import SubmissionRequest
from typing import List, Dict, Any
from datetime import date

# ----------------------
# Database Helper Methods
# ----------------------

async def get_user_by_email(email: str, db: AsyncSession):
    result = await db.execute(select(TeamMember).where(TeamMember.email == email))
    user = result.scalars().first()
    if not user:
        raise ValueError(f"No user found for email: {email}")
    return user

async def get_group_activity_id(name: str, db: AsyncSession) -> int:
    """Helper function to get the ID of a GroupActivity by its name."""
    result = await db.execute(select(GroupActivity).where(GroupActivity.name == name))
    activity = result.scalars().first()
    if not activity:
        raise ValueError(f"Group Activity '{name}' not found.")
    return activity.id

async def get_function_activity_id(name: str, db: AsyncSession) -> int:
    """Helper function to get the ID of a FunctionActivity by its name."""
    result = await db.execute(select(FunctionActivity).where(FunctionActivity.name == name))
    activity = result.scalars().first()
    if not activity:
        raise ValueError(f"Function Activity '{name}' not found.")
    return activity.id

async def _create_task(task_type: str, description: str, status: str, group_activity_id: int, function_activity_id: int, db: AsyncSession) -> int: # <--- MODIFIED
    """
    Private helper function to create a new task in the database.
    This encapsulates the task creation logic.
    """
    try:
        new_task = Task(
            type=task_type,             # <--- MODIFIED
            description=description,    # <--- MODIFIED
            status=status,
            group_activity_id=group_activity_id,
            function_activity_id=function_activity_id
        )
        db.add(new_task)
        await db.flush()
        print(f"✅ Created new task: '{description}' of type '{task_type}'") # <--- MODIFIED
        return new_task.id

    except ValueError as e:
        raise e

async def get_task_id(task_type: str, description: str, group_activity_name: str, function_activity_name: str, status: str, db: AsyncSession): # <--- MODIFIED
    """
    Finds a task by its components, or creates it if it doesn't exist.
    """
    group_activity_id = await get_group_activity_id(group_activity_name, db)
    function_activity_id = await get_function_activity_id(function_activity_name, db)

    query = select(Task).where(
        Task.type == task_type,                         # <--- MODIFIED
        Task.description == description,              # <--- MODIFIED
        Task.group_activity_id == group_activity_id,
        Task.function_activity_id == function_activity_id,
        Task.status == status
    )
    result = await db.execute(query)

    task = result.scalars().first()
    if task:
        return task.id
    else:
        # If not found, call the dedicated creation function
        return await _create_task(task_type, description, status, group_activity_id, function_activity_id, db) # <--- MODIFIED




async def delete_existing_entries(email: str, week_date, db: AsyncSession):
    result = await db.execute(select(TeamMember).where(TeamMember.email == email))
    user = result.scalars().first()
    if not user:
        return
    await db.execute(
        delete(TimeEntry).where(
            TimeEntry.team_member_id == user.id,
            func.date(TimeEntry.date_of_work) >= week_date - timedelta(days=6),
            func.date(TimeEntry.date_of_work) <= week_date
        )
    )


# ----------------------
# Entry Creation Logic
# ----------------------

def create_time_entry(team_member_id, task_id, date_of_work, hours, notes, submission_id, status: str, daily_mode: bool, daily_hours: dict, timestamp: datetime): # <--- MODIFIED

    print("daily_hours:", daily_hours)
    return TimeEntry(
        submission_id=submission_id,
        hours=hours,
        notes=notes,
        date_of_work=date_of_work,
        task_id=task_id,
        team_member_id=team_member_id,
        status=status,
        daily_mode=daily_mode, # Save the mode
        # Save the daily hours, defaulting to 0 if not provided
        sun=daily_hours.get("sun", 0.0),
        mon=daily_hours.get("mon", 0.0),
        tue=daily_hours.get("tue", 0.0),
        wed=daily_hours.get("wed", 0.0),
        thu=daily_hours.get("thu", 0.0),
        timestamp=timestamp
    )


async def build_task_entries(data: SubmissionRequest, user, db: AsyncSession, submission_id: str, status: str, timestamp: datetime): # <--- MODIFIED

    entries = []
    for task in data.tasks:
        try:
            task_id = await get_task_id("Work", task.description, task.group_activity, task.function_activity, task.status, db)

            daily_hours = {}
            total_hours = 0
            if data.daily_mode:
                daily_hours = {"sun": task.sun, "mon": task.mon, "tue": task.tue, "wed": task.wed, "thu": task.thu}
                total_hours = sum(daily_hours.values())
            else:
                total_hours = task.weekly_hours

            if total_hours > 0:
                entries.append(create_time_entry(user.id, task_id, data.week_date, total_hours, task.notes, submission_id, status, data.daily_mode, daily_hours, timestamp)) 

        except ValueError as e:
            print(f"Skipping task due to error: {e}")
            continue
    return entries


async def build_meeting_entries(data: SubmissionRequest, user, db: AsyncSession, submission_id: str, status: str, timestamp: datetime): # <--- MODIFIED

    entries = []
    for meeting in data.meetings:
        if meeting.hours <= 0:
            continue
        try:
            task_id = await get_task_id("Meeting", meeting.description, meeting.group_activity, meeting.function_activity, "Done", db) # <--- MODIFIED

        except ValueError:
            continue
        entries.append(create_time_entry(
            team_member_id=user.id,
            task_id=task_id,
            date_of_work=data.week_date,
            hours=meeting.hours,
            notes=meeting.notes,
            submission_id=submission_id,
            status=status,
            daily_mode=False,     
            daily_hours={},
            timestamp=timestamp         
        ))
    return entries


# ----------------------
# Orchestrator
# ----------------------

async def submit_timesheet(data: SubmissionRequest, db: AsyncSession):
    timestamp = datetime.now()
    submission_id = str(uuid.uuid4())

    user = await get_user_by_email(data.user_email, db)

    if data.overwrite:
        await delete_existing_entries(data.user_email, data.week_date, db)

    submission_status = data.status.value 

    task_entries = await build_task_entries(data, user, db, submission_id, submission_status, timestamp)       
    meeting_entries = await build_meeting_entries(data, user, db, submission_id, submission_status, timestamp) 

    if not task_entries and not meeting_entries:
        raise ValueError("No valid time entries to submit.")

    db.add_all(task_entries + meeting_entries)
    await db.commit()

    return {"success": True, "message": "Timesheet submitted successfully."}


async def _get_entries_for_week(
    user_email: str,
    week_date: date,
    statuses: List[str], # <-- The parameter is now used correctly
    session: AsyncSession
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Private helper to retrieve time entries for a user and week, filtered by specific statuses.
    This contains the core data fetching and shaping logic to avoid duplication.
    """
    try:
        # 1. Get the TeamMember object for the given email
        user = await get_user_by_email(user_email, session)

        # 2. Determine the date range for the week.
        # The `week_date` parameter is likely the end of the work week (e.g., Thursday).
        # Assuming a 5-day work week (Sun-Thu) as per build_task_entries daily_mode loop.
        week_start_date = week_date - timedelta(days=4)  # Assuming week_date is Thursday, this makes week_start_date Sunday
        week_end_date = week_date  # Keep week_date as the end for the query range

        # 3. Query TimeEntry records for the user within the specified week range.
        # Eagerly load related Task, GroupActivity, and FunctionActivity objects
        # to avoid N+1 queries when accessing their attributes later.
        query = select(TimeEntry).where(
            TimeEntry.team_member_id == user.id,  # Corrected: use team_member_id instead of non-existent TimeEntry.email
            func.date(TimeEntry.date_of_work) >= week_start_date,
            func.date(TimeEntry.date_of_work) <= week_end_date,
            TimeEntry.status.in_(statuses)
        ).options(
            joinedload(TimeEntry.task).joinedload(Task.group_activity),
            joinedload(TimeEntry.task).joinedload(Task.function_activity)
        )

        result = await session.execute(query)
        entries = result.scalars().all()

        # Prepare dictionaries to group entries by unique task/meeting and day
        # This will allow reconstruction of the DataFrame format expected by the frontend.
        grouped_tasks = {}
        grouped_meetings = {}

        for entry in entries:
            # Access related data via the 'task' relationship. Handle cases where task might be None.
            if not entry.task:
                continue

            task_obj = entry.task
            group_activity_obj = task_obj.group_activity
            function_activity_obj = task_obj.function_activity

            # Extract names, defaulting to "N/A" if relationship is missing or name is empty
            group_activity_name = group_activity_obj.name if group_activity_obj and group_activity_obj.name else "N/A"
            function_activity_name = function_activity_obj.name if function_activity_obj and function_activity_obj.name else "N/A"
            task_status = task_obj.status if task_obj.status else "N/A"

            task_description = task_obj.description if task_obj.description else "N/A" # <--- MODIFIED
            task_type = task_obj.type if task_obj.type else "N/A" 

            # Determine if the entry is for a 'meeting' or a regular 'task'
            # based on the Task.name, as implied by build_meeting_entries.
            is_meeting = (task_type.lower() == 'meeting') # <--- MODIFIED

            # Create a unique key for grouping. For tasks, include status. For meetings, use descriptive name.
            if is_meeting:
                key = (group_activity_name, function_activity_name, task_description, entry.notes) # <--- MODIFIED
                target_dict = grouped_meetings
            else:
                key = (group_activity_name, function_activity_name, task_status, task_description, entry.notes) # <--- MODIFIED
                target_dict = grouped_tasks

            if key not in target_dict:
                # Initialize the entry structure for this unique task/meeting
                new_entry_data = {
                    "Group Activity": group_activity_name,
                    "Function Activity": function_activity_name,
                    "Total Weekly Hours": 0.0,
                    "Notes": entry.notes,
                    "daily_mode": entry.daily_mode,
                    "sun": entry.sun,
                    "mon": entry.mon,
                    "tue": entry.tue,
                    "wed": entry.wed,
                    "thu": entry.thu,
                }
                if is_meeting:
                    new_entry_data["Meeting Description"] = task_description # <--- MODIFIED
                else:
                    new_entry_data["Task Description"] = task_description # <--- MODIFIED
                    new_entry_data["Status"] = task_status
                target_dict[key] = new_entry_data
            else:
                # Add hours to the correct day and update total weekly hours
                day_name = entry.date_of_work.strftime('%a').lower()  # 'sun', 'mon', 'tue', 'wed', 'thu' etc.
                if day_name in target_dict[key]:  # Check if the day column exists
                    target_dict[key][day_name] += entry.hours
            target_dict[key]["Total Weekly Hours"] += entry.hours

        # Convert grouped dictionaries to lists of dictionaries for the frontend DataFrames
        final_tasks_data = list(grouped_tasks.values())
        final_meetings_data = list(grouped_meetings.values())

        return {"tasks": final_tasks_data, "meetings": final_meetings_data}
    except Exception as e:
        print(f"Error fetching entries for week: {e}")
        return {"tasks": [], "meetings": []}

async def get_submission_for_week(user_email: str, week_date: date, session: AsyncSession):
    """
    Gets a user's FINAL timesheet (submitted or approved) to be used as a template.
    """
    return await _get_entries_for_week(user_email, week_date, ["submitted", "approved"], session)


# 3. The second public function. Its intent is to restore DRAFTS.
async def get_draft_submission_for_week(user_email: str, session: AsyncSession) -> Dict[str, Any]:
    """
    Finds the user's MOST RECENT draft submission and retrieves all entries
    for that corresponding week.
    """
    user = await get_user_by_email(user_email, session)

    # Step 1: Find the single most recent date from any of the user's draft entries.
    latest_draft_date_query = (
        select(TimeEntry.date_of_work)
        .where(TimeEntry.team_member_id == user.id, TimeEntry.status == 'draft')
        .order_by(desc(TimeEntry.date_of_work))
        .limit(1)
    )
    result = await session.execute(latest_draft_date_query)
    latest_date = result.scalar_one_or_none()

    # If no drafts exist for the user, return empty data.
    if not latest_date:
        return {"tasks": [], "meetings": [], "week_date": None}

    # Step 2: Calculate the week range based on that single latest date.
    week_ending_date = latest_date - timedelta(days=(latest_date.weekday() - 3 + 7) % 7)
    # Step 3: Use your existing logic to fetch all entries within that calculated week.
    # We pass the calculated dates to the original helper function.
    # Note: This assumes you have the _get_entries_for_week helper we discussed.
    # If not, the query logic would be placed here directly.
    submission_data = await _get_entries_for_week(user_email, week_ending_date, ["draft"], session)

    # Step 4: Add the week_date to the response so the frontend knows which date to set.
    submission_data["week_date"] = week_ending_date.strftime('%Y-%m-%d')
    return submission_data
