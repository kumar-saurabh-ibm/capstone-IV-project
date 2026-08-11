from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(
    page_title="Customer 360 Dashboard",
    page_icon="📊",
    layout="wide"
)

# 2. Database Connection Helper
# Path dynamically targets customer360.duckdb in data folder
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "customer360.duckdb"

@st.cache_data(ttl=60)
def fetch_gold_data():
    """Fetch gold_customer_360 table in read-only mode to prevent file locks."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("SELECT * FROM gold_customer_360").df()
    con.close()
    return df

# Load Data
try:
    df = fetch_gold_data()
except Exception as e:
    st.error(f"❌ Could not connect to database at `{DB_PATH}`: {e}")
    st.stop()

# 3. Sidebar Filters
st.sidebar.header("🔍 Filter Options")

selected_segments = st.sidebar.multiselect(
    "Customer Segment",
    options=df["customer_segment"].unique(),
    default=df["customer_segment"].unique()
)

selected_status = st.sidebar.multiselect(
    "Activity Status",
    options=df["customer_activity_status"].unique(),
    default=df["customer_activity_status"].unique()
)

# Apply Filters
filtered_df = df[
    (df["customer_segment"].isin(selected_segments)) &
    (df["customer_activity_status"].isin(selected_status))
]

# 4. Main Dashboard Title
st.title("📊 Customer 360 Data Product Dashboard")
st.caption(f"Showing **{len(filtered_df)}** of **{len(df)}** total customer profiles")
st.markdown("---")

# 5. Key Metrics Cards (KPIs)
m1, m2, m3, m4 = st.columns(4)

total_rev = filtered_df["total_spend"].sum()
avg_spend = filtered_df["average_order_value"].mean() if not filtered_df.empty else 0
tot_orders = filtered_df["total_orders"].sum()
tot_tickets = filtered_df["support_tickets"].sum()

m1.metric("Total Revenue", f"${total_rev:,.2f}")
m2.metric("Avg Order Value", f"${avg_spend:,.2f}")
m3.metric("Total Orders", f"{tot_orders:,}")
m4.metric("Support Tickets", f"{tot_tickets:,}")

st.markdown("---")

# 6. Interactive Charts
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Revenue by Segment")
    segment_revenue = filtered_df.groupby("customer_segment", as_index=False)["total_spend"].sum()
    fig_bar = px.bar(
        segment_revenue,
        x="customer_segment",
        y="total_spend",
        color="customer_segment",
        labels={"total_spend": "Total Spend ($)", "customer_segment": "Segment"},
        text_auto="$.2s"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_chart2:
    st.subheader("Customer Activity Status")
    fig_pie = px.pie(
        filtered_df,
        names="customer_activity_status",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# 7. Customer Search & Raw Data View
st.subheader("📋 Customer Search & Details")

search_term = st.text_input("Search customer by ID, First Name, or Email:")
if search_term:
    search_filtered = filtered_df[
        filtered_df["customer_id"].str.contains(search_term, case=False, na=False) |
        filtered_df["first_name"].str.contains(search_term, case=False, na=False) |
        filtered_df["email"].str.contains(search_term, case=False, na=False)
    ]
else:
    search_filtered = filtered_df

st.dataframe(
    search_filtered,
    use_container_width=True,
    hide_index=True
)
