# Optional: Can be used to keep reference of loaded objects in RAM
CACHE = {}

def get_cached(key):
    return CACHE.get(key)