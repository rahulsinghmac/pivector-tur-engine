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

# Custom Brand Styling (PiVector Emerald Teal)
st.markdown("""
<style>
    :root {
        --pivector-teal: #00c49f;
        --pivector-dark: #0f172a;
    }
    .metric-card {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #00c49f;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stProgress > div > div > div > div {
        background-color: #00c49f;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Connection & Caching
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        logs_df = conn.read(worksheet="TUR_Logs", ttl="0m")
        # Ensure correct column types
        if logs_df is not None and not logs_df.empty:
            logs_df["Activity Date"] = pd.to_datetime(logs_df["Activity Date"]).dt.date
            logs_df["Duration (Hours)"] = pd.to_numeric(logs_df["Duration (Hours)"], errors="coerce").fillna(0.0)
        else:
            logs_df = pd.DataFrame(columns=[
                "Entry ID", "Timestamp", "Cluster Head Email", "Cluster Head Name",
                "Activity Date", "Activity Category", "Specific Task / Description",
                "Start Time", "End Time", "Duration (Hours)", "Outcome / Deliverable",
                "Evidence Link", "Status / Verification"
            ])
        return logs_df
    except Exception as e:
        st.error(f"Error loading logs: {e}")
        return pd.DataFrame()

def load_categories():
    try:
        tax_df = conn.read(worksheet="Activity_Taxonomy", ttl="10m")
        if tax_df is not None and not tax_df.empty and "Category" in tax_df.columns:
            return tax_df["Category"].dropna().tolist()
    except Exception:
        pass
    return [
        "Academic & Classroom Support",
        "Operations & Administration",
        "Parent & Stakeholder Management",
        "Curriculum & Assessments",
        "Team & Strategy"
    ]

# ---------------------------------------------------------
# Sidebar & Navigation
# ---------------------------------------------------------
try:
    st.sidebar.image("PiVector-logo2.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("## **PiVector**")

st.sidebar.markdown("### **Time Utility Report (TUR)**")
portal_mode = st.sidebar.radio(
    "Select Portal View",
    ["Cluster Head Workspace", "Executive TUR Dashboard"]
)

categories = load_categories()

# ---------------------------------------------------------
# VIEW 1: Cluster Head Workspace (Data Entry & Ledger)
# ---------------------------------------------------------
if portal_mode == "Cluster Head Workspace":
    st.title("⚡ Cluster Head Daily TUR Ledger")
    st.caption("Log daily activity slots with clear deliverables and evidence.")

    col_meta1, col_meta2, col_meta3 = st.columns([2, 2, 2])
    with col_meta1:
        ch_name = st.text_input("Your Full Name", placeholder="e.g. Shwetha Singh")
    with col_meta2:
        ch_email = st.text_input("Work Email Address", placeholder="e.g. shwetha@thephoenixedu.com")
    with col_meta3:
        active_date = st.date_input("Activity Date", value=date.today())

    # Load existing logs for this user & day
    all_logs = load_data()
    day_logs = pd.DataFrame()
    total_hours_today = 0.0

    if not all_logs.empty and ch_email:
        day_logs = all_logs[
            (all_logs["Cluster Head Email"].str.lower() == ch_email.strip().lower()) &
            (all_logs["Activity Date"] == active_date)
        ]
        total_hours_today = day_logs["Duration (Hours)"].sum()

    # Daily Target & Progress Gauge
    st.markdown("---")
    prog_col1, prog_col2 = st.columns([3, 1])
    target_hours = 8.0
    utilization_pct = min(1.0, total_hours_today / target_hours)

    with prog_col1:
        st.markdown(f"**Day Utility Progress:** `{total_hours_today:.2f} hrs` / `{target_hours:.1f} hrs target`")
        st.progress(utilization_pct)
    with prog_col2:
        if total_hours_today >= target_hours:
            st.success("🎯 Day Target Achieved!")
        elif total_hours_today >= 5.0:
            st.info(f"⏳ {target_hours - total_hours_today:.2f} hrs remaining")
        else:
            st.warning(f"⚠️ {target_hours - total_hours_today:.2f} hrs needed")

    # Slot Logging Form
    st.markdown("### 📝 Log a Time Slot")
    with st.form("slot_entry_form", clear_on_submit=True):
        form_col1, form_col2, form_col3 = st.columns([2, 1, 1])
        with form_col1:
            category = st.selectbox("Activity Category", categories)
        with form_col2:
            start_t = st.time_input("Start Time", value=time(9, 0))
        with form_col3:
            end_t = st.time_input("End Time", value=time(10, 30))

        task_desc = st.text_area("Specific Task & Key Context", placeholder="Detail what was conducted, who was involved, and focal areas...")
        
        col_out1, col_out2 = st.columns(2)
        with col_out1:
            outcome = st.text_input("Tangible Deliverable / Outcome", placeholder="e.g. Conducted 2 demo classes; rubric scorecard completed")
        with col_out2:
            evidence = st.text_input("Evidence Document / Drive URL", placeholder="https://docs.google.com/...")

        submit_btn = st.form_submit_button("Record Time Slot", use_container_width=True)

        if submit_btn:
            # Time calculation
            start_dt = datetime.combine(active_date, start_t)
            end_dt = datetime.combine(active_date, end_t)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60

            if not ch_name or not ch_email:
                st.error("Please fill in your Name and Work Email above before logging.")
            elif duration_minutes <= 0:
                st.error("End Time must be after Start Time.")
            elif not task_desc or not outcome:
                st.error("Please provide both Task Description and a concrete Deliverable / Outcome.")
            else:
                duration_hours = round(duration_minutes / 60, 2)
                new_row = pd.DataFrame([{
                    "Entry ID": str(uuid.uuid4())[:8],
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Cluster Head Email": ch_email.strip().lower(),
                    "Cluster Head Name": ch_name.strip(),
                    "Activity Date": str(active_date),
                    "Activity Category": category,
                    "Specific Task / Description": task_desc.strip(),
                    "Start Time": start_t.strftime("%H:%M"),
                    "End Time": end_t.strftime("%H:%M"),
                    "Duration (Hours)": duration_hours,
                    "Outcome / Deliverable": outcome.strip(),
                    "Evidence Link": evidence.strip(),
                    "Status / Verification": "Pending"
                }])

                updated_df = pd.concat([all_logs, new_row], ignore_index=True)
                conn.update(worksheet="TUR_Logs", data=updated_df)
                st.success(f"Slot saved: {duration_hours} hrs logged for {category}!")
                st.rerun()

    # Today's Ledger Display
    st.markdown("### 📋 Today's Recorded Activity Ledger")
    if not day_logs.empty:
        display_cols = ["Start Time", "End Time", "Duration (Hours)", "Activity Category", "Specific Task / Description", "Outcome / Deliverable", "Evidence Link", "Status / Verification"]
        st.dataframe(
            day_logs[display_cols].sort_values(by="Start Time"),
            use_container_width=True,
            column_config={
                "Evidence Link": st.column_config.LinkColumn("Evidence", display_text="Open Link")
            }
        )
    else:
        st.info("No activity slots logged yet for the selected date.")

# ---------------------------------------------------------
# VIEW 2: Executive Dashboard (Boss / Leadership Portal)
# ---------------------------------------------------------
else:
    st.title("📊 PiVector Executive TUR Audit Engine")
    st.caption("Cluster Head Time Utility, Category Allocation & Deliverable Verification")

    df = load_data()

    if df.empty:
        st.warning("No TUR log records found in the database.")
    else:
        # Date and Cluster Head Filters
        f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
        min_date = df["Activity Date"].min()
        max_date = df["Activity Date"].max()

        with f_col1:
            date_range = st.date_input("Date Range", [min_date, max_date])
        with f_col2:
            all_leads = ["All Cluster Heads"] + sorted(df["Cluster Head Name"].dropna().unique().tolist())
            selected_lead = st.selectbox("Filter Cluster Head", all_leads)
        with f_col3:
            all_cats = ["All Categories"] + categories
            selected_cat = st.selectbox("Filter Activity Category", all_cats)

        # Apply Filters
        filtered = df.copy()
        if len(date_range) == 2:
            filtered = filtered[(filtered["Activity Date"] >= date_range[0]) & (filtered["Activity Date"] <= date_range[1])]
        if selected_lead != "All Cluster Heads":
            filtered = filtered[filtered["Cluster Head Name"] == selected_lead]
        if selected_cat != "All Categories":
            filtered = filtered[filtered["Activity Category"] == selected_cat]

        # Top Executive Metric Cards
        total_hours = filtered["Duration (Hours)"].sum()
        total_slots = len(filtered)
        unique_leads = filtered["Cluster Head Name"].nunique()
        avg_hrs_lead = round(total_hours / max(1, unique_leads), 1)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Hours Logged", f"{total_hours:.1f} hrs")
        m2.metric("Total Slots Recorded", total_slots)
        m3.metric("Active Cluster Heads", unique_leads)
        m4.metric("Avg Hours / Cluster Head", f"{avg_hrs_lead:.1f} hrs")

        st.markdown("---")

        # Visual Analytics
        c_chart1, c_chart2 = st.columns(2)

        with c_chart1:
            st.markdown("#### 🕒 Time Allocation by Category")
            cat_summary = filtered.groupby("Activity Category")["Duration (Hours)"].sum().reset_index()
            fig_pie = px.pie(
                cat_summary,
                names="Activity Category",
                values="Duration (Hours)",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_chart2:
            st.markdown("#### 👥 Bandwidth by Cluster Head")
            lead_summary = filtered.groupby(["Cluster Head Name", "Activity Category"])["Duration (Hours)"].sum().reset_index()
            fig_bar = px.bar(
                lead_summary,
                x="Duration (Hours)",
                y="Cluster Head Name",
                color="Activity Category",
                orientation='h',
                barmode='stack',
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_bar.update_layout(margin=dict(t=20, b=20, l=10, r=10), yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)

        # Audit & Deliverable Verification Ledger
        st.markdown("### 🔎 Master Audit & Verification Ledger")
        st.caption("Inspect deliverables and click direct evidence links.")

        audit_cols = [
            "Activity Date", "Cluster Head Name", "Start Time", "End Time",
            "Duration (Hours)", "Activity Category", "Specific Task / Description",
            "Outcome / Deliverable", "Evidence Link", "Status / Verification"
        ]

        st.dataframe(
            filtered[audit_cols].sort_values(by="Activity Date", ascending=False),
            use_container_width=True,
            column_config={
                "Evidence Link": st.column_config.LinkColumn("Evidence Doc", display_text="Inspect Evidence")
            }
        )

        # Quick CSV Download for Boss
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Report as CSV",
            data=csv,
            file_name=f"PiVector_TUR_Report_{date.today()}.csv",
            mime="text/csv",
        )