# backend/api/auth_router.py
import os
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse 
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
import database
from database import TeamMember, get_session 
from sqlalchemy.orm import selectinload

# Load environment variables from the .env file
load_dotenv()

# --- Configuration ---
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.environ.get("SECRET_KEY") # For signing our own JWTs


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Placeholder URL


router = APIRouter(prefix="/auth", tags=["Authentication"])

# Create the Google OAuth2 client
google_client = GoogleOAuth2(CLIENT_ID, CLIENT_SECRET)


def create_app_access_token(user: database.TeamMember) -> str:
    """Creates a JWT access token for our application."""
    to_encode = {
        "sub": user.email,
        "user_id": user.id,
        "team_id": user.team_id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=8) # Token valid for 8 hours
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


@router.get("/google/login")
async def google_login():
    """
    Redirects the user to Google's authentication page.
    The redirect_uri must be registered in your Google Cloud Console.
    """
    redirect_uri = "http://127.0.0.1:8000/auth/google/callback"
    authorization_url = await google_client.get_authorization_url(
    redirect_uri,
    scope=["email", "profile"]
        )
    return RedirectResponse(url=authorization_url)

@router.get("/google/callback")
async def google_callback(code: str, session: AsyncSession = Depends(database.get_session)):
    """
    Handles the callback from Google and redirects the user back to the
    frontend with their application-specific access token.
    """
    # The URL of your running Streamlit application
    frontend_url = "http://localhost:8501" # Corrected URL
    redirect_uri = "http://127.0.0.1:8000/auth/google/callback"

    try:
        # Get the access token and user info from Google
        token_data = await google_client.get_access_token(code, redirect_uri)
        user_info_from_google = await google_client.get_id_email(token_data["access_token"])
        user_email = user_info_from_google[1]

        # Find the user in your database
        query = select(database.TeamMember).where(database.TeamMember.email == user_email)
        result = await session.execute(query)
        user = result.scalars().first()

        if not user:
            # If the user doesn't exist, redirect with an error
            return RedirectResponse(url=f"{frontend_url}?error=UserNotFound")

        print(f"User found: {user.email}, ID: {user.id}, Team ID: {user.team_id}", user)
        # Create your application's own JWT access token
        app_token = create_app_access_token(user)
        
        # This is the key change: redirect back to the Streamlit app
        # with the token as a URL query parameter.
        return RedirectResponse(url=f"{frontend_url}?token={app_token}")

    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        # On any other error, redirect back to the frontend with a generic error
        return RedirectResponse(url=f"{frontend_url}?error=LoginFailed")
    

@router.get("/user")
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(TeamMember)
        .options(selectinload(TeamMember.team))  # 👈 Force-load the relationship
        .where(TeamMember.email == email)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "full_name": user.full_name,
        "team": user.team.name if user.team else "Unknown"
    }