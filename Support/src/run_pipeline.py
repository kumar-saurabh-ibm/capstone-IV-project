from utils import *
from schema import *


print("Customer 360 starter pipeline")
print("TODO: implement Bronze, Silver and Gold transformations.")

# TODO 1: create Bronze tables from CSV files
create_bronze_db(SOURCE, bronze_con)

# TODO 2.1: create Silver cleaned/deduplicated tables

## Order of tables creation is important

# customers
create_table(customers_schema, silver_con)
create_table(quarantine_customer_schema, silver_con)

# orders
create_table(orders_schema, silver_con)
create_table(quarantine_orders_schema, silver_con)

# payments
create_table(payments_schema, silver_con)
create_table(quarantine_payments_schema, silver_con)

# customer support
create_table(customer_support_schema, silver_con)
create_table(quarantine_customer_support_schema, silver_con)

# web events 
create_table(web_events_schema, silver_con)
create_table(quarantine_web_events_schema, silver_con)


# TODO 2.2 : Clean and store the data in the silver DB
clean_customers()
clean_orders()
clean_payments()
clean_customer_support()
clean_web_events()


# TODO 3: create Gold customer metrics
# TODO 4: create gold_customer_360
# TODO 5: run data quality checks
# TODO 6: write a final quality report

bronze_con.close()
silver_con.close()
