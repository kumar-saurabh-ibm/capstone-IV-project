from pathlib import Path
import duckdb
import pandas as pd

# ------------------------------------------------------------------------------
# 1. PATH SETUP & DATABASE CONNECTION
# ------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "customer360.duckdb"
SOURCE = ROOT / "data" / "source"
CATALOG = ROOT / "catalog"

# Ensure output directories exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CATALOG.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB_PATH))


# ==============================================================================
# TODO 1: CREATE BRONZE TABLES FROM CSV FILES
# ==============================================================================
def create_bronze_table(file_path, table_name, connection):
    """Load a CSV file into a Bronze database table."""
    df = pd.read_csv(file_path)
    df.to_sql(
        name=f"bronze_{table_name}",
        con=connection,
        index=False,
        if_exists="replace"
    )
    print(f"  ✓ Bronze table created: bronze_{table_name}")


def create_bronze_db(source_path, connection):
    """Create Bronze tables from all CSV files in the source directory."""
    print("\n[1/6] Building Bronze Layer...")
    source_path = Path(source_path)
    for file_path in source_path.glob("*.csv"):
        table_name = file_path.stem
        try:
            create_bronze_table(file_path, table_name, connection)
        except Exception as e:
            print(f"  ❌ Failed to process {file_path.name}: {e}")


# ==============================================================================
# TODO 2: CREATE SILVER CLEANED/DEDUPLICATED TABLES
# ==============================================================================
def create_silver_tables(connection):
    """Clean, format, and deduplicate Bronze data into Silver tables."""
    print("\n[2/6] Building Silver Layer (Cleaning & Deduplicating)...")

    # 1a. Silver Customers (Cleaned)
    connection.execute("""
    CREATE OR REPLACE TABLE silver_customers AS
    SELECT 
        TRIM(customer_id) AS customer_id,
        TRIM(first_name) AS first_name,
        TRIM(last_name) AS last_name,
        LOWER(TRIM(email)) AS email,
        REGEXP_REPLACE(CAST(phone AS VARCHAR), '[^0-9]', '', 'g') AS phone,
        TRIM(state) AS state,
        CAST(registration_date AS DATE) AS registration_date,
        UPPER(TRIM(customer_status)) AS customer_status
    FROM bronze_customers;
    """)
    print("  ✓ Silver table created: silver_customers")

    # 1b. Silver Customers Deduplicated (Required by Lineage)
    connection.execute("""
    CREATE OR REPLACE TABLE silver_customers_dedup AS
    WITH ranked AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id 
                ORDER BY registration_date DESC
            ) AS rn
        FROM silver_customers
    )
    SELECT customer_id, first_name, last_name, email, phone, state, registration_date, customer_status
    FROM ranked
    WHERE rn = 1;
    """)
    print("  ✓ Silver table created: silver_customers_dedup")

    # 2. Silver Orders
    connection.execute("""
    CREATE OR REPLACE TABLE silver_orders AS
    WITH ranked AS (
        SELECT 
            TRIM(order_id) AS order_id,
            TRIM(customer_id) AS customer_id,
            CAST(order_date AS DATE) AS order_date,
            CAST(order_amount AS DECIMAL(10, 2)) AS order_amount,
            UPPER(TRIM(order_status)) AS order_status,
            ROW_NUMBER() OVER (
                PARTITION BY TRIM(order_id) 
                ORDER BY order_date DESC
            ) AS rn
        FROM bronze_orders
        WHERE order_amount >= 0 AND customer_id IS NOT NULL
    )
    SELECT order_id, customer_id, order_date, order_amount, order_status
    FROM ranked
    WHERE rn = 1;
    """)
    print("  ✓ Silver table created: silver_orders")

    # 3. Silver Payments
    connection.execute("""
    CREATE OR REPLACE TABLE silver_payments AS
    WITH ranked AS (
        SELECT 
            TRIM(payment_id) AS payment_id,
            TRIM(order_id) AS order_id,
            CAST(payment_date AS DATE) AS payment_date,
            CAST(payment_amount AS DECIMAL(10, 2)) AS payment_amount,
            UPPER(TRIM(payment_status)) AS payment_status,
            ROW_NUMBER() OVER (
                PARTITION BY TRIM(payment_id) 
                ORDER BY payment_date DESC
            ) AS rn
        FROM bronze_payments
        WHERE payment_amount >= 0
    )
    SELECT payment_id, order_id, payment_date, payment_amount, payment_status
    FROM ranked
    WHERE rn = 1;
    """)
    print("  ✓ Silver table created: silver_payments")

    # 4. Silver Customer Support
    connection.execute("""
    CREATE OR REPLACE TABLE silver_customer_support AS
    WITH ranked AS (
        SELECT 
            TRIM(ticket_id) AS ticket_id,
            TRIM(customer_id) AS customer_id,
            CAST(ticket_date AS DATE) AS ticket_date,
            UPPER(TRIM(category)) AS category,
            UPPER(TRIM(ticket_status)) AS ticket_status,
            ROW_NUMBER() OVER (
                PARTITION BY TRIM(ticket_id) 
                ORDER BY ticket_date DESC
            ) AS rn
        FROM bronze_customer_support
    )
    SELECT ticket_id, customer_id, ticket_date, category, ticket_status
    FROM ranked
    WHERE rn = 1;
    """)
    print("  ✓ Silver table created: silver_customer_support")

    # 5. Silver Web Events
    connection.execute("""
    CREATE OR REPLACE TABLE silver_web_events AS
    WITH ranked AS (
        SELECT 
            TRIM(event_id) AS event_id,
            TRIM(customer_id) AS customer_id,
            CAST(event_date AS DATE) AS event_date,
            UPPER(TRIM(event_type)) AS event_type,
            UPPER(TRIM(channel)) AS channel,
            ROW_NUMBER() OVER (
                PARTITION BY TRIM(event_id) 
                ORDER BY event_date DESC
            ) AS rn
        FROM bronze_web_events
    )
    SELECT event_id, customer_id, event_date, event_type, channel
    FROM ranked
    WHERE rn = 1;
    """)
    print("  ✓ Silver table created: silver_web_events")


