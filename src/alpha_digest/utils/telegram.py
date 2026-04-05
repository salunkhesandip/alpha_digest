"""Telegram utilities for sending Alpha Digest summaries."""

import os
import datetime

from telegram import Bot

from src.alpha_digest.config import logger


async def send_summary_to_telegram(
    audio_path: str | None = None,
) -> str:
    """Send MP3 audio to a Telegram chat.

    Requires environment variables:
        TELEGRAM_BOT_TOKEN: Bot API token from BotFather
        TELEGRAM_CHAT_ID: Target chat/group ID

    Args:
        audio_path: Optional path to an MP3 file to send

    Returns:
        Status string: "sent", "skipped", or error message
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        return "skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"

    bot = Bot(token=bot_token)

    if audio_path and os.path.exists(audio_path):
        day_date = datetime.datetime.now().strftime("%A, %d %B %Y")
        caption = f"Alpha Digest - {day_date}"
        caption = caption[:1024]  # Telegram caption limit
        with open(audio_path, "rb") as audio:
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=f"Alpha Digest ({day_date})",
                caption=caption,
            )
        logger.info("Telegram: audio file sent to chat %s", chat_id)
        return "sent"

    return "skipped: no audio file available"
