from functools import lru_cache
import requests
from PIL import Image
from io import BytesIO

@lru_cache(maxsize=200)
def get_cached_image(url: str):
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert("RGBA")