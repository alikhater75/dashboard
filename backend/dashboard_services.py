# backend/dashboard_services.py

from sqlalchemy.orm import selectinload
import database, schemas
from sqlalchemy.ext.asyncio import AsyncSession
from database import GroupActivity, Portfolio, Project
from sqlalchemy import select

# --- Portfolio Services ---

async def get_portfolio(db: AsyncSession, portfolio_id: int):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    return result.scalars().first()

async def get_all_portfolios(db: AsyncSession):
    result = await db.execute(select(Portfolio))
    return result.scalars().all()

async def create_portfolio(db: AsyncSession, portfolio: schemas.PortfolioCreate):
    db_portfolio = Portfolio(name=portfolio.name)
    db.add(db_portfolio)
    await db.commit()  # AWAIT FIX
    await db.refresh(db_portfolio) # AWAIT FIX
    return db_portfolio

async def update_portfolio(db: AsyncSession, portfolio_id: int, portfolio: schemas.PortfolioCreate):
    db_portfolio = await get_portfolio(db, portfolio_id)
    if db_portfolio:
        db_portfolio.name = portfolio.name
        await db.commit()  # AWAIT FIX
        await db.refresh(db_portfolio) # AWAIT FIX
    return db_portfolio

async def delete_portfolio(db: AsyncSession, portfolio_id: int):
    db_portfolio = await get_portfolio(db, portfolio_id)
    if db_portfolio:
        await db.delete(db_portfolio) # AWAIT FIX
        await db.commit()  # AWAIT FIX
    return db_portfolio

# --- Project Services ---

async def get_project(db: AsyncSession, project_id: int):
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalars().first()

async def get_all_projects(db: AsyncSession):
    # Use selectinload for better performance on related objects
    result = await db.execute(select(Project).options(selectinload(Project.portfolio)))
    return result.scalars().unique().all()

async def create_project(db: AsyncSession, project: schemas.ProjectCreate):
    db_project = Project(project_name=project.name, portfolio_id=project.portfolio_id)
    db.add(db_project)
    await db.commit()  # AWAIT FIX
    await db.refresh(db_project) # AWAIT FIX
    return db_project

async def update_project(db: AsyncSession, project_id: int, project: schemas.ProjectCreate):
    db_project = await get_project(db, project_id)
    if db_project:
        db_project.project_name = project.name
        db_project.portfolio_id = project.portfolio_id
        await db.commit()  # AWAIT FIX
        await db.refresh(db_project) # AWAIT FIX
    return db_project

async def delete_project(db: AsyncSession, project_id: int):
    db_project = await get_project(db, project_id)
    if db_project:
        await db.delete(db_project) # AWAIT FIX
        await db.commit()  # AWAIT FIX
    return db_project

# --- Group Activity Services ---

async def get_group_activity(db: AsyncSession, activity_id: int):
    result = await db.execute(select(GroupActivity).where(GroupActivity.id == activity_id))
    return result.scalars().first()

async def get_all_group_activities(db: AsyncSession):
    result = await db.execute(select(GroupActivity).options(selectinload(GroupActivity.project).selectinload(Project.portfolio)))
    return result.scalars().unique().all()

async def create_group_activity(db: AsyncSession, activity: schemas.GroupActivityCreate):
    db_activity = GroupActivity(name=activity.name, project_id=activity.project_id)
    db.add(db_activity)
    await db.commit()  # AWAIT FIX
    await db.refresh(db_activity) # AWAIT FIX
    return db_activity

async def update_group_activity(db: AsyncSession, activity_id: int, activity: schemas.GroupActivityCreate):
    db_activity = await get_group_activity(db, activity_id)
    if db_activity:
        db_activity.name = activity.name
        db_activity.project_id = activity.project_id
        await db.commit()  # AWAIT FIX
        await db.refresh(db_activity) # AWAIT FIX
    return db_activity

async def delete_group_activity(db: AsyncSession, activity_id: int):
    db_activity = await get_group_activity(db, activity_id)
    if db_activity:
        await db.delete(db_activity) # AWAIT FIX
        await db.commit()  # AWAIT FIX
    return db_activity






