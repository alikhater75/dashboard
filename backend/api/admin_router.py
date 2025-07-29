# backend/api/admin_router.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import schemas, dashboard_services, database

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.post("/portfolios", response_model=schemas.Portfolio)
async def create_portfolio(portfolio: schemas.PortfolioCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.create_portfolio(db=db, portfolio=portfolio)

@router.put("/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(portfolio_id: int, portfolio: schemas.PortfolioCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.update_portfolio(db=db, portfolio_id=portfolio_id, portfolio=portfolio)

@router.delete("/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
async def delete_portfolio(portfolio_id: int, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.delete_portfolio(db=db, portfolio_id=portfolio_id)

@router.post("/projects", response_model=schemas.Project)
async def create_project(project: schemas.ProjectCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.create_project(db=db, project=project)

@router.put("/projects/{project_id}", response_model=schemas.Project)
async def update_project(project_id: int, project: schemas.ProjectCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.update_project(db=db, project_id=project_id, project=project)

@router.delete("/projects/{project_id}", response_model=schemas.Project)
async def delete_project(project_id: int, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.delete_project(db=db, project_id=project_id)

@router.post("/group_activities", response_model=schemas.GroupActivity)
async def create_group_activity(activity: schemas.GroupActivityCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.create_group_activity(db=db, activity=activity)

@router.put("/group_activities/{activity_id}", response_model=schemas.GroupActivity)
async def update_group_activity(activity_id: int, activity: schemas.GroupActivityCreate, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.update_group_activity(db=db, activity_id=activity_id, activity=activity)

@router.delete("/group_activities/{activity_id}", response_model=schemas.GroupActivity)
async def delete_group_activity(activity_id: int, db: AsyncSession = Depends(database.get_session)):
    return await dashboard_services.delete_group_activity(db=db, activity_id=activity_id)