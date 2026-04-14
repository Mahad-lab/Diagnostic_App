# registration.py
"""
Patient Registration Module for Medical Camp EMR
Professional version using SQLAlchemy + PostgreSQL
"""

import streamlit as st
import pandas as pd
import re
import random
from typing import Tuple
from sqlalchemy import text
from database import get_db, Patient  # Import from database.py

# ========================= VALIDATION =========================

def validate_patient_inputs(
    name: str, cnic: str, nationality: str, address: str, phone: str, gender: str, age: int
) -> Tuple[bool, str]:
    """
    Validate patient registration inputs.
    Returns (is_valid, result_message_or_formatted_cnic)
    """
    # Clean inputs
    name = name.strip().title()
    cnic = cnic.strip().replace("-", "").replace(" ", "")
    nationality = nationality.strip().title()
    address = address.strip()
    phone = phone.strip()
    gender = gender.strip()

    # Name validation
    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces."

    # CNIC Logic (Camp-friendly: allow no ID)
    if not cnic or cnic == "0":
        # Generate temporary ID for patients without CNIC
        rand_id = random.randint(100000, 999999)
        formatted_cnic = f"NO-ID-{rand_id}"
    else:
        if not cnic.isdigit():
            return False, "CNIC must contain digits only."

        if len(cnic) != 13:
            return False, "CNIC must be exactly 13 digits (or leave empty for patients without ID)."

        # Format CNIC nicely: 12345-1234567-1
        formatted_cnic = f"{cnic[:5]}-{cnic[5:12]}-{cnic[12:]}"

    # Gender validation
    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."

    # Age validation
    if not isinstance(age, int) or age < 0 or age > 120:
        return False, "Age must be a valid number between 0 and 120."

    return True, formatted_cnic


# ========================= REGISTRATION UI =========================

def run_registration():
    """Main patient registration function."""

    # Security check
    if not st.session_state.get("logged_in", False):
        st.warning("Please login to access this page.")
        st.stop()

    role = st.session_state.get("role", "")
    if role not in ["registration", "admin"]:
        st.error("You do not have permission to access patient registration.")
        st.stop()

    st.set_page_config(layout="centered", page_title="Patient Registration")
    st.title("🧾 Patient Registration")
    st.markdown("Register new patients for the medical camp.")

    # ------------------- Registration Form -------------------
    with st.form("patient_registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Full Name *", placeholder="Enter patient full name")
            nationality = st.text_input("Nationality", value="Pakistani")
            phone = st.text_input("Phone Number", placeholder="03xx-xxxxxxx")
            age = st.number_input("Age", min_value=0, max_value=120, step=1, value=25)

        with col2:
            cnic = st.text_input(
                "CNIC / ID",
                placeholder="1234512345671 or leave empty",
                help="Leave empty if patient has no CNIC. A temporary ID will be generated."
            )
            gender = st.selectbox("Gender *", ["", "Male", "Female", "Other"])
            address = st.text_area("Address", placeholder="Enter full address", height=100)

        submitted = st.form_submit_button("✅ Register Patient", use_container_width=True)

    # ------------------- Form Submission Handling -------------------
    if submitted:
        if not name.strip():
            st.error("❌ Patient Name is required.")
            st.stop()

        is_valid, result = validate_patient_inputs(
            name, cnic, nationality, address, phone, gender, int(age)
        )

        if not is_valid:
            st.error(f"❌ {result}")
        else:
            final_cnic = result

            try:
                with next(get_db()) as db:
                    # Check if CNIC already exists (optional - can be removed if you want duplicates)
                    existing = db.execute(
                        text("SELECT patient_id FROM patients WHERE cnic = :cnic"),
                        {"cnic": final_cnic}
                    ).fetchone()

                    if existing and not final_cnic.startswith("NO-ID-"):
                        st.warning(f"⚠️ A patient with CNIC {final_cnic} already exists.")
                    else:
                        new_patient = Patient(
                            patient_name=name.strip(),
                            cnic=final_cnic,
                            nationality=nationality.strip(),
                            address=address.strip(),
                            phone=phone.strip(),
                            gender=gender,
                            age=int(age)
                        )

                        db.add(new_patient)
                        db.commit()
                        db.refresh(new_patient)

                        st.success(
                            f"✅ **Patient Registered Successfully!**\n\n"
                            f"**Name:** {name}\n"
                            f"**Patient ID:** {new_patient.patient_id}\n"
                            f"**CNIC:** {final_cnic}"
                        )

                        # Clear form by rerunning
                        st.rerun()

            except Exception as e:
                st.error(f"Database error while registering patient: {e}")

    # ------------------- Recent Registrations -------------------
    st.markdown("---")
    st.subheader("📋 Recently Registered Patients (Latest 10)")

    try:
        with next(get_db()) as db:
            df = pd.read_sql(
                text("""
                    SELECT 
                        patient_id, 
                        patient_name, 
                        cnic, 
                        gender, 
                        age, 
                        phone,
                        nationality
                    FROM patients 
                    ORDER BY patient_id DESC 
                    LIMIT 10
                """),
                db.bind
            )

        if df.empty:
            st.info("No patients registered yet.")
        else:
            # Nice formatting
            df_display = df.copy()
            df_display.columns = [col.replace("_", " ").title() for col in df_display.columns]
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"Error loading patient list: {e}")


if __name__ == "__main__":
    run_registration()