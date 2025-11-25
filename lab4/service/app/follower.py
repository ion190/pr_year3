from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .store import store

app = FastAPI(title="kv-follower")

class ReplicateReq(BaseModel):
    key: str
    value: str

@app.post('/replicate')
async def replicate(req: ReplicateReq):
    # apply the replicated write locally
    await store.put(req.key, req.value)
    return {"status": "ok"}

@app.get('/get/{key}')
async def get_key(key: str):
    v = await store.get(key)
    if v is None:
        raise HTTPException(status_code=404, detail='not found')
    return {"key": key, "value": v}

@app.get('/dump')
async def dump():
    return await store.items()
