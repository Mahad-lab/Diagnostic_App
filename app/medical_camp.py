"""
Medical Camp EMR & Pharmacy Module
SQLAlchemy + PostgreSQL — full implementation
"""
import os
import re
import random

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

from database import get_db, get_engine, Patient, Visit, Stock


# ========================= DATA LOADERS =========================

@st.cache_data(ttl=None)
def _load_icd_diagnosis() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icd_diagnosis.csv")
    try:
        df = pd.read_csv(csv_path)
        candidates = ["Diagnosis", "diagnosis", "Description", "description",
                      "Disease", "disease", "LONG_DESCRIPTION", "short_description"]
        for col in candidates:
            if col in df.columns:
                return df.rename(columns={col: "Diagnosis"})
        fallback = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        return df.rename(columns={fallback: "Diagnosis"})
    except Exception as e:
        st.warning(f"Could not load ICD diagnosis CSV: {e}")
        return pd.DataFrame(columns=["Diagnosis"])


@st.cache_data(ttl=None)
def _load_icd_symptoms() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ICD10_Symptom_List_All.csv")
    try:
        df = pd.read_csv(csv_path)
        candidates = ["Symptom", "symptom", "Description", "description", "symptom_text"]
        for col in candidates:
            if col in df.columns:
                return df.rename(columns={col: "Symptom"})
        return df.rename(columns={df.columns[0]: "Symptom"})
    except Exception as e:
        st.warning(f"Could not load ICD symptoms CSV: {e}")
        return pd.DataFrame(columns=["Symptom"])


def _load_stock() -> pd.DataFrame:
    try:
        return pd.read_sql("SELECT * FROM stock ORDER BY generic", get_engine())
    except Exception as e:
        st.error(f"Error loading stock: {e}")
        return pd.DataFrame()


def _deduct_stock_atomic(key: str, qty: int) -> None:
    with get_db() as db:
        db.execute(
            text("UPDATE stock SET stock_qty = stock_qty - :qty WHERE key = :key AND stock_qty >= :qty"),
            {"qty": qty, "key": key},
        )
        db.commit()


def _stock_csv_template() -> str:
    import io
    buf = io.StringIO()
    pd.DataFrame(columns=[
        "key", "generic", "brand", "dosage_form", 
        "dose","expiry", "unit", "stock_qty",
    ]).to_csv(buf, index=False)
    return buf.getvalue()


def _upsert_stock(df: pd.DataFrame) -> None:
    """Insert or update stock rows using PostgreSQL ON CONFLICT."""
    with get_db() as db:
        for _, row in df.iterrows():
            db.execute(
                text("""
                    INSERT INTO stock (key, generic, brand, dosage_form, dose, expiry, unit, stock_qty)
                    VALUES (:key, :generic, :brand, :dosage_form, :dose, :expiry, :unit, :stock_qty)
                    ON CONFLICT (key) DO UPDATE SET
                        stock_qty    = EXCLUDED.stock_qty,
                        expiry       = EXCLUDED.expiry,
                        generic      = EXCLUDED.generic,
                        brand        = EXCLUDED.brand,
                        dosage_form  = EXCLUDED.dosage_form,
                        dose         = EXCLUDED.dose,
                        unit         = EXCLUDED.unit
                """),
                {
                    "key":         str(row.get("key", "")),
                    "generic":     str(row.get("generic", "")),
                    "brand":       str(row.get("brand", "")),
                    "dosage_form": str(row.get("dosage_form", "")),
                    "dose":        str(row.get("dose", "")),
                    "expiry":      row.get("expiry") or None,
                    "unit":        str(row.get("unit", "")),
                    "stock_qty":   int(row.get("stock_qty", 0)),
                },
            )
        db.commit()


# ========================= MAIN ENTRY =========================

