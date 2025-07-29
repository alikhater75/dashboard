# src/api_client.py

import httpx
from typing import Dict, Any, List

# The base URL for your running backend API
API_BASE_URL = "http://127.0.0.1:8000"


async def submit_timesheet(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Posts the complete timesheet submission payload to the backend."""
    async with httpx.AsyncClient() as client:
        # Set a longer timeout to handle potentially slow database operations
        response = await client.post(f"{API_BASE_URL}/submissions/", json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    

async def load_week_submission(user_email: str, week_date: str) -> Dict[str, Any]:
    """Fetches a previous submission from the backend."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/submissions/load-week/",
            params={"user_email": user_email, "week_date": week_date}
        )
        response.raise_for_status()
        return response.json()
    

async def load_draft_submission(user_email: str) -> Dict[str, Any]:
    """Fetches IN-PROGRESS DRAFT entries for the current week from the backend."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/submissions/load-draft/{user_email}")
        response.raise_for_status()
        return response.json()

async def get_user_details(email: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/auth/user", params={"email": email})
        response.raise_for_status()
        return response.json()
    

async def get_portfolios() -> List[Dict]:
    """Fetches all portfolios from the backend."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/portfolios") # Corrected endpoint
        response.raise_for_status()
        return response.json()

async def get_projects() -> List[Dict]:
    """Fetches all projects from the backend."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/projects") # Corrected endpoint
        response.raise_for_status()
        return response.json()

async def get_group_activities() -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/group_activities")
        response.raise_for_status()
        return response.json()

async def get_function_activities(team: str) -> list[str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/function_activities", params={"team": team})
        response.raise_for_status()
        return response.json()



# Admin API calls
async def add_portfolio(name: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/admin/portfolios", json={"name": name})
        response.raise_for_status()
        return response.json()

async def update_portfolio(portfolio_id: int, name: str):
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{API_BASE_URL}/admin/portfolios/{portfolio_id}", json={"name": name})
        response.raise_for_status()
        return response.json()

async def delete_portfolio(portfolio_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/admin/portfolios/{portfolio_id}")
        response.raise_for_status()
        return response.json()

async def add_project(name: str, portfolio_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/admin/projects", json={"project_name": name, "portfolio_id": portfolio_id})
        response.raise_for_status()
        return response.json()

async def update_project(project_id: int, name: str, portfolio_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{API_BASE_URL}/admin/projects/{project_id}", json={"project_name": name, "portfolio_id": portfolio_id})
        response.raise_for_status()
        return response.json()

async def delete_project(project_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/admin/projects/{project_id}")
        response.raise_for_status()
        return response.json()

async def add_group_activity(name: str, project_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/admin/group_activities", json={"name": name, "project_id": project_id})
        response.raise_for_status()
        return response.json()
    
async def update_group_activity(activity_id: int, name: str, project_id: int):
    """Updates a group activity's name and its associated project."""
    async with httpx.AsyncClient() as client:
        # The project_id is now included in the JSON payload
        payload = {"name": name, "project_id": project_id}
        response = await client.put(f"{API_BASE_URL}/admin/group_activities/{activity_id}", json=payload)
        response.raise_for_status()
        return response.json()

async def delete_group_activity(activity_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/admin/group_activities/{activity_id}")
        response.raise_for_status()
        return response.json()
