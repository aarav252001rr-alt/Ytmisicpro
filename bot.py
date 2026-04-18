"""
bot.py — YT Music Telegram Bot
- Audio only (128 / 192 / 320 kbps)
- Playlist support (max 50 songs)
- Auto-delete files after 1 hour
- Webhook mode for Render free tier
"""

import os
import asyncio
import logging
from pathlib import Path
from threading import Timer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from downloader import search_youtube, download_audio, get_video_info, get_playlist_info, download_playlist_items

# ─── Config ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
RENDER_URL   = os.environ.get("RENDER_URL", "")   # e.g. https://ytbot.onrender.com
PORT         = int(os.environ.get("PORT", 8080))
WEBHOOK_PATH = "/webhook"

DOWNLOAD_DIR         = Path("downloads")
AUTO_DELETE_SECONDS  = 3600   # 1 hour

DOWNLOAD_DIR.mkdir(exist_ok=True)


# ─── Auto-delete helper ───────────────────────────────────────────────────────
def schedule_delete(path: str, delay: int = AUTO_DELETE_SECONDS):
    """delay seconds baad file silently delete karo."""
    def _del():
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Auto-deleted: {path}")
        except Exception as e:
            logger.warning(f"Delete failed {path}: {e}")

    t = Timer(delay, _del)
    t.daemon = True
    t.start()


# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 *YT Music Bot* — Swaagat hai!\n\n"
        "*Kya bhej sakte ho:*\n"
        "🔍 Song ka *naam* → search + download\n"
        "🔗 *YouTube song link* → seedha download\n"
        "📋 *YouTube playlist link* → poori playlist\n\n"
        "*Quality options:* `128` · `192` · `320` kbps\n\n"
        "⏰ Files *1 ghante* baad auto-delete ho jaati hain.\n\n"
        "_Bas bhejo, baaki main sambhal lunga!_ 🎶"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)


# ─── Message router ───────────────────────────────────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    is_yt      = "youtube.com" in text or "youtu.be" in text
    is_playlist = "list=" in text

    if is_yt and is_playlist:
        await handle_playlist(update, ctx, text)
    elif is_yt:
        await handle_yt_link(update, ctx, text)
    else:
        await handle_search(update, ctx, text)


# ─── Single YouTube link ──────────────────────────────────────────────────────
async def handle_yt_link(update: Update, ctx, url: str):
    msg = await update.message.reply_text("⏳ Link check kar raha hoon...")

    info = await asyncio.to_thread(get_video_info, url)
    if not info:
        await msg.edit_text("❌ Song nahi mila. Link sahi hai?")
        return

    ctx.user_data["url"]   = url
    ctx.user_data["title"] = info["title"]

    title = info["title"][:55]
    dur   = seconds_to_min(info.get("duration", 0))

    await msg.edit_text(
        f"🎵 *{title}*\n⏱ Duration: {dur}\n\nQuality chunno 👇",
        parse_mode="Markdown",
        reply_markup=audio_quality_keyboard()
    )


# ─── Search by name ───────────────────────────────────────────────────────────
async def handle_search(update: Update, ctx, query: str):
    msg = await update.message.reply_text(
        f"🔍 *{query}* dhundh raha hoon...", parse_mode="Markdown"
    )

    results = await asyncio.to_thread(search_youtube, query, max_results=5)
    if not results:
        await msg.edit_text("❌ Koi result nahi mila. Dusra naam try karo.")
        return

    buttons = []
    for i, r in enumerate(results):
        dur   = seconds_to_min(r.get("duration", 0))
        t     = r["title"]
        label = f"🎵 {t[:38]}… ({dur})" if len(t) > 38 else f"🎵 {t} ({dur})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"sel|{i}")])

    ctx.user_data["search_results"] = results
    await msg.edit_text(
        f"🔍 *{query}* ke results — ek chunno 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─── Playlist ─────────────────────────────────────────────────────────────────
async def handle_playlist(update: Update, ctx, url: str):
    msg = await update.message.reply_text("📋 Playlist check kar raha hoon...")

    info = await asyncio.to_thread(get_playlist_info, url)
    if not info:
        await msg.edit_text("❌ Playlist nahi mila. Link sahi ya public hai?")
        return

    count = info["count"]
    title = info["title"][:50]
    limit = min(count, 50)

    ctx.user_data["playlist_url"]   = url
    ctx.user_data["playlist_title"] = title
    ctx.user_data["playlist_count"] = count

    note = f"\n⚠️ Sirf pehle *50 songs* download honge." if count > 50 else ""
    await msg.edit_text(
        f"📋 *{title}*\n📀 {count} songs{note}\n\nQuality chunno 👇",
        parse_mode="Markdown",
        reply_markup=playlist_quality_keyboard()
    )


# ─── Callback handler ─────────────────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # ── Search result select ──
    if data.startswith("sel|"):
        idx     = int(data.split("|")[1])
        results = ctx.user_data.get("search_results", [])
        if idx >= len(results):
            await q.edit_message_text("❌ Error. Phir se search karo.")
            return

        song = results[idx]
        ctx.user_data["url"]   = song["url"]
        ctx.user_data["title"] = song["title"]

        title = song["title"][:55]
        dur   = seconds_to_min(song.get("duration", 0))

        await q.edit_message_text(
            f"🎵 *{title}*\n⏱ {dur}\n\nQuality chunno 👇",
            parse_mode="Markdown",
            reply_markup=audio_quality_keyboard()
        )

    # ── Single audio download ──
    elif data.startswith("aud|"):
        quality = data.split("|")[1]
        url     = ctx.user_data.get("url")
        title   = ctx.user_data.get("title", "song")

        if not url:
            await q.edit_message_text("❌ Session expire hua. Phir se bhejo.")
            return

        await q.edit_message_text(
            f"⬇️ Download ho raha hai...\n*{title[:45]}*\n_🎵 {quality} kbps_",
            parse_mode="Markdown"
        )

        try:
            file_path = await asyncio.to_thread(download_audio, url, quality, DOWNLOAD_DIR)
            schedule_delete(file_path)

            with open(file_path, "rb") as f:
                await q.message.reply_audio(
                    audio=f,
                    title=title[:64],
                    caption=(
                        f"🎵 *{title[:100]}*\n"
                        f"_Quality: {quality} kbps_\n"
                        f"⏰ 1 ghante baad auto-delete"
                    ),
                    parse_mode="Markdown"
                )

            await q.edit_message_text(
                f"✅ *{title[:50]}*\n_🎵 {quality} kbps — Sent!_\n\n"
                "⏰ File 1 ghante mein auto-delete ho jaayegi.",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Single download error: {e}")
            await q.edit_message_text(
                f"❌ Download fail hua.\n`{str(e)[:150]}`",
                parse_mode="Markdown"
            )

    # ── Playlist download ──
    elif data.startswith("pl|"):
        quality  = data.split("|")[1]
        pl_url   = ctx.user_data.get("playlist_url")
        pl_title = ctx.user_data.get("playlist_title", "Playlist")
        count    = ctx.user_data.get("playlist_count", 0)

        if not pl_url:
            await q.edit_message_text("❌ Session expire hua. Phir se bhejo.")
            return

        limit = min(count, 50)
        status_msg = await q.edit_message_text(
            f"⬇️ Playlist download shuru...\n"
            f"📋 *{pl_title}*\n"
            f"📀 {limit} songs · 🎵 {quality} kbps\n\n"
            "_Songs ek-ek karke aayenge..._",
            parse_mode="Markdown"
        )

        sent   = 0
        failed = 0

        async for item in download_playlist_items(pl_url, quality, DOWNLOAD_DIR, limit):
            if item["status"] == "ok":
                path   = item["path"]
                stitle = item["title"]
                schedule_delete(path)
                try:
                    with open(path, "rb") as f:
                        await q.message.reply_audio(
                            audio=f,
                            title=stitle[:64],
                            caption=f"🎵 *{stitle[:100]}*\n_Quality: {quality} kbps_",
                            parse_mode="Markdown"
                        )
                    sent += 1
                    # Progress update har 5 songs pe
                    if sent % 5 == 0:
                        await status_msg.edit_text(
                            f"⬇️ Playlist chal rahi hai...\n"
                            f"📋 *{pl_title}*\n"
                            f"✅ {sent}/{limit} done · ❌ {failed} failed",
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    logger.error(f"Send error {stitle}: {e}")
                    failed += 1
            else:
                failed += 1

        await status_msg.edit_text(
            f"✅ *Playlist Complete!*\n"
            f"📋 {pl_title}\n"
            f"📤 Sent: *{sent}* · ❌ Failed: *{failed}*\n\n"
            f"⏰ Files 1 ghante mein auto-delete ho jaayengi.",
            parse_mode="Markdown"
        )

    elif data == "cancel":
        await q.edit_message_text("❌ Cancelled.")


# ─── Keyboards ────────────────────────────────────────────────────────────────
def audio_quality_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 128 kbps", callback_data="aud|128"),
            InlineKeyboardButton("🎵 192 kbps", callback_data="aud|192"),
            InlineKeyboardButton("🎵 320 kbps", callback_data="aud|320"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


def playlist_quality_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 128 kbps", callback_data="pl|128"),
            InlineKeyboardButton("🎵 192 kbps", callback_data="pl|192"),
            InlineKeyboardButton("🎵 320 kbps", callback_data="pl|320"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])


def seconds_to_min(sec):
    if not sec:
        return "?:??"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


# ─── Main ─────────────────────────────────────────────────────────────────────
import asyncio as _asyncio

async def _run():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN env variable set nahi hai!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    if RENDER_URL:
        webhook_url = f"{RENDER_URL.rstrip('/')}{WEBHOOK_PATH}"
        logger.info(f"🚀 Webhook mode | {webhook_url} | port={PORT}")
        async with app:
            await app.bot.set_webhook(webhook_url)
            await app.updater.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=WEBHOOK_PATH,
            )
            await app.start()
            logger.info("Bot running... Press Ctrl+C to stop")
            await _asyncio.Event().wait()   # forever
    else:
        logger.info("🔄 Polling mode (local)")
        async with app:
            await app.updater.start_polling(drop_pending_updates=True)
            await app.start()
            await _asyncio.Event().wait()


def main():
    _asyncio.run(_run())


if __name__ == "__main__":
    main()
