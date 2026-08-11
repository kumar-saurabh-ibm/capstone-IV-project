# Customer 360 Business Rules

## Revenue

Only orders with status:
- COMPLETED
- DELIVERED

contribute to `total_spend` and `total_orders`.

## Customer Segment

| Rule | Segment |
|---|---|
| total_spend >= 50000 | VIP |
| total_spend >= 25000 | HIGH_VALUE |
| total_orders >= 10 | FREQUENT |
| total_orders >= 3 | REGULAR |
| otherwise | OCCASIONAL |

## Activity Status

| Rule | Status |
|---|---|
| last order within 30 days | ACTIVE |
| last order 31–90 days ago | AT_RISK |
| more than 90 days or no order | INACTIVE |

## Customer Identity

One row in Customer 360 represents one unique customer.