def run_app() -> None:
    if not st.session_state.get("logged_in", False):
        st.warning("Please log in from the main page.")
        st.stop()

    role = st.session_state.get("role", "")

    st.title("🏥 Medical Camp EMR System")

    # Load lookup data once per session
    if "icd_df" not in st.session_state:
        with st.spinner("Loading Diagnosis Database..."):
            st.session_state["icd_df"] = _load_icd_diagnosis()

    if "icd_symptoms_df" not in st.session_state:
        with st.spinner("Loading Symptoms Database..."):
            st.session_state["icd_symptoms_df"] = _load_icd_symptoms()

    if "stock_df" not in st.session_state:
        st.session_state["stock_df"] = _load_stock()

    if len(st.session_state.get("icd_df", [])) == 0:
        st.warning("⚠️ ICD Diagnosis data not loaded.")

    # Admin quick controls
    if role == "admin":
        with st.expander("⚠️ Admin Database Controls"):
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🚨 RELOAD STOCK FROM DB"):
                    st.session_state["stock_df"] = _load_stock()
                    st.rerun()
            with c2:
                st.info("Re-reads stock from PostgreSQL.")

    # Role-based navigation
    if role == "admin":
        tabs = ["Patient Entry", "Patient Records", "Pharmacy Dispensation", "Admin"]
    elif role == "doctor":
        tabs = ["Patient Entry", "Patient Records"]
    elif role == "pharmacy":
        tabs = ["Pharmacy Dispensation", "Patient Records"]
    else:
        tabs = ["Patient Entry"]

    selected_page = st.sidebar.radio("📌 Main Menu", tabs)

    if selected_page == "Patient Entry":
        _patient_entry_tab(role)
    elif selected_page == "Patient Records":
        _patient_records_tab(role)
    elif selected_page == "Pharmacy Dispensation":
        _pharmacy_tab()
    elif selected_page == "Admin" and role == "admin":
        _admin_tab()


# ========================= PATIENT ENTRY TAB =========================

