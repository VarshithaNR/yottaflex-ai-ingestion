"""HTTP transport with bounded retry and Retry-After support."""
import time, requests

class APIError(RuntimeError): pass

class APIClient:
    def __init__(self, base_url, token, timeout=5, max_retries=3, backoff_base=.1, sleep=time.sleep):
        self.base_url=base_url.rstrip("/"); self.timeout=timeout; self.max_retries=max_retries; self.backoff_base=backoff_base; self.sleep=sleep; self.retries=0
        self.session=requests.Session(); self.session.headers["Authorization"]=f"Bearer {token}"
    def get_page(self, stream, page, page_size):
        for attempt in range(self.max_retries+1):
            try:
                r=self.session.get(f"{self.base_url}/{stream}",params={"page":page,"page_size":page_size},timeout=self.timeout)
                if r.status_code == 429 or r.status_code >= 500:
                    if attempt == self.max_retries: raise APIError(f"retry limit reached: HTTP {r.status_code}")
                    self.retries+=1; delay=float(r.headers.get("Retry-After",self.backoff_base*2**attempt)); self.sleep(delay); continue
                if r.status_code >= 400: raise APIError(f"permanent HTTP {r.status_code}: {r.text[:200]}")
                try: return r.json()
                except ValueError as exc: raise APIError("malformed JSON response") from exc
            except (requests.Timeout,requests.ConnectionError) as exc:
                if attempt == self.max_retries: raise APIError(f"retry limit reached: {exc}") from exc
                self.retries+=1; self.sleep(self.backoff_base*2**attempt)
