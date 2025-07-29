# backend/src/api/submission_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import schemas
import services
from database import get_session
from datetime import date

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"]
)

@router.post("/", status_code=201)
async def submit_new_timesheet(submission: schemas.SubmissionRequest, session: AsyncSession = Depends(get_session)):
    """
    Endpoint to receive and process a new timesheet submission.
    """
    try:
        # Also change the service call to services.submit_timesheet as per services.py
        result = await services.submit_timesheet(submission, session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Generic error for other potential issues
        print(f"Error processing submission: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
   
@router.get("/load-draft/{user_email}") # The email is now part of the path
async def load_draft_data(user_email: str, session: AsyncSession = Depends(get_session)):
    """Endpoint to load a previous week's DRAFT submission data."""
    try:
        submission_data = await services.get_draft_submission_for_week(user_email, session)
        return submission_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/load-week/")
async def load_week_data(
    user_email: str,
    week_date: date,
    session: AsyncSession = Depends(get_session)
):
    """Endpoint to load a previous week's submission data."""
    try:
        submission_data = await services.get_submission_for_week(user_email, week_date, session)
        return submission_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
