import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser
from aiogram import Bot
from aiogram.types import InputMediaPhoto

from config import RSS_URL, TWITTER_BEARER_TOKEN, TWITTER_USERNAMES
from database.mongo import groups_col, users_col

CHECK_INTERVAL = 300
LAST_SEEN_FILE = Path(__file__).resolve().parent / "last_news_state.json"
IMAGE_LIMIT = 10
TWITTER_API_BASE = "https://api.twitter.com/2"


def clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def load_state() -> Dict[str, str]:
    if not LAST_SEEN_FILE.exists():
        return {}
    try:
        return json.loads(LAST_SEEN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logging.warning("Could not load last news state: %s", exc)
        return {}


def save_state(state: Dict[str, str]) -> None:
    try:
        LAST_SEEN_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logging.error("Could not save last news state: %s", exc)


def clean_twitter_text(text: str) -> str:
    return clean_html(text)


def format_tweet(tweet: Dict[str, Any], username: str) -> str:
    text = clean_twitter_text(tweet.get("text", ""))
    created_at = tweet.get("created_at", "")
    tweet_id = tweet.get("id")
    url = f"https://twitter.com/{username}/status/{tweet_id}" if username and tweet_id else ""

    caption = ["🔥 <b>Twitter Update</b>"]
    if username:
        caption.append(f"👤 @{username}")
    if created_at:
        caption.append(f"🕒 {created_at}")
    if text:
        caption.append(text)
    if url:
        caption.append(f"🔗 {url}")

    return "\n\n".join(caption)


def extract_tweet_images(tweet: Dict[str, Any], includes: Dict[str, Any]) -> List[str]:
    image_urls: List[str] = []
    media_list = includes.get("media", []) if includes else []

    for media in media_list:
        if media.get("type") == "photo" and media.get("url"):
            image_urls.append(media["url"])

    if not image_urls:
        text = tweet.get("text", "")
        image_urls.extend(re.findall(r"https?://\S+\.(?:png|jpg|jpeg)", text))

    seen = []
    for url in image_urls:
        if url not in seen:
            seen.append(url)
    return seen[:IMAGE_LIMIT]


def is_dead_chat_error(exc: Exception) -> bool:
    reason = str(exc).lower()
    return any(
        token in reason
        for token in [
            "bot was blocked",
            "chat not found",
            "user is deactivated",
            "forbidden",
            "bot was kicked",
            "not in chat",
            "group is deactivated",
        ]
    )


async def send_post(
    bot: Bot,
    chat_id: int,
    text: str,
    image_urls: List[str],
    collection,
    filter_doc,
) -> bool:
    try:
        if image_urls:
            if len(image_urls) == 1:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image_urls[0],
                    caption=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            else:
                media = [
                    InputMediaPhoto(media=image_urls[0], caption=text, parse_mode="HTML")
                ]
                media.extend(InputMediaPhoto(media=url) for url in image_urls[1:IMAGE_LIMIT])
                await bot.send_media_group(chat_id=chat_id, media=media)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
        return True
    except Exception as exc:
        logging.error("Failed to send post to %s: %s", chat_id, exc)
        if collection is not None and is_dead_chat_error(exc):
            await collection.delete_one(filter_doc)
            logging.info("Removed dead chat %s from %s", chat_id, collection.name)
        return False


async def broadcast_all(bot: Bot, text: str, image_urls: List[str]) -> None:
    success = 0
    fail = 0

    async for user in users_col.find({}):
        if await send_post(bot, user["user_id"], text, image_urls, users_col, {"_id": user["_id"]}):
            success += 1
        else:
            fail += 1
        await asyncio.sleep(0.03)

    async for group in groups_col.find({}):
        if await send_post(bot, group["chat_id"], text, image_urls, groups_col, {"_id": group["_id"]}):
            success += 1
        else:
            fail += 1
        await asyncio.sleep(0.1)

    logging.info("News sent | Success: %s, Fail: %s", success, fail)


async def get_twitter_user_id(session: aiohttp.ClientSession, username: str) -> Optional[str]:
    url = f"{TWITTER_API_BASE}/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            logging.warning("Twitter user lookup failed for %s: %s", username, resp.status)
            return None
        payload = await resp.json()
    return payload.get("data", {}).get("id")


async def fetch_tweets_for_user(session: aiohttp.ClientSession, user_id: str) -> Optional[Dict[str, Any]]:
    params = {
        "max_results": "5",
        "tweet.fields": "created_at,attachments,author_id",
        "expansions": "attachments.media_keys",
        "media.fields": "url,type",
        "exclude": "retweets,replies",
    }
    url = f"{TWITTER_API_BASE}/users/{user_id}/tweets"
    async with session.get(url, params=params, headers={"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}) as resp:
        if resp.status != 200:
            logging.warning("Twitter timeline fetch failed for %s: %s", user_id, resp.status)
            return None
        return await resp.json()


async def get_twitter_updates() -> List[Dict[str, Any]]:
    updates: List[Dict[str, Any]] = []
    if not TWITTER_BEARER_TOKEN or not TWITTER_USERNAMES:
        return updates

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for username in TWITTER_USERNAMES:
            user_id = await get_twitter_user_id(session, username)
            if not user_id:
                continue
            payload = await fetch_tweets_for_user(session, user_id)
            if not payload:
                continue
            tweets = payload.get("data", [])
            includes = payload.get("includes", {})
            for tweet in tweets:
                updates.append({
                    "source": f"twitter:{username}",
                    "username": username,
                    "tweet": tweet,
                    "includes": includes,
                    "tweet_id": tweet.get("id"),
                    "created_at": tweet.get("created_at"),
                })
    updates.sort(key=lambda item: item.get("created_at") or "", reverse=False)
    return updates


async def news_worker(bot: Bot) -> None:
    state = load_state()
    if state:
        logging.info("Loaded last news state from file")

    logging.info("🟢 News Poller started")

    while True:
        try:
            sent_updated = False

            if TWITTER_BEARER_TOKEN and TWITTER_USERNAMES:
                updates = await get_twitter_updates()
                for update in updates:
                    source = update["source"]
                    tweet_id = update["tweet_id"]
                    last_id = state.get(source)
                    if last_id == tweet_id:
                        continue
                    if last_id is None:
                        state[source] = tweet_id
                        continue

                    caption = format_tweet(update["tweet"], update["username"])
                    images = extract_tweet_images(update["tweet"], update["includes"])
                    await broadcast_all(bot, caption, images)
                    state[source] = tweet_id
                    save_state(state)
                    logging.info("📢 New Twitter post broadcasted from %s", update["username"])
                    sent_updated = True

            if not sent_updated:
                feed = await fetch_rss()
                if feed.entries:
                    latest = feed.entries[0]
                    entry_id = latest.get("id") or latest.get("link") or latest.get("title")
                    if entry_id:
                        rss_key = "rss"
                        last_id = state.get(rss_key)
                        if last_id is None:
                            state[rss_key] = entry_id
                            save_state(state)
                            logging.info("Initialized RSS last seen state")
                        elif entry_id != last_id:
                            caption = "🔥 <b>RSS Update</b>\n\n"
                            title = clean_html(latest.get("title", ""))
                            published = clean_html(latest.get("published", "") or latest.get("updated", ""))
                            summary = clean_html(latest.get("summary", "") or latest.get("description", ""))
                            link = latest.get("link", "")
                            if title:
                                caption += f"📌 {title}\n\n"
                            if published:
                                caption += f"🕒 {published}\n\n"
                            if summary:
                                caption += f"{summary}\n\n"
                            if link:
                                caption += f"🔗 {link}"
                            images = []
                            if latest.get("media_content"):
                                images = [item.get("url") for item in latest.get("media_content", []) if isinstance(item, dict) and item.get("url")]
                            await broadcast_all(bot, caption, images)
                            state[rss_key] = entry_id
                            save_state(state)
                            logging.info("📢 New RSS post broadcasted")

        except Exception:
            logging.exception("News worker error")

        await asyncio.sleep(CHECK_INTERVAL)
