"""Deterministic local FastAPI source with named fault scenarios."""
import os
from fastapi import FastAPI, Header, HTTPException, Query
from .generator import make_dataset

app=FastAPI(title="Reliable ingestion mock source")
token=os.getenv("API_TOKEN","demo-token")
scenario=os.getenv("MOCK_SCENARIO","normal")
dataset=make_dataset(int(os.getenv("MOCK_RECORDS","25")))
calls={}
def check(auth):
    if auth != f"Bearer {token}": raise HTTPException(401,"invalid bearer token")
def serve(stream, page, page_size, authorization):
    check(authorization); key=(stream,page); calls[key]=calls.get(key,0)+1
    if scenario=="retry-500-once" and calls[key]==1: raise HTTPException(500,"injected transient error")
    if scenario=="rate-limit-once" and calls[key]==1: raise HTTPException(429,"injected rate limit",headers={"Retry-After":"0"})
    items=dataset[stream]; start=(page-1)*page_size
    return {"items":items[start:start+page_size],"page":page,"has_more":start+page_size<len(items)}
@app.get("/customers")
def customers(page:int=Query(1,ge=1),page_size:int=Query(100,ge=1,le=1000),authorization:str|None=Header(None)):
    return serve("customers",page,page_size,authorization)
@app.get("/orders")
def orders(page:int=Query(1,ge=1),page_size:int=Query(100,ge=1,le=1000),authorization:str|None=Header(None)):
    return serve("orders",page,page_size,authorization)
