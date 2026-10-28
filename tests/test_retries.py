from app.client import APIClient

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
