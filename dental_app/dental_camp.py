"""
Dental Camp Module — Medical Camp EMR
SQLAlchemy + PostgreSQL implementation
"""
import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from database import get_db, get_engine, DentalVisit

# Cache patient data to prevent page reloading on input
@st.cache_data(ttl=300)  # Cache for 5 minutes
def _get_patients_df():
    """Fetch patient list with caching to prevent reruns."""
    return pd.read_sql(
        "SELECT patient_id, patient_name, age, gender FROM patients ORDER BY patient_id DESC",
        get_engine(),
    )

IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dental_images")


def _ensure_image_folder() -> None:
    os.makedirs(IMAGE_FOLDER, exist_ok=True)


def _save_image(uploaded_file, patient_id: int, tag: str) -> str | None:
    """Save uploaded image to disk; return filename or None."""
    if uploaded_file is None:
        return None
    _ensure_image_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"P_{patient_id}_{tag}_{timestamp}.jpg"
    filepath  = os.path.join(IMAGE_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filename


def _yn(val: bool) -> str:
    return "Yes" if val else "No"


# ========================= MAIN ENTRY =========================

def run_dental_app() -> None:
    if not st.session_state.get("logged_in", False):
        st.warning("Please log in from the main page.")
        st.stop()

    st.title("🦷 Dental Camp Module")

    tab1, tab2 = st.tabs(["Dental Assessment", "View Records"])

    with tab1:
        _assessment_tab()

    with tab2:
        _records_tab()


# ========================= ASSESSMENT TAB =========================

def _assessment_tab() -> None:
    st.subheader("New Dental Visit")

    patients_df = _get_patients_df()  # Use cached function

    if patients_df.empty:
        st.info("No patients registered. Register patients via the main EMR app first.")
        return

    patient_list = [
        f"{row['patient_id']} - {row['patient_name']}"
        for _, row in patients_df.iterrows()
    ]
    selected_patient = st.selectbox("Select Patient", [""] + patient_list)

    if not selected_patient:
        return

    pid    = int(selected_patient.split(" - ")[0])
    p_data = patients_df[patients_df["patient_id"] == pid].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.info(f"Name: {p_data['patient_name']}")
    c2.info(f"Age: {p_data['age']}")
    c3.info(f"Gender: {p_data['gender']}")

    # Wrap all form inputs in st.form() to prevent constant reruns
    with st.form(key=f"dental_form_{pid}", clear_on_submit=False):

        # 1. History & Complaints
        st.markdown("### 1. History & Complaints")
        col_a, col_b = st.columns(2)
        pc  = col_a.text_area("Presenting Complaint",             key=f"pc_{pid}")
        hpc = col_b.text_area("History of Presenting Complaint",  key=f"hpc_{pid}")
        st.markdown("---")

        # 2. Dental History
        st.markdown("### 2. Dental History")
        dh_cols    = st.columns(5)
        la_exp     = dh_cols[0].checkbox("LA Experience?", key=f"la_{pid}")
        scaling    = dh_cols[1].checkbox("Scaling?",       key=f"sc_{pid}")
        filling    = dh_cols[2].checkbox("Filling/RCT?",   key=f"fl_{pid}")
        extract    = dh_cols[3].checkbox("Extraction?",    key=f"ex_{pid}")
        prosthesis = dh_cols[4].checkbox("Prosthesis?",    key=f"pr_{pid}")
        st.markdown("---")

        # 3. Habits & Brushing
        st.markdown("### 3. Habits & Brushing")
        h_cols = st.columns(6)
        habits = {
            "Smoking": h_cols[0].checkbox("Smoking",   key=f"h_sm_{pid}"),
            "Gutkha":  h_cols[1].checkbox("Gutkha",    key=f"h_gu_{pid}"),
            "Naswar":  h_cols[2].checkbox("Naswar",     key=f"h_na_{pid}"),
            "Pan":     h_cols[3].checkbox("Pan/Betel",  key=f"h_pa_{pid}"),
            "Mauva":   h_cols[4].checkbox("Mauva",      key=f"h_ma_{pid}"),
            "Alcohol": h_cols[5].checkbox("Alcohol",    key=f"h_al_{pid}"),
        }

        b_cols     = st.columns(3)
        brush_type = b_cols[0].selectbox("Brushing Type", ["Nil", "Finger", "Miswak", "Brush"],          key=f"b_type_{pid}")
        brush_freq = b_cols[1].selectbox("Frequency",     ["OD (Once)", "BD (Twice)", "TDS (Thrice)"],    key=f"b_freq_{pid}")
        brush_time = b_cols[2].selectbox("Timing",        ["Morning", "Night", "Both"],                   key=f"b_time_{pid}")
        st.markdown("---")

        # 4. Medical Alert
        st.markdown("### 4. Medical Alert")
        med_conditions = [
            "Diabetes", "Hypertension (BP)", "Heart Disease", "Asthma",
            "Hepatitis", "Bleeding Disorder", "Pregnancy", "Allergies",
        ]
        selected_meds = st.multiselect("Select Positive Findings", med_conditions, key=f"meds_{pid}")
        st.markdown("---")

        # 5. Dentition Chart
        st.markdown("### 5. Dentition Status (Tooth Chart)")
        tooth_codes = ["Healthy", "Decayed (D)", "Filled (F)", "Mobile (M)", "BDR", "Missing"]

        st.write("**Upper Right (11–18)**")
        cols_ur  = st.columns(8)
        ur_status = {
            str(t): cols_ur[i].selectbox(str(t), tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed")
            for i, t in enumerate(range(18, 10, -1))
        }

        st.write("**Upper Left (21–28)**")
        cols_ul  = st.columns(8)
        ul_status = {
            str(t): cols_ul[i].selectbox(str(t), tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed")
            for i, t in enumerate(range(21, 29))
        }

        st.write("**Lower Left (31–38)**")
        cols_ll  = st.columns(8)
        ll_status = {
            str(t): cols_ll[i].selectbox(str(t), tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed")
            for i, t in enumerate(range(31, 39))
        }

        st.write("**Lower Right (41–48)**")
        cols_lr  = st.columns(8)
        lr_status = {
            str(t): cols_lr[i].selectbox(str(t), tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed")
            for i, t in enumerate(range(48, 40, -1))
        }
        st.markdown("---")

        # 6. Clinical Pictures
        st.markdown("### 6. Clinical Pictures")
        cam1, cam2 = st.columns(2)
        with cam1:
            st.write("**📸 Pre-Op Picture**")
            pre_img = st.camera_input("Take Pre-Op Photo", key=f"cam_pre_{pid}")
        with cam2:
            st.write("**📸 Post-Op Picture**")
            post_img = st.camera_input("Take Post-Op Photo", key=f"cam_post_{pid}")
        st.markdown("---")

        # 7. Diagnosis & Prescription
        st.markdown("### 7. Diagnosis & Prescription")
        prov_diag = st.text_input("Provisional Diagnosis", key=f"diag_{pid}")
        st.markdown("**Write Prescriptions**")

        num_meds = st.number_input("Number of Medicines", min_value=1, max_value=10, value=1, key=f"num_meds_{pid}")
        med_list = []
        for i in range(int(num_meds)):
            c1, c2   = st.columns([3, 2])
            m_name   = c1.text_input(f"Medicine Name {i + 1}",  placeholder="e.g. Amoxil 500mg", key=f"d_med_{i}_{pid}")
            m_instr  = c2.text_input(f"Dosage/Instr {i + 1}",   value="1+0+1, 3 Days",             key=f"d_ins_{i}_{pid}")
            if m_name:
                med_list.append(f"{m_name} ({m_instr})")

        st.write("---")
        
        submit_btn = st.form_submit_button("💾 Save Dental Visit", type="primary", use_container_width=True)
    
    # Process form submission
    if submit_btn:
        pre_filename  = _save_image(pre_img,  pid, "PreOp")
        post_filename = _save_image(post_img, pid, "PostOp")

        full_chart  = {**ur_status, **ul_status, **ll_status, **lr_status}
        chart_data  = {k: v for k, v in full_chart.items() if v != "Healthy"}
        chart_json  = json.dumps(chart_data)
        meds_str    = "; ".join(med_list)
        med_hist_str = ", ".join(selected_meds)

        try:
            with get_db() as db:
                dental_visit = DentalVisit(
                    patient_id            = pid,
                    doctor_name           = "Dentist",
                    presenting_complaint  = pc,
                    history_complaint     = hpc,
                    la_experience         = _yn(la_exp),
                    scaling               = _yn(scaling),
                    filling_rct           = _yn(filling),
                    extraction            = _yn(extract),
                    prosthesis            = _yn(prosthesis),
                    smoking               = _yn(habits["Smoking"]),
                    gutkha                = _yn(habits["Gutkha"]),
                    naswar                = _yn(habits["Naswar"]),
                    pan                   = _yn(habits["Pan"]),
                    mauva                 = _yn(habits["Mauva"]),
                    alcohol               = _yn(habits["Alcohol"]),
                    brushing_type         = brush_type,
                    brushing_freq         = brush_freq,
                    brushing_timing       = brush_time,
                    medical_history_notes = med_hist_str,
                    dentition_status      = chart_json,
                    provisional_diagnosis = prov_diag,
                    medicines             = meds_str,
                    dispensed             = "No",
                    pre_op_image          = pre_filename,
                    post_op_image         = post_filename,
                )
                db.add(dental_visit)
                db.commit()
            st.success("✅ Dental Visit & Images Saved Successfully!")
        except Exception as e:
            st.error(f"Error saving: {e}")


# ========================= RECORDS TAB =========================

def _records_tab() -> None:
    st.header("Dental Records")

    col1, col2 = st.columns([1, 3])
    if col1.button("🔄 Refresh List"):
        st.rerun()

    try:
        summary_df = pd.read_sql(
            """
            SELECT d.visit_id, p.patient_name, p.age, p.gender,
                   d.visit_date, d.provisional_diagnosis
            FROM dental_visits d
            JOIN patients p ON d.patient_id = p.patient_id
            ORDER BY d.visit_date DESC
            """,
            get_engine(),
        )
    except Exception as e:
        st.error(f"Error loading records: {e}")
        return

    st.dataframe(summary_df, use_container_width=True)

    # Export
    st.write("---")
    try:
        full_df = pd.read_sql(
            """
            SELECT d.*, p.patient_name, p.age, p.gender, p.cnic
            FROM dental_visits d
            JOIN patients p ON d.patient_id = p.patient_id
            ORDER BY d.visit_date DESC
            """,
            get_engine(),
        )
        csv = full_df.to_csv(index=False).encode("utf-8")
        col2.download_button(
            label="📥 Download Complete Records (CSV)",
            data=csv,
            file_name="dental_camp_full_data.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error loading full records: {e}")

    # Detail view
    st.write("---")
    st.subheader("🔍 View Full Case Detail")

    if summary_df.empty:
        st.info("No dental records yet.")
        return

    visit_ids = summary_df["visit_id"].tolist()
    selected_vid = st.selectbox(
        "Select Visit ID to view details",
        [""] + [str(v) for v in visit_ids],
    )

    if not selected_vid:
        return

    try:
        detail_df = pd.read_sql(
            f"SELECT * FROM dental_visits WHERE visit_id = {int(selected_vid)}",
            get_engine(),
        )
    except Exception as e:
        st.error(f"Error loading visit detail: {e}")
        return

    if detail_df.empty:
        return

    row = detail_df.iloc[0]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Clinical Info")
        st.info(f"**PC:** {row['presenting_complaint']}\n\n**History:** {row['history_complaint']}")
        st.warning(f"**Medical Alert:** {row['medical_history_notes']}")

        st.markdown("#### Clinical Images")
        i1, i2 = st.columns(2)
        if row["pre_op_image"]:
            pre_path = os.path.join(IMAGE_FOLDER, row["pre_op_image"])
            if os.path.exists(pre_path):
                i1.image(pre_path, caption="Pre-Op")
            else:
                i1.write("Image file not found")
        else:
            i1.write("No Pre-Op Image")

        if row["post_op_image"]:
            post_path = os.path.join(IMAGE_FOLDER, row["post_op_image"])
            if os.path.exists(post_path):
                i2.image(post_path, caption="Post-Op")
            else:
                i2.write("Image file not found")
        else:
            i2.write("No Post-Op Image")

    with c2:
        st.markdown("#### Habits & Findings")
        habits_found = [
            h.capitalize()
            for h in ["smoking", "gutkha", "naswar", "pan", "mauva", "alcohol"]
            if row.get(h) == "Yes"
        ]
        st.write("**Habits:** " + (", ".join(habits_found) if habits_found else "None"))
        st.write(f"**Brushing:** {row['brushing_type']} ({row['brushing_freq']}, {row['brushing_timing']})")

        st.markdown("#### 🦷 Dentition")
        try:
            teeth_data = json.loads(row["dentition_status"] or "{}")
            if not teeth_data:
                st.write("No issues recorded.")
            else:
                t_cols = st.columns(3)
                for i, (tooth, status) in enumerate(teeth_data.items()):
                    t_cols[i % 3].error(f"**#{tooth}**: {status}")
        except Exception:
            st.write("Error reading dentition chart.")

    st.markdown("---")
    st.success(f"**Diagnosis:** {row['provisional_diagnosis']}")
    st.write(f"**Prescription:** {row['medicines']}")
