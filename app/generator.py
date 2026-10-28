"""Seeded synthetic order/customer source records."""
from datetime import datetime, timezone, timedelta
import random

def make_dataset(n=25,seed=731):
    rng=random.Random(seed); now=datetime(2025,1,1,tzinfo=timezone.utc)
    customers=[{"customer_id":f"C{i:07d}","name":f"Customer {i}","email":f"customer{i}@example.com","created_at":(now-timedelta(days=rng.randrange(500))).isoformat()} for i in range((n+4)//5)]
    orders=[]
    for i in range(n):
        c=customers[i%len(customers)]
        orders.append({"order_id":f"O{i:08d}","customer_id":c["customer_id"],"amount":f"{rng.randrange(100,100000)/100:.2f}","currency":"USD","status":rng.choice(["pending","paid","shipped"]),"updated_at":(now+timedelta(seconds=i)).isoformat(),"source_event_id":f"EVT-{i:08d}"})
    return {"customers":customers,"orders":orders}
