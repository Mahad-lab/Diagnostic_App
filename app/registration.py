"""
Patient Registration Module - Medical Camp EMR
SQLAlchemy + PostgreSQL
"""
import re
import random
from typing import Tuple

import pandas as pd
import streamlit as st

from database import get_db, get_engine, Patient


def _validate(name: str, cnic: str, nationality: str, address: str, phone: str, gender: str, age: int) -> Tuple[bool, str]:
    name = name.strip().title()
    cnic = cnic.strip().replace("-", "").replace(" ", "")

    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces."

    if not cnic or cnic == "0":
        formatted_cnic = f"NO-ID-{random.randint(100000, 999999)}"
    else:
        if not cnic.isdigit():
            return False, "CNIC must contain only digits."
        if len(cnic) != 13:
            return False, "CNIC must be exactly 13 digits (or leave empty)."
        formatted_cnic = f"{cnic[:5]}-{cnic[5:12]}-{cnic[12:]}"

    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."

    if not isinstance(age, int) or age < 0 or age > 120:
        return False, "Age must be between 0 and 120."

    return True, formatted_cnic


def run_registration() -> None:
    if not st.session_state.get("logged_in", False):
        st.warning("Please login from the main page.")
        st.stop()

    role = st.session_state.get("role", "")
    if role not in ["registration", "admin"]:
        st.error("Access denied. Only Registration Staff or Admin can register patients.")
        st.stop()

    st.title("🧾 Patient Registration")
    st.markdown("Register new patients for the medical camp.")

    with st.form("patient_registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="Enter patient's full name")
            nationality = st.text_input("Nationality", value="Pakistani")
            phone = st.text_input("Phone Number", placeholder="03xx-xxxxxxx")
            age = st.number_input("Age", min_value=0, max_value=120, value=25, step=1)
        with col2:
            cnic = st.text_input(
                "CNIC (13 digits)",
                placeholder="1234512345671 or leave blank",
                help="Leave empty if patient has no CNIC. A temporary ID will be generated.",
            )
            gender = st.selectbox("Gender *", ["", "Male", "Female", "Other"])
            address = st.text_area("Address", placeholder="Full address here...", height=100)
        submitted = st.form_submit_button("✅ Register Patient", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Patient Name is required.")
        else:
            is_valid, result = _validate(name, cnic, nationality, address, phone, gender, int(age))
            if not is_valid:
                st.error(f"❌ {result}")
            else:
                final_cnic = result
                try:
                    with get_db() as db:
                        patient = Patient(
                            patient_name=name.strip(),
                            cnic=final_cnic,
                            nationality=nationality.strip() or None,
                            address=address.strip() or None,
                            phone=phone.strip() or None,
                            gender=gender,
                            age=int(age),
                        )
                        db.add(patient)
                        db.commit()
                        db.refresh(patient)
                    st.success(
                        f"✅ **Registered!** | Patient ID: **{patient.patient_id}** "
                        f"| Name: **{name.strip()}** | CNIC: **{final_cnic}**"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to register patient: {e}")

    st.markdown("---")
    st.subheader("📋 Recently Registered Patients")
    try:
        df = pd.read_sql(
            "SELECT patient_id, patient_name, cnic, gender, age, phone, nationality "
            "FROM patients ORDER BY patient_id DESC LIMIT 10",
            get_engine(),
        )
        if df.empty:
            st.info("No patients registered yet.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error loading patients: {e}")
