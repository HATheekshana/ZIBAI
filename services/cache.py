from PIL import Image

CACHE = {}

def preload_assets(asset_map: dict):
    """
    asset_map = {url: local_path}
    """
    for key, path in asset_map.items():
        CACHE[key] = Image.open(path).convert("RGBA")

def get_cached_image(key: str):
    return CACHE[key]