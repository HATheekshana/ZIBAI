import aiohttp
from PIL import Image
from io import BytesIO
from functools import lru_cache

session = None

async def init_cache():
    global session
    session = aiohttp.ClientSession()

@lru_cache(maxsize=300)
def _memory_cache(url: str):
    return None  # placeholder only

async def get_cached_image(url: str):
    global session

    # memory hit (fast path)
    cached = _memory_cache(url)
    if cached:
        return cached.copy()

    async with session.get(url) as r:
        data = await r.read()
        img = Image.open(BytesIO(data)).convert("RGBA")
        _memory_cache.cache_clear()
        _memory_cache.cache_info()
        _memory_cache(url)  # store key
        return img.copy()