import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, time, date
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
    .stProgress > div > div > div > div {
        background-color: #00c49f;
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
def get_users_directory():
    try:
        df = conn.read(worksheet="Users_Directory", ttl="1m")
        if df is not None and not df.empty:
            df["Email"] = df["Email"].str.strip().str.lower()
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["Email", "Name", "Role", "Program / Pod Name", "Reporting To Email"])

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
# Session State & Authentication
# ---------------------------------------------------------
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

users_df = get_users_directory()

# ---------------------------------------------------------
# Sidebar: Branding & User Session
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

    if st.sidebar.button("Logout / Change ID", use_container_width=True):
        st.session_state.authenticated_user = None
        st.rerun()

# ---------------------------------------------------------
# Gatekeeper: Login View (Enter Work Email)
# ---------------------------------------------------------
if not st.session_state.authenticated_user:
    st.title("⚡ PiVector Time Utility Report Engine")
    st.markdown("Enter your registered work email to unlock your workspace.")
    
    with st.container():
        input_col, btn_col = st.columns([3, 1])
        with input_col:
            entered_email = st.text_input("Work Email Address", placeholder="e.g. shwetha.singh@thephoenixedu.com").strip().lower()
        with btn_col:
            st.write("")
            st.write("")
            login_btn = st.button("Enter Workspace ➔", use_container_width=True)

        if login_btn:
            if not entered_email:
                st.warning("Please enter your work email to proceed.")
            else:
                user_match = users_df[users_df["Email"] == entered_email]
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    st.session_state.authenticated_user = user_data
                    st.success(f"Welcome, {user_data['Name']}!")
                    st.rerun()
                else:
                    st.error(f"Email '{entered_email}' is not registered in the Users Directory. Please reach out to leadership.")
    st.stop()

# ---------------------------------------------------------
# Authenticated Workspaces
# ---------------------------------------------------------
curr_user = st.session_state.authenticated_user
user_role = curr_user["Role"]
user_email = curr_user["Email"]
user_name = curr_user["Name"]
user_pod = curr_user.get("Program / Pod Name", "")

# =========================================================
# TIER 1: CLUSTER HEAD WORKSPACE
# =========================================================
if user_role == "Cluster Head":
    st.title(f"⚡ Cluster Head TUR Workspace")
    st.caption(f"Cluster Head: **{user_name}** | Pod: **{user_pod}**")

    categories = get_categories_for_role("Cluster Head")
    all_logs = get_logs()

    # Date Picker & Day Summary
    col_d1, col_d2 = st.columns([2, 4])
    with col_d1:
        active_date = st.date_input("Activity Date", value=date.today())

    # Filter logs for this specific Cluster Head
    my_logs = pd.DataFrame()
    total_hours_today = 0.0

    if not all_logs.empty:
        my_logs = all_logs[all_logs["Cluster Head Email"].str.lower() == user_email]
        today_logs = my_logs[my_logs["Activity Date"] == active_date]
        total_hours_today = today_logs["Duration (Hours)"].sum()
    else:
        today_logs = pd.DataFrame()

    # 8-Hour Target Progress Meter
    st.markdown("---")
    prog_col1, prog_col2 = st.columns([3, 1])
    target_hours = 8.0
    utilization_pct = min(1.0, total_hours_today / target_hours)

    with prog_col1:
        st.markdown(f"**Day Utility Progress ({active_date.strftime('%d %b %Y')}):** `{total_hours_today:.2f} hrs` / `{target_hours:.1f} hrs target`")
        st.progress(utilization_pct)
    with prog_col2:
        if total_hours_today >= target_hours:
            st.success("🎯 8-Hour Day Target Completed!")
        elif total_hours_today >= 5.0:
            st.info(f"⏳ {target_hours - total_hours_today:.2f} hrs remaining")
        else:
            st.warning(f"⚠️ {target_hours - total_hours_today:.2f} hrs needed")

    # Slot Logging Form
    st.markdown("### 📝 Log Activity Slot")
    with st.form("ch_slot_form", clear_on_submit=True):
        f_c1, f_c2, f_c3 = st.columns([2, 1, 1])
        with f_c1:
            category = st.selectbox("Activity Category", categories)
        with f_c2:
            start_t = st.time_input("Start Time", value=time(9, 0))
        with f_c3:
            end_t = st.time_input("End Time", value=time(10, 30))

        task_desc = st.text_area("Specific Task / Description", placeholder="Outline actions taken, topics, teachers/schools engaged...")
        
        f_o1, f_o2 = st.columns(2)
        with f_o1:
            outcome = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted 2 demo classes; feedback scorecard published")
        with f_o2:
            evidence = st.text_input("Evidence Link (Drive/Docs)", placeholder="https://docs.google.com/...")

        submit_btn = st.form_submit_button("Record Time Slot", use_container_width=True)

        if submit_btn:
            start_dt = datetime.combine(active_date, start_t)
            end_dt = datetime.combine(active_date, end_t)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60

            if duration_minutes <= 0:
                st.error("End Time must be after Start Time.")
            elif not task_desc or not outcome:
                st.error("Both Task Description and Deliverable are mandatory.")
            else:
                duration_hours = round(duration_minutes / 60, 2)
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
                    "Duration (Hours)": duration_hours,
                    "Outcome / Deliverable": outcome.strip(),
                    "Evidence Link": evidence.strip(),
                    "Status / Verification": "Pending",
                    "Role": "Cluster Head"
                }])

                updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                conn.update(worksheet="TUR_Logs", data=updated_df)
                st.success(f"Slot recorded: {duration_hours} hrs logged under {category}!")
                st.rerun()

    # My History & Today's Ledger
    st.markdown("---")
    tab_today, tab_history = st.tabs(["📋 Today's Recorded Slots", "📜 My Previous Activity History"])
    
    with tab_today:
        if not today_logs.empty:
            cols = ["Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable", "Evidence Link", "Status / Verification"]
            st.dataframe(
                today_logs[cols].sort_values(by="Start Time"),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence", display_text="Open Doc")}
            )
        else:
            st.info("No slots recorded yet for today.")

    with tab_history:
        if not my_logs.empty:
            cols = ["Activity Date", "Start Time", "End Time", "Duration (Hours)", "Activity Category", "Outcome / Deliverable", "Evidence Link", "Status / Verification"]
            st.dataframe(
                my_logs[cols].sort_values(by="Activity Date", ascending=False),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence", display_text="Open Doc")}
            )
        else:
            st.info("No prior history records found.")

# =========================================================
# TIER 2: PROGRAM HEAD WORKSPACE
# =========================================================
elif user_role == "Program Head":
    st.title("⚡ Program Head Supervisory Portal")
    st.caption(f"Program Lead: **{user_name}** | Supervised Pod: **{user_pod}**")

    # Find reporting Cluster Heads
    pod_cluster_heads = users_df[
        (users_df["Role"] == "Cluster Head") &
        ((users_df["Reporting To Email"] == user_email) | (users_df["Program / Pod Name"] == user_pod))
    ]
    pod_ch_emails = pod_cluster_heads["Email"].tolist()

    all_logs = get_logs()
    pod_logs = all_logs[all_logs["Cluster Head Email"].str.lower().isin(pod_ch_emails)] if not all_logs.empty else pd.DataFrame()

    ph_tab1, ph_tab2 = st.tabs(["👥 Supervised Cluster Heads & TUR Ledger", "📝 Log My Program Head TUR"])

    with ph_tab1:
        st.markdown("### 📋 Cluster Head Utilization Overview")
        if pod_logs.empty:
            st.info("No TUR submissions recorded yet for your cluster heads.")
        else:
            # Metrics
            total_cluster_hours = pod_logs["Duration (Hours)"].sum()
            active_heads = pod_logs["Cluster Head Email"].nunique()
            p1, p2, p3 = st.columns(3)
            p1.metric("Total Hours Monitored", f"{total_cluster_hours:.1f} hrs")
            p2.metric("Active Cluster Heads", active_heads)
            p3.metric("Total Submitted Slots", len(pod_logs))

            # Filter by Cluster Head
            sel_ch = st.selectbox("Filter by Cluster Head", ["All Supervised Leads"] + pod_cluster_heads["Name"].tolist())
            display_pod_logs = pod_logs.copy()
            if sel_ch != "All Supervised Leads":
                display_pod_logs = display_pod_logs[display_pod_logs["Cluster Head Name"] == sel_ch]

            # Detailed Review Table with Evidence Links
            st.dataframe(
                display_pod_logs[[
                    "Activity Date", "Cluster Head Name", "Start Time", "End Time",
                    "Duration (Hours)", "Activity Category", "Outcome / Deliverable",
                    "Evidence Link", "Status / Verification"
                ]].sort_values(by="Activity Date", ascending=False),
                use_container_width=True,
                column_config={"Evidence Link": st.column_config.LinkColumn("Evidence Document", display_text="Open Evidence")}
            )

    with ph_tab2:
        st.markdown("### 📝 Log Program Head TUR")
        ph_categories = get_categories_for_role("Program Head")

        with st.form("ph_slot_form", clear_on_submit=True):
            f_date = st.date_input("Activity Date", value=date.today(), key="ph_d")
            f_cat = st.selectbox("Program Head Category", ph_categories)
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                p_start = st.time_input("Start Time", value=time(9, 30), key="ph_s")
            with c_t2:
                p_end = st.time_input("End Time", value=time(11, 0), key="ph_e")

            p_task = st.text_area("Supervisory Focus / Actions", placeholder="Cluster check-ins, tutor evaluations, program health reviews...")
            p_out = st.text_input("Outcome / Deliverable", placeholder="e.g. Conducted cluster weekly sync; resolved 3 escalations")
            p_evi = st.text_input("Evidence Link", placeholder="https://docs.google.com/...")

            ph_submit = st.form_submit_button("Record Program Slot", use_container_width=True)

            if ph_submit:
                dur_min = (datetime.combine(f_date, p_end) - datetime.combine(f_date, p_start)).total_seconds() / 60
                if dur_min <= 0:
                    st.error("End Time must be after Start Time.")
                elif not p_task or not p_out:
                    st.error("Both Focus and Deliverable fields are required.")
                else:
                    new_row = pd.DataFrame([{
                        "Entry ID": str(uuid.uuid4())[:8],
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Cluster Head Email": user_email,
                        "Cluster Head Name": user_name,
                        "Activity Date": str(f_date),
                        "Activity Category": f_cat,
                        "Specific Task / Description": p_task.strip(),
                        "Start Time": p_start.strftime("%H:%M"),
                        "End Time": p_end.strftime("%H:%M"),
                        "Duration (Hours)": round(dur_min / 60, 2),
                        "Outcome / Deliverable": p_out.strip(),
                        "Evidence Link": p_evi.strip(),
                        "Status / Verification": "Verified",
                        "Role": "Program Head"
                    }])
                    updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                    conn.update(worksheet="TUR_Logs", data=updated_df)
                    st.success("Program Head slot saved!")
                    st.rerun()

