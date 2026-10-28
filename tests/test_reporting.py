from app.storage import Store

def test_empty_counts(tmp_path):
    assert Store(tmp_path/"x.db").counts()=={"customers":0,"orders":0,"order_events":0}
