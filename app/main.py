# app.py
"""
Medical Camp EMR - Main Application Entry Point
A secure, role-based Streamlit application for Medical Camp management.
"""

import streamlit as st
from typing import Dict, Any

# Import modules (ensure these files are in the same directory)
import medical_camp
import registration

# ========================= CONFIGURATION =========================

st.set_page_config(
    page_title="Medical Camp EMR",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Hardcoded users with roles (In production, replace with secure database + hashing)
USERS: Dict[str, Dict[str, str]] = {
    "admin": {"password": "admin", "role": "admin"},
    "doctor": {"password": "d1234", "role": "doctor"},
    "pharmacy": {"password": "p1234", "role": "pharmacy"},
    "registration": {"password": "r1234", "role": "registration"},
}

# ========================= SESSION STATE INITIALIZATION =========================

def initialize_session_state() -> None:
    """Initialize session state variables if they don't exist."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "username" not in st.session_state:
        st.session_state.username = ""


# ========================= AUTO-LOGIN LOGIC =========================

def handle_auto_login() -> None:
    """Handle automatic login via URL query parameters (for page refresh persistence)."""
    if st.session_state.logged_in:
        return

    query_params = st.query_params

    if "username" in query_params and "role" in query_params:
        username = query_params["username"]
        role = query_params["role"]

        # Validate credentials from URL
        if (
            username in USERS
            and USERS[username]["role"] == role
        ):
            st.session_state.logged_in = True
            st.session_state.role = role
            st.session_state.username = username
            st.rerun()


# ========================= LOGIN FORM =========================

def show_login_form() -> None:
    """Display the login form when user is not authenticated."""
    st.title("🔒 Medical Camp EMR")
    st.markdown("### Secure Login")

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if username in USERS and USERS[username]["password"] == password:
                # Successful login
                st.session_state.logged_in = True
                st.session_state.role = USERS[username]["role"]
                st.session_state.username = username

                # Persist login via URL query params
                st.query_params["username"] = username
                st.query_params["role"] = USERS[username]["role"]

                st.success(f"✅ Welcome, **{username}**! Role: **{st.session_state.role.upper()}**")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")


# ========================= MAIN APPLICATION =========================

def main() -> None:
    """Main application entry point."""
    initialize_session_state()

    # Handle auto-login from URL (useful after refresh)
    handle_auto_login()

    # ====================== LOGIN SCREEN ======================
    if not st.session_state.logged_in:
        show_login_form()
        return

    # ====================== AUTHENTICATED APP ======================
    role = st.session_state.role
    username = st.session_state.username

    # Sidebar - User Info & Logout
    with st.sidebar:
        st.success(f"✅ Logged in as **{username}**")
        st.info(f"Role: **{role.upper()}**")

        st.divider()

        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            # Clear everything for secure logout
            st.session_state.clear()
            st.query_params.clear()
            st.success("Logged out successfully.")
            st.rerun()

    # ====================== ROLE-BASED ROUTING ======================
    if role in ["admin", "doctor", "pharmacy"]:
        medical_camp.run_app()

    elif role == "registration":
        registration.run_registration()

    else:
        st.error("❌ Unauthorized role detected. Please contact administrator.")
        if st.button("Logout"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()


# ========================= ENTRY POINT =========================

if __name__ == "__main__":
    main()


# Run command (for reference):
# streamlit run app.py --server.port 8501