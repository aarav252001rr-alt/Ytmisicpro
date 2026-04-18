# 🎵 YT Music Telegram Bot

**Features:**
- Song naam se search → top 5 results
- YouTube link se direct download
- YouTube playlist support (max 50 songs)
- Audio only: 128 / 192 / 320 kbps MP3
- Files 1 ghante baad auto-delete
- Render free tier compatible (webhook mode)

---

## 📁 File Structure

```
ytmusic_bot/
├── bot.py           ← Main bot (webhook + handlers)
├── downloader.py    ← yt-dlp wrapper
├── requirements.txt ← Python dependencies
├── render.yaml      ← Render deploy config
└── downloads/       ← Temp folder (auto-create)
```

---

## 🚀 Render pe Deploy karna (Free)

### Step 1 — BotFather se token lo
1. Telegram pe **@BotFather** kholo
2. `/newbot` → naam do → token copy karo

### Step 2 — GitHub repo banao
1. GitHub pe new **public** repository banao
2. Yeh 4 files upload karo:
   - `bot.py`
   - `downloader.py`
   - `requirements.txt`
   - `render.yaml`

### Step 3 — Render account banao
1. [render.com](https://render.com) pe free account banao
2. **New → Web Service** click karo
3. GitHub repo connect karo
4. Settings:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Plan:** Free

### Step 4 — FFmpeg install karna (IMPORTANT)
Render pe FFmpeg manually install karne ke liye `build.sh` banao:

**build.sh** (ek aur file add karo GitHub pe):
```bash
#!/bin/bash
apt-get install -y ffmpeg
pip install -r requirements.txt
```

Phir Render mein Build Command change karo:
```
chmod +x build.sh && ./build.sh
```

### Step 5 — Environment Variables set karo
Render dashboard → Environment → Add:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `1234567890:ABCdef...` (BotFather wala) |
| `RENDER_URL` | `https://yt-music-bot.onrender.com` (apna URL) |
| `PORT` | `8080` |

> `RENDER_URL` Render deploy hone ke baad milega — pehle deploy karo, phir URL copy karke set karo aur redeploy karo.

### Step 6 — Deploy!
**Manual Deploy** click karo. Bot chal jaayega! 🎉

---

## 💻 Local Test (Termux / Linux)

```bash
# FFmpeg install karo
pkg install ffmpeg -y          # Termux
# ya
sudo apt install ffmpeg -y     # Linux

# Dependencies install karo
pip install -r requirements.txt

# BOT_TOKEN set karo (RENDER_URL mat daalo — polling mode chalega)
export BOT_TOKEN="1234567890:ABCdef..."

# Bot chalao
python bot.py
```

---

## ⚠️ Important Notes

| Point | Detail |
|-------|--------|
| **FFmpeg** | Zaroor chahiye — bina iske MP3 nahi banega |
| **File size** | Telegram bots 50MB tak bhej sakte hain free mein |
| **Playlist limit** | Max 50 songs per playlist (Render timeout se bachne ke liye) |
| **Render free** | 750 hrs/month free — idle pe sleep ho jaata hai, pehle request slow |
| **Auto-delete** | Files server pe 1 ghante baad delete — Telegram pe rehti hain |
