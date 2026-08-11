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
    rejected_at timestamp,
    source_table varchar(30)
)'''

orders_schema = '''create table if not exists orders (
    order_id varchar(10) primary key,
    customer_id varchar(10),
    order_date date,
    order_amount numeric(10,2),
    order_status varchar(15),

    foreign key (customer_id)
    references customers(customer_id)
)
'''

quarantine_orders_schema = '''create table if not exists quarantine_orders(
    order_id varchar(10),
    customer_id varchar(10),
    order_date date,
    order_amount numeric(10,2),
    order_status varchar(15),
    rejection_reason varchar(100),
    rejected_at timestamp,
    source_table varchar(30)
)
'''

payments_schema = '''
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(10) PRIMARY KEY,
    order_id VARCHAR(10),
    payment_date DATE,
    payment_amount NUMERIC(10,2),
    payment_status VARCHAR(15),

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
)
'''

quarantine_payments_schema = '''
CREATE TABLE IF NOT EXISTS quarantine_payments (
    payment_id VARCHAR(10),
    order_id VARCHAR(10),
    payment_date DATE,
    payment_amount NUMERIC(10,2),
    payment_status VARCHAR(15),
    rejection_reason VARCHAR(100),
    rejected_at timestamp,
    source_table VARCHAR(30)
)
'''

customer_support_schema = '''
CREATE TABLE IF NOT EXISTS customer_support (
    ticket_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10),
    ticket_date DATE,
    category VARCHAR(30),
    ticket_status VARCHAR(15),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
)
'''

quarantine_customer_support_schema = '''
CREATE TABLE IF NOT EXISTS quarantine_customer_support (
    ticket_id VARCHAR(10),
    customer_id VARCHAR(10),
    ticket_date DATE,
    category VARCHAR(30),
    ticket_status VARCHAR(15),
    rejection_reason VARCHAR(100),
    rejected_at timestamp,
    source_table VARCHAR(30)
)
'''

web_events_schema = '''
CREATE TABLE IF NOT EXISTS web_events (
    event_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10),
    event_date DATE,
    event_type VARCHAR(30),
    channel VARCHAR(20),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
)
'''

quarantine_web_events_schema = '''
CREATE TABLE IF NOT EXISTS quarantine_web_events (
    event_id VARCHAR(10),
    customer_id VARCHAR(10),
    event_date DATE,
    event_type VARCHAR(30),
    channel VARCHAR(20),
    rejection_reason VARCHAR(100),
    rejected_at timestamp,
    source_table VARCHAR(30)
)
'''