def _patient_entry_tab(role: str) -> None:
    st.header("Patient Visit Entry")

    if role == "doctor":
        if st.button("🔄 Refresh Patient List"):
            st.rerun()

    patients_df = pd.read_sql(
        "SELECT patient_id, patient_name, cnic FROM patients ORDER BY patient_id DESC",
        get_engine(),
    )

    patient_options = []
    if role in ["admin", "registration"]:
        patient_options.append("+ Register New Patient")
    for _, r in patients_df.iterrows():
        patient_options.append(f"{int(r['patient_id'])} - {r['patient_name']} ({r['cnic']})")

    if not patient_options:
        st.info("No patients available. Ask registration staff to register a patient first.")
        return

    selected_label = st.selectbox("Select Registered Patient", options=patient_options, index=0)
    registering_new = selected_label == "+ Register New Patient"

    if registering_new and role not in ["admin", "registration"]:
        st.error("Permission denied: Cannot register new patients.")
        st.stop()

    # Patient details section
    st.subheader("Personal Details")
    if registering_new:
        p_name        = st.text_input("Patient Name", key="reg_p_name")
        p_cnic        = st.text_input("CNIC (leave empty if none)", key="reg_p_cnic")
        p_nationality = st.text_input("Nationality", value="Pakistani", key="reg_p_nationality")
        p_address     = st.text_area("Address", key="reg_p_address")
        p_phone       = st.text_input("Phone Number", key="reg_p_phone")
        p_gender      = st.selectbox("Gender", ["", "Male", "Female", "Other"], key="reg_p_gender")
        p_age         = int(st.number_input("Age", min_value=0, max_value=120, step=1, key="reg_p_age"))
        pid           = None
    else:
        pid = int(selected_label.split(" - ")[0])
        row_df = pd.read_sql(
            f"SELECT * FROM patients WHERE patient_id = {pid}",
            get_engine(),
        )
        if row_df.empty:
            st.error("Patient not found.")
            st.stop()
        row = row_df.iloc[0]
        st.text_input("Patient Name", value=row["patient_name"], disabled=True)
        st.text_input("CNIC",         value=row["cnic"],         disabled=True)
        st.text_input("Age",          value=str(row["age"]),     disabled=True)
        p_name        = row["patient_name"]
        p_cnic        = row["cnic"]
        p_nationality = row["nationality"]
        p_address     = row["address"]
        p_phone       = row["phone"]
        p_gender      = row["gender"]
        p_age         = int(row["age"]) if row["age"] is not None else 0

    # Clinical
    st.subheader("Clinical Data")
    doctor_type = st.selectbox(
        "Doctor Type",
        ["General Physician", "Cardiologist", "Pediatrician", "Dermatologist", "Other"],
        key="doctor_type",
    )

    # Vitals
    st.subheader("Vitals")
    c1, c2, c3, c4 = st.columns(4)
    bp_sys     = c1.number_input("BP Sys",     min_value=0, value=0)
    bp_dia     = c2.number_input("BP Dia",     min_value=0, value=0)
    heart_rate = c3.number_input("HR (BPM)",   min_value=0, value=0)
    temp       = c4.number_input("Temp (°C)",  value=36.0)

    c5, c6, c7 = st.columns(3)
    sat_o2        = c5.number_input("O2 Sat %",       min_value=0, max_value=100, value=98)
    rr            = c6.number_input("Resp Rate",       min_value=0, value=0)
    blood_glucose = c7.number_input("Glucose (mg/dL)", min_value=0, value=0)

    patient_history = st.text_area("Patient History / Complaints")

    # Symptoms search
    st.subheader("Symptoms")
    if "selected_symptoms" not in st.session_state:
        st.session_state.selected_symptoms = []

    sym_search = st.text_input("🔍 Search Symptoms (type 3+ letters)", key="sym_search_box")
    sym_options: list = []
    if len(sym_search) >= 3:
        sym_df = st.session_state.get("icd_symptoms_df")
        if sym_df is not None and not sym_df.empty:
            mask = sym_df["Symptom"].str.contains(sym_search, case=False, na=False)
            sym_options = sym_df[mask]["Symptom"].head(20).tolist()

    new_sym = st.selectbox("Select Symptom", [""] + sym_options, key="sym_picker")
    if new_sym and new_sym not in st.session_state.selected_symptoms:
        st.session_state.selected_symptoms.append(new_sym)

    if st.session_state.selected_symptoms:
        st.write("**Selected:**")
        for s in list(st.session_state.selected_symptoms):
            col_a, col_b = st.columns([8, 1])
            col_a.text(s)
            if col_b.button("❌", key=f"del_sym_{s}"):
                st.session_state.selected_symptoms.remove(s)
                st.rerun()

    # Diagnosis search
    st.subheader("Diagnosis (ICD-10)")
    if "selected_diagnosis" not in st.session_state:
        st.session_state.selected_diagnosis = []

    diag_search = st.text_input("🔍 Search Diagnosis (type 3+ letters)", key="diag_search_box")
    diag_options: list = []
    if len(diag_search) >= 3:
        diag_df = st.session_state.get("icd_df")
        if diag_df is not None and not diag_df.empty:
            mask = diag_df["Diagnosis"].str.contains(diag_search, case=False, na=False)
            diag_options = diag_df[mask]["Diagnosis"].head(20).tolist()

    new_diag = st.selectbox("Select Diagnosis", [""] + diag_options, key="diag_picker")
    if new_diag and new_diag not in st.session_state.selected_diagnosis:
        st.session_state.selected_diagnosis.append(new_diag)

    if st.session_state.selected_diagnosis:
        st.write("**Selected:**")
        for d in list(st.session_state.selected_diagnosis):
            col_a, col_b = st.columns([8, 1])
            col_a.text(d)
            if col_b.button("❌", key=f"del_diag_{d}"):
                st.session_state.selected_diagnosis.remove(d)
                st.rerun()

    # Prescription
    st.subheader("Prescription")
    stock_df = st.session_state.get("stock_df", pd.DataFrame())
    num_meds = st.number_input("Number of Medicines", min_value=1, max_value=10, value=1)
    medicines = []

    for i in range(int(num_meds)):
        st.markdown(f"**Medicine {i + 1}**")
        med_options = stock_df["generic"].dropna().unique().tolist() if not stock_df.empty else []
        sel_generic = st.selectbox(f"Medicine {i + 1}", [""] + med_options, key=f"med_{i}")
        if sel_generic:
            med_row = stock_df[stock_df["generic"] == sel_generic].iloc[0]
            c1, c2, c3 = st.columns(3)
            freq     = c1.text_input(f"Frequency {i + 1}", "1+0+1",     key=f"freq_{i}")
            time_day = c2.text_input(f"Timing {i + 1}",   "After Meal", key=f"time_{i}")
            amount   = c3.text_input(f"Days/Qty {i + 1}", "3 Days",     key=f"amt_{i}")
            medicines.append({
                "generic":   med_row["generic"],
                "brand":     med_row["brand"],
                "frequency": freq,
                "time":      time_day,
                "amount":    amount,
            })

    # Save visit
    if st.button("💾 Save Visit", type="primary"):
        if registering_new and not p_name.strip():
            st.error("Patient Name is required.")
            return

        try:
            with get_db() as db:
                if registering_new:
                    cnic_clean = p_cnic.strip().replace("-", "").replace(" ", "")
                    if not cnic_clean or cnic_clean == "0":
                        cnic_clean = f"NO-ID-{random.randint(100000, 999999)}"
                    elif cnic_clean.isdigit() and len(cnic_clean) == 13:
                        cnic_clean = f"{cnic_clean[:5]}-{cnic_clean[5:12]}-{cnic_clean[12:]}"

                    patient = Patient(
                        patient_name=str(p_name).strip(),
                        cnic=cnic_clean,
                        nationality=str(p_nationality).strip() or None,
                        address=str(p_address).strip() or None,
                        phone=str(p_phone).strip() or None,
                        gender=str(p_gender),
                        age=int(p_age),
                    )
                    db.add(patient)
                    db.flush()
                    patient_id = patient.patient_id
                else:
                    patient_id = pid

                med_str = "; ".join(
                    f"{m['generic']} [{m['brand']}] ({m['frequency']}, {m['amount']})"
                    for m in medicines
                )

                visit = Visit(
                    patient_id=patient_id,
                    doctor_type=doctor_type,
                    history=patient_history,
                    bp=f"{bp_sys}/{bp_dia}",
                    heart_rate=int(heart_rate),
                    sat_o2=float(sat_o2),
                    temp=float(temp),
                    rr=int(rr),
                    blood_glucose=float(blood_glucose),
                    gender=str(p_gender),
                    age=int(p_age),
                    symptoms="; ".join(st.session_state.selected_symptoms),
                    indications="; ".join(st.session_state.selected_diagnosis),
                    medicines=med_str,
                    dispensed="No",
                )
                db.add(visit)
                db.commit()

            st.success("✅ Visit Saved Successfully!")
            st.session_state.selected_symptoms = []
            st.session_state.selected_diagnosis = []
            st.rerun()

        except Exception as e:
            st.error(f"Error saving visit: {e}")


