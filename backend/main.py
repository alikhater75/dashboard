# backend/main.py
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Simplified imports
from api import admin_router, submission_router, auth_router, activity_router

app = FastAPI(
    title="Timesheet Backend API",
    description="API service for the timesheet submission application.",
    version="1.0.0"
)

# --- Add CORS Middleware ---
# This is the new section to add.
# It allows your frontend to communicate with your backend.

origins = [
    "http://localhost",
    "http://localhost:8501",  # The default port for Streamlit
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
# --- End of new section ---


# app.include_router(data_router.router)
app.include_router(admin_router.router)
app.include_router(submission_router.router)
app.include_router(auth_router.router)
app.include_router(activity_router.router,)

@app.get("/", tags=["Root"])
async def read_root():
    return {"status": "ok", "message": "Welcome to the Timesheet API!"}