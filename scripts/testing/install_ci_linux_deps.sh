#!/usr/bin/env bash
set -euo pipefail

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ffmpeg \
  libxcb-cursor0 \
  libxkbcommon-x11-0 \
  libegl1-mesa \
  libegl-mesa0 \
  libgl1-mesa-glx \
  libxrandr2 \
  libxkbfile1 \
  libglib2.0-0 \
  libfontconfig1 \
  libdbus-1-3 \
  libx11-xcb1 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-randr0 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-xfixes0 \
  libxcb-xinerama0 \
  libxcb-xkb1 \
  libpulse0 \
  libopengl0 \
  libgtk-3-0 \
  libnotify4 \
  libnss3 \
  libnspr4 \
  libxss1 \
  libxtst6 \
  libasound2 \
  libdrm2 \
  libgbm1 \
  libatspi2.0-0 \
  libcups2 \
  tk
