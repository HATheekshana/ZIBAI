import io
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from services.wish_logic import wish_single
from services.image_service import combine_images

router = Router()
BG = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

@router.message(Command("wish"))
async def wish_cmd(message: types.Message):
    res = await wish_single(message.from_user.id)
    if "error" in res: return await message.answer(res["error"])

    img = await combine_images(res["url"], BG, res["name"], res["rarity"])
    out = io.BytesIO()
    img.save(out, format="PNG")
    
    await message.answer_photo(
        photo=BufferedInputFile(out.getvalue(), filename="wish.png"),
        caption=f"{res['msg']} **{res['name']}**"
    )