import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, time, date, timedelta
import uuid

# ---------------------------------------------------------
# Page Configuration & Styling
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
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #00c49f;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Google Sheets Connection & Data Fetchers
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

EXPECTED_LOG_COLS = [
    "Entry ID", "Timestamp", "Cluster Head Email", "Cluster Head Name",
    "Activity Date", "Activity Category", "Specific Task / Description",
    "Start Time", "End Time", "Duration (Hours)", "Outcome / Deliverable",
    "Evidence Link", "Status / Verification", "Role"
]

@st.cache_data(ttl=60)
# 1. Update the directory loader to disable aggressive caching and normalize PIN formatting
def get_users_directory():
    try:
        df = conn.read(worksheet="Users_Directory", ttl="0m")
        if df is not None and not df.empty:
            df["Email"] = df["Email"].astype(str).str.strip().str.lower()
            # Handles numeric values like 1234 or 1234.0 properly into '1234'
            df["PIN"] = df["PIN"].astype(str).str.replace(".0", "", regex=False).str.strip()
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

if "preset_start" not in st.session_state:
    st.session_state.preset_start = time(9, 0)
if "preset_end" not in st.session_state:
    st.session_state.preset_end = time(10, 30)

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
        st.sidebar.caption(f"Pod: {curr_user['Program / Pod Name']}")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated_user = None
        st.rerun()

# ---------------------------------------------------------
# Gatekeeper: Authentication Check
# ---------------------------------------------------------
if not st.session_state.authenticated_user:
    st.title("⚡ PiVector TUR Access Portal")
    st.caption("Secure enterprise gateway for Cluster Heads, Program Leads & Leadership")

    with st.container():
        login_col1, login_col2 = st.columns([2, 1])
        with login_col1:
            entered_email = st.text_input("Work Email Address", placeholder="e.g. shwetha.singh@thephoenixedu.com").strip().lower()
            entered_pin = st.text_input("4-Digit Access PIN", type="password", max_chars=4, placeholder="••••").strip()
            login_btn = st.button("Authenticate & Enter ➔", use_container_width=True)

        if login_btn:
            if not entered_email or not entered_pin:
                st.warning("Please enter both your work email and 4-digit PIN.")
            else:
                users_df = get_users_directory()
                user_match = users_df[
                    (users_df["Email"] == entered_email) & 
                    (users_df["PIN"] == entered_pin)
                ]
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    st.session_state.authenticated_user = user_data
                    st.rerun()
                else:
                    st.error("Invalid email or PIN. Please check your credentials.")
    
    # Halt execution here until user logs in
    st.stop()

# ---------------------------------------------------------
# Only runs AFTER successful authentication
# ---------------------------------------------------------
curr_user = st.session_state.authenticated_user
user_role = curr_user["Role"]
user_email = curr_user["Email"]
user_name = curr_user["Name"]
user_pod = curr_user.get("Program / Pod Name", "")

# ---------------------------------------------------------
# Active Session Context
# ---------------------------------------------------------
curr_user = st.session_state.authenticated_user
user_role = curr_user["Role"]
user_email = curr_user["Email"]
user_name = curr_user["Name"]
user_pod = curr_user.get("Program / Pod Name", "")

