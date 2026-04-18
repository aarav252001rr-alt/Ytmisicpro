#!/bin/bash
# Render build script — FFmpeg (no root needed) + Python dependencies
set -e

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🎬 Installing FFmpeg (static binary, no root)..."
mkdir -p /opt/ffmpeg
curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
  -o /tmp/ffmpeg.tar.xz
tar -xf /tmp/ffmpeg.tar.xz -C /tmp/
# Extracted folder ka naam dynamic hota hai, isliye find use karo
FFMPEG_DIR=$(find /tmp -maxdepth 1 -type d -name "ffmpeg-*-static" | head -1)
cp "$FFMPEG_DIR/ffmpeg" /opt/ffmpeg/ffmpeg
cp "$FFMPEG_DIR/ffprobe" /opt/ffmpeg/ffprobe
chmod +x /opt/ffmpeg/ffmpeg /opt/ffmpeg/ffprobe

echo "✅ FFmpeg version: $(/opt/ffmpeg/ffmpeg -version | head -1)"
echo "✅ Build complete!"
