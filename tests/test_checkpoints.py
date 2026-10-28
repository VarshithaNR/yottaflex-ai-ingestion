from app.storage import Store

def test_checkpoint_starts_at_one_and_advances_atomically(tmp_path):
    s=Store(tmp_path/"x.db")
    assert s.checkpoint("orders")==1
    s.save_page("orders",1,lambda c:None)
    assert s.checkpoint("orders")==2

def test_failed_page_callback_rolls_back_checkpoint_and_rows(tmp_path):
    s=Store(tmp_path/"x.db")
    def fail(c):
        c.execute("INSERT INTO checkpoints(stream,next_page) VALUES('sentinel',1)")
        raise RuntimeError("simulated interruption")
    try: s.save_page("orders",1,fail)
    except RuntimeError: pass
    assert s.checkpoint("orders")==1
    with s.connect() as c: assert c.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]==0