# ========================= PATIENT RECORDS TAB =========================

def _patient_records_tab(role: str) -> None:
    st.header("All Patient Records & Analytics")

    if st.button("🔄 Refresh Records"):
        st.rerun()

    try:
        df = pd.read_sql(
            """
            SELECT
                p.patient_id, p.patient_name, p.cnic, p.age, p.gender,
                v.visit_id, v.doctor_type, v.visit_date, v.history,
                v.bp, v.heart_rate, v.symptoms, v.indications,
                v.medicines, v.dispensed, v.dispensed_details
            FROM patients p
            LEFT JOIN visits v ON p.patient_id = v.patient_id
            ORDER BY v.visit_date DESC NULLS LAST, p.patient_id DESC
            """,
            get_engine(),
        )
    except Exception as e:
        st.error(f"Error fetching records: {e}")
        return

    if df.empty:
        st.info("No patients or visits recorded yet.")
        return

    # Analytics dashboard
    with st.expander("📊 Analytics & Dashboard", expanded=False):
        st.subheader("Camp Statistics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Visits",    int(df["visit_id"].dropna().nunique()))
        c2.metric("Unique Patients", int(df["patient_id"].nunique()))
        c3.metric("Total Records",   len(df))

        total_visits = df["visit_id"].dropna().nunique()
        if total_visits > 0:
            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown("**Visits by Doctor Type**")
                st.bar_chart(df["doctor_type"].value_counts())
            with col_b:
                st.markdown("**Age Distribution**")
                bins   = [0, 10, 20, 30, 40, 50, 60, 120]
                labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "51-60", "60+"]
                age_groups = (
                    pd.cut(df["age"].fillna(0), bins=bins, labels=labels, right=False)
                    .value_counts()
                    .sort_index()
                )
                st.bar_chart(age_groups)
            with col_c:
                st.markdown("**Gender Distribution**")
                st.bar_chart(df["gender"].fillna("Unknown").value_counts())

            st.markdown("---")
            st.markdown("**Top Medical Trends**")
            c_sym, c_diag, c_med = st.columns(3)

            sym_list  = [s.strip() for sub in df["symptoms"].dropna().str.split(";")   for s in sub if s.strip()]
            diag_list = [i.strip() for sub in df["indications"].dropna().str.split(";") for i in sub if i.strip()]
            med_list  = []
            for m_str in df["medicines"].dropna():
                for m in m_str.split(";"):
                    m = m.strip()
                    if m:
                        med_list.append(m.split("[")[0].strip() if "[" in m else m)

            with c_sym:
                st.caption("Most Common Symptoms")
                st.dataframe(pd.Series(sym_list).value_counts().head(5), use_container_width=True)
            with c_diag:
                st.caption("Most Common Diagnoses")
                st.dataframe(pd.Series(diag_list).value_counts().head(5), use_container_width=True)
            with c_med:
                st.caption("Most Prescribed Medicines")
                st.dataframe(pd.Series(med_list).value_counts().head(5), use_container_width=True)

    # Print records
    st.write("---")
    with st.expander("🖨️ Print Records", expanded=False):
        print_mode = st.selectbox(
            "Select Print Mode:",
            ["None", "Print Specific Visit", "Print Entire Database"],
            key="print_mode_selector",
        )

        if print_mode == "Print Specific Visit":
            valid_visits = df["visit_id"].dropna().unique().astype(int).astype(str).tolist()
            selected_v   = st.selectbox("Select Visit ID", [""] + valid_visits, key="specific_visit_selector")

            if selected_v:
                v = df[df["visit_id"] == int(selected_v)].iloc[0]
                html_receipt = f"""
                <div style="max-width:800px;margin:0 auto;background:white;color:black;
                            padding:20px;font-family:Arial,sans-serif;">
                    <h2 style="text-align:center;border-bottom:2px solid #333;
                               padding-bottom:10px;">Medical Camp - Patient Record</h2>
                    <table style="width:100%;font-size:14px;">
                        <tr>
                            <td><strong>Visit ID:</strong> {v['visit_id']}</td>
                            <td style="text-align:right;"><strong>Date:</strong> {v['visit_date']}</td>
                        </tr>
                        <tr>
                            <td><strong>Patient:</strong> {v['patient_name']} (ID: {v['patient_id']})</td>
                            <td style="text-align:right;"><strong>Doctor:</strong> {v['doctor_type']}</td>
                        </tr>
                        <tr>
                            <td><strong>Age / Gender:</strong> {v['age']} / {v['gender']}</td>
                            <td></td>
                        </tr>
                    </table>
                    <br>
                    <h3>Clinical Information</h3>
                    <p><strong>Vitals:</strong> BP: {v['bp']} &nbsp;|&nbsp; HR: {v['heart_rate']}</p>
                    <p><strong>History / Complaints:</strong> {v['history']}</p>
                    <p><strong>Symptoms:</strong> {v['symptoms']}</p>
                    <p><strong>Diagnosis:</strong> {v['indications']}</p>
                    <br>
                    <h3>Prescription (Rx)</h3>
                    <p style="line-height:1.6;">{str(v['medicines']).replace(';', '<br>')}</p>
                    <br><br>
                    <p style="text-align:right;border-top:1px solid #000;
                               display:inline-block;float:right;padding-top:5px;">
                        Doctor's Signature
                    </p>
                    <div style="clear:both;"></div>
                </div>
                """
                st.markdown("### 📄 Visual Preview")
                components.html(html_receipt, height=450, scrolling=True)
                printable = (
                    f"<html><head><title>Print Visit {v['visit_id']}</title></head>"
                    f"<body onload='window.print()'>{html_receipt}</body></html>"
                )
                st.download_button(
                    "🖨️ Download & Print",
                    data=printable,
                    file_name=f"visit_{selected_v}.html",
                    mime="text/html",
                    type="primary",
                    key="download_visit_btn",
                )
                st.info("💡 Click the button above. The downloaded file will auto-open your print dialog.")

        elif print_mode == "Print Entire Database":
            clean_df   = df.drop(columns=["dispensed_details"], errors="ignore")
            html_table = f"""
            <div style="background:white;color:black;padding:20px;font-family:Arial,sans-serif;">
                <h2 style="text-align:center;">Full Medical Camp Patient Records</h2>
                <p style="text-align:center;">
                    Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                </p>
                {clean_df.to_html(index=False, border=1)}
            </div>
            """
            st.markdown("### 📄 Visual Preview")
            components.html(html_table, height=450, scrolling=True)
            printable = (
                f"<html><head><title>All Records</title></head>"
                f"<body onload='window.print()'>{html_table}</body></html>"
            )
            st.download_button(
                "🖨️ Download & Print All Records",
                data=printable,
                file_name="All_Patient_Records.html",
                mime="text/html",
                type="primary",
                key="download_all_btn",
            )
            st.info("💡 Click the button above to download the printable records file.")

    # Records table
    st.write("---")
    st.markdown("### Record Table")
    st.dataframe(df, use_container_width=True)

    # Record management (admin / doctor only)
    if role in ["admin", "doctor"]:
        st.write("---")
        st.subheader("Manage Records")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("##### 🗑️ Delete Specific Visit")
            if "visit_id" in df.columns and df["visit_id"].notna().any():
                valid_visits = df["visit_id"].dropna().unique().astype(int).astype(str).tolist()
                del_visit    = st.selectbox("Select Visit ID", [""] + valid_visits, key="delete_visit_select")
                if st.button("Confirm Delete Visit", type="primary", key="del_visit_btn"):
                    if del_visit:
                        with get_db() as db:
                            db.execute(text("DELETE FROM visits WHERE visit_id = :vid"), {"vid": int(del_visit)})
                            db.commit()
                        st.success(f"✅ Visit {del_visit} deleted.")
                        st.rerun()
                    else:
                        st.warning("Select a Visit ID first.")
            else:
                st.info("No visits to delete.")

        with c2:
            st.markdown("##### 🧹 Delete Patient (and all their visits)")
            all_patients = df["patient_id"].dropna().unique().astype(int).astype(str).tolist()
            del_patient  = st.selectbox("Select Patient ID", [""] + all_patients, key="delete_patient_select")
            if st.button("Confirm Delete Patient", type="primary", key="del_patient_btn"):
                if del_patient:
                    with get_db() as db:
                        db.execute(text("DELETE FROM visits  WHERE patient_id = :pid"), {"pid": int(del_patient)})
                        db.execute(text("DELETE FROM patients WHERE patient_id = :pid"), {"pid": int(del_patient)})
                        db.commit()
                    st.success(f"✅ Patient {del_patient} and all their visits deleted.")
                    st.rerun()
                else:
                    st.warning("Select a Patient ID first.")


