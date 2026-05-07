#!/usr/bin/env bash
set -euo pipefail

package_exists() {
  apt-cache show "$1" >/dev/null 2>&1
}

choose_package() {
  local candidate
  for candidate in "$@"; do
    if package_exists "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

apt-get update

packages=(
  ffmpeg
  libxcb-cursor0
  libxkbcommon-x11-0
  libxrandr2
  libxkbfile1
  libglib2.0-0
  libfontconfig1
  libdbus-1-3
  libx11-xcb1
  libxcb-icccm4
  libxcb-image0
  libxcb-keysyms1
  libxcb-randr0
  libxcb-render-util0
  libxcb-shape0
  libxcb-xfixes0
  libxcb-xinerama0
  libxcb-xkb1
  libpulse0
  libopengl0
  libgtk-3-0
  libnotify4
  libnss3
  libnspr4
  libxss1
  libxtst6
  libdrm2
  libgbm1
  libatspi2.0-0
  libcups2
  tk
)

packages+=("$(choose_package libegl1-mesa libegl1 libegl-mesa0)")
packages+=("$(choose_package libgl1-mesa-glx libgl1)")
packages+=("$(choose_package libasound2t64 libasound2)")

DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
