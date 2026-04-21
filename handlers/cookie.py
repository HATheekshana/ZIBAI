
import genshin
from aiogram import Router, types ,F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile, InputMediaPhoto
import json
from aiogram.exceptions import TelegramBadRequest
import html
import calendar
from cryptography.fernet import Fernet
from aiogram.filters import Command, CommandObject
from datetime import datetime
from config import KEY
from database.mongo import users_col

cipher = Fernet(KEY)
cookie = Router()
@cookie.message(Command("cookie_login"))
async def cmd_cookie_login(message: types.Message, command: CommandObject):
    if message.chat.type != "private":
        return await message.reply("❌ <b>Private DMs only!</b>", parse_mode="HTML")

    if not command.args or len(command.args.split()) < 2:
        return await message.reply(
            "<b>Usage:</b>\n<code>/cookie_login [ltuid_v2] [ltoken_v2]</code>\n"
            "<b>Use /cookiehelp for tutorial </b>",
            parse_mode="HTML"
        )

    args = command.args.split()

    cookie_dict = {
        "ltuid_v2": args[0],
        "ltoken_v2": args[1]
    }

    if len(args) >= 3:
        cookie_dict["cookie_token_v2"] = args[2]

    check_client = genshin.Client(cookie_dict)
    check_client.region = genshin.Region.OVERSEAS

    try:
        await check_client.get_reward_info(game=genshin.Game.GENSHIN)

        all_accounts = await check_client.get_game_accounts()
        genshin_acc = next((acc for acc in all_accounts if acc.game == genshin.Game.GENSHIN), None)

        if not genshin_acc:
            return await message.reply("❌ <b>Error:</b> No Genshin accounts found.")

        encrypted_str = cipher.encrypt(json.dumps(cookie_dict).encode()).decode()

        await users_col.update_one(
            {"user_id": str(message.from_user.id)},
            {"$set": {
                "hoyolab_data": encrypted_str,
                "genshin_uid": genshin_acc.uid,
                "nickname": genshin_acc.nickname,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )

        status_msg = "all 3 tokens" if "cookie_token_v2" in cookie_dict else "2 tokens"
        await message.reply(
            f"<b>Success!</b> Logged in as <b>{genshin_acc.nickname}</b>.\n"
            f"Saved <b>{status_msg}</b> securely.",
            parse_mode="HTML"
        )

    except genshin.InvalidCookies:
        await message.reply("❌ <b>Error:</b> Tokens are invalid or expired.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ <b>Validation Failed:</b> <code>{str(e)}</code>", parse_mode="HTML")
def get_diary_markup(viewing_month: int):
    builder = InlineKeyboardBuilder()

    actual_month = datetime.now().month

    allowed_months = []
    for i in range(3):
        m = actual_month - i
        if m <= 0: m += 12
        allowed_months.append(m)

    prev_month = viewing_month - 1 if viewing_month > 1 else 12

    if prev_month not in allowed_months:
        btn_text = f"Back to {calendar.month_name[actual_month]}"
        btn_data = "diary_view_current"
    else:
        btn_text = f"{calendar.month_name[prev_month]}"
        btn_data = f"diary_view_{prev_month}"

    builder.row(types.InlineKeyboardButton(text=btn_text, callback_data=btn_data))

    if viewing_month != actual_month:
        builder.row(types.InlineKeyboardButton(text="Current Month", callback_data="diary_view_current"))

    return builder.as_markup()
def format_diary_report(diary: genshin.models.Diary) -> str:
    perc = diary.data.primogems_rate
    trend_emoji = "📈" if perc >= 0 else "📉"
    trend_text = "more" if perc >= 0 else "less"

    sources = ""
    for cat in diary.data.categories:
        sources += f"• {cat.name}: <b>{cat.percentage}%</b>\n"
    month_name = calendar.month_name[diary.month]
    return (
        f"<b>⋆˙⟡Traveler's Diary: {month_name}⟡˙⋆</b>\n"
        "─────── ୨୧ ───────\n"
        f"⚡︎ Primogems: <b>{diary.data.current_primogems}</b>\n"
        f"⚡︎ Mora: <b>{diary.data.current_mora}</b>\n\n"

        f"{trend_emoji} <b>Monthly Change:</b>\n"
        f"You got <b>{abs(perc)}%</b> {trend_text} than last month.\n\n"

        f"<b>Source Breakdown:</b>\n"
        f"{sources}"
        "─────── ୨୧ ───────"
    )

async def get_diary_client(user_id: str):
    """Helper to decrypt cookies and return a genshin Client."""
    user = await users_col.find_one({"user_id": str(user_id)})
    if not user or "hoyolab_data" not in user:
        return None

    decrypted_data = cipher.decrypt(user["hoyolab_data"].encode()).decode()
    cookies = json.loads(decrypted_data)

    client = genshin.Client(cookies)
    client.region = genshin.Region.OVERSEAS
    return client

@cookie.message(Command("diary"))
async def cmd_diary(message: types.Message):
    client = await get_diary_client(message.from_user.id)

    if not client:
        return await message.reply("<b>Not Logged In!</b>\nUse /cookie_login first.", parse_mode="HTML")

    status_msg = await message.reply("<b>Opening Diary...</b>", parse_mode="HTML")

    try:
        diary = await client.get_genshin_diary()
        await status_msg.edit_text(
            format_diary_report(diary),
            reply_markup=get_diary_markup(diary.month),
            parse_mode="HTML"
        )
    except Exception as e:
        await status_msg.edit_text(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")

@cookie.callback_query(F.data.startswith("diary_view_"))
async def handle_diary_pagination(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data_parts = callback.data.split("_")
    month_val = None if data_parts[-1] == "current" else int(data_parts[-1])

    await callback.answer("Updating Diary...")
    client = await get_diary_client(user_id)

    try:
        diary = await client.get_genshin_diary(month=month_val)
        new_text = format_diary_report(diary)
        new_markup = get_diary_markup(diary.month)

        await callback.message.edit_text(
            new_text,
            parse_mode="HTML",
            reply_markup=new_markup
        )

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise e

@cookie.message(Command("dailylogin"))
async def cmd_daily_login(message: types.Message):
    user = await users_col.find_one({"user_id": str(message.from_user.id)})

    if not user or "hoyolab_data" not in user:
        return await message.reply("<b>Not Logged In!</b>\nUse /cookie_login first.", parse_mode="HTML")

    try:
        decrypted_data = cipher.decrypt(user["hoyolab_data"].encode()).decode()
        cookies = json.loads(decrypted_data)

        client = genshin.Client(cookies)
        client.region = genshin.Region.OVERSEAS

        reward = await client.claim_daily_reward(game=genshin.Game.GENSHIN)

        safe_name = html.escape(message.from_user.full_name)
        await message.reply(
            f"<b>Daily Reward Claimed!</b>\n"
            f"User: <b>{safe_name}</b>\n"
            f"Reward: <b>{reward.amount}x {reward.name}</b>",
            parse_mode="HTML"
        )

    except genshin.AlreadyClaimed:
        await message.reply("<b>Already Done:</b> You've already claimed your reward today!", parse_mode="HTML")
    except genshin.InvalidCookies:
        await message.reply("<b>Expired:</b> Your cookies have expired. Please login again.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")
def get_guide_keyboard(step: int):
    builder = InlineKeyboardBuilder()

    if step > 1:
        builder.button(text="Back", callback_data=f"cookie_guide:{step-1}")

    if step < 5:
        builder.button(text="Next", callback_data=f"cookie_guide:{step+1}")
    else:
        builder.button(text="Done", callback_data="cookie_guide:close")

    builder.adjust(2)
    return builder.as_markup()

GUIDE_TEXTS = {
    1: "<b>Step 1: Login to HoYoLAB</b>\n\nOpen your browser and login to <a href='https://www.hoyolab.com'>hoyolab.com</a>. Make sure you are on the home page.",
    2: "<b>Step 2: Open Developer Tools</b>\n\nPress <code>Ctrl + Shift + I</code> (or <code>F12</code>) to open the Inspect panel. Click on the (1) aplication tab on top, then on the left side under (2)<code>Cookies</code>, click on Cookies and select the one under it.",
    3: "<b>Step 3: Scroll down and search for <code>ltuid_v2</code> and <code>ltoken_v2</code> values.</b>",
    4: "<b>Step 4: Click on the value and copy it</b>",
    5: "<b>Once you have both values, use the command:\n<code>/cookie_login [ltuid_v2] [ltoken_v2]</code>\n\nExample:\n<code>/cookie_login 123456789 v2_abcdefg...</code></b>"
}

GUIDE_IMAGES = {
    1: "images/tutorial/tutorial1.jpg",
    2: "images/tutorial/tutorial2.jpg",
    3: "images/tutorial/tutorial3.jpg",
    4: "images/tutorial/tutorial4.jpg",
    5: "images/tutorial/tutorial5.jpg"
}
@cookie.message(Command("cookiehelp"))
async def cmd_cookiehelp(message: types.Message):
    if message.chat.type != "private":
        return await message.reply("This command only works in Private DMs to protect your privacy.")

    photo = FSInputFile(GUIDE_IMAGES[1])
    await message.reply_photo(
        photo=photo,
        caption=GUIDE_TEXTS[1],
        reply_markup=get_guide_keyboard(1),
        parse_mode="HTML"
    )

@cookie.callback_query(F.data.startswith("cookie_guide:"))
async def handle_guide_navigation(callback: types.CallbackQuery):
    step = callback.data.split(":")[1]

    if step == "close":
        await callback.message.delete()
        return await callback.answer("Guide closed.")

    step = int(step)

    new_photo = InputMediaPhoto(
        media=FSInputFile(GUIDE_IMAGES[step]),
        caption=GUIDE_TEXTS[step],
        parse_mode="HTML"
    )

    await callback.message.edit_media(
        media=new_photo,
        reply_markup=get_guide_keyboard(step)
    )
    await callback.answer()
@cookie.message(Command("resin"))
async def cmd_resin(message: types.Message):
    user = await users_col.find_one({"user_id": str(message.from_user.id)})

    if not user or "hoyolab_data" not in user:
        return await message.reply("<b>Not Logged In!</b>\nUse /cookie_login first.", parse_mode="HTML")

    try:
        decrypted_data = cipher.decrypt(user["hoyolab_data"].encode()).decode()
        cookies = json.loads(decrypted_data)

        client = genshin.Client(cookies)
        client.region = genshin.Region.OVERSEAS

        notes = await client.get_genshin_notes()

        response = (
            f"<b>Current Resin:</b> {notes.current_resin}/{notes.max_resin}\n"
        )

        if notes.current_resin < notes.max_resin:
            recovery_time = notes.remaining_resin_recovery_time
            response += f"<b>Full Recovery:</b> {recovery_time}\n"
        else:
            response += "<b>Your Resin is full!</b>\n"

        response += f"\n<b>Daily Commissions:</b> {notes.completed_commissions}/{notes.max_commissions}"

        await message.reply(response, parse_mode="HTML")

    except genshin.InvalidCookies:
        await message.reply("<b>Expired:</b> Your cookies have expired. Please login again.", parse_mode="HTML")
    except genshin.DataNotPublic:
        await message.reply(
            "<b>Error:</b> Your Real-Time Notes are private.\n\n"
            "Go to HoYoLAB -> Settings -> Privacy Settings -> Enable 'Real-time Notes'.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")
