import io
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, FSInputFile
from services.wish_logic import wish_single
from services.image_service import combine_images

router = Router()
BG = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

@router.message(Command("wish"))
async def wish_cmd(message: types.Message):
    res = await wish_single(str(message.from_user.id))
    if "error" in res: return await message.answer(res["error"])

    img = await combine_images(res["url"], BG, res["name"], res["rarity"])
    out = io.BytesIO()
    img.save(out, format="PNG")
    await message.answer_photo(BufferedInputFile(out.getvalue(), filename="w.png"), caption=f"{res['msg']} {res['name']}")

@router.message(Command("wish10"))
async def wish10_cmd(message: types.Message):
    results = []
    best = None
    for _ in range(10):
        r = await wish_single(str(message.from_user.id))
        if "error" in r: break
        results.append(f"꩜ {r['name']} {'★'*r['rarity']}")
        if not best or r['rarity'] > best['rarity']: best = r
    
    if not results: return await message.answer("Not enough wishes!")
    
    img = await combine_images(best["url"], BG, best["name"], best["rarity"])
    out = io.BytesIO()
    img.save(out, format="PNG")
    await message.answer_photo(BufferedInputFile(out.getvalue(), filename="w.png"), caption="\n".join(results))