from pathlib import Path
import duckdb
import pandas as pd
import datetime

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
        print(f"Error creating table for the query : {query} : \n\n Error message : {e}")\
            
            
# ==================================================================================================================
#                               Bronze DB Creation
# ==================================================================================================================
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


# =====================================================================================================================
#                                    Data Cleaning and Validation
# =====================================================================================================================
def clean_customers(table_name='customers', quarantine_tablename='quarantine_customers', bronze_connection=bronze_con, silver_connection=silver_con):
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
                f"""
                INSERT INTO {quarantine_tablename}
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
                f"""
                INSERT INTO {table_name}
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

def clean_orders(table_name='orders', quarantine_tablename='quarantine_orders', bronze_connection=bronze_con, silver_connection=silver_con):
    read_query = f'''select * from {table_name}'''
    try:
        df = pd.read_sql(read_query, bronze_connection)
        # print the top 10 data first
        print(df.head(10))

        # ------------------------------------- Handle Mismatched Columns ----------------------------------------------------
        required_columns = [
            'order_id',
            'customer_id',
            'order_date',
            'order_amount',
            'order_status',
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
        df["order_status"] = (
            df["order_status"]
            .str.strip()
            .str.upper()
        )

        # ----------------------------------------- Handling Date values -----------------------------------------------------------
        df["order_date"] = pd.to_datetime(
            df["order_date"],
            errors="coerce" # NaT for non-date values
        )
        # -----------------------------------------Handling Rejected Records -------------------------------------------------------
        df["rejection_reason"] = ""

        # ----------------------------------------- Validating Null Values ----------------------------------------------------------
        # Validate customer_id -> not null
        df.loc[
            df["order_id"].isna(),
            "rejection_reason"
        ] += "Missing order_id; "

        # Validate first_name -> not null
        df.loc[
            df["customer_id"].isna(),
            "rejection_reason"
        ] += "Missing customer_id; "

        # validating reagistration_date -> NaT
        df.loc[
            df["order_date"].isna(),
            "rejection_reason"
        ] += "Invalid order_date; "

        # ------------------------------------------- Handling Duplicate Values ------------------------------------------------------
        # Handling Primary key duplicates
        BUSINESS_KEY = ['order_id']
        business_key_duplicate_mask = df.duplicated(
            subset=BUSINESS_KEY,
            keep="first"
        )

        df.loc[
            business_key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate business key: order_id; "


        # ---------------------------------- Handling Values in Range --------------------------------------------------------------
        
        df.loc[
            ~df['order_status'].isin(['DELIVERED', 'CANCELLED', 'PENDING', 'COMPLETED']),
            "rejection_reason"
        ] += "key customer_status value not in the list ['DELIVERED', 'CANCELLED', 'PENDING']; "
        
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
                f"""
                INSERT INTO {quarantine_tablename}
                SELECT
                    order_id,
                    customer_id,
                    order_date,
                    order_amount,
                    order_status,
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
                f"""
                INSERT INTO {table_name}
                SELECT
                    order_id, 
                    customer_id,
                    order_date,
                    order_amount,
                    order_status
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
        
def clean_payments(
    table_name='payments',
    quarantine_tablename='quarantine_payments',
    bronze_connection=bronze_con,
    silver_connection=silver_con
):

    read_query = f'''SELECT * FROM {table_name}'''

    try:

        # ==========================================================
        # READ DATA FROM BRONZE
        # ==========================================================

        df = pd.read_sql(
            read_query,
            bronze_connection
        )

        print(df.head(10))

        # ==========================================================
        # HANDLE MISMATCHED COLUMNS
        # ==========================================================

        required_columns = [
            'payment_id',
            'order_id',
            'payment_date',
            'payment_amount',
            'payment_status'
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        print(f"Missing Columns : {missing_columns}")

        if missing_columns:
            raise ValueError(
                f"Missing columns: {missing_columns}"
            )

        # ==========================================================
        # CLEANING STRING COLUMNS
        # ==========================================================

        df["payment_id"] = (
            df["payment_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["order_id"] = (
            df["order_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["payment_status"] = (
            df["payment_status"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        # ==========================================================
        # HANDLE DATE VALUES
        # ==========================================================

        df["payment_date"] = pd.to_datetime(
            df["payment_date"],
            errors="coerce"
        )

        # ==========================================================
        # HANDLE NUMERIC VALUES
        # ==========================================================

        df["payment_amount"] = pd.to_numeric(
            df["payment_amount"],
            errors="coerce"
        )

        # ==========================================================
        # CREATE REJECTION REASON
        # ==========================================================

        df["rejection_reason"] = ""

        # ==========================================================
        # VALIDATE NULL VALUES
        # ==========================================================

        df.loc[
            df["payment_id"].isna(),
            "rejection_reason"
        ] += "Missing payment_id; "

        df.loc[
            df["order_id"].isna(),
            "rejection_reason"
        ] += "Missing order_id; "

        df.loc[
            df["payment_date"].isna(),
            "rejection_reason"
        ] += "Invalid payment_date; "

        df.loc[
            df["payment_amount"].isna(),
            "rejection_reason"
        ] += "Invalid payment_amount; "

        df.loc[
            df["payment_status"].isna(),
            "rejection_reason"
        ] += "Missing payment_status; "

        # ==========================================================
        # HANDLE DUPLICATE PAYMENT IDs
        # ==========================================================

        BUSINESS_KEY = ['payment_id']

        business_key_duplicate_mask = df.duplicated(
            subset=BUSINESS_KEY,
            keep="first"
        )

        df.loc[
            business_key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate business key: payment_id; "

        # ==========================================================
        # VALIDATE PAYMENT AMOUNT
        # ==========================================================

        df.loc[
            df["payment_amount"] < 0,
            "rejection_reason"
        ] += "payment_amount cannot be negative; "

        # ==========================================================
        # VALIDATE PAYMENT STATUS
        # ==========================================================

        df.loc[
            ~df["payment_status"].isin(
                ['SUCCESS', 'FAILED', 'REFUNDED']
            ),
            "rejection_reason"
        ] += (
            "payment_status not in "
            "['SUCCESS', 'FAILED', 'REFUNDED']; "
        )

        # ==========================================================
        # VALIDATE FOREIGN KEY: order_id
        #
        # payments.order_id
        #        ↓
        # orders.order_id
        # ==========================================================

        existing_orders = silver_connection.execute(
                    """
                    SELECT order_id
                    FROM orders
                    """
                ).fetchdf()

        existing_order_ids = set(
            existing_orders["order_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )
        

        invalid_order_fk_mask = (
            df["order_id"].notna()
            & ~df["order_id"].isin(existing_order_ids)
        )

        df.loc[
            invalid_order_fk_mask,
            "rejection_reason"
        ] += (
            "Invalid foreign key: order_id "
            "does not exist in orders; "
        )

        # ==========================================================
        # SPLIT VALID AND REJECTED RECORDS
        # ==========================================================

        rejected_df = df[
            df["rejection_reason"] != ""
        ].copy()

        valid_df = df[
            df["rejection_reason"] == ""
        ].copy()

        # ==========================================================
        # ADD QUARANTINE METADATA
        # ==========================================================

        rejected_df["rejected_at"] = datetime.datetime.now()

        rejected_df["source_table"] = table_name

        # ==========================================================
        # WRITE REJECTED RECORDS
        # ==========================================================

        if not rejected_df.empty:

            silver_connection.register(
                "quarantine_df",
                rejected_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {quarantine_tablename}
                SELECT
                    payment_id,
                    order_id,
                    payment_date,
                    payment_amount,
                    payment_status,
                    rejection_reason,
                    rejected_at,
                    source_table
                FROM quarantine_df
                """
            )

            silver_connection.unregister(
                "quarantine_df"
            )

        # ==========================================================
        # REMOVE VALIDATION COLUMN
        # ==========================================================

        valid_df = valid_df.drop(
            columns=["rejection_reason"]
        )

        # ==========================================================
        # WRITE VALID RECORDS TO SILVER
        # ==========================================================

        if not valid_df.empty:

            silver_connection.register(
                "valid_payments",
                valid_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {table_name}
                SELECT
                    payment_id,
                    order_id,
                    payment_date,
                    payment_amount,
                    payment_status
                FROM valid_payments
                """
            )

            silver_connection.unregister(
                "valid_payments"
            )

        # ==========================================================
        # PRINT SUMMARY
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
        print(
            f"Error while data cleaning for the table : "
            f"{table_name}\n\n"
            f"Error message : {e}"
        )

def clean_web_events(
    table_name='web_events',
    quarantine_tablename='quarantine_web_events',
    bronze_connection=bronze_con,
    silver_connection=silver_con
):

    read_query = f'''SELECT * FROM {table_name}'''

    try:

        # ==========================================================
        # READ DATA FROM BRONZE
        # ==========================================================

        df = pd.read_sql(
            read_query,
            bronze_connection
        )

        print(df.head(10))

        # ==========================================================
        # HANDLE MISMATCHED COLUMNS
        # ==========================================================

        required_columns = [
            'event_id',
            'customer_id',
            'event_date',
            'event_type',
            'channel'
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        print(f"Missing Columns : {missing_columns}")

        if missing_columns:
            raise ValueError(
                f"Missing columns: {missing_columns}"
            )

        # ==========================================================
        # CLEANING STRING COLUMNS
        # ==========================================================

        df["event_id"] = (
            df["event_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["customer_id"] = (
            df["customer_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["event_type"] = (
            df["event_type"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["channel"] = (
            df["channel"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        # ==========================================================
        # HANDLE DATE VALUES
        # ==========================================================

        df["event_date"] = pd.to_datetime(
            df["event_date"],
            errors="coerce"
        )

        # ==========================================================
        # CREATE REJECTION REASON
        # ==========================================================

        df["rejection_reason"] = ""

        # ==========================================================
        # VALIDATE NULL VALUES
        # ==========================================================

        df.loc[
            df["event_id"].isna(),
            "rejection_reason"
        ] += "Missing event_id; "

        df.loc[
            df["customer_id"].isna(),
            "rejection_reason"
        ] += "Missing customer_id; "

        df.loc[
            df["event_date"].isna(),
            "rejection_reason"
        ] += "Invalid event_date; "

        df.loc[
            df["event_type"].isna(),
            "rejection_reason"
        ] += "Missing event_type; "

        df.loc[
            df["channel"].isna(),
            "rejection_reason"
        ] += "Missing channel; "

        # ==========================================================
        # HANDLE DUPLICATE EVENT IDs
        # ==========================================================

        BUSINESS_KEY = ['event_id']

        business_key_duplicate_mask = df.duplicated(
            subset=BUSINESS_KEY,
            keep="first"
        )

        df.loc[
            business_key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate business key: event_id; "

        # ==========================================================
        # VALIDATE EVENT TYPE
        # ==========================================================

        df.loc[
            ~df["event_type"].isin(
                ['LOGIN', 'PRODUCT_VIEW', 'CART', 'SEARCH', 'PAGE_VIEW']
            ),
            "rejection_reason"
        ] += (
            "event_type not in "
            "['LOGIN', 'PRODUCT_VIEW', 'CART', 'SEARCH', 'PAGE_VEIW']; "
        )

        # ==========================================================
        # VALIDATE CHANNEL
        # ==========================================================

        df.loc[
            ~df["channel"].isin(
                ['EMAIL', 'MOBILE', 'WEB']
            ),
            "rejection_reason"
        ] += (
            "channel not in "
            "['EMAIL', 'MOBILE', 'WEB']; "
        )

        # ==========================================================
        # VALIDATE FOREIGN KEY: customer_id
        #
        # web_events.customer_id
        #        ↓
        # customers.customer_id
        # ==========================================================

        existing_customers = silver_connection.execute(
            """
            SELECT customer_id
            FROM customers
            """
        ).fetchdf()

        existing_customer_ids = set(
            existing_customers["customer_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        invalid_customer_fk_mask = (
            df["customer_id"].notna()
            & ~df["customer_id"].isin(existing_customer_ids)
        )

        df.loc[
            invalid_customer_fk_mask,
            "rejection_reason"
        ] += (
            "Invalid foreign key: customer_id "
            "does not exist in customers; "
        )

        # ==========================================================
        # SPLIT VALID AND REJECTED RECORDS
        # ==========================================================

        rejected_df = df[
            df["rejection_reason"] != ""
        ].copy()

        valid_df = df[
            df["rejection_reason"] == ""
        ].copy()

        # ==========================================================
        # ADD QUARANTINE METADATA
        # ==========================================================

        rejected_df["rejected_at"] = datetime.datetime.now()

        rejected_df["source_table"] = table_name

        # ==========================================================
        # WRITE REJECTED RECORDS
        # ==========================================================

        if not rejected_df.empty:

            silver_connection.register(
                "quarantine_df",
                rejected_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {quarantine_tablename}
                SELECT
                    event_id,
                    customer_id,
                    event_date,
                    event_type,
                    channel,
                    rejection_reason,
                    rejected_at,
                    source_table
                FROM quarantine_df
                """
            )

            silver_connection.unregister(
                "quarantine_df"
            )

        # ==========================================================
        # REMOVE VALIDATION COLUMN
        # ==========================================================

        valid_df = valid_df.drop(
            columns=["rejection_reason"]
        )

        # ==========================================================
        # WRITE VALID RECORDS TO SILVER
        # ==========================================================

        if not valid_df.empty:

            silver_connection.register(
                "valid_web_events",
                valid_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {table_name}
                SELECT
                    event_id,
                    customer_id,
                    event_date,
                    event_type,
                    channel
                FROM valid_web_events
                """
            )

            silver_connection.unregister(
                "valid_web_events"
            )

        # ==========================================================
        # PRINT SUMMARY
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

        print(
            f"Error while data cleaning for the table : "
            f"{table_name}\n\n"
            f"Error message : {e}"
        )

def clean_customer_support(
    table_name='customer_support',
    quarantine_tablename='quarantine_customer_support',
    bronze_connection=bronze_con,
    silver_connection=silver_con
):

    read_query = f'''SELECT * FROM {table_name}'''

    try:

        # ==========================================================
        # READ DATA FROM BRONZE
        # ==========================================================

        df = pd.read_sql(
            read_query,
            bronze_connection
        )

        print(df.head(10))

        # ==========================================================
        # HANDLE MISMATCHED COLUMNS
        # ==========================================================

        required_columns = [
            'ticket_id',
            'customer_id',
            'ticket_date',
            'category',
            'ticket_status'
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        print(f"Missing Columns : {missing_columns}")

        if missing_columns:
            raise ValueError(
                f"Missing columns: {missing_columns}"
            )

        # ==========================================================
        # CLEANING STRING COLUMNS
        # ==========================================================

        df["ticket_id"] = (
            df["ticket_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["customer_id"] = (
            df["customer_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["category"] = (
            df["category"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        df["ticket_status"] = (
            df["ticket_status"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        # ==========================================================
        # HANDLE DATE VALUES
        # ==========================================================

        df["ticket_date"] = pd.to_datetime(
            df["ticket_date"],
            errors="coerce"
        )

        # ==========================================================
        # CREATE REJECTION REASON
        # ==========================================================

        df["rejection_reason"] = ""

        # ==========================================================
        # VALIDATE NULL VALUES
        # ==========================================================

        df.loc[
            df["ticket_id"].isna(),
            "rejection_reason"
        ] += "Missing ticket_id; "

        df.loc[
            df["customer_id"].isna(),
            "rejection_reason"
        ] += "Missing customer_id; "

        df.loc[
            df["ticket_date"].isna(),
            "rejection_reason"
        ] += "Invalid ticket_date; "

        df.loc[
            df["category"].isna(),
            "rejection_reason"
        ] += "Missing category; "

        df.loc[
            df["ticket_status"].isna(),
            "rejection_reason"
        ] += "Missing ticket_status; "

        # ==========================================================
        # HANDLE DUPLICATE TICKET IDs
        # ==========================================================

        BUSINESS_KEY = ['ticket_id']

        business_key_duplicate_mask = df.duplicated(
            subset=BUSINESS_KEY,
            keep="first"
        )

        df.loc[
            business_key_duplicate_mask,
            "rejection_reason"
        ] += "Duplicate business key: ticket_id; "

        # ==========================================================
        # VALIDATE CATEGORY
        # ==========================================================

        df.loc[
            ~df["category"].isin(
                ['PRODUCT', 'ACCOUNT', 'DELIVERY', 'PAYMENT']
            ),
            "rejection_reason"
        ] += (
            "category not in "
            "['PRODUCT', 'ACCOUNT', 'DELIVERY', 'PAYMENT']; "
        )

        # ==========================================================
        # VALIDATE TICKET STATUS
        # ==========================================================

        df.loc[
            ~df["ticket_status"].isin(
                ['OPEN', 'CLOSED', 'RESOLVED']
            ),
            "rejection_reason"
        ] += (
            "ticket_status not in "
            "['OPEN', 'CLOSED', 'RESOLVED']; "
        )

        # ==========================================================
        # VALIDATE FOREIGN KEY: customer_id
        #
        # customer_support.customer_id
        #             ↓
        # customers.customer_id
        # ==========================================================

        existing_customers = silver_connection.execute(
            """
            SELECT customer_id
            FROM customers
            """
        ).fetchdf()

        existing_customer_ids = set(
            existing_customers["customer_id"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        invalid_customer_fk_mask = (
            df["customer_id"].notna()
            & ~df["customer_id"].isin(existing_customer_ids)
        )

        df.loc[
            invalid_customer_fk_mask,
            "rejection_reason"
        ] += (
            "Invalid foreign key: customer_id "
            "does not exist in customers; "
        )

        # ==========================================================
        # SPLIT VALID AND REJECTED RECORDS
        # ==========================================================

        rejected_df = df[
            df["rejection_reason"] != ""
        ].copy()

        valid_df = df[
            df["rejection_reason"] == ""
        ].copy()

        # ==========================================================
        # ADD QUARANTINE METADATA
        # ==========================================================

        rejected_df["rejected_at"] = datetime.datetime.now()

        rejected_df["source_table"] = table_name

        # ==========================================================
        # WRITE REJECTED RECORDS
        # ==========================================================

        if not rejected_df.empty:

            silver_connection.register(
                "quarantine_df",
                rejected_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {quarantine_tablename}
                SELECT
                    ticket_id,
                    customer_id,
                    ticket_date,
                    category,
                    ticket_status,
                    rejection_reason,
                    rejected_at,
                    source_table
                FROM quarantine_df
                """
            )

            silver_connection.unregister(
                "quarantine_df"
            )

        # ==========================================================
        # REMOVE VALIDATION COLUMN
        # ==========================================================

        valid_df = valid_df.drop(
            columns=["rejection_reason"]
        )

        # ==========================================================
        # WRITE VALID RECORDS TO SILVER
        # ==========================================================

        if not valid_df.empty:

            silver_connection.register(
                "valid_customer_support",
                valid_df
            )

            silver_connection.execute(
                f"""
                INSERT INTO {table_name}
                SELECT
                    ticket_id,
                    customer_id,
                    ticket_date,
                    category,
                    ticket_status
                FROM valid_customer_support
                """
            )

            silver_connection.unregister(
                "valid_customer_support"
            )

        # ==========================================================
        # PRINT SUMMARY
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

        print(
            f"Error while data cleaning for the table : "
            f"{table_name}\n\n"
            f"Error message : {e}"
        )


