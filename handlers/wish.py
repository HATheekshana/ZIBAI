from aiogram import Router
from aiogram.types import Message
from services.wish_logic import wish_single, wish_ten
from services.image_service import combine_images
from io import BytesIO

router = Router()


@router.message(commands=["wish"])
async def wish_cmd(message: Message):

    res = await wish_single(message.from_user.id)

    img = await combine_images(
        res["image"],
        res["image"],  # SAME KEY SYSTEM
        res["name"],
        res["rarity"]
    )

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    await message.answer_photo(buf, caption=res["text"])


@router.message(commands=["wish10"])
async def wish10_cmd(message: Message):

    res = await wish_ten(message.from_user.id)

    img = await combine_images(
        res["image"],
        res["image"],
        res["name"],
        res["rarity"]
    )

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    await message.answer_photo(buf, caption=res["text"])