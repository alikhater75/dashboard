# src/database.py

import os
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession
import os
from sqlalchemy.ext.asyncio import create_async_engine

Base = declarative_base()

class Portfolio(Base):
    __tablename__ = 'portfolios'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    projects = relationship("Project", back_populates="portfolio")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String, unique=True, nullable=False)
    status = Column(String, default='Active', nullable=False)

    portfolio_id = Column(Integer, ForeignKey('portfolios.id'))
    portfolio = relationship("Portfolio", back_populates="projects")

    group_activities = relationship("GroupActivity", back_populates="project")

class GroupActivity(Base):
    __tablename__ = 'group_activities'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship("Project", back_populates="group_activities")

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    members = relationship("TeamMember", back_populates="team")
    function_activities = relationship("FunctionActivity", back_populates="team")

class TeamMember(Base):
    __tablename__ = 'team_members'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    status = Column(String, default='Active')
    role = Column(String, default='user', nullable=False)


    # Foreign Key to the new Teams table
    team_id = Column(Integer, ForeignKey('teams.id'))
    # Self-referencing Foreign Key for the manager
    manager_id = Column(Integer, ForeignKey('team_members.id'))

    # Relationships
    team = relationship("Team", back_populates="members")
    time_entries = relationship("TimeEntry", back_populates="team_member")
    # Relationship for reports/employees
    reports = relationship("TeamMember", back_populates="manager", remote_side=[id])
    manager = relationship("TeamMember", back_populates="reports", remote_side=[manager_id])


class FunctionActivity(Base):
    __tablename__ = 'function_activities'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # Foreign Key to the new Teams table
    team_id = Column(Integer, ForeignKey('teams.id'))
    # Relationship
    team = relationship("Team", back_populates="function_activities")
    
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    type = Column(String)
    description  = Column(String) # e.g., "Implement login authentication"
    status = Column(String, default='To Start')

    # --- Foreign Keys to link everything ---
    owner_id = Column(Integer, ForeignKey('team_members.id'))
    group_activity_id = Column(Integer, ForeignKey('group_activities.id'))
    function_activity_id = Column(Integer, ForeignKey('function_activities.id'))

    # --- Relationships ---
    owner = relationship("TeamMember")
    group_activity = relationship("GroupActivity")
    function_activity = relationship("FunctionActivity")

    # Link to the time logged against this task
    time_entries = relationship("TimeEntry", back_populates="task")

# ... The TimeEntry class should have all columns including name, team, manager_email etc.
class TimeEntry(Base):
    __tablename__ = 'time_entries'
    id = Column(Integer, primary_key=True)
    hours = Column(Float, nullable=False)
    notes = Column(String, nullable=True)
    date_of_work = Column(DateTime, nullable=False)
    submission_id = Column(String(36), index=True, nullable=False) # Groups entries from one submission
    timestamp = Column(DateTime, nullable=False)
    status = Column(String, nullable=True)

    daily_mode = Column(Boolean, nullable=False, default=False)
    sun = Column(Float, nullable=False, default=0.0)
    mon = Column(Float, nullable=False, default=0.0)
    tue = Column(Float, nullable=False, default=0.0)
    wed = Column(Float, nullable=False, default=0.0)
    thu = Column(Float, nullable=False, default=0.0)
    
    # --- Just two main foreign keys ---
    task_id = Column(Integer, ForeignKey('tasks.id'))
    team_member_id = Column(Integer, ForeignKey('team_members.id')) # Who logged the time

    # --- Relationships ---
    task = relationship("Task", back_populates="time_entries")
    team_member = relationship("TeamMember")



# Replace with this new function
def get_engine():
    """
    Returns a new SQLAlchemy engine for our PostgreSQL database,
    using the URL from the environment variables.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url is None:
        raise ValueError("DATABASE_URL environment variable is not set.")

    # For async connection with psycopg2/asyncpg
    return create_async_engine(db_url)

def create_database_and_tables():
    """Creates all defined tables in the PostgreSQL database if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database setup complete. Connected to PostgreSQL.")

# Replace with this new async generator function
async def get_session():
    """Async session generator for FastAPI dependencies."""
    engine = get_engine()
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session