# ==============================================================================
# TODO 3: CREATE GOLD CUSTOMER METRICS
# ==============================================================================
def create_gold_metrics(connection):
    """Aggregate metrics according to Business Rules (Only COMPLETED/DELIVERED orders)."""
    print("\n[3/6] Building Gold Customer Metrics...")

    # 1. Orders metric: Only COMPLETED or DELIVERED orders contribute
    connection.execute("""
    CREATE OR REPLACE TABLE gold_customer_orders AS
    SELECT 
        customer_id,
        COUNT(CASE WHEN order_status IN ('COMPLETED', 'DELIVERED') THEN order_id END) AS total_orders,
        COALESCE(SUM(CASE WHEN order_status IN ('COMPLETED', 'DELIVERED') THEN order_amount ELSE 0.00 END), 0.00) AS total_spend,
        COALESCE(AVG(CASE WHEN order_status IN ('COMPLETED', 'DELIVERED') THEN order_amount END), 0.00) AS average_order_value,
        MIN(CASE WHEN order_status IN ('COMPLETED', 'DELIVERED') THEN order_date END) AS first_order_date,
        MAX(CASE WHEN order_status IN ('COMPLETED', 'DELIVERED') THEN order_date END) AS last_order_date
    FROM silver_orders
    GROUP BY customer_id;
    """)

    # 2. Support metric
    connection.execute("""
    CREATE OR REPLACE TABLE gold_customer_support AS
    SELECT 
        customer_id,
        COUNT(ticket_id) AS support_tickets,
        COUNT(CASE WHEN ticket_status IN ('RESOLVED', 'CLOSED') THEN 1 END) AS resolved_tickets
    FROM silver_customer_support
    GROUP BY customer_id;
    """)

    # 3. Web Engagement metric
    connection.execute("""
    CREATE OR REPLACE TABLE gold_customer_engagement AS
    SELECT 
        customer_id,
        COUNT(event_id) AS web_events,
        COUNT(DISTINCT event_date) AS web_active_days,
        MAX(event_date) AS last_activity_date
    FROM silver_web_events
    GROUP BY customer_id;
    """)
    print("  ✓ Created Gold metric tables: gold_customer_orders, gold_customer_support, gold_customer_engagement")


