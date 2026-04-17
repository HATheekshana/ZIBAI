import asyncio
from PIL import Image, ImageDraw, ImageFont
from services.cache import get_cached_image

def render_image(bg, char, name, rarity):

    bg = bg.copy().convert("RGBA")
    draw = ImageDraw.Draw(bg)

    scale = bg.height / char.height
    char = char.resize(
        (int(char.width * scale), bg.height),
        Image.Resampling.LANCZOS
    )

    x = (bg.width - char.width) // 2
    bg.paste(char, (x, 0), char)

    try:
        font = ImageFont.truetype("assets/fonts/arial.ttf", 60)
    except:
        font = ImageFont.load_default()

    draw.text((50, bg.height - 100), name, fill=(255, 255, 255), font=font)
    draw.text((50, bg.height - 40), "★" * rarity, fill=(255, 200, 0), font=font)

    return bg


async def combine_images(char_key, bg_key, name, rarity):

    loop = asyncio.get_event_loop()

    bg = await loop.run_in_executor(None, lambda: get_cached_image(bg_key))
    char = await loop.run_in_executor(None, lambda: get_cached_image(char_key))

    result = await loop.run_in_executor(
        None,
        render_image,
        bg,
        char,
        name,
        rarity
    )

    return result