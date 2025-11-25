from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
from .store import store
from .common import FOLLOWER_COUNT, WRITE_QUORUM, follower_url, random_delay_before_replicate

app = FastAPI(title="kv-leader")

class PutReq(BaseModel):
    key: str
    value: str
    quorum: int | None = None

async def replicate_to_follower(follower_index: int, key: str, value: str, client: httpx.AsyncClient) -> bool:
    
    # wsait a small random delay (to simulate network lag), then POST to follower replicate endpoint.
    
    await random_delay_before_replicate()
    url = follower_url(follower_index)
    payload = {"key": key, "value": value}
    try:
        r = await client.post(url, json=payload, timeout=1.0)
        r.raise_for_status()
        return True
    except Exception:
        return False

@app.post('/put')
async def put(req: PutReq):
    # apply the write locally first
    await store.put(req.key, req.value)

    # determine required confirmations from followers
    effective_quorum = req.quorum if req.quorum is not None else WRITE_QUORUM
    effective_quorum = max(0, min(effective_quorum, FOLLOWER_COUNT))

    # prepare concurrent replication tasks to all followers
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(replicate_to_follower(i + 1, req.key, req.value, client)) for i in range(FOLLOWER_COUNT)]

        confirmations = 0
        remaining = set(tasks)

        # wait for tasks to finish as they complete; short-circuit when quorum reached
        while remaining and confirmations < effective_quorum:
            done, pending = await asyncio.wait(remaining, return_when=asyncio.FIRST_COMPLETED, timeout=2.0)
            if not done:
                # timeout waiting for any follower; break and evaluate confirmations so far
                break
            for d in done:
                remaining.remove(d)
                try:
                    result = d.result()
                except Exception:
                    result = False
                if result:
                    confirmations += 1

        # Cancel any remaining tasks (we don't wait for all followers in this simple lab)
        for p in list(remaining):
            try:
                p.cancel()
            except Exception:
                pass

    if confirmations >= effective_quorum:
        return {"status": "ok", "confirmed": confirmations}
    else:
        # if we didn't reach quorum, we fail the request (semi-synchronous policy)
        raise HTTPException(status_code=500, detail={"status": "failed", "confirmed": confirmations})

@app.get('/get/{key}')
async def get_key(key: str):
    v = await store.get(key)
    if v is None:
        raise HTTPException(status_code=404, detail='not found')
    return {"key": key, "value": v}

@app.get('/dump')
async def dump():
    return await store.items()
