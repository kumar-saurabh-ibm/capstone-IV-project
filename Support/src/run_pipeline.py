import datetime
from pathlib import Path
import pandas as pd
from utils import *
from schema import *


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


# TODO 1.1 : Run the script
create_bronze_db(SOURCE, bronze_con)

# TODO 2: create Silver cleaned/deduplicated tables


# TODO 2.1 : Create table in the silver database
create_table(customers_schema, silver_con)
create_table(quarantine_customer_schema, silver_con)


## data cleaning of the customers table data
def clean_customers(table_name='customers', bronze_connection=bronze_con, silver_connection=silver_con):
    read_query = f'''select * from {table_name}'''
    try:
        df = pd.read_sql(read_query, bronze_connection)
        # print the top 10 data first
        print(df.head(10))

        # ------------------------------------- Handle Mismatched Columns ----------------------------------------------------
        required_columns = [
            'customer_id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'state',
            'registration_date',
            'customer_status'
        ]
        missing_columns = [col for col in required_columns
                           if col not in df.columns]
        # print the missing columns
        print(f"Missing Columsn : {missing_columns}")

        if(missing_columns):
             raise ValueError(
                f"Missing columns: {missing_columns}"
            )

        # -------------------------------- Cleaning String Columns ----------------------------------------------------
        df["first_name"] = (
            df["first_name"]
            .str.strip()
            .str.lower()
            .str.title()
        )
        df["last_name"] = (
            df["last_name"]
            .str.strip()
            .str.lower()
            .str.title()
        )
        df["email"] = (
            df["email"]
            .str.strip()
            .str.lower()
        )
        df["phone"] = (
            df["phone"]
            .astype("string")
            .str.strip()
        )
        df["state"] = (
            df["state"]
            .str.strip()
            .str.lower()
            .str.title()
        )
        df["customer_status"] = (
            df["customer_status"]
            .str.strip()
            .str.upper()
        )

        # ----------------------------------------- Handling Date values -----------------------------------------------------------
        df["registration_date"] = pd.to_datetime(
            df["registration_date"],
            errors="coerce" # NaT for non-date values
        )
        # -----------------------------------------Handling Rejected Records -------------------------------------------------------
        df["rejection_reason"] = ""

        # ----------------------------------------- Validating Null Values ----------------------------------------------------------
        # Validate customer_id -> not null
        df.loc[
            df["customer_id"].isna(),
            "rejection_reason"
        ] += "Missing customer_id; "

        # Validate first_name -> not null
        df.loc[
            df["first_name"].isna(),
            "rejection_reason"
        ] += "Missing first_name; "

        # validating reagistration_date -> NaT
        df.loc[
            df["registration_date"].isna(),
            "rejection_reason"
        ] += "Invalid registration_date; "

        # ------------------------------------------- Handling Duplicate Values ------------------------------------------------------
        # Handling Primary key duplicates
        BUSINESS_KEY = ['customer_id']
        business_key_duplicate_mask = df.duplicated(
            subset=BUSINESS_KEY,
            keep="first"
        )

        df.loc[
            business_key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate business key: cutomer_id; "

        # Handling email duplicates
        key = ['email']
        key_duplicate_mask = df.duplicated(
            subset=key,
            keep='first'
        )
        df.loc[
            key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate key: email; "

        # Handling phone duplicates
        key = ['phone']
        key_duplicate_mask = df.duplicated(
            subset=key,
            keep='first'
        )
        df.loc[
            key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate key: phone; "

        # ---------------------------------- Handling Values in Range --------------------------------------------------------------
        
        df.loc[
            ~df['customer_status'].isin(['ACTIVE', 'INACTIVE', 'AT_RISK']),
            "rejection_reason"
        ] += "key customer_status value not in the list ['ACTIVE', 'INACTIVE', 'AT_RISK']; "
        
        # ==========================================================
        #  SPLIT VALID AND REJECTED RECORDS
        # ==========================================================

        rejected_df = df[
            df["rejection_reason"] != ""
        ].copy()

        valid_df = df[
            df["rejection_reason"] == ""
        ].copy()

        # ==========================================================
        #  ADD QUARANTINE METADATA
        # ==========================================================

        rejected_df["rejected_at"] = datetime.datetime.now()
        rejected_df["source_table"] = table_name

        # ==========================================================
        #  WRITE REJECTED RECORDS
        # ==========================================================

        if not rejected_df.empty:

            # Register Pandas DataFrame with DuckDB
            silver_connection.register(
                "quarantine_df",
                rejected_df
            )

            # Insert registered DataFrame into quarantine table
            silver_connection.execute(
                """
                INSERT INTO quarantine_customers
                SELECT
                    customer_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    state,
                    registration_date,
                    customer_status,
                    rejection_reason,
                    rejected_at,
                    source_table
                FROM quarantine_df
                """
            )

            # Remove temporary registration
            silver_connection.unregister(
                "quarantine_df"
            )

        # ==========================================================
        #  REMOVE VALIDATION COLUMN
        # ==========================================================

        valid_df = valid_df.drop(
            columns=["rejection_reason"]
        )

        

        # ==========================================================
        #  WRITE VALID RECORDS TO SILVER
        # ==========================================================

        if not valid_df.empty:

            # Register Pandas DataFrame with DuckDB
            silver_connection.register(
                "valid_customers",
                valid_df
            )

            # Insert registered DataFrame into Silver
            silver_connection.execute(
                """
                INSERT INTO customers
                SELECT
                    customer_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    state,
                    registration_date,
                    customer_status
                FROM valid_customers
                """
            )

            # Remove temporary registration
            silver_connection.unregister(
                "valid_customers"
            )

        # ==========================================================
        #  PRINT SUMMARY
        # ==========================================================

        print("=" * 50)

        print(
            f"Total Bronze records : {len(df)}"
        )

        print(
            f"Valid Silver records : {len(valid_df)}"
        )

        print(
            f"Rejected records     : {len(rejected_df)}"
        )

        print("=" * 50)
    except Exception as e:
        print(f"Error while data cleaning for the table : {table_name} \n\n Error message : {e}")

# TODO 2.2 : Run clean_customers() function
clean_customers()


# TODO 3: create Gold customer metrics
# TODO 4: create gold_customer_360
# TODO 5: run data quality checks
# TODO 6: write a final quality report

bronze_con.close()
silver_con.close()
