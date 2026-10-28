import pytest
from app.client import APIClient, APIError
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

class Response:
    def __init__(self,status,headers=None): self.status_code=status; self.headers=headers or {}; self.text=""
    def json(self): return {"items":[],"has_more":False}
class Session:
    headers={}
    def __init__(self): self.n=0
    def get(self,*a,**k):
        self.n+=1
        return Response(429,{"Retry-After":"0"}) if self.n==1 else Response(200)

def test_rate_limit_retried_and_respects_header():
    c=APIClient("http://x","t",max_retries=2,sleep=lambda _:None); c.session=Session()
    assert c.get_page("orders",1,2)["items"]==[]
    assert c.retries==1 and c.session.n==2

def test_retry_exhaustion_is_a_pipeline_error():
    class AlwaysFail(Session):
        def get(self,*a,**k): return Response(503)
    c=APIClient("http://x","t",max_retries=2,sleep=lambda _:None); c.session=AlwaysFail()
    with pytest.raises(APIError,match="retry limit"):
        c.get_page("orders",1,2)
    assert c.retries==2

def test_malformed_json_is_fatal_and_not_retried():
    class BadJson(Response):
        def __init__(self): super().__init__(200)
        def json(self): raise ValueError("bad json")
    class BadSession(Session):
        def get(self,*a,**k): self.n+=1; return BadJson()
    c=APIClient("http://x","t",max_retries=3,sleep=lambda _:None); c.session=BadSession()
    with pytest.raises(APIError,match="malformed JSON"):
        c.get_page("orders",1,2)
    assert c.retries==0 and c.session.n==1

def test_http_date_retry_after_is_respected():
    class DateThenSuccess(Session):
        def get(self,*a,**k):
            self.n+=1
            if self.n==1: return Response(429,{"Retry-After":format_datetime(datetime.now(timezone.utc)+timedelta(seconds=2),usegmt=True)})
            return Response(200)
    delays=[]
    c=APIClient("http://x","t",max_retries=1,sleep=delays.append); c.session=DateThenSuccess()
    c.get_page("orders",1,2)
    assert len(delays)==1 and 0<=delays[0]<=2

def test_transient_timeout_is_retried():
    class TimeoutThenSuccess(Session):
        def get(self,*a,**k):
            self.n+=1
            if self.n==1: raise __import__("requests").Timeout("injected timeout")
            return Response(200)
    delays=[]
    c=APIClient("http://x","t",max_retries=2,backoff_base=.01,sleep=delays.append); c.session=TimeoutThenSuccess()
    assert c.get_page("orders",1,2)["items"]==[]
    assert c.retries==1 and delays==[.01]
