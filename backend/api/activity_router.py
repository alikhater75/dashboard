# backend/api/activity_router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Portfolio, Project, GroupActivity, FunctionActivity, Team
from database import get_session as get_async_session
from sqlalchemy.orm import selectinload, subqueryload

router = APIRouter()

@router.get("/portfolios")
async def get_all_portfolios(db: AsyncSession = Depends(get_async_session)):
    """Endpoint to get a list of all portfolios."""
    result = await db.execute(select(Portfolio))
    portfolios = result.scalars().all()
    return [{"id": p.id, "name": p.name} for p in portfolios]

@router.get("/projects")
async def get_projects(db: AsyncSession = Depends(get_async_session)):
    """Endpoint to get a list of all projects with their portfolio."""
    result = await db.execute(select(Project).options(subqueryload(Project.portfolio)))
    projects = result.scalars().all()
    return [
        {
            "id": p.id,
            "project_name": p.project_name,
            "portfolio_id": p.portfolio.id if p.portfolio else None,
            "portfolio_name": p.portfolio.name if p.portfolio else "N/A"
        }
        for p in projects
    ]

@router.get("/group_activities")
async def get_group_activities(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(
        select(GroupActivity)
        .options(
            selectinload(GroupActivity.project).selectinload(Project.portfolio)
        )
    )
    group_activities = result.scalars().all()

    return [
        {
            "name": ga.name,
            "id": ga.id,
            "project": ga.project.project_name if ga.project else "Unknown",
            "portfolio": ga.project.portfolio.name if ga.project and ga.project.portfolio else "Unknown"
        }
        for ga in group_activities
    ]


@router.get("/function_activities")
async def get_function_activities(team: str = Query(...), db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(
        select(FunctionActivity).join(Team).where(Team.name == team)
    )
    function_activities = result.scalars().all()
    return [fa.name for fa in function_activities]
