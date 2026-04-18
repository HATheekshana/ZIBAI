import genshin
import os
from aiogram import Router, types
from aiogram.filters import Command
from database.mongo import users_col
from dotenv import load_dotenv

router5 = Router()
load_dotenv()

# Moved inside a helper to avoid global state issues
async def get_abyss_data(uid: str):
    cookies = {
        "ltuid_v2": os.getenv("LTUID_V2"),
        "ltoken_v2": os.getenv("LTOKEN_V2")
    }
    # Use 'async with' for better memory management
    async with genshin.Client(cookies, region=genshin.Region.OVERSEAS) as client:
        return await client.get_spiral_abyss(uid)
async def format_abyss_info(abyss_data):
    season = abyss_data.season
    res = f"⸸ SPIRAL ABYSS S{season} ⸸\n"

    for floor in sorted(abyss_data.floors, key=lambda x: x.floor):
        if floor.floor < 11: continue
        res += f"ꫂ❁ FLOOR {floor.floor}】\n"
        for chamber in floor.chambers:
            stars = "✮" * chamber.stars + "☆" * (3 - chamber.stars)
            res += f"⧽ Chamber {chamber.chamber} - {stars}\n"
        res += "╰➤─── ⋆⋅⸸⋅⋆ ──────\n\n"

    rank = abyss_data.ranks
    res += f"✎ Deepest Descent: {abyss_data.max_floor}\n"
    res += f"✎ Total Stars: {abyss_data.total_stars}\n"
    res += f"✎ Total Battles: {abyss_data.total_battles}\n"

    def get_rank_str(possible_attrs):
        for attr in possible_attrs:
            val = getattr(rank, attr, None)
            if val and isinstance(val, list) and len(val) > 0:
                return f"{val[0].value} ({val[0].name})"
        return "N/A"

    res += f"✎ Most Kills: {get_rank_str(['most_kills'])}\n"
    res += f"✎ Strongest Strike: {get_rank_str(['strongest_strike'])}\n"

    res += f"✎ Most Damage Taken: {get_rank_str(['take_damage', 'max_damage_taken', 'most_damage_taken'])}\n"

    res += f"✎ Most Bursts: {get_rank_str(['most_bursts', 'most_bursts_used'])}\n"
    res += f"✎ Most Skills: {get_rank_str(['most_skills', 'most_skills_used'])}\n"

    return res
@router5.message(Command("abyssinfo"))
async def abyss_info_command(message: types.Message):
    user_data = await users_col.find_one({"user_id": str(message.from_user.id)})
    if not user_data or "genshin_uid" not in user_data:
        return await message.answer("❌ Please /login <uid> first.")

    uid = str(user_data["genshin_uid"]).strip()
    status_msg = await message.answer("⏳ Fetching Abyss data from HoYoLAB...")

    try:
        abyss = await get_abyss_data(uid)
        formatted_text = await format_abyss_info(abyss) # Ensure format_abyss_info is defined
        await status_msg.edit_text(formatted_text)

    except genshin.errors.DataNotPublic:
        await status_msg.edit_text("❌ Your Abyss stats are private. Please enable 'Public' in HoYoLAB settings.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error fetching Abyss data: {str(e)}")