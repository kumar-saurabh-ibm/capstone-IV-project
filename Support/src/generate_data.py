from pathlib import Path
import random
from datetime import date, timedelta
import pandas as pd
from faker import Faker

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)

BASE = Path(__file__).resolve().parents[1] / "data" / "source" # parents[2] moves to the parent directory
BASE.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 120
N_ORDERS = 420
N_PAYMENTS = 440
N_SUPPORT = 180
N_EVENTS = 600

states = ["Tamil Nadu", "Karnataka", "Telangana", "Maharashtra", "Kerala", "Delhi"]
statuses = ["COMPLETED", "DELIVERED", "CANCELLED", "PENDING"]
support_statuses = ["OPEN", "RESOLVED", "CLOSED"]
channels = ["WEB", "MOBILE", "EMAIL"]
event_types = ["PAGE_VIEW", "PRODUCT_VIEW", "LOGIN", "CART", "SEARCH"]

def random_date(days=365):
    return date.today() - timedelta(days=random.randint(0, days))

customers = []
for i in range(1, N_CUSTOMERS + 1):
    email = fake.email().lower()
    phone = fake.msisdn()[:10]
    customers.append({
        "customer_id": f"C{i:04d}",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": email,
        "phone": phone,
        "state": random.choice(states),
        "registration_date": random_date(900).isoformat(),
        "customer_status": random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "INACTIVE"])
    })

# Intentional quality issues
customers[4]["email"] = customers[4]["email"].upper()
customers[8]["phone"] = None
customers.append(customers[4].copy())  # duplicate customer

customer_ids = [c["customer_id"] for c in customers[:N_CUSTOMERS]]

orders = []
for i in range(1, N_ORDERS + 1):
    orders.append({
        "order_id": f"O{i:05d}",
        "customer_id": random.choice(customer_ids),
        "order_date": random_date(365).isoformat(),
        "order_amount": round(random.uniform(500, 35000), 2),
        "order_status": random.choice(statuses)
    })

# Intentional negative amount and duplicate order
orders[10]["order_amount"] = -1200
orders.append(orders[20].copy())

payments = []
for i in range(1, N_PAYMENTS + 1):
    payments.append({
        "payment_id": f"P{i:05d}",
        "order_id": random.choice([o["order_id"] for o in orders[:N_ORDERS]]),
        "payment_date": random_date(365).isoformat(),
        "payment_amount": round(random.uniform(500, 35000), 2),
        "payment_status": random.choice(["SUCCESS", "SUCCESS", "FAILED", "REFUNDED"])
    })

support = []
for i in range(1, N_SUPPORT + 1):
    support.append({
        "ticket_id": f"T{i:05d}",
        "customer_id": random.choice(customer_ids),
        "ticket_date": random_date(365).isoformat(),
        "category": random.choice(["PAYMENT", "DELIVERY", "PRODUCT", "ACCOUNT"]),
        "ticket_status": random.choice(support_statuses)
    })

events = []
for i in range(1, N_EVENTS + 1):
    events.append({
        "event_id": f"E{i:05d}",
        "customer_id": random.choice(customer_ids),
        "event_date": random_date(180).isoformat(),
        "event_type": random.choice(event_types),
        "channel": random.choice(channels)
    })

pd.DataFrame(customers).to_csv(BASE / "customers.csv", index=False)
pd.DataFrame(orders).to_csv(BASE / "orders.csv", index=False)
pd.DataFrame(payments).to_csv(BASE / "payments.csv", index=False)
pd.DataFrame(support).to_csv(BASE / "customer_support.csv", index=False)
pd.DataFrame(events).to_csv(BASE / "web_events.csv", index=False)

print(f"Generated source data in {BASE}")
