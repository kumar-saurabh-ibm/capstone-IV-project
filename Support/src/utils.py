from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1] # corrected to reach the "root" directory
BRONZE_DB = ROOT / "data"/ "bronze"/ "bronze_customer.duckdb"
SILVER_DB = ROOT / "data" / "silver" / "silver_customer.duckdb"
SOURCE = ROOT / "data" / "source"

bronze_con = duckdb.connect(str(BRONZE_DB))
silver_con = duckdb.connect(str(SILVER_DB))


# ====================================================================================================================
#                                  Utility Functions
# ====================================================================================================================

def remove_extension(filename):
    return Path(filename).stem

def create_table(query, connection):
    try:
        connection.execute(query)
    except Exception as e:
        print(f"Error creating table for the query : {query} : \n\n Error message : {e}")