import os
import io
import asyncio
import logging
import aiohttp
from PIL import Image, ImageDraw, ImageFont

CACHE_DIR = "cache_assets"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

async def get_image_obj(url_or_path):
    if not isinstance(url_or_path, str) or not url_or_path.startswith("http"):
        return Image.open(url_or_path).convert("RGBA")

    filename = url_or_path.split("/")[-1]
    local_path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(local_path):
        return Image.open(local_path).convert("RGBA")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url_or_path, timeout=10) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    img = Image.open(io.BytesIO(content)).convert("RGBA")
                    img.save(local_path)
                    return img
                else:
                    logging.error(f"Image 404: {url_or_path}")
                    return Image.new("RGBA", (1280, 720), (45, 20, 84))
        except Exception as e:
            return Image.new("RGBA", (1280, 720), (45, 20, 84))

def render_logic(bg, char, name, rarity):
    bg_img = bg.copy()
    scale = bg_img.height / char.height
    char_resized = char.resize((int(char.width * scale), bg_img.height), Image.Resampling.LANCZOS)
    
    x = (bg_img.width - char_resized.width) // 2
    bg_img.paste(char_resized, (x, 0), char_resized)

    draw = ImageDraw.Draw(bg_img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    except:
        font = ImageFont.load_default()

    stars = "★" * rarity if isinstance(rarity, int) else str(rarity)
    draw.text((62, bg_img.height - 152), name, font=font, fill=(0,0,0)) 
    draw.text((60, bg_img.height - 150), name, font=font, fill=(255,255,255))
    draw.text((60, bg_img.height - 70), stars, font=font, fill=(255, 215, 0))
    return bg_img

async def combine_images(cha_path, bg_path, display_name, rarity):
    loop = asyncio.get_event_loop()
    bg = await get_image_obj(bg_path)
    char = await get_image_obj(cha_path)
    return await loop.run_in_executor(None, render_logic, bg, char, display_name, rarity)