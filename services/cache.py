from PIL import Image
from io import BytesIO
import requests

def get_cached_image(url: str):
    r = requests.get(url, timeout=10)

    # ❗ Must be success
    if r.status_code != 200:
        raise ValueError(f"Bad response: {r.status_code}")

    content_type = r.headers.get("Content-Type", "")

    # ❗ Must be image
    if "image" not in content_type:
        raise ValueError(f"Not image response: {content_type}")

    data = r.content

    # ❗ prevent empty/corrupt
    if len(data) < 500:
        raise ValueError("Image too small or corrupted")

    try:
        return Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        raise ValueError("Invalid image format received")