# =========================================================
# TIER 3: CORE LEADERSHIP TEAM (CLT - J H A K K A S  V I E W)
# =========================================================
else:
    st.title("📊 PiVector Core Leadership Command Deck")
    st.caption("Complete Bird's-Eye View: Time Utility, Program Allocation & Evidence Verification")

    all_logs = get_logs()

    if all_logs.empty:
        st.warning("No records found in TUR database.")
    else:
        # CLT Global Filters
        f1, f2, f3 = st.columns([2, 2, 2])
        min_d = all_logs["Activity Date"].min()
        max_d = all_logs["Activity Date"].max()

        with f1:
            d_range = st.date_input("Date Range", [min_d, max_d])
        with f2:
            role_filter = st.selectbox("Filter Role", ["All Roles", "Cluster Head", "Program Head"])
        with f3:
            all_people = ["Everyone"] + sorted(all_logs["Cluster Head Name"].dropna().unique().tolist())
            lead_filter = st.selectbox("Filter Person", all_people)

        # Apply Filters
        clt_data = all_logs.copy()
        if len(d_range) == 2:
            clt_data = clt_data[(clt_data["Activity Date"] >= d_range[0]) & (clt_data["Activity Date"] <= d_range[1])]
        if role_filter != "All Roles":
            clt_data = clt_data[clt_data["Role"] == role_filter]
        if lead_filter != "Everyone":
            clt_data = clt_data[clt_data["Cluster Head Name"] == lead_filter]

        # Executive Metrics
        tot_hours = clt_data["Duration (Hours)"].sum()
        tot_entries = len(clt_data)
        unique_members = clt_data["Cluster Head Name"].nunique()
        avg_per_member = round(tot_hours / max(1, unique_members), 1)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Hours Monitored", f"{tot_hours:,.1f} hrs")
        kpi2.metric("Total Activities Logged", f"{tot_entries:,}")
        kpi3.metric("Active Team Members", unique_members)
        kpi4.metric("Avg Hours / Member", f"{avg_per_member:.1f} hrs")

        st.markdown("---")

        # Visual Analytics (Jhakkas Visualizations)
        v_col1, v_col2 = st.columns(2)

        with v_col1:
            st.markdown("#### 🕒 Time Distribution by Category")
            cat_sum = clt_data.groupby("Activity Category")["Duration (Hours)"].sum().reset_index()
            fig_pie = px.pie(
                cat_sum,
                names="Activity Category",
                values="Duration (Hours)",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

        with v_col2:
            st.markdown("#### 👥 Bandwidth by Team Member")
            member_sum = clt_data.groupby(["Cluster Head Name", "Activity Category"])["Duration (Hours)"].sum().reset_index()
            fig_bar = px.bar(
                member_sum,
                x="Duration (Hours)",
                y="Cluster Head Name",
                color="Activity Category",
                orientation='h',
                barmode='stack',
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)

        # Timeline Trend
        st.markdown("#### 📈 Daily Time Investment Trend")
        daily_trend = clt_data.groupby("Activity Date")["Duration (Hours)"].sum().reset_index()
        fig_trend = px.area(
            daily_trend,
            x="Activity Date",
            y="Duration (Hours)",
            markers=True,
            color_discrete_sequence=["#00c49f"]
        )
        fig_trend.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_trend, use_container_width=True)

        # Master Evidence & Verification Table
        st.markdown("### 🔎 Master Audit & Evidence Ledger")
        st.dataframe(
            clt_data[[
                "Activity Date", "Role", "Cluster Head Name", "Start Time", "End Time",
                "Duration (Hours)", "Activity Category", "Specific Task / Description",
                "Outcome / Deliverable", "Evidence Link", "Status / Verification"
            ]].sort_values(by="Activity Date", ascending=False),
            use_container_width=True,
            column_config={"Evidence Link": st.column_config.LinkColumn("Evidence Doc", display_text="Inspect")}
        )

        # CSV Download for Board/Executive meetings
        csv_data = clt_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Executive TUR Dataset (CSV)",
            data=csv_data,
            file_name=f"PiVector_TUR_Master_{date.today()}.csv",
            mime="text/csv",
        )
