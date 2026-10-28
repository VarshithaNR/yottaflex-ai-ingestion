from app.validation import validate_order, validate_customer
from app.generator import make_dataset, make_quality_dataset

def test_valid_and_invalid_customer():
    row=make_dataset(1)["customers"][0]
    assert validate_customer(row)[0] is not None
    row["email"]="invalid"
    assert validate_customer(row)[1]

def test_customer_created_at_requires_timezone():
    row=make_dataset(1)["customers"][0]
    row["created_at"]="2025-01-01T00:00:00"
    assert "timezone" in validate_customer(row)[1]

def test_order_rules():
    row=make_dataset(1)["orders"][0]
    assert validate_order(row)[0]["amount"]==row["amount"]
    row["amount"]="-1"
    assert "non-negative" in validate_order(row)[1]

def test_null_required_values_and_naive_timestamp_are_rejected():
    row=make_dataset(1)["orders"][0]
    row["order_id"]=None
    assert validate_order(row)[1]
    row=make_dataset(1)["orders"][0]
    row["updated_at"]="2025-01-01T00:00:00"
    assert "timezone" in validate_order(row)[1]

def test_additive_schema_field_is_accepted_and_preserved():
    row=make_quality_dataset(1)["orders"][0]
    parsed,error=validate_order(row)
    assert error is None
    assert parsed["unexpected_source_flag"]=="additive-schema-change"
