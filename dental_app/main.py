"""
Dental Camp EMR - Main Application Entry Point
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from typing import Dict

import dental_camp
from database import init_db

st.set_page_config(
    page_title="Dental Camp EMR",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

USERS: Dict[str, Dict[str, str]] = {
    "admin":   {"password": "admin", "role": "admin"},
    "dentist": {"password": "dent1234", "role": "dentist"},
}


def _init_session() -> None:
    for key, val in {"logged_in": False, "role": "", "username": ""}.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _auto_login() -> None:
    if st.session_state.logged_in:
        return
    params   = st.query_params
    username = params.get("username")
    role     = params.get("role")
    if username and role and username in USERS and USERS[username]["role"] == role:
        st.session_state.logged_in = True
        st.session_state.role      = role
        st.session_state.username  = username
        st.rerun()


def _show_login() -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🦷 Dental Camp EMR")
        st.markdown("### Secure Login")
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            if st.form_submit_button("Login", use_container_width=True):
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.role      = USERS[username]["role"]
                    st.session_state.username  = username
                    st.query_params["username"] = username
                    st.query_params["role"]     = USERS[username]["role"]
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")


def main() -> None:
    _init_session()
    _auto_login()

    if not st.session_state.logged_in:
        _show_login()
        return

    try:
        init_db()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return

    username = st.session_state.username
    role     = st.session_state.role

    with st.sidebar:
        st.success(f"✅ **{username}**")
        st.info(f"Role: **{role.upper()}**")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    dental_camp.run_dental_app()


if __name__ == "__main__":
    main()
