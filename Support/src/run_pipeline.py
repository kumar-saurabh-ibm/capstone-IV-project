from pathlib import Path
import duckdb
import pandas as pd
from utils import remove_extension

ROOT = Path(__file__).resolve().parents[1] # corrected to reach the "root" directory
BRONZE_DB = ROOT / "data"/ "bronze"/ "customer360.duckdb"
SOURCE = ROOT / "data" / "source"

bronze_con = duckdb.connect(str(BRONZE_DB))

print("Customer 360 starter pipeline")
print("TODO: implement Bronze, Silver and Gold transformations.")

# TODO 1: create Bronze tables from CSV files
def crete_bronze_table(file_name, table_name):
    try:
        table_path = file_name
        df = pd.read_csv(table_path, sep=",", header=0)
        df.to_sql(table_name, con=bronze_con, index=False)

        # verify if the table is created or not
        query = f'select * from {table_name} limit 5;'
        df = pd.read_sql(query, con=bronze_con)
        print(df)
    except Exception as e:
        print(f"Some error occured : {e}")

# read all the files from the source and convert it into bronze db
def create_bronze_DB(source_path):
    source_path = Path(source_path)

    for file_path in source_path.iterdir():
        if file_path.is_file():
            try:
                table_name = remove_extension(file_path)
                crete_bronze_table(file_path, table_name)
            except Exception as e:
                print(f"Some error occured in create_bronze_DB : {e}")


## Run this script to create bronze DB from the source database
create_bronze_DB(SOURCE)

# TODO 2: create Silver cleaned/deduplicated tables
# TODO 3: create Gold customer metrics
# TODO 4: create gold_customer_360
# TODO 5: run data quality checks
# TODO 6: write a final quality report

bronze_con.close()
