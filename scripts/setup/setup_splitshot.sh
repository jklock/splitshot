#!/usr/bin/env bash
# SplitShot system dependency installer.
# Supports apt-get, dnf/yum, pacman, and zypper on Linux, plus Homebrew on macOS.
# Installs everything needed to run SplitShot (CLI + Electron): ffmpeg,
# PySide6/Qt runtime, Electron Linux deps, and Python native extension build deps.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_VERSION="${SPLITSHOT_PYTHON_VERSION:-3.12}"

log() { printf '[splitshot-setup] %s\n' "$*"; }
fail() { printf '[splitshot-setup] error: %s\n' "$*" >&2; exit 1; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_local_bin_on_path() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
}

install_uv_with_script() {
  if have_cmd uv; then return; fi
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ensure_local_bin_on_path
  have_cmd uv || fail "uv was installed but is not on PATH. Open a new shell and re-run the script."
}

# ── macOS ─────────────────────────────────────────────────────────────

brew_install() {
  local formula="$1"
  if brew list "$formula" >/dev/null 2>&1; then return; fi
  log "Installing $formula with Homebrew"
  brew install "$formula"
}

install_macos_dependencies() {
  have_cmd brew || fail "Homebrew is required on macOS. Install it from https://brew.sh and re-run this script."
  brew_install uv
  brew_install ffmpeg
}

# ── Linux package manager detection ───────────────────────────────────

linux_pkg_manager() {
  if have_cmd apt-get; then echo 'apt-get'; return; fi
  if have_cmd dnf;    then echo 'dnf';    return; fi
  if have_cmd yum;    then echo 'yum';    return; fi
  if have_cmd pacman; then echo 'pacman'; return; fi
  if have_cmd zypper; then echo 'zypper'; return; fi
  fail "No supported Linux package manager found."
}

# ── Package sets ──────────────────────────────────────────────────────

APT_PACKAGES=(
  # ffmpeg
  ffmpeg

  # PySide6 / Qt runtime
  libxcb-cursor0
  libxkbcommon-x11-0
  libegl1-mesa
  libegl-mesa0
  libgl1-mesa-glx
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

  # Electron runtime
  libgtk-3-0
  libnotify4
  libnss3
  libnspr4
  libxss1
  libxtst6
  libasound2t64
  libdrm2
  libgbm1
  libatspi2.0-0
  libcups2

  # Python native extension build deps
  build-essential
  python3-dev
  libblas-dev
  liblapack-dev
  gfortran
  libssl-dev
  pkg-config

  # General
  curl
)

DNF_PACKAGES=(
  ffmpeg ffmpeg-libs

  # PySide6 / Qt runtime
  libxcb
  xcb-util
  xcb-util-cursor
  xcb-util-image
  xcb-util-keysyms
  xcb-util-renderutil
  xcb-util-wm
  libxkbcommon-x11
  mesa-libEGL
  mesa-libGL
  libXrandr
  libglib2.0
  fontconfig
  dbus-libs
  libX11-xcb
  pulseaudio-libs
  libopengl

  # Electron runtime
  gtk3
  libnotify
  nss
  nspr
  libXScrnSaver
  libXtst
  alsa-lib
  libdrm
  libgbm
  at-spi2-core
  cups-libs

  # Python native extension build deps
  gcc
  gcc-c++
  make
  python3-devel
  blas-devel
  lapack-devel
  gcc-gfortran
  openssl-devel
  pkgconfig

  curl
)

YUM_PACKAGES=("${DNF_PACKAGES[@]}")
YUM_PACKAGES+=(epel-release)

PACMAN_PACKAGES=(
  ffmpeg

  qt6-base
  libxcb
  xcb-util-cursor
  xcb-util-wm
  libxkbcommon-x11
  libgl
  libxrandr
  glib2
  fontconfig
  dbus
  libpulse

  gtk3
  libnotify
  nss
  nspr
  libxss
  libxtst
  alsa-lib
  libdrm
  libgbm
  at-spi2-core

  base-devel
  python
  blas
  lapack
  gcc-fortran
  openssl
  pkg-config

  curl
)

ZYPPER_PACKAGES=(
  ffmpeg

  libxcb-cursor0
  libxkbcommon-x11-0
  Mesa-libEGL1
  Mesa-libGL1
  libXrandr2
  glib2
  fontconfig
  dbus-1
  libpulse0
  libopengl0

  gtk3
  libnotify4
  nss
  nspr
  libXss1
  libXtst6
  alsa
  libdrm2
  libgbm1
  at-spi2-core
  cups-libs

  gcc
  gcc-c++
  make
  python3-devel
  blas-devel
  lapack-devel
  gcc-fortran
  libopenssl-devel
  pkg-config

  curl
)

# ── Linux install ─────────────────────────────────────────────────────

install_linux_apt() {
  sudo apt-get update -qq
  sudo apt-get install -y -qq "${APT_PACKAGES[@]}"
}

install_linux_dnf() {
  sudo dnf install -y "${DNF_PACKAGES[@]}"
}

install_linux_yum() {
  sudo yum install -y epel-release
  sudo yum install -y "${YUM_PACKAGES[@]}"
}

install_linux_pacman() {
  sudo pacman -Sy --noconfirm "${PACMAN_PACKAGES[@]}"
}

install_linux_zypper() {
  sudo zypper install -y "${ZYPPER_PACKAGES[@]}"
}

install_linux_dependencies() {
  local manager
  manager="$(linux_pkg_manager)"
  log "Installing Linux dependencies with $manager"
  case "$manager" in
    apt-get) install_linux_apt ;;
    dnf)     install_linux_dnf ;;
    yum)     install_linux_yum ;;
    pacman)  install_linux_pacman ;;
    zypper)  install_linux_zypper ;;
  esac
  install_uv_with_script
}

# ── Bootstrap ─────────────────────────────────────────────────────────

bootstrap_workspace() {
  ensure_local_bin_on_path
  cd "$ROOT_DIR"
  log "Installing Python $PYTHON_VERSION through uv"
  uv python install "$PYTHON_VERSION"
  log "Syncing project dependencies"
  uv sync
  log "Running SplitShot runtime check"
  uv run splitshot --check
}

main() {
  log "Preparing SplitShot on $(uname -s)"
  case "$(uname -s)" in
    Darwin) install_macos_dependencies ;;
    Linux)  install_linux_dependencies ;;
    *) fail "This script supports macOS and Linux. Use scripts/setup/setup_splitshot.ps1 on Windows." ;;
  esac
  bootstrap_workspace
  cat <<EOF

[splitshot-setup] Ready.
[splitshot-setup] Launch commands:
  uv run splitshot

EOF
}

main "$@"
