"""Seeded synthetic order/customer source records."""
from datetime import datetime, timezone, timedelta
import random
from copy import deepcopy

def make_dataset(n=25,seed=731):
    rng=random.Random(seed); now=datetime(2025,1,1,tzinfo=timezone.utc)
    customers=[{"customer_id":f"C{i:07d}","name":f"Customer {i}","email":f"customer{i}@example.com","created_at":(now-timedelta(days=rng.randrange(500))).isoformat()} for i in range((n+4)//5)]
    orders=[]
    for i in range(n):
        c=customers[i%len(customers)]
        orders.append({"order_id":f"O{i:08d}","customer_id":c["customer_id"],"amount":f"{rng.randrange(100,100000)/100:.2f}","currency":"USD","status":rng.choice(["pending","paid","shipped"]),"updated_at":(now+timedelta(seconds=i)).isoformat(),"source_event_id":f"EVT-{i:08d}"})
    return {"customers":customers,"orders":orders}

def make_quality_dataset(n=25,seed=731):
    """Return deterministic normal input plus labelled data-quality scenarios."""
    dataset=make_dataset(n,seed)
    if not dataset["orders"]:
        return dataset
    original=dataset["orders"][0]
    original["unexpected_source_flag"]="additive-schema-change"
    dataset["orders"].append(deepcopy(original))
    conflict=deepcopy(original); conflict["amount"]="999.99"; dataset["orders"].append(conflict)
    missing=deepcopy(original); missing.pop("status"); missing["source_event_id"]="EVT-MISSING-STATUS"; dataset["orders"].append(missing)
    bad_fk=deepcopy(original); bad_fk.update(order_id="O-INVALID-FK",customer_id="C-DOES-NOT-EXIST",source_event_id="EVT-INVALID-FK"); dataset["orders"].append(bad_fk)
    late=deepcopy(original); late.update(source_event_id="EVT-LATE",status="refunded",updated_at="2024-01-01T00:00:00+00:00"); dataset["orders"].append(late)
    return dataset