# =========================================================
# TIER 1: CLUSTER HEAD (Clean 24-Hour Entry)
# =========================================================
if user_role == "Cluster Head":
    st.title("⚡ Cluster Head Daily TUR")
    st.caption(f"Logged in: **{user_name}** | Pod: **{user_pod}**")

    categories = get_categories_for_role("Cluster Head")
    all_logs = get_logs()

    # Active date picker
    active_date = st.date_input("Activity Date", value=date.today())

    # Get this user's logs
    my_logs = all_logs[all_logs["Cluster Head Email"].str.lower() == user_email] if not all_logs.empty else pd.DataFrame()
    today_logs = my_logs[my_logs["Activity Date"] == active_date] if not my_logs.empty else pd.DataFrame()

    st.markdown("### 📝 Log Time Slot")
    st.info("🕒 **Time Format:** 24-Hour Clock (e.g., 09:00 for 9:00 AM, 15:30 for 3:30 PM)")

    # Hours (00-23) and standard 15-minute intervals
    hour_options = [f"{h:02d}" for h in range(6, 24)]  # 06 to 23
    minute_options = ["00", "15", "30", "45"]

    with st.form("ch_log_form", clear_on_submit=True):
        category = st.selectbox("Activity Category", categories)

        col_st, col_et = st.columns(2)
        with col_st:
            st.markdown("**Start Time (24h)**")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                start_hr = st.selectbox("Hour", hour_options, index=3, key="s_hr")  # defaults to 09
            with s_col2:
                start_min = st.selectbox("Min", minute_options, index=0, key="s_min")

        with col_et:
            st.markdown("**End Time (24h)**")
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                end_hr = st.selectbox("Hour", hour_options, index=4, key="e_hr")    # defaults to 10
            with e_col2:
                end_min = st.selectbox("Min", minute_options, index=2, key="e_min") # defaults to 30

        task_desc = st.text_area("Specific Task / Description", placeholder="Outline actions taken, topics, teachers/schools engaged...")
        
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            outcome = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted 2 demo classes; scored rubric")
        with col_o2:
            evidence = st.text_input("Evidence Link (Google Drive / Docs)", placeholder="https://docs.google.com/...")

        submit_btn = st.form_submit_button("Record Time Slot ➔", use_container_width=True)

        if submit_btn:
            start_t = time(int(start_hr), int(start_min))
            end_t = time(int(end_hr), int(end_min))

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
                    "Evidence Link": evidence.strip(),
                    "Status / Verification": "Submitted",
                    "Role": "Cluster Head"
                }])

                updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                conn.update(worksheet="TUR_Logs", data=updated_df)
                st.success(f"Slot recorded: {dur_hrs} hrs under '{category}'!")
                st.rerun()

    # User's Entries View
    st.markdown("---")
    tab_current, tab_past = st.tabs([f"📋 Today's Entries ({len(today_logs)} logged)", "📜 Previous History"])
    
    with tab_current:
        if not today_logs.empty:
            cols = ["Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable", "Evidence Link"]
            st.dataframe(
                today_logs[cols].sort_values(by="Start Time"),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence", display_text="Open Doc")}
            )
        else:
            st.info("No entries recorded for this date yet.")

    with tab_past:
        if not my_logs.empty:
            cols = ["Activity Date", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Outcome / Deliverable", "Evidence Link"]
            st.dataframe(
                my_logs[cols].sort_values(by="Activity Date", ascending=False),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence", display_text="Open Doc")}
            )
        else:
            st.info("No past logs found.")
# =========================================================
# TIER 2: PROGRAM HEAD (10x Pod Supervisory Review)
# =========================================================
elif user_role == "Program Head":
    st.title("⚡ Program Head Supervisory Portal")
    st.caption(f"Program Lead: **{user_name}** | Supervised Pod: **{user_pod}**")

    # Filter cluster heads reporting to this lead
    pod_cluster_heads = users_df[
        (users_df["Role"] == "Cluster Head") &
        ((users_df["Reporting To Email"] == user_email) | (users_df["Program / Pod Name"] == user_pod))
    ]
    pod_emails = pod_cluster_heads["Email"].tolist()

    all_logs = get_logs()
    pod_logs = all_logs[all_logs["Cluster Head Email"].str.lower().isin(pod_emails)] if not all_logs.empty else pd.DataFrame()

    ph_tab_review, ph_tab_self = st.tabs(["👥 Pod Review & Cluster Logs", "📝 Log My Program Head TUR"])

    with ph_tab_review:
        today_date = date.today()
        st.markdown("### 🚦 Today's Pod Submission Status")

        # Status check for supervised heads
        status_data = []
        for _, ch in pod_cluster_heads.iterrows():
            ch_email = ch["Email"]
            ch_name = ch["Name"]
            ch_today = pod_logs[(pod_logs["Cluster Head Email"] == ch_email) & (pod_logs["Activity Date"] == today_date)]
            hours_today = ch_today["Duration (Hours)"].sum() if not ch_today.empty else 0.0
            slots_count = len(ch_today)
            status_data.append({
                "Cluster Head": ch_name,
                "Email": ch_email,
                "Slots Today": slots_count,
                "Hours Logged Today": f"{hours_today:.2f} hrs",
                "Status": "✅ Active" if slots_count > 0 else "⏳ Not Logged"
            })

        st.dataframe(pd.DataFrame(status_data), use_container_width=True)

        st.markdown("---")
        st.markdown("### 📋 Filtered Activity Ledger")
        
        selected_ch = st.selectbox("Select Cluster Head to Inspect", ["All Cluster Heads"] + pod_cluster_heads["Name"].tolist())
        display_logs = pod_logs.copy()
        if selected_ch != "All Cluster Heads":
            display_logs = display_logs[display_logs["Cluster Head Name"] == selected_ch]

        if not display_logs.empty:
            st.dataframe(
                display_logs[[
                    "Activity Date", "Cluster Head Name", "Start Time", "End Time",
                    "Duration (Hours)", "Activity Category", "Outcome / Deliverable",
                    "Evidence Link"
                ]].sort_values(by="Activity Date", ascending=False),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence Doc", display_text="Inspect")}
            )
        else:
            st.info("No records to display for this selection.")

    with ph_tab_self:
        st.markdown("### 📝 Record Program Head TUR")
        ph_categories = get_categories_for_role("Program Head")

        with st.form("ph_log_form", clear_on_submit=True):
            p_date = st.date_input("Date", value=date.today(), key="ph_d")
            p_cat = st.selectbox("Supervisory Category", ph_categories)
            pt_col1, pt_col2 = st.columns(2)
            with pt_col1:
                p_s = st.time_input("Start Time", value=time(9, 30), key="ph_st")
            with pt_col2:
                p_e = st.time_input("End Time", value=time(11, 0), key="ph_et")

            p_task = st.text_area("Supervisory Details", placeholder="Reviewing cluster performance, tutor escalations, program milestones...")
            p_out = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted weekly pod review; 2 interventions aligned")
            p_evi = st.text_input("Evidence Link", placeholder="https://docs.google.com/...")

            if st.form_submit_button("Record Program Log", use_container_width=True):
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
                        "Evidence Link": p_evi.strip(),
                        "Status / Verification": "Verified",
                        "Role": "Program Head"
                    }])
                    updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                    conn.update(worksheet="TUR_Logs", data=updated_df)
                    st.success("Program slot saved!")
                    st.rerun()

