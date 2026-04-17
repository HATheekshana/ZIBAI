import asyncio
from PIL import Image, ImageDraw, ImageFont
from services.cache import get_cached_image

def render_image(bg, char, name, rarity):
    bg = bg.copy().convert("RGBA")

    draw = ImageDraw.Draw(bg)

    # =========================
    # CHARACTER PLACEMENT AREA
    # =========================

    # scale character properly (old style "fit to height")
    scale = bg.height / char.height
    new_size = (int(char.width * scale), bg.height)
    char = char.resize(new_size, Image.Resampling.LANCZOS)

    x_offset = (bg.width - char.width) // 2
    bg.paste(char, (x_offset, 0), char)

    # =========================
    # TEXT LAYER (OLD STYLE)
    # =========================

    try:
        name_font = ImageFont.truetype("assets/fonts/ARIALBD 1.TTF", 80)
        star_font = ImageFont.truetype("assets/fonts/Arial-Unicode-MS.ttf", 60)
    except:
        name_font = ImageFont.load_default()
        star_font = ImageFont.load_default()

    stars = "★" * rarity if isinstance(rarity, int) else str(rarity)

    # shadow effect (old genshin style feel)
    draw.text((52, bg.height - 152), name, fill=(0, 0, 0, 180), font=name_font)
    draw.text((50, bg.height - 150), name, fill=(255, 255, 255), font=name_font)

    draw.text((52, bg.height - 92), stars, fill=(0, 0, 0, 180), font=star_font)
    draw.text((50, bg.height - 90), stars, fill=(255, 200, 0), font=star_font)

    return bg

async def combine_images(char_url, bg_url, name, rarity):

    bg = await get_cached_image(bg_url)
    char = await get_cached_image(char_url)

    loop = asyncio.get_event_loop()

    result = await loop.run_in_executor(
        None,
        render_image,
        bg,
        char,
        name,
        rarity
    )

    return result