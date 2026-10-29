import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, time, date
import uuid

# ---------------------------------------------------------
# Page Configuration & Global Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="PiVector TUR Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root {
        --pv-teal: #00c49f;
        --pv-dark: #0f172a;
    }
    .badge-ch {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-ph {
        background-color: #fef3c7;
        color: #b45309;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-clt {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    /* Responsive HTML Table with Multiline Text Auto-Wrapping */
    .tur-table-container {
        width: 100%;
        overflow-x: auto;
        margin-top: 12px;
        margin-bottom: 24px;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .tur-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 0.88rem;
        background-color: #ffffff;
    }
    .tur-table th {
        background-color: #0f172a;
        color: #f8fafc;
        text-align: left;
        padding: 10px 14px;
        font-weight: 600;
        border-bottom: 2px solid #cbd5e1;
        white-space: nowrap;
    }
    .tur-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
        color: #1e293b;
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        line-height: 1.45;
    }
    .tur-table tr:nth-child(even) {
        background-color: #f8fafc;
    }
    .tur-table tr:hover {
        background-color: #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def render_wrapped_table(df):
    """Renders a fully responsive HTML table with multiline auto-wrapping."""
    if df.empty:
        st.info("No records to display.")
        return
    
    df_display = df.copy()
    df_display.index = range(1, len(df_display) + 1)
    df_display.index.name = "S.No."
    
    html = df_display.to_html(classes="tur-table", escape=False)
    st.markdown(f'<div class="tur-table-container">{html}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Google Sheets Connection & Data Fetchers
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

EXPECTED_LOG_COLS = [
    "Entry ID", "Timestamp", "Cluster Head Email", "Cluster Head Name",
    "Activity Date", "Activity Category", "Specific Task / Description",
    "Start Time", "End Time", "Duration (Hours)", "Outcome / Deliverable",
    "Status / Verification", "Role"
]

def get_users_directory():
    try:
        df = conn.read(worksheet="Users_Directory", ttl="0m")
        if df is not None and not df.empty:
            df["Email"] = df["Email"].astype(str).str.strip().str.lower()
            df["PIN"] = (
                df["PIN"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
                .apply(lambda p: p.zfill(4) if p.isdigit() and len(p) < 4 else p)
            )
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["Email", "PIN", "Name", "Role", "Program / Pod Name", "Reporting To Email"])

def get_logs():
    try:
        df = conn.read(worksheet="TUR_Logs", ttl="0m")
        if df is not None and not df.empty and "Activity Date" in df.columns:
            df = df.dropna(how="all")
            df["Activity Date"] = pd.to_datetime(df["Activity Date"], errors="coerce").dt.date
            df["Duration (Hours)"] = pd.to_numeric(df["Duration (Hours)"], errors="coerce").fillna(0.0)
            return df
        return pd.DataFrame(columns=EXPECTED_LOG_COLS)
    except Exception as e:
        st.error(f"Error fetching logs: {e}")
        return pd.DataFrame(columns=EXPECTED_LOG_COLS)

@st.cache_data(ttl=300)
def get_categories_for_role(role_name):
    try:
        df = conn.read(worksheet="Activity_Taxonomy", ttl="5m")
        if df is not None and not df.empty:
            matched = df[df["Role"].str.lower() == role_name.lower()]
            if not matched.empty:
                return matched["Category"].dropna().tolist()
    except Exception:
        pass
    if role_name == "Program Head":
        return [
            "Program Oversight",
            "Cluster Oversight",
            "Tutor Reviews",
            "Student Reviews"
        ]
    return [
        "Pedagogy Training",
        "Classi Training",
        "HW Session Training",
        "Demo Class Prep",
        "Student Review",
        "Class Audit",
        "New Initiatives",
        "Other Leadership Responsibilities"
    ]

# ---------------------------------------------------------
# Session State Setup
# ---------------------------------------------------------
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "show_pin_change" not in st.session_state:
    st.session_state.show_pin_change = False

users_df = get_users_directory()

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
try:
    st.sidebar.image("PiVector-logo2.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("## **⚡ PiVector**")

st.sidebar.markdown("### **Time Utility Report (TUR)**")

if st.session_state.authenticated_user:
    curr_user = st.session_state.authenticated_user
    st.sidebar.markdown("---")
    st.sidebar.write(f"Logged in as: **{curr_user['Name']}**")
    
    role = curr_user["Role"]
    if role == "Core Leadership":
        st.sidebar.markdown('<span class="badge-clt">Core Leadership</span>', unsafe_allow_html=True)
    elif role == "Program Head":
        st.sidebar.markdown('<span class="badge-ph">Program Head</span>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<span class="badge-ch">Cluster Head</span>', unsafe_allow_html=True)

    if curr_user.get("Program / Pod Name"):
        st.sidebar.caption(f"Track: **{curr_user['Program / Pod Name']}**")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔑 Change My PIN", use_container_width=True):
        st.session_state.show_pin_change = not st.session_state.show_pin_change
        st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated_user = None
        st.session_state.show_pin_change = False
        st.rerun()

# ---------------------------------------------------------
# Gatekeeper Authentication Check
# ---------------------------------------------------------
if not st.session_state.authenticated_user:
    st.title("⚡ PiVector TUR Access Portal")
    st.caption("Secure enterprise gateway for Cluster Heads, Program Leads & Leadership")

    with st.container():
        login_col1, login_col2 = st.columns([2, 1])
        with login_col1:
            entered_email = st.text_input("Work Email Address", placeholder="e.g. pallavi.gupta@pivector.in").strip().lower()
            entered_pin = st.text_input("4-Digit Access PIN", type="password", max_chars=4, placeholder="••••").strip()
            login_btn = st.button("Authenticate & Enter ➔", use_container_width=True)

        if login_btn:
            if not entered_email or not entered_pin:
                st.warning("Please enter both your work email and 4-digit PIN.")
            else:
                fresh_users = get_users_directory()
                norm_entered_pin = entered_pin.zfill(4) if entered_pin.isdigit() and len(entered_pin) < 4 else entered_pin
                user_match = fresh_users[
                    (fresh_users["Email"] == entered_email) & 
                    (fresh_users["PIN"] == norm_entered_pin)
                ]
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    st.session_state.authenticated_user = user_data
                    st.rerun()
                else:
                    st.error("Invalid email or PIN. Please check your credentials.")
    st.stop()

# ---------------------------------------------------------
# Active Authenticated Session & Forced PIN Reset Check
# ---------------------------------------------------------
curr_user = st.session_state.authenticated_user
user_role = curr_user["Role"]
user_email = curr_user["Email"]
user_name = curr_user["Name"]
user_pod = curr_user.get("Program / Pod Name", "")
current_pin = str(curr_user.get("PIN", "")).strip()

is_default_pin = (current_pin == "1234")
if is_default_pin or st.session_state.show_pin_change:
    st.warning("🔒 Security Setup: Update Your 4-Digit PIN" if is_default_pin else "🔑 Update Your 4-Digit PIN")
    st.info("To protect your account and logs, choose a private 4-digit PIN that only you know.")

    with st.form("pin_reset_form"):
        new_pin = st.text_input("New 4-Digit PIN", type="password", max_chars=4, placeholder="4 digits")
        confirm_pin = st.text_input("Confirm New PIN", type="password", max_chars=4, placeholder="Confirm 4 digits")
        save_pin_btn = st.form_submit_button("Save New PIN ➔", use_container_width=True)

        if save_pin_btn:
            if not new_pin.isdigit() or len(new_pin) != 4:
                st.error("PIN must be exactly 4 numerical digits.")
            elif new_pin == "1234":
                st.error("You cannot reuse the default PIN '1234'. Choose a unique PIN.")
            elif new_pin != confirm_pin:
                st.error("New PIN and Confirm PIN do not match.")
            else:
                all_u = get_users_directory()
                idx_matches = all_u[all_u["Email"] == user_email].index
                if not idx_matches.empty:
                    pin_str = str(new_pin).zfill(4)
                    all_u.at[idx_matches[0], "PIN"] = pin_str
                    conn.update(worksheet="Users_Directory", data=all_u)
                    st.session_state.authenticated_user["PIN"] = pin_str
                    st.session_state.show_pin_change = False
                    st.success("Your PIN has been updated securely!")
                    st.rerun()

    if is_default_pin:
        st.stop()

# =========================================================
# TIER 1: CLUSTER HEAD (Logger + Soft-Delete / Edit)
# =========================================================
if user_role == "Cluster Head":
    st.title("⚡ Cluster Head Daily TUR")
    st.caption(f"Logged in: **{user_name}** | Track: **{user_pod}**")

    categories = get_categories_for_role("Cluster Head")
    all_logs = get_logs()

    active_date = st.date_input("Activity Date", value=date.today())

    if not all_logs.empty and "Cluster Head Email" in all_logs.columns:
        my_logs = all_logs[
            (all_logs["Cluster Head Email"].astype(str).str.strip().str.lower() == user_email) &
            (all_logs.get("Status / Verification", "") != "Deleted by User")
        ].copy()
    else:
        my_logs = pd.DataFrame(columns=EXPECTED_LOG_COLS)

    today_logs = my_logs[my_logs["Activity Date"] == active_date] if not my_logs.empty else pd.DataFrame(columns=EXPECTED_LOG_COLS)

    st.markdown("### 📝 Log Time Slot")
    st.info("🕒 **Time Format:** 24-Hour Clock (e.g. 09:00 for 9:00 AM, 15:30 for 3:30 PM)")

    with st.form("ch_log_form", clear_on_submit=True):
        category = st.selectbox("Activity Category", categories)

        col_st, col_et = st.columns(2)
        with col_st:
            start_t = st.time_input("Start Time (24h)", value=time(9, 0))
        with col_et:
            end_t = st.time_input("End Time (24h)", value=time(10, 30))

        task_desc = st.text_area("Specific Task / Description", placeholder="Outline actions taken, topics, teachers/schools engaged...")
        outcome = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted 2 demo classes; scored rubric")

        submit_btn = st.form_submit_button("Record Time Slot ➔", use_container_width=True)

        if submit_btn:
            start_dt = datetime.combine(active_date, start_t)
            end_dt = datetime.combine(active_date, end_t)
            dur_mins = (end_dt - start_dt).total_seconds() / 60

            if dur_mins <= 0:
                st.error("End Time must be later than Start Time.")
            elif not task_desc or not outcome:
                st.error("Please add a brief description and deliverable.")
            else:
                dur_hrs = round(dur_mins / 60, 2)
                new_row = pd.DataFrame([{
                    "Entry ID": str(uuid.uuid4())[:8],
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Cluster Head Email": user_email,
                    "Cluster Head Name": user_name,
                    "Activity Date": str(active_date),
                    "Activity Category": category,
                    "Specific Task / Description": task_desc.strip(),
                    "Start Time": start_t.strftime("%H:%M"),
                    "End Time": end_t.strftime("%H:%M"),
                    "Duration (Hours)": dur_hrs,
                    "Outcome / Deliverable": outcome.strip(),
                    "Status / Verification": "Submitted",
                    "Role": "Cluster Head"
                }])

                updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                conn.update(worksheet="TUR_Logs", data=updated_df)
                st.success(f"Slot recorded: {dur_hrs} hrs under '{category}'!")
                st.rerun()

    # Self-Service Edit / Soft-Delete Panel
    if not my_logs.empty:
        with st.expander("✏️ Edit or Delete an Existing Entry"):
            st.caption("Select one of your previously submitted entries to update or remove.")
            
            my_logs_sorted = my_logs.sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
            entry_options = {}
            for _, r in my_logs_sorted.iterrows():
                eid = str(r["Entry ID"])
                label = f"{r['Activity Date']} | {r['Start Time']}-{r['End Time']} | {r['Activity Category']} ({str(r['Outcome / Deliverable'])[:25]}...)"
                entry_options[label] = eid

            chosen_label = st.selectbox("Select Entry to Modify", list(entry_options.keys()))
            chosen_eid = entry_options[chosen_label]
            selected_row = my_logs[my_logs["Entry ID"].astype(str) == str(chosen_eid)].iloc[0]

            try:
                s_parts = [int(p) for p in str(selected_row["Start Time"]).split(":")]
                curr_start = time(s_parts[0], s_parts[1])
            except Exception:
                curr_start = time(9, 0)
            try:
                e_parts = [int(p) for p in str(selected_row["End Time"]).split(":")]
                curr_end = time(e_parts[0], e_parts[1])
            except Exception:
                curr_end = time(10, 0)

            curr_cat_idx = categories.index(selected_row["Activity Category"]) if selected_row["Activity Category"] in categories else 0

            with st.form("edit_ch_entry_form"):
                e_date = st.date_input("Date", value=selected_row["Activity Date"])
                e_cat = st.selectbox("Category", categories, index=curr_cat_idx)
                
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_start = st.time_input("Start Time (24h)", value=curr_start)
                with ec2:
                    e_end = st.time_input("End Time (24h)", value=curr_end)

                e_task = st.text_area("Task Description", value=str(selected_row["Specific Task / Description"]))
                e_out = st.text_input("Outcome / Deliverable", value=str(selected_row["Outcome / Deliverable"]))

                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    update_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with b_col2:
                    delete_btn = st.form_submit_button("🗑️ Delete This Entry", use_container_width=True)

                if update_btn:
                    dur_m = (datetime.combine(e_date, e_end) - datetime.combine(e_date, e_start)).total_seconds() / 60
                    if dur_m <= 0:
                        st.error("End Time must be after Start Time.")
                    else:
                        row_idx = all_logs[all_logs["Entry ID"].astype(str) == str(chosen_eid)].index
                        if not row_idx.empty:
                            idx = row_idx[0]
                            all_logs.at[idx, "Activity Date"] = str(e_date)
                            all_logs.at[idx, "Activity Category"] = e_cat
                            all_logs.at[idx, "Start Time"] = e_start.strftime("%H:%M")
                            all_logs.at[idx, "End Time"] = e_end.strftime("%H:%M")
                            all_logs.at[idx, "Duration (Hours)"] = round(dur_m / 60, 2)
                            all_logs.at[idx, "Specific Task / Description"] = e_task.strip()
                            all_logs.at[idx, "Outcome / Deliverable"] = e_out.strip()

                            conn.update(worksheet="TUR_Logs", data=all_logs)
                            st.success("Entry updated successfully!")
                            st.rerun()

                if delete_btn:
                    row_idx = all_logs[all_logs["Entry ID"].astype(str) == str(chosen_eid)].index
                    if not row_idx.empty:
                        idx = row_idx[0]
                        all_logs.at[idx, "Status / Verification"] = "Deleted by User"
                        conn.update(worksheet="TUR_Logs", data=all_logs)
                        st.warning("Entry removed successfully.")
                        st.rerun()

    st.markdown("---")
    tab_current, tab_past = st.tabs([f"📋 Today's Entries ({len(today_logs)} logged)", "📜 Previous History"])
    
    with tab_current:
        if not today_logs.empty:
            cols = ["Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
            sorted_today = today_logs[cols].sort_values(by="Start Time", ascending=False)
            render_wrapped_table(sorted_today)
        else:
            st.info("No entries recorded for this date yet.")

    with tab_past:
        if not my_logs.empty:
            cols = ["Activity Date", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
            sorted_past = my_logs[cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
            render_wrapped_table(sorted_past)
        else:
            st.info("No past logs found.")

# =========================================================
# TIER 2: PROGRAM HEAD (Pod Supervisory Review & Personal Logs)
# =========================================================
elif user_role == "Program Head":
    st.title("⚡ Program Head Supervisory Portal")
    st.caption(f"Program Lead: **{user_name}** | Track: **{user_pod}**")

    pod_cluster_heads = users_df[
        (users_df["Role"] == "Cluster Head") &
        ((users_df["Reporting To Email"].str.lower() == user_email) | (users_df["Program / Pod Name"] == user_pod))
    ]
    pod_emails = pod_cluster_heads["Email"].str.lower().tolist()

    all_logs = get_logs()
    
    if not all_logs.empty and "Cluster Head Email" in all_logs.columns:
        logs_emails_clean = all_logs["Cluster Head Email"].astype(str).str.strip().str.lower()
        active_status = all_logs.get("Status / Verification", "") != "Deleted by User"
        pod_logs = all_logs[logs_emails_clean.isin(pod_emails) & active_status].copy()
        my_ph_logs = all_logs[(logs_emails_clean == user_email) & active_status].copy()
    else:
        pod_logs = pd.DataFrame(columns=EXPECTED_LOG_COLS)
        my_ph_logs = pd.DataFrame(columns=EXPECTED_LOG_COLS)

    ph_tab_review, ph_tab_self, ph_tab_my_history = st.tabs([
        f"👥 {user_pod} Pod Review", 
        "📝 Log My Program Head TUR",
        f"📜 My Submitted Logs ({len(my_ph_logs)})"
    ])

    with ph_tab_review:
        today_date = date.today()
        st.markdown(f"### 🚦 Today's Status ({today_date.strftime('%d %b %Y')})")

        status_data = []
        for _, ch in pod_cluster_heads.iterrows():
            ch_email = str(ch["Email"]).strip().lower()
            ch_name = ch["Name"]
            
            if not pod_logs.empty and "Activity Date" in pod_logs.columns:
                ch_today = pod_logs[
                    (pod_logs["Cluster Head Email"].astype(str).str.strip().str.lower() == ch_email) & 
                    (pod_logs["Activity Date"] == today_date)
                ]
                hours_today = ch_today["Duration (Hours)"].sum() if not ch_today.empty else 0.0
                slots_count = len(ch_today)
            else:
                hours_today = 0.0
                slots_count = 0

            status_data.append({
                "Cluster Head": ch_name,
                "Email": ch_email,
                "Hours Logged Today": f"{hours_today:.2f} hrs",
                "Status": "✅ Active" if slots_count > 0 else "⏳ Not Logged"
            })

        render_wrapped_table(pd.DataFrame(status_data))

        st.markdown("---")
        st.markdown("### 📋 Pod Activity Ledger (Most Recent First)")
        
        selected_ch = st.selectbox("Filter Cluster Head", ["All Leads in Pod"] + pod_cluster_heads["Name"].tolist())
        display_logs = pod_logs.copy()
        if selected_ch != "All Leads in Pod" and not display_logs.empty:
            display_logs = display_logs[display_logs["Cluster Head Name"] == selected_ch]

        if not display_logs.empty:
            cols = ["Activity Date", "Cluster Head Name", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
            available_cols = [c for c in cols if c in display_logs.columns]
            sorted_pod_logs = display_logs[available_cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
            render_wrapped_table(sorted_pod_logs)
        else:
            st.info("No records to display for this pod yet.")

    with ph_tab_self:
        st.markdown("### 📝 Record Program Head TUR")
        ph_categories = get_categories_for_role("Program Head")

        with st.form("ph_log_form", clear_on_submit=True):
            p_date = st.date_input("Date", value=date.today(), key="ph_d")
            p_cat = st.selectbox("Supervisory Category", ph_categories)
            
            c_st, c_et = st.columns(2)
            with c_st:
                p_s = st.time_input("Start Time (24h)", value=time(9, 30), key="ph_st")
            with c_et:
                p_e = st.time_input("End Time (24h)", value=time(11, 0), key="ph_et")

            p_task = st.text_area("Supervisory Details", placeholder="Reviewing cluster performance, tutor escalations, program milestones...")
            p_out = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted weekly pod review; 2 interventions aligned")

            if st.form_submit_button("Record Program Log ➔", use_container_width=True):
                dur_min = (datetime.combine(p_date, p_e) - datetime.combine(p_date, p_s)).total_seconds() / 60
                
                if dur_min <= 0:
                    st.error("End Time must be after Start Time.")
                elif not p_task or not p_out:
                    st.error("Please fill in task description and outcome.")
                else:
                    new_row = pd.DataFrame([{
                        "Entry ID": str(uuid.uuid4())[:8],
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Cluster Head Email": user_email,
                        "Cluster Head Name": user_name,
                        "Activity Date": str(p_date),
                        "Activity Category": p_cat,
                        "Specific Task / Description": p_task.strip(),
                        "Start Time": p_s.strftime("%H:%M"),
                        "End Time": p_e.strftime("%H:%M"),
                        "Duration (Hours)": round(dur_min / 60, 2),
                        "Outcome / Deliverable": p_out.strip(),
                        "Status / Verification": "Verified",
                        "Role": "Program Head"
                    }])
                    updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                    conn.update(worksheet="TUR_Logs", data=updated_df)
                    st.success("Program slot saved!")
                    st.rerun()

    with ph_tab_my_history:
        st.markdown(f"### 📜 My Submitted Supervisory Logs ({user_name})")

        if not my_ph_logs.empty:
            with st.expander("✏️ Edit or Delete My Submitted Log"):
                ph_options = {}
                for _, r in my_ph_logs.sort_values(by=["Activity Date", "Start Time"], ascending=[False, False]).iterrows():
                    eid = str(r["Entry ID"])
                    label = f"{r['Activity Date']} | {r['Start Time']}-{r['End Time']} | {r['Activity Category']}"
                    ph_options[label] = eid

                chosen_ph_label = st.selectbox("Select Log to Modify", list(ph_options.keys()))
                chosen_ph_eid = ph_options[chosen_ph_label]
                sel_ph_row = my_ph_logs[my_ph_logs["Entry ID"].astype(str) == str(chosen_ph_eid)].iloc[0]

                try:
                    ps_parts = [int(p) for p in str(sel_ph_row["Start Time"]).split(":")]
                    p_curr_s = time(ps_parts[0], ps_parts[1])
                except Exception:
                    p_curr_s = time(9, 30)
                try:
                    pe_parts = [int(p) for p in str(sel_ph_row["End Time"]).split(":")]
                    p_curr_e = time(pe_parts[0], pe_parts[1])
                except Exception:
                    p_curr_e = time(11, 0)

                ph_categories = get_categories_for_role("Program Head")
                p_cat_idx = ph_categories.index(sel_ph_row["Activity Category"]) if sel_ph_row["Activity Category"] in ph_categories else 0

                with st.form("edit_ph_entry_form"):
                    pe_date = st.date_input("Date", value=sel_ph_row["Activity Date"])
                    pe_cat = st.selectbox("Category", ph_categories, index=p_cat_idx)
                    pec1, pec2 = st.columns(2)
                    with pec1:
                        pe_start = st.time_input("Start Time (24h)", value=p_curr_s)
                    with pec2:
                        pe_end = st.time_input("End Time (24h)", value=p_curr_e)

                    pe_task = st.text_area("Supervisory Details", value=str(sel_ph_row["Specific Task / Description"]))
                    pe_out = st.text_input("Outcome / Deliverable", value=str(sel_ph_row["Outcome / Deliverable"]))

                    ph_btn1, ph_btn2 = st.columns(2)
                    with ph_btn1:
                        ph_save = st.form_submit_button("💾 Save Changes", use_container_width=True)
                    with ph_btn2:
                        ph_del = st.form_submit_button("🗑️ Delete This Log", use_container_width=True)

                    if ph_save:
                        dur_m = (datetime.combine(pe_date, pe_end) - datetime.combine(pe_date, pe_start)).total_seconds() / 60
                        if dur_m <= 0:
                            st.error("End Time must be after Start Time.")
                        else:
                            row_idx = all_logs[all_logs["Entry ID"].astype(str) == str(chosen_ph_eid)].index
                            if not row_idx.empty:
                                idx = row_idx[0]
                                all_logs.at[idx, "Activity Date"] = str(pe_date)
                                all_logs.at[idx, "Activity Category"] = pe_cat
                                all_logs.at[idx, "Start Time"] = pe_start.strftime("%H:%M")
                                all_logs.at[idx, "End Time"] = pe_end.strftime("%H:%M")
                                all_logs.at[idx, "Duration (Hours)"] = round(dur_m / 60, 2)
                                all_logs.at[idx, "Specific Task / Description"] = pe_task.strip()
                                all_logs.at[idx, "Outcome / Deliverable"] = pe_out.strip()

                                conn.update(worksheet="TUR_Logs", data=all_logs)
                                st.success("Log updated!")
                                st.rerun()

                    if ph_del:
                        row_idx = all_logs[all_logs["Entry ID"].astype(str) == str(chosen_ph_eid)].index
                        if not row_idx.empty:
                            idx = row_idx[0]
                            all_logs.at[idx, "Status / Verification"] = "Deleted by User"
                            conn.update(worksheet="TUR_Logs", data=all_logs)
                            st.warning("Log removed.")
                            st.rerun()

            st.markdown("---")
            cols = ["Activity Date", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
            available_my_cols = [c for c in cols if c in my_ph_logs.columns]
            sorted_my_logs = my_ph_logs[available_my_cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
            render_wrapped_table(sorted_my_logs)
        else:
            st.info("You haven't logged any personal supervisory activities yet.")

# =========================================================
# TIER 3: CORE LEADERSHIP (Clean Executive Cockpit)
# =========================================================
else:
    st.title("📊 CLT Executive Review Portal")
    st.caption(f"Logged in: **{user_name}** | Core Leadership")

    all_logs = get_logs()

    if all_logs.empty:
        st.warning("No records found in TUR database.")
    else:
        col_f1, col_f2 = st.columns([2, 2])
        min_d = all_logs["Activity Date"].min()
        max_d = all_logs["Activity Date"].max()

        with col_f1:
            d_range = st.date_input("Date Range", [min_d, max_d])
        with col_f2:
            pods = ["All Subject Tracks"] + sorted([p for p in users_df["Program / Pod Name"].dropna().unique() if p != "All Programs"])
            selected_pod = st.selectbox("Filter Subject Track / Pod", pods)

        filtered_logs = all_logs[all_logs.get("Status / Verification", "") != "Deleted by User"].copy()
        if len(d_range) == 2:
            filtered_logs = filtered_logs[(filtered_logs["Activity Date"] >= d_range[0]) & (filtered_logs["Activity Date"] <= d_range[1])]

        display_users = users_df[users_df["Role"] != "Core Leadership"].copy()
        if selected_pod != "All Subject Tracks":
            display_users = display_users[display_users["Program / Pod Name"] == selected_pod]

        clt_tab_roster, clt_tab_member, clt_tab_audit, clt_tab_export = st.tabs([
            "👥 Team Overview & Compliance", 
            "🔍 Member-by-Member Inspection", 
            "🗑️ Audit & Deleted Records",
            "📥 Data Export"
        ])

        with clt_tab_roster:
            st.markdown("### 📋 Team Bandwidth Summary")
            roster_data = []
            for _, u in display_users.iterrows():
                u_email = str(u["Email"]).lower()
                u_name = u["Name"]
                u_role = u["Role"]
                u_pod = u.get("Program / Pod Name", "-")

                u_logs = filtered_logs[filtered_logs["Cluster Head Email"].str.lower() == u_email]
                total_hrs = u_logs["Duration (Hours)"].sum() if not u_logs.empty else 0.0

                roster_data.append({
                    "Name": u_name,
                    "Role": u_role,
                    "Track / Pod": u_pod,
                    "Total Hours": round(total_hrs, 2),
                    "Status": "✅ Active" if total_hrs > 0 else "⚠️ No Logs"
                })

            roster_df = pd.DataFrame(roster_data)
            roster_df = roster_df.sort_values(by=["Total Hours", "Name"], ascending=[False, True])
            render_wrapped_table(roster_df)

        with clt_tab_member:
            st.markdown("### 🔍 Individual Member Drill-Down")
            member_names = display_users["Name"].tolist()
            
            if not member_names:
                st.info("No members found for this track.")
            else:
                chosen_member = st.selectbox("Select Member to Inspect", member_names)
                member_row = display_users[display_users["Name"] == chosen_member].iloc[0]
                member_email = str(member_row["Email"]).lower()

                member_logs = filtered_logs[filtered_logs["Cluster Head Email"].str.lower() == member_email]
                m_hrs = member_logs["Duration (Hours)"].sum() if not member_logs.empty else 0.0
                
                c_m1, c_m2 = st.columns(2)
                c_m1.metric("Track / Role", f"{member_row['Program / Pod Name']} ({member_row['Role']})")
                c_m2.metric("Total Hours Logged", f"{m_hrs:.2f} hrs")

                st.markdown("---")

                if not member_logs.empty:
                    st.markdown("#### Time Allocation Breakdown")
                    m_cat_sum = member_logs.groupby("Activity Category")["Duration (Hours)"].sum().reset_index()
                    fig_m = px.bar(
                        m_cat_sum,
                        x="Duration (Hours)",
                        y="Activity Category",
                        orientation="h",
                        color="Duration (Hours)",
                        color_continuous_scale="Teal"
                    )
                    fig_m.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10), yaxis_title="")
                    st.plotly_chart(fig_m, use_container_width=True)

                    st.markdown("#### Activity Ledger (Most Recent First)")
                    cols = ["Activity Date", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
                    sorted_member_logs = member_logs[cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
                    render_wrapped_table(sorted_member_logs)
                else:
                    st.info(f"No activity records found for {chosen_member} in the selected date range.")

        with clt_tab_audit:
            st.markdown("### 🗑️ Soft-Deleted Records Audit Trail")
            st.caption("Entries deleted by users remain recorded here. Leadership can inspect them anytime.")
            deleted_logs = all_logs[all_logs.get("Status / Verification", "") == "Deleted by User"].copy()
            if not deleted_logs.empty:
                cols = ["Activity Date", "Cluster Head Name", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable"]
                available_del_cols = [c for c in cols if c in deleted_logs.columns]
                sorted_del = deleted_logs[available_del_cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
                render_wrapped_table(sorted_del)
            else:
                st.info("No records have been deleted by users.")

        with clt_tab_export:
            st.markdown("### 📥 Export Filtered Logs")
            export_cols = [c for c in filtered_logs.columns if c != "Evidence Link"]
            sorted_export = filtered_logs[export_cols].sort_values(by=["Activity Date", "Start Time"], ascending=[False, False])
            csv_data = sorted_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV Dataset",
                data=csv_data,
                file_name=f"PiVector_TUR_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