# ==============================================================================
# TODO 4: CREATE GOLD_CUSTOMER_360
# ==============================================================================
def create_gold_customer_360(connection):
    """Join silver_customers_dedup with Gold metrics & apply Business Rules."""
    print("\n[4/6] Building Unified `gold_customer_360` Data Product...")

    connection.execute("""
    CREATE OR REPLACE TABLE gold_customer_360 AS
    WITH max_orders AS (
        SELECT MAX(last_order_date) AS max_order_date FROM gold_customer_orders
    )
    SELECT 
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.phone,
        c.state,
        c.registration_date,
        
        COALESCE(o.total_orders, 0) AS total_orders,
        COALESCE(o.total_spend, 0.00) AS total_spend,
        COALESCE(o.average_order_value, 0.00) AS average_order_value,
        o.first_order_date,
        o.last_order_date,
        
        COALESCE(s.support_tickets, 0) AS support_tickets,
        COALESCE(s.resolved_tickets, 0) AS resolved_tickets,
        
        COALESCE(e.web_events, 0) AS web_events,
        COALESCE(e.web_active_days, 0) AS web_active_days,
        e.last_activity_date,
        
        -- Business Rules: Customer Segment
        CASE 
            WHEN COALESCE(o.total_spend, 0) >= 50000 THEN 'VIP'
            WHEN COALESCE(o.total_spend, 0) >= 25000 THEN 'HIGH_VALUE'
            WHEN COALESCE(o.total_orders, 0) >= 10 THEN 'FREQUENT'
            WHEN COALESCE(o.total_orders, 0) >= 3 THEN 'REGULAR'
            ELSE 'OCCASIONAL'
        END AS customer_segment,
        
        -- Business Rules: Activity Status based on last order date recency
        CASE 
            WHEN o.last_order_date IS NULL THEN 'INACTIVE'
            WHEN o.last_order_date >= (SELECT max_order_date FROM max_orders) - INTERVAL 30 DAY THEN 'ACTIVE'
            WHEN o.last_order_date >= (SELECT max_order_date FROM max_orders) - INTERVAL 90 DAY THEN 'AT_RISK'
            ELSE 'INACTIVE'
        END AS customer_activity_status,
        
        CURRENT_DATE AS product_refresh_date

    FROM silver_customers_dedup c
    LEFT JOIN gold_customer_orders o ON c.customer_id = o.customer_id
    LEFT JOIN gold_customer_support s ON c.customer_id = s.customer_id
    LEFT JOIN gold_customer_engagement e ON c.customer_id = e.customer_id;
    """)
    print("  ✓ Published `gold_customer_360` data product.")


