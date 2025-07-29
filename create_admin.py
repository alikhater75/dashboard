# create_admin.py

import getpass
from src.database import get_session, TeamMember
from src.auth import hash_password

def setup_admin():
    """A command-line utility to set the password for an admin user."""
    session = get_session()
    try:
        print("--- Admin User Setup ---")
        email = input("Enter the email of the user to make an admin: ").strip()
        
        user = session.query(TeamMember).filter_by(email=email).first()

        if not user:
            print(f"❌ Error: No user found with the email '{email}'. Please run the data sync first.")
            return

        print(f"Found user: {user.full_name}")

        password = getpass.getpass("Enter a new password for the admin: ")
        confirm_password = getpass.getpass("Confirm the new password: ")

        if password != confirm_password:
            print("❌ Error: Passwords do not match.")
            return
        
        if len(password) < 8:
            print("❌ Error: Password must be at least 8 characters long.")
            return

        # Hash the password and update the user record
        user.hashed_password = hash_password(password)
        user.is_admin = True
        
        session.commit()
        print(f"✅ Success! '{user.full_name}' is now an administrator.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    setup_admin()