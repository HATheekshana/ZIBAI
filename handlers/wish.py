from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from services.wish_logic import wish_single, wish_ten
from services.image_service import combine_images
from io import BytesIO

router = Router()

@router.message(Command("wish"))
async def wish_cmd(message: Message):
    res = await wish_single(message.from_user.id)

    if res["error"]:
        await message.answer(res["error"])
        return

    img = await combine_images(res["image"], res["bg"], res["name"], res["rarity"])

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    photo = BufferedInputFile(buf.getvalue(), filename="wish.png")

    await message.answer_photo(
        photo=photo,
        caption=res["text"]
    )


@router.message(Command("wish10"))
async def wish10_cmd(message: Message):
    res = await wish_ten(message.from_user.id)

    img = await combine_images(res["image"], res["bg"], res["name"], res["rarity"])

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    photo = BufferedInputFile(buf.getvalue(), filename="wish10.png")

    await message.answer_photo(
        photo=photo,
        caption=res["text"]
    )