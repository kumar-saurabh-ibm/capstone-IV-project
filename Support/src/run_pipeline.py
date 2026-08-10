from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "customer360.duckdb"
SOURCE = ROOT / "data" / "source"

con = duckdb.connect(str(DB))

print("Customer 360 starter pipeline")
print("TODO: implement Bronze, Silver and Gold transformations.")

# TODO 1: create Bronze tables from CSV files
# TODO 2: create Silver cleaned/deduplicated tables
# TODO 3: create Gold customer metrics
# TODO 4: create gold_customer_360
# TODO 5: run data quality checks
# TODO 6: write a final quality report

con.close()
