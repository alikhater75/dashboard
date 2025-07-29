# Sensor Tech Workload Dashboard

## 1. Overview

The Sensor Tech Workload Dashboard is a comprehensive web application designed to streamline the process of timesheet submission and analysis. It provides a user-friendly interface for team members to submit their weekly work hours and a powerful administrative dashboard for managers to oversee projects, manage team data, and analyze workload distribution.

The application is built with a modern technology stack, featuring a secure authentication system, a robust backend API, and an interactive frontend.

---

## 2. Features

* **Secure User Authentication**: Employs Google OAuth2 for a secure and seamless login experience.
* **Intuitive Timesheet Submission**: A dynamic form allows users to easily log hours against specific projects and activities.
* **Drafts & Submissions**: Users can save their timesheet as a draft and return later to complete it before final submission.
* **Administrative Dashboard**: A dedicated interface for administrators to perform CRUD (Create, Read, Update, Delete) operations on:
    * Portfolios
    * Projects
    * Team Members
    * Functional Activities
* **Data Analysis**: The system is designed to collect structured data, paving the way for future data analysis and visualization of team workload.

---

## 3. Technology Stack

* **Backend**:
    * **Framework**: FastAPI
    * **Database**: PostgreSQL
    * **ORM**: SQLAlchemy
    * **Database Migrations**: Alembic
    * **Authentication**: JWT (JSON Web Tokens)
* **Frontend**:
    * **Framework**: Streamlit
* **Programming Language**: Python 3.10+

---

## 4. Project Structure

The project is organized into two main components:

* **`backend/`**: Contains the FastAPI application, which handles all business logic, API endpoints, database interactions, and user authentication.
* **`automation-refactored/`**: The root directory for the Streamlit frontend application, which provides the user interface for timesheet submission and the admin dashboard.

---

## 5. Setup and Installation

Follow these steps carefully to set up and run the project locally.

### Step 1: Prerequisites

* **Python**: Ensure you have Python 3.10 or newer installed.
* **PostgreSQL**: A running instance of PostgreSQL is required. You can install it directly or run it via Docker.

### Step 2: Configure the Backend

1.  **Navigate to the Backend Directory**:
    ```bash
    cd automation-refactored/backend
    ```

2.  **Create and Activate a Virtual Environment**:
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Backend Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up the Database**:
    * Create a new database in PostgreSQL (e.g., `workload_db`).
    * In the `backend/` directory, create a file named `.env` by copying the example or creating it from scratch.
    * Update the `.env` file with your database credentials and Google OAuth details. It should look like this:

    ```env
    # backend/.env
    DATABASE_URL="postgresql://YOUR_POSTGRES_USER:YOUR_POSTGRES_PASSWORD@localhost:5432/workload_db"
    GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
    SECRET_KEY="a_very_secret_key_for_jwt" # Generate a random string for this
    ALGORITHM="HS256"
    ```
    **Note**: Replace the placeholder values with your actual credentials.

5.  **Apply Database Migrations**:
    Run the following command to create all the necessary tables in your database based on the latest schema.
    ```bash
    alembic upgrade head
    ```

### Step 3: Populate the Database (Mandatory First Step)

The application requires initial data (like projects, teams, etc.) to function correctly. The ETL (Extract, Transform, Load) script populates the database from source Excel files.

**This step must be run before you start the application for the first time.**

1.  **Ensure you are in the `backend/` directory** with the virtual environment activated.
2.  Run the ETL script:
    ```bash
    python etl.py
    ```
    This will read data from the Excel files specified in `etl_config.py` and load it into your PostgreSQL database.

### Step 4: Configure the Frontend

1.  **Navigate to the Root Project Directory**:
    ```bash
    # From the backend directory
    cd ..
    ```

2.  **Create and Activate a Virtual Environment** (this is separate from the backend's environment):
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Frontend Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 6. Running the Application

The application consists of two separate services that must be run concurrently: the backend server and the frontend app.

1.  **Start the Backend Server**:
    * Open a terminal, navigate to `automation-refactored/backend/`, and activate its virtual environment.
    * Run the following command:
        ```bash
        uvicorn main:app --reload --port 8001
        ```
    * The backend API will now be running at `http://127.0.0.1:8001`.

2.  **Start the Frontend Application**:
    * Open a **new** terminal, navigate to `automation-refactored/`, and activate its virtual environment.
    * Run the following command:
        ```bash
        streamlit run submit_timesheet.py
        ```
    * The application will open in your web browser.

