import os
import random
import asyncio

FOLLOWER_COUNT = int(os.getenv('FOLLOWER_COUNT'))
MIN_DELAY_MS = float(os.getenv('MIN_DELAY_MS'))
MAX_DELAY_MS = float(os.getenv('MAX_DELAY_MS'))
WRITE_QUORUM = int(os.getenv('WRITE_QUORUM'))
FOLLOWER_BASE_URL = os.getenv('FOLLOWER_BASE_URL')

def follower_url(i: int) -> str:
    return f"http://follower{i}:{8000 + i}/replicate"

async def random_delay_before_replicate():
    d_ms = random.uniform(MIN_DELAY_MS, MAX_DELAY_MS)
    await asyncio.sleep(d_ms / 1000.0)
