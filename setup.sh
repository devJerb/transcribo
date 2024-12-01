#!/bin/bash

# Download FFmpeg static binary
echo "Downloading FFmpeg..."
wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O ffmpeg.tar.xz

# Extract the binary
echo "Extracting FFmpeg..."
tar -xf ffmpeg.tar.xz
mv ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe .

# Clean up
rm -rf ffmpeg.tar.xz ffmpeg-*-static

# Ensure binaries are executable
chmod +x ffmpeg ffprobe

echo "FFmpeg setup complete!"
