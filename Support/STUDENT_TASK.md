# Student Capstone Task

## Scenario

ShopEasy has customer data across multiple operational systems.

Your team must build a trusted Customer 360 data product.

## Source files

- customers.csv
- orders.csv
- payments.csv
- customer_support.csv
- web_events.csv

## Required outcome

Create:

```text
Bronze
  ↓
Silver
  ↓
Gold
  ↓
Customer 360
```

Then publish it as a documented data product.

## Task 1 — Profile sources

Identify:
- row counts
- nulls
- duplicates
- invalid values
- relationships

## Task 2 — Build Bronze

Load all source files into DuckDB.

## Task 3 — Build Silver

Clean and standardize the source data.

At minimum:
- normalize email
- normalize phone
- standardize status values
- remove invalid negative orders
- deduplicate customers

## Task 4 — Build Gold

Create:
- customer order metrics
- support metrics
- engagement metrics

## Task 5 — Build Customer 360

One row must represent one customer.

Required:
- identity
- total orders
- total spend
- average order value
- first order
- last order
- support tickets
- resolved tickets
- web events
- customer segment
- activity status

## Task 6 — Data quality

Implement at least five checks.

## Task 7 — Data product

Complete:
- product description
- owner
- consumers
- refresh
- business rules
- data dictionary
- lineage
- quality report

## Task 8 — Catalog

Demonstrate how a new consumer would discover Customer 360.

## Task 9 — Consumer

Create/run the Streamlit application.

## Final presentation

Explain:
1. Business problem
2. Architecture
3. Transformations
4. Customer 360
5. Quality
6. Product documentation
7. Catalog
8. Consumer
