#!/bin/bash
# Render build script — FFmpeg (no root, uses $HOME) + Python deps
set -e

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🎬 Installing FFmpeg static binary..."
mkdir -p "$HOME/ffmpeg"
curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
  -o /tmp/ffmpeg.tar.xz
tar -xf /tmp/ffmpeg.tar.xz -C /tmp/
FFMPEG_DIR=$(find /tmp -maxdepth 1 -type d -name "ffmpeg-*-static" | head -1)
cp "$FFMPEG_DIR/ffmpeg"  "$HOME/ffmpeg/ffmpeg"
cp "$FFMPEG_DIR/ffprobe" "$HOME/ffmpeg/ffprobe"
chmod +x "$HOME/ffmpeg/ffmpeg" "$HOME/ffmpeg/ffprobe"

echo "✅ FFmpeg: $("$HOME/ffmpeg/ffmpeg" -version | head -1)"
echo "✅ Build complete!"
