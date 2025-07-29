import streamlit as st
import jwt
import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
BACKEND_LOGIN_URL = "http://127.0.0.1:8000/auth/google/login"
SECRET_KEY = os.environ.get("SECRET_KEY")

def handle_login_redirect():
    """
    Checks for a token in the URL's query parameters.
    If a token is found, it validates it, sets the session state,
    and clears the token from the URL.
    """
    if 'token' in st.query_params and not st.session_state.get('logged_in'):
        token = st.query_params['token']
        try:
            # Decode the token to get user information
            payload = jwt.decode(
                token,
                key=SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": True}
            )
            # Store user info and login state in the session
            st.session_state.access_token = token
            st.session_state.user_email = payload.get("sub")
            st.session_state.user_id = payload.get("user_id")
            st.session_state.user_team_id = payload.get("team_id")
            # st.session_state.user_role = payload.get("role")
            st.session_state.user_role = 'admin'

            st.session_state.logged_in = True
            
            st.query_params.clear()
            st.rerun()

        except Exception as e:
            st.error(f"Login failed: {e}")
            st.session_state.logged_in = False
            st.query_params.clear()

def show_login_page():
    """
    Displays the login page with a button to sign in with Google.
    """
    st.set_page_config(layout="centered", page_title="Login")
    st.title("Welcome to the Timesheet App")
    st.write("Please sign in to continue.")

    st.link_button(
        "Sign in with Google",
        BACKEND_LOGIN_URL,
        use_container_width=True,
        type="primary"
    )
    
    if 'error' in st.query_params:
        st.error(f"Login failed: {st.query_params['error']}. Please try again.")
        st.query_params.clear()