# =========================================================
# TIER 3: CORE LEADERSHIP TEAM (Member-by-Member Review)
# =========================================================
else:
    st.title("📊 CLT Executive Review Portal")
    st.caption("Member-by-Member Time Utility, Deliverables & Evidence Inspection")

    all_logs = get_logs()

    if all_logs.empty:
        st.warning("No records found in TUR database.")
    else:
        # Date and Pod Filter Bar
        col_f1, col_f2 = st.columns([2, 2])
        min_d = all_logs["Activity Date"].min()
        max_d = all_logs["Activity Date"].max()

        with col_f1:
            d_range = st.date_input("Date Range", [min_d, max_d])
        with col_f2:
            pods = ["All Programs / Pods"] + sorted([p for p in users_df["Program / Pod Name"].dropna().unique() if p != "All Programs"])
            selected_pod = st.selectbox("Filter by Program / Pod", pods)

        # Filter dataset by date
        filtered_logs = all_logs.copy()
        if len(d_range) == 2:
            filtered_logs = filtered_logs[(filtered_logs["Activity Date"] >= d_range[0]) & (filtered_logs["Activity Date"] <= d_range[1])]

        # Filter members by pod
        display_users = users_df[users_df["Role"] != "Core Leadership"].copy()
        if selected_pod != "All Programs / Pods":
            display_users = display_users[display_users["Program / Pod Name"] == selected_pod]

        # Tabbed Layout: Team Roster vs Individual Member Drill-Down
        clt_tab_roster, clt_tab_member, clt_tab_export = st.tabs([
            "👥 Team Overview & Compliance", 
            "🔍 Member-by-Member Inspection", 
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
                slots_count = len(u_logs)

                roster_data.append({
                    "Name": u_name,
                    "Role": u_role,
                    "Program / Pod": u_pod,
                    "Total Hours": round(total_hrs, 2),
                    "Total Slots": slots_count,
                    "Status": "✅ Active" if slots_count > 0 else "⚠️ No Logs"
                })

            st.dataframe(pd.DataFrame(roster_data), use_container_width=True)

        with clt_tab_member:
            st.markdown("### 🔍 Individual Member Drill-Down")
            member_names = display_users["Name"].tolist()
            
            if not member_names:
                st.info("No members found for the selected pod.")
            else:
                chosen_member = st.selectbox("Select Member to Inspect", member_names)
                member_row = display_users[display_users["Name"] == chosen_member].iloc[0]
                member_email = str(member_row["Email"]).lower()

                member_logs = filtered_logs[filtered_logs["Cluster Head Email"].str.lower() == member_email]

                # Member summary cards
                m_hrs = member_logs["Duration (Hours)"].sum() if not member_logs.empty else 0.0
                m_slots = len(member_logs)
                
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Role", member_row["Role"])
                c_m2.metric("Total Hours Logged", f"{m_hrs:.2f} hrs")
                c_m3.metric("Total Activities", m_slots)

                st.markdown("---")

                if not member_logs.empty:
                    # Category breakdown chart
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

                    # Detailed Ledger
                    st.markdown("#### Activity & Evidence Ledger")
                    st.dataframe(
                        member_logs[[
                            "Activity Date", "Start Time", "End Time", "Duration (Hours)",
                            "Activity Category", "Specific Task / Description", 
                            "Outcome / Deliverable", "Evidence Link"
                        ]].sort_values(by="Activity Date", ascending=False),
                        use_container_width=True,
                        column_config={"Evidence Link": st.column_config.LinkColumn("Evidence Doc", display_text="Open Evidence")}
                    )
                else:
                    st.info(f"No activity records found for {chosen_member} in the selected date range.")

        with clt_tab_export:
            st.markdown("### 📥 Export Filtered Logs")
            csv_data = filtered_logs.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV Dataset",
                data=csv_data,
                file_name=f"PiVector_TUR_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