# ==============================================================================
# TODO 5: RUN DATA QUALITY CHECKS
# ==============================================================================
def run_data_quality_checks(connection):
    """Execute quality tests against gold_customer_360."""
    print("\n[5/6] Executing Data Quality Checks...")

    checks = []

    # Check 1: Primary key non-null & unique
    null_pk = connection.execute("SELECT COUNT(*) FROM gold_customer_360 WHERE customer_id IS NULL OR customer_id = ''").fetchone()[0]
    dup_pk = connection.execute("SELECT COUNT(customer_id) - COUNT(DISTINCT customer_id) FROM gold_customer_360").fetchone()[0]
    checks.append({
        "test_name": "Customer ID Not Null & Unique",
        "passed": null_pk == 0 and dup_pk == 0,
        "details": f"Nulls: {null_pk}, Duplicates: {dup_pk}"
    })

    # Check 2: Non-negative spend
    neg_spend = connection.execute("SELECT COUNT(*) FROM gold_customer_360 WHERE total_spend < 0").fetchone()[0]
    checks.append({
        "test_name": "Non-Negative Spend Check",
        "passed": neg_spend == 0,
        "details": f"Negative spend records: {neg_spend}"
    })

    # Check 3: Non-negative order count
    neg_orders = connection.execute("SELECT COUNT(*) FROM gold_customer_360 WHERE total_orders < 0").fetchone()[0]
    checks.append({
        "test_name": "Non-Negative Order Count Check",
        "passed": neg_orders == 0,
        "details": f"Negative order records: {neg_orders}"
    })

    # Check 4: Valid segment enum
    invalid_seg = connection.execute("""
        SELECT COUNT(*) FROM gold_customer_360 
        WHERE customer_segment NOT IN ('VIP', 'HIGH_VALUE', 'FREQUENT', 'REGULAR', 'OCCASIONAL')
    """).fetchone()[0]
    checks.append({
        "test_name": "Valid Customer Segment Enum",
        "passed": invalid_seg == 0,
        "details": f"Invalid segment values: {invalid_seg}"
    })

    # Check 5: Valid activity status enum
    invalid_stat = connection.execute("""
        SELECT COUNT(*) FROM gold_customer_360 
        WHERE customer_activity_status NOT IN ('ACTIVE', 'AT_RISK', 'INACTIVE')
    """).fetchone()[0]
    checks.append({
        "test_name": "Valid Customer Activity Status Enum",
        "passed": invalid_stat == 0,
        "details": f"Invalid activity status values: {invalid_stat}"
    })

    for check in checks:
        status_str = "PASS ✓" if check["passed"] else "FAIL ❌"
        print(f"  • [{status_str}] {check['test_name']} ({check['details']})")

    return checks


# ==============================================================================
# TODO 6: WRITE A FINAL QUALITY REPORT
# ==============================================================================
def write_quality_report(checks, connection, catalog_dir):
    """Write markdown summary report to catalog directory."""
    print("\n[6/6] Writing Quality Report to Catalog...")

    catalog_path = Path(catalog_dir)
    catalog_path.mkdir(parents=True, exist_ok=True)
    report_file = catalog_path / "quality_report.md"

    all_passed = all(check["passed"] for check in checks)
    total_customers = connection.execute("SELECT COUNT(*) FROM gold_customer_360").fetchone()[0]
    total_revenue = connection.execute("SELECT SUM(total_spend) FROM gold_customer_360").fetchone()[0] or 0.0

    markdown_content = f"""# Customer 360 - Data Quality Validation Report

**Overall Status:** {'✅ ALL CHECKS PASSED' if all_passed else '❌ QUALITY CHECKS FAILED'}

## Quality Requirements Results

| Quality Requirement | Status | Verification Details |
| :--- | :--- | :--- |
"""
    for check in checks:
        status_icon = "PASS ✅" if check["passed"] else "FAIL ❌"
        markdown_content += f"| {check['test_name']} | {status_icon} | {check['details']} |\n"

    markdown_content += f"""
## Summary Metrics

* **Total Customer Profiles:** {total_customers}
* **Total Qualifying Revenue:** ${total_revenue:,.2f}
"""

    report_file.write_text(markdown_content, encoding="utf-8")
    print(f"  ✓ Quality report written to `{report_file}`")


# ------------------------------------------------------------------------------
# MAIN EXECUTION ORCHESTRATION
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    create_bronze_db(SOURCE, con)
    create_silver_tables(con)
    create_gold_metrics(con)
    create_gold_customer_360(con)
    
    qa_results = run_data_quality_checks(con)
    write_quality_report(qa_results, con, CATALOG)
    
    con.close()
    print("\n" + "=" * 60)
    print("✨ Customer 360 Pipeline Finished Successfully!")
    print("=" * 60)