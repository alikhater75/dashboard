# backend/src/api/data_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import schemas
import services
from database import get_session
# from .auth_router import get_current_user
import asyncio

import schemas
import services
import database

router = APIRouter(
    prefix="/data",
    tags=["Form Data"]
)

@router.get("/portfolios", response_model=List[schemas.Portfolio])
async def read_all_portfolios(session: AsyncSession = Depends(get_session)):
    """Endpoint to get a list of all portfolios."""
    portfolios = await services.get_all_portfolios(session)
    return portfolios

@router.get("/projects/{portfolio_id}", response_model=List[schemas.Project])
async def read_projects_for_portfolio(portfolio_id: int, session: AsyncSession = Depends(get_session)):
    """Endpoint to get projects filtered by a specific portfolio."""
    projects = await services.get_projects_by_portfolio(portfolio_id, session)
    if not projects:
        raise HTTPException(status_code=404, detail="No projects found for this portfolio")
    return projects

@router.get("/group-activities/{project_id}", response_model=List[schemas.GroupActivity])
async def read_group_activities_for_project(project_id: int, session: AsyncSession = Depends(get_session)):
    """Endpoint to get group activities filtered by a specific project."""
    group_activities = await services.get_group_activities_by_project(project_id, session)
    return group_activities

@router.get("/function-activities/{team_id}", response_model=List[schemas.FunctionActivity])
async def read_function_activities_for_team(team_id: int, session: AsyncSession = Depends(get_session)):
    """Endpoint to get function activities filtered by a specific team."""
    function_activities = await services.get_function_activities_by_team(team_id, session)
    return function_activities


# @router.get("/form-data", response_model=schemas.FormData)
# async def get_form_data(
#     session: AsyncSession = Depends(database.get_session),
#     current_user: database.TeamMember = Depends(get_current_user) 
# ):
#     """
#     Provides all necessary data for the frontend to build the timesheet form
#     in a single, efficient API call.
#     """
#     try:
#         # Fetch data concurrently for better performance
#         projects_task = services.get_all_projects(session)
#         func_activities_task = services.get_all_function_activities(session)
        
#         projects, func_activities = await asyncio.gather(
#             projects_task, func_activities_task
#         )

#         group_activities = sorted(list(set(p.group_activity for p in projects if p.group_activity)))
#         statuses = ["To Start", "Ongoing", "On Hold", "Done"]

#         # Construct the response using the user object and fetched data.
#         # Pydantic will automatically convert the database objects to your schema models.
#         return {
#             "user_info": current_user,
#             "group_activities": group_activities,
#             "function_activities": func_activities,
#             "statuses": statuses
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
