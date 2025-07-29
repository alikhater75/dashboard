# backend/schemas.py

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import date
from enum import Enum

# --- Base Schemas for Core Models ---

class Portfolio(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class Project(BaseModel):
    id: int
    project_name: str
    class Config:
        from_attributes = True
        
class GroupActivity(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True
        
class FunctionActivity(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    name: str

class ProjectCreate(BaseModel):
    name: str
    portfolio_id: int

class GroupActivityCreate(BaseModel):
    name: str
    project_id: int

# --- Schemas for the Timesheet Submission Payload ---

class TimeEntryCreate(BaseModel):
    hours: float
    notes: Optional[str] = None

class TaskCreate(BaseModel):
    type: str = "Work" 
    description: str 
    status: str
    group_activity_id: int
    function_activity_id: int
    entry: TimeEntryCreate # Nested time entry data

class MeetingCreate(BaseModel):
    type: str = "Meeting" 
    description: str 
    group_activity_id: int
    function_activity_id: int
    entry: TimeEntryCreate # Nested time entry data

class TimesheetSubmission(BaseModel):
    user_email: EmailStr
    week_date: date
    tasks: List[TaskCreate]
    meetings: List[MeetingCreate]


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

class User(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    team_id: int
    role: str


    class Config:
        from_attributes = True


class TaskEntry(BaseModel):
    # Use Field(alias=...) to map incoming JSON keys (DataFrame columns)
    type: str = Field("Work", alias="Type")
    description: str = Field(..., alias="Task Description")
    group_activity: str = Field(..., alias="Group Activity")
    function_activity: str = Field(..., alias="Function Activity")
    status: str = Field(..., alias="Status")
    weekly_hours: float = Field(..., alias="Total Weekly Hours")
    sun: Optional[float] = Field(0, alias="sun")
    mon: Optional[float] = Field(0, alias="mon")
    tue: Optional[float] = Field(0, alias="tue")
    wed: Optional[float] = Field(0, alias="wed")
    thu: Optional[float] = Field(0, alias="thu")
    notes: Optional[str] = Field("", alias="Notes")

    class Config:
        # This tells Pydantic to look for aliases first, then field names
        populate_by_name = True 

class MeetingEntry(BaseModel):
    type: str = Field("Meeting", alias="Type") 
    description: str = Field(..., alias="Meeting Description")
    group_activity: str = Field(..., alias="Group Activity")
    function_activity: str = Field(..., alias="Function Activity")
    # Frontend sends 'Total Weekly Hours' for meetings too, so alias 'hours'
    hours: float = Field(..., alias="Total Weekly Hours") 
    notes: Optional[str] = Field("", alias="Notes")

    class Config:
        populate_by_name = True

class TimeEntryStatus(str, Enum):
    """Enumeration for the status of a time entry."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    
class SubmissionRequest(BaseModel):
    user_email: str
    user_name: str
    user_team: str
    week_date: date
    daily_mode: bool
    tasks: List[TaskEntry]
    meetings: List[MeetingEntry]
    overwrite: bool = False
    status: TimeEntryStatus = TimeEntryStatus.SUBMITTED 

