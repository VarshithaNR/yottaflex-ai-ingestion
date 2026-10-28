"""Pydantic API payload schemas."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, ConfigDict

class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")
    customer_id: str
    name: str
    email: EmailStr
    created_at: datetime

class Order(BaseModel):
    model_config = ConfigDict(extra="allow")
    order_id: str
    customer_id: str
    amount: Decimal
    currency: str
    status: str
    updated_at: datetime
    source_event_id: str
