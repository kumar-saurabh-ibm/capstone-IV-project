# Create data contract for the Customers table
customers_schema = '''create table if not exists customers (
    customer_id varchar(10) primary key,
    first_name varchar(30) not null,
    last_name varchar(30),
    email varchar(30) unique,
    phone varchar(15) unique,
    state varchar(20),
    registration_date date,
    customer_status varchar(10)
);'''

quarantine_customer_schema = '''create table if not exists quarantine_customers (
    customer_id varchar(10),
    first_name varchar(30),
    last_name varchar(30),
    email varchar(30),
    phone varchar(15),
    state varchar(20),
    registration_date date,
    customer_status varchar(10),
    rejection_reason varchar(100),
    rejected_at date,
    source_table varchar(30)
)'''