# ========================= PHARMACY TAB =========================

def _pharmacy_tab() -> None:
    st.header("Pharmacy Dispensation")

    if st.button("🔄 Refresh Stock from DB"):
        st.session_state["stock_df"] = _load_stock()
        st.success("Stock refreshed.")

    if "stock_df" not in st.session_state:
        st.session_state["stock_df"] = _load_stock()
    stock_df = st.session_state["stock_df"]

    patients_df = pd.read_sql(
        "SELECT patient_id, patient_name FROM patients ORDER BY patient_id DESC",
        get_engine(),
    )

    if patients_df.empty:
        st.info("No patients found. Register a patient first.")
        return

    patient_labels = [
        f"{row['patient_id']} - {row['patient_name']}"
        for _, row in patients_df.iterrows()
    ]
    selected_patient_label = st.selectbox(
        "Select Patient to Dispense For",
        [""] + patient_labels,
        key="pharmacy_patient_selector",
    )

    if not selected_patient_label:
        return

    selected_patient_id = int(selected_patient_label.split(" - ")[0])

    visits_df = pd.read_sql(
        f"SELECT visit_id, visit_date, doctor_type, medicines, dispensed "
        f"FROM visits WHERE patient_id = {selected_patient_id} ORDER BY visit_date DESC",
        get_engine(),
    )

    if visits_df.empty:
        st.info("No visits found for this patient.")
        return

    filter_mode = st.radio(
        "Show visits:",
        ["Pending (not dispensed)", "All", "Dispensed"],
        index=0,
        horizontal=True,
        key="pharmacy_filter_radio",
    )

    if filter_mode == "Pending (not dispensed)":
        view_df = visits_df[visits_df["dispensed"].fillna("No") != "Yes"]
    elif filter_mode == "Dispensed":
        view_df = visits_df[visits_df["dispensed"].fillna("No") == "Yes"]
    else:
        view_df = visits_df

    if view_df.empty:
        st.warning("No visits match this filter.")
        return

    visit_options = [
        f"{int(r.visit_id)} — {r.visit_date} ({r.doctor_type})"
        for r in view_df.itertuples()
    ]
    selected_visit_label = st.selectbox(
        "Select Visit", [""] + visit_options, key="pharmacy_visit_selector"
    )

    if not selected_visit_label:
        return

    visit_id  = int(selected_visit_label.split(" — ")[0])
    visit_row = view_df[view_df["visit_id"] == visit_id].iloc[0]

    raw_meds = str(visit_row.get("medicines", "")).split(";")
    st.subheader(f"Dispensing for Visit ID: {visit_id}")
    st.write(f"**Doctor:** {visit_row['doctor_type']}")

    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
    c1.markdown("**Medicine**")
    c2.markdown("**Brand**")
    c3.markdown("**Stock**")
    c4.markdown("**Prescribed**")
    c5.markdown("**Dispense Qty**")
    st.divider()

    dispense_plan = []
    for i, raw in enumerate(raw_meds):
        med_text = raw.strip()
        if not med_text:
            continue

        brand_match  = re.search(r"\[([^\]]+)\]", med_text)
        brand        = brand_match.group(1).strip() if brand_match else ""
        generic      = med_text.split("[")[0].strip()
        generic_norm = generic.lower()

        possible = stock_df[stock_df["generic"].str.lower() == generic_norm]
        brand_options = possible["brand"].unique().tolist()

        selected_brand = brand
        if brand_options:
            default_ix     = brand_options.index(brand) if brand in brand_options else 0
            selected_brand = st.selectbox(
                f"Brand for {generic}",
                options=brand_options,
                index=default_ix,
                key=f"br_{visit_id}_{i}",
                label_visibility="collapsed",
            )

        matched   = stock_df[
            (stock_df["generic"].str.strip().str.lower() == generic_norm)
            & (stock_df["brand"].str.strip().str.lower() == selected_brand.lower())
        ]
        stock_qty = int(matched.iloc[0]["stock_qty"]) if not matched.empty else 0

        prescribed_match   = re.search(r"\(([^)]*)\)", med_text)
        prescribed_details = prescribed_match.group(1) if prescribed_match else ""

        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
        c1.write(generic)
        c2.write(selected_brand)
        c3.write(stock_qty)
        c4.caption(prescribed_details)
        with c5:
            qty_to_dispense = st.number_input(
                "Qty",
                min_value=0,
                max_value=max(stock_qty, 0),
                value=0,
                step=1,
                key=f"qty_{visit_id}_{i}",
                label_visibility="collapsed",
            )

        dispense_plan.append({
            "display":       f"{generic} [{selected_brand}]",
            "generic":       generic,
            "brand":         selected_brand,
            "dispense_qty":  int(qty_to_dispense),
            "matched_index": matched.index[0] if not matched.empty else None,
        })
        st.divider()

    if st.button("✅ Confirm Dispensation", type="primary"):
        to_dispense = [d for d in dispense_plan if d["dispense_qty"] > 0]
        if not to_dispense:
            st.error("Enter quantity > 0 for at least one medicine.")
            return

        dispensed_summary = []
        try:
            for d in to_dispense:
                if d["matched_index"] is not None:
                    item_key = stock_df.at[d["matched_index"], "key"]
                    _deduct_stock_atomic(item_key, d["dispense_qty"])
                    dispensed_summary.append(f"{d['display']} (Qty: {d['dispense_qty']})")
                else:
                    st.error(f"Stock key not found for {d['display']}")

            with get_db() as db:
                db.execute(
                    text("UPDATE visits SET dispensed = 'Yes', dispensed_details = :details WHERE visit_id = :vid"),
                    {"details": "; ".join(dispensed_summary), "vid": visit_id},
                )
                db.commit()

            st.session_state["stock_df"] = _load_stock()
            st.success("✅ Dispensation saved! Inventory updated.")
            st.rerun()

        except Exception as e:
            st.error(f"Error saving dispensation: {e}")


