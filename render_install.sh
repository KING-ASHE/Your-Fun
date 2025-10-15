#!/usr/bin/env bash

# This script must use Linux (LF) line endings.

echo "--- Starting FFmpeg Installation ---"

FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_ARCHIVE=$(basename $FFMPEG_URL)
FFMPEG_DIR=$(basename $FFMPEG_ARCHIVE .tar.xz)

echo "Downloading FFmpeg static build..."
curl -L "$FFMPEG_URL" -o "$FFMPEG_ARCHIVE"

if [ ! -f "$FFMPEG_ARCHIVE" ]; then
  echo "Error: FFmpeg download failed!"
  exit 1
fi

echo "Extracting FFmpeg..."
# Use tar with J for .tar.xz extraction
tar -xf "$FFMPEG_ARCHIVE"

# Create a bin directory in the home path
mkdir -p "$HOME/bin"

# Move executables to the custom bin directory
# The extracted directory name is complex, we use find to locate it
EXTRACTED_FFMPEG_DIR=$(find . -maxdepth 1 -type d -name "ffmpeg-*-amd64-static" | head -n 1)

if [ -z "$EXTRACTED_FFMPEG_DIR" ]; then
    echo "Error: Could not find the extracted FFmpeg directory."
    exit 1
fi

echo "Moving binaries from $EXTRACTED_FFMPEG_DIR to $HOME/bin"
mv "$EXTRACTED_FFMPEG_DIR/ffmpeg" "$HOME/bin/"
mv "$EXTRACTED_FFMPEG_DIR/ffprobe" "$HOME/bin/"

# Test run to verify installation
"$HOME/bin/ffmpeg" -version

# Clean up temporary files
rm -rf "$FFMPEG_ARCHIVE" "$EXTRACTED_FFMPEG_DIR"

echo "--- FFmpeg installation complete ---"