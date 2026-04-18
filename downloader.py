"""
downloader.py — yt-dlp wrapper
- search_youtube()
- get_video_info()
- get_playlist_info()
- download_audio()
- download_playlist_items()  ← async generator
"""

import re
import time
import logging
import asyncio
import shutil
from pathlib import Path
import yt_dlp

logger = logging.getLogger(__name__)

# FFmpeg path — Render pe /opt/ffmpeg mein install hota hai, warna system PATH
import os as _os
_HOME_FFMPEG = Path(_os.environ.get("HOME", "/root")) / "ffmpeg"
_FFMPEG_LOCATION = str(_HOME_FFMPEG) if (_HOME_FFMPEG / "ffmpeg").exists() else None

# ─── Search ───────────────────────────────────────────────────────────────────
def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            results = []
            for e in (info.get("entries") or []):
                if not e:
                    continue
                vid_id = e.get("id", "")
                if not vid_id:
                    continue
                results.append({
                    "title":     e.get("title", "Unknown"),
                    "url":       f"https://www.youtube.com/watch?v={vid_id}",
                    "duration":  e.get("duration"),
                    "channel":   e.get("uploader", ""),
                })
            return results
    except Exception as ex:
        logger.error(f"Search error: {ex}")
        return []


# ─── Single video info ────────────────────────────────────────────────────────
def get_video_info(url: str) -> dict | None:
    ydl_opts = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title":    info.get("title", "Unknown"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", ""),
            }
    except Exception as ex:
        logger.error(f"Video info error: {ex}")
        return None


# ─── Playlist info ────────────────────────────────────────────────────────────
def get_playlist_info(url: str) -> dict | None:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 50,   # max 50 check karo
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = [e for e in (info.get("entries") or []) if e]
            return {
                "title": info.get("title", "Playlist"),
                "count": len(entries),
                "entries": entries,
            }
    except Exception as ex:
        logger.error(f"Playlist info error: {ex}")
        return None


# ─── Audio download (single) ──────────────────────────────────────────────────
def download_audio(url: str, quality: str, dest: Path) -> str:
    """
    MP3 download karo.
    quality: "128" | "192" | "320"
    Returns: local file path (str)
    """
    abr       = str(quality)
    safe_name = _video_id(url) or str(int(time.time()))
    out_tmpl  = str(dest / f"{safe_name}_{abr}.%(ext)s")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [{
            "key":              "FFmpegExtractAudio",
            "preferredcodec":   "mp3",
            "preferredquality": abr,
        }],
    }
    if _FFMPEG_LOCATION:
        ydl_opts["ffmpeg_location"] = _FFMPEG_LOCATION

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return _find_file(dest, f"{safe_name}_{abr}")


# ─── Playlist download — async generator ──────────────────────────────────────
async def download_playlist_items(url: str, quality: str, dest: Path, limit: int = 50):
    """
    Playlist ke songs ek-ek download karo.
    Async generator: yield {"status": "ok", "path": ..., "title": ...}
                  or {"status": "error", "title": ...}
    """
    # Pehle entries lo
    info = await asyncio.to_thread(get_playlist_info, url)
    if not info:
        return

    entries = info["entries"][:limit]

    for entry in entries:
        vid_id = entry.get("id", "")
        title  = entry.get("title", "Unknown")

        if not vid_id:
            yield {"status": "error", "title": title}
            continue

        video_url = f"https://www.youtube.com/watch?v={vid_id}"
        try:
            file_path = await asyncio.to_thread(download_audio, video_url, quality, dest)
            yield {"status": "ok", "path": file_path, "title": title}
        except Exception as e:
            logger.error(f"Playlist item error [{title}]: {e}")
            yield {"status": "error", "title": title}

        # Rate limit se bachne ke liye thoda wait
        await asyncio.sleep(1)


# ─── Internal helpers ─────────────────────────────────────────────────────────
def _video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _find_file(dest: Path, stem: str) -> str:
    """Downloaded file ka path dhundo (extension unknown)."""
    # Pehle mp3 try karo
    mp3 = dest / f"{stem}.mp3"
    if mp3.exists():
        return str(mp3)

    # Koi bhi matching file dhundo
    matches = list(dest.glob(f"{stem}.*"))
    if matches:
        return str(matches[0])

    raise FileNotFoundError(f"File nahi mila: {dest}/{stem}.*")