# ========================= ADMIN TAB =========================

def _admin_tab() -> None:
    st.subheader("Admin Controls")

    st.markdown("#### 📄 Download CSV Template")
    template_csv = _stock_csv_template()
    st.download_button(
        "📥 Download Standard Stock CSV Template",
        data=template_csv,
        file_name="stock_template.csv",
        mime="text/csv",
    )
    st.caption("Columns: key, generic, brand, dosage_form, dose, expiry, unit, stock_qty")

    st.markdown("---")
    st.markdown("#### 📦 Upload Standard Stock CSV")
    uploaded = st.file_uploader("Upload stock CSV (standard format)", type=["csv"], key="std_csv")
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.dataframe(df.head(), use_container_width=True)
            required = {"key", "generic", "brand", "dosage_form", "dose", "expiry", "unit", "stock_qty"}
            missing  = required - set(df.columns)
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                if st.button("📤 Import to Database"):
                    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce").dt.date
                    _upsert_stock(df)
                    st.session_state["stock_df"] = _load_stock()
                    st.success(f"✅ Imported {len(df)} stock items.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    st.markdown("---")
    st.markdown("#### 🗑️ Clear All Stock Data")
    with st.container():
        clear_password = st.text_input(
            "Enter admin password to clear all stock",
            type="password",
            key="clear_stock_pw",
        )
        if st.button("⚠️ DELETE ALL STOCK", type="primary", key="clear_stock_btn"):
            if clear_password != "secret":
                st.error("Incorrect password. Action denied.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("DELETE FROM stock"))
                        db.commit()
                    st.session_state["stock_df"] = _load_stock()
                    st.success("✅ All stock data cleared.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing stock: {e}")

    st.markdown("---")
    st.markdown("#### 📥 Export All Stock Data")
    col_dl1, col_dl2 = st.columns([2, 6])
    with col_dl1:
        stock_df_dl = _load_stock()
        if not stock_df_dl.empty:
            csv_data = stock_df_dl.to_csv(index=False).encode("utf-8")
            st.download_button(
                "💾 Download All Stock as CSV",
                data=csv_data,
                file_name="all_stock_data.csv",
                mime="text/csv",
                key="download_stock_csv",
                type="primary",
            )
        else:
            st.info("No stock data available to download.")
    with col_dl2:
        st.caption("Exports the full stock table from the database as a CSV file.")

    st.markdown("---")
    st.markdown("#### 📊 Current Stock")
    stock_df = _load_stock()
    if stock_df.empty:
        st.info("No stock loaded yet.")
    else:
        st.dataframe(stock_df, use_container_width=True)
