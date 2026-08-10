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
def create_bronze_table(file_path, table_name, connection):
    """Load a CSV file into a Bronze database table."""

    df = pd.read_csv(file_path)

    df.to_sql(
        name=table_name,
        con=connection,
        index=False,
        if_exists="replace"
    )

    print(f"Bronze table created: {table_name}")


def create_bronze_db(source_path, connection):
    """Create Bronze tables from all CSV files in the source directory."""

    source_path = Path(source_path)

    for file_path in source_path.glob("*.csv"):
        table_name = file_path.stem

        try:
            create_bronze_table(
                file_path,
                table_name,
                connection
            )

        except Exception as e:
            print(f"Failed to process {file_path.name}: {e}")


# Run the script
create_bronze_db(SOURCE, bronze_con)

# TODO 2: create Silver cleaned/deduplicated tables
# TODO 3: create Gold customer metrics
# TODO 4: create gold_customer_360
# TODO 5: run data quality checks
# TODO 6: write a final quality report

bronze_con.close()
