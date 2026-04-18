#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_VERSION="${SPLITSHOT_PYTHON_VERSION:-3.12}"

log() {
  printf '[splitshot-setup] %s\n' "$*"
}

fail() {
  printf '[splitshot-setup] error: %s\n' "$*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ensure_local_bin_on_path() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
}

install_uv_with_script() {
  if have_cmd uv; then
    return
  fi
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ensure_local_bin_on_path
  have_cmd uv || fail "uv was installed but is not on PATH. Open a new shell and re-run the script."
}

brew_install() {
  local formula="$1"
  if brew list "$formula" >/dev/null 2>&1; then
    return
  fi
  log "Installing $formula with Homebrew"
  brew install "$formula"
}

install_macos_dependencies() {
  have_cmd brew || fail "Homebrew is required on macOS. Install it from https://brew.sh and re-run this script."
  brew_install uv
  brew_install ffmpeg
}

linux_pkg_manager() {
  if have_cmd apt-get; then
    printf 'apt-get'
    return
  fi
  if have_cmd dnf; then
    printf 'dnf'
    return
  fi
  if have_cmd pacman; then
    printf 'pacman'
    return
  fi
  if have_cmd zypper; then
    printf 'zypper'
    return
  fi
  fail "No supported Linux package manager found. Install curl, ffmpeg, and uv manually, then re-run this script."
}

install_linux_dependencies() {
  local manager
  manager="$(linux_pkg_manager)"
  case "$manager" in
    apt-get)
      log "Installing Linux prerequisites with apt-get"
      sudo apt-get update
      sudo apt-get install -y curl ffmpeg
      ;;
    dnf)
      log "Installing Linux prerequisites with dnf"
      sudo dnf install -y curl ffmpeg ffmpeg-libs
      ;;
    pacman)
      log "Installing Linux prerequisites with pacman"
      sudo pacman -Sy --noconfirm curl ffmpeg
      ;;
    zypper)
      log "Installing Linux prerequisites with zypper"
      sudo zypper install -y curl ffmpeg
      ;;
  esac
  install_uv_with_script
}

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
    Darwin)
      install_macos_dependencies
      ;;
    Linux)
      install_linux_dependencies
      ;;
    *)
      fail "This script supports macOS and Linux. Use scripts/setup/setup_splitshot.ps1 on Windows."
      ;;
  esac

  bootstrap_workspace

  cat <<EOF

[splitshot-setup] Ready.
[splitshot-setup] Launch commands:
  uv run splitshot

EOF
}

main "$@"