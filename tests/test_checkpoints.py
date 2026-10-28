from app.storage import Store

def test_checkpoint_starts_at_one_and_advances_atomically(tmp_path):
    s=Store(tmp_path/"x.db")
    assert s.checkpoint("orders")==1
    s.save_page("orders",1,lambda c:None)
    assert s.checkpoint("orders")==2
