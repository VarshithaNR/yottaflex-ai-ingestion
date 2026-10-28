"""Record validation and normalization."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from pydantic import ValidationError
from .models import Customer, Order

STATUSES = {"pending", "paid", "shipped", "cancelled", "refunded"}
CURRENCIES = {"USD", "EUR", "GBP", "INR", "CAD"}

def validate_customer(record: object) -> tuple[dict | None, str | None]:
    try:
        row = Customer.model_validate(record).model_dump(mode="python")
        if not row["customer_id"].strip(): return None, "customer_id must be non-empty"
        if not row["name"].strip(): return None, "name must be non-empty"
        created=row["created_at"]
        if created.tzinfo is None: return None, "created_at must include timezone"
        row["created_at"]=created.astimezone(timezone.utc).isoformat()
        row["email"]=str(row["email"])
        return row, None
    except (ValidationError, AttributeError, TypeError) as exc:
        return None, str(exc)

def validate_order(record: object) -> tuple[dict | None, str | None]:
    try:
        row = Order.model_validate(record).model_dump(mode="python")
        if not row["order_id"].strip(): return None, "order_id must be non-empty"
        if not row["customer_id"].strip(): return None, "customer_id must be non-empty"
        if not row["source_event_id"].strip() or not re.fullmatch(r"[A-Za-z0-9._:-]+", row["source_event_id"]):
            return None, "invalid source_event_id"
        amount = Decimal(str(row["amount"]))
        if not amount.is_finite() or amount < 0: return None, "amount must be finite and non-negative"
        if row["currency"] not in CURRENCIES: return None, "unsupported currency"
        if row["status"] not in STATUSES: return None, "unsupported status"
        ts = row["updated_at"]
        if ts.tzinfo is None: return None, "updated_at must include timezone"
        row["amount"] = str(amount.quantize(Decimal("0.01")))
        row["updated_at"] = ts.astimezone(timezone.utc).isoformat()
        return row, None
    except (ValidationError, AttributeError, TypeError, InvalidOperation, ValueError) as exc:
        return None, str(exc)
