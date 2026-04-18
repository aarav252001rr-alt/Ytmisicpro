#!/bin/bash
# Render build script — FFmpeg + Python dependencies
set -e
apt-get install -y ffmpeg
pip install -r requirements.txt
echo "✅ Build complete!"
