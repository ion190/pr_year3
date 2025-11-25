import asyncio

class KVStore:
    def __init__(self):
        self._data = {}
        self._lock = asyncio.Lock()

    async def put(self, key: str, value: str):
        async with self._lock:
            self._data[key] = value

    async def get(self, key: str):
        async with self._lock:
            return self._data.get(key)

store = KVStore()
