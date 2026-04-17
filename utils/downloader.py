import aiohttp
from PIL import Image
import io

async def download_image_async(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            data = await res.read()
            return Image.open(io.BytesIO(data)).convert("RGBA")
        