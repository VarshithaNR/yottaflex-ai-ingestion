from app.validation import validate_order, validate_customer
from app.generator import make_dataset

def test_valid_and_invalid_customer():
    row=make_dataset(1)["customers"][0]
    assert validate_customer(row)[0] is not None
    row["email"]="invalid"
    assert validate_customer(row)[1]

def test_order_rules():
    row=make_dataset(1)["orders"][0]
    assert validate_order(row)[0]["amount"]==row["amount"]
    row["amount"]="-1"
    assert "non-negative" in validate_order(row)[1]
