from pathlib import Path
import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "customer360.duckdb"

st.set_page_config(page_title="Customer 360", layout="wide")
st.title("Customer 360 Data Product")

st.info("Student task: connect this application to gold_customer_360.")

if not DB.exists():
    st.warning("Run the pipeline first.")
else:
    con = duckdb.connect(str(DB), read_only=True)
    customers = con.execute("SELECT * FROM gold_customer_360 LIMIT 0").fetchdf()
    st.write("TODO: implement customer search and summary.")
    con.close()
