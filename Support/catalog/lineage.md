# Customer 360 Lineage

```text
customers.csv
     ↓
bronze_customers
     ↓
silver_customers
     ↓
silver_customers_dedup
     ↓
gold_customer_360

orders.csv
     ↓
bronze_orders
     ↓
silver_orders
     ↓
gold_customer_orders
     ↓
gold_customer_360

customer_support.csv
     ↓
bronze_customer_support
     ↓
silver_customer_support
     ↓
gold_customer_support
     ↓
gold_customer_360

web_events.csv
     ↓
bronze_web_events
     ↓
silver_web_events
     ↓
gold_customer_engagement
     ↓
gold_customer_360
```

Important field lineage:

- `total_spend` ← orders.order_amount → qualifying order filter → SUM
- `total_orders` ← orders.order_id → qualifying order filter → COUNT
- `support_tickets` ← customer_support.ticket_id → COUNT
- `web_events` ← web_events.event_id → COUNT
- `customer_segment` ← total_spend / total_orders → business CASE logic
- `customer_activity_status` ← last_order_date → recency rules
