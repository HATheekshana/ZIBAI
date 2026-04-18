import aiohttp
async def get_enkadata(uid):
    url = f"https://enka.network/api/uid/{uid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                player_info = data.get("playerInfo", {})
                showcase = player_info.get("showAvatarInfoList", [])
                return {
                    "abyssfloor":player_info.get("towerFloorIndex", "Unknown"),
                    "abysslevel":player_info.get("towerLevelIndex", "Unknown"),
                    "nickname": player_info.get("nickname", "Unknown"),
                    "level": player_info.get("level", 0),
                    "achievements": player_info.get("finishAchievementNum", 0),
                    "worldLevel": player_info.get("worldLevel", 0),
                    "signature": player_info.get("signature", ""),
                    "nameCardId": player_info.get("nameCardId", ""),
                    "showAvatarInfoList": showcase
                }
            return {"abyssfloor": "?", "abysslevel": "?", "nickname": "Unknown", "level": 0, "achievements": 0, "worldLevel": 0, "signature": "", "nameCardId": "", "showAvatarInfoList": []}