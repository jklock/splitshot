#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER_DIR="${1:-${SPLITSHOT_RUNNER_DIR:-}}"

log() { printf '[splitshot-runner-setup] %s\n' "$*"; }
fail() { printf '[splitshot-runner-setup] error: %s\n' "$*" >&2; exit 1; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }
report_optional_version() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    log "$name: $("$@" 2>/dev/null | head -n 1)"
  else
    log "$name: not installed globally (workflow can still provision it)"
  fi
}

require_apt() {
  have_cmd apt-get || fail "This script currently expects apt-get on the Linux runner host."
}

pkg_installed() {
  dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

ensure_packages() {
  local missing=()
  for pkg in "$@"; do
    if ! pkg_installed "$pkg"; then
      missing+=("$pkg")
    fi
  done
  if [ "${#missing[@]}" -eq 0 ]; then
    log "Base runner packages already installed"
    return
  fi
  log "Installing base runner packages: ${missing[*]}"
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
}

ensure_ci_linux_deps() {
  local required=(
    ffmpeg
    libxkbfile1
    libgtk-3-0
    libnotify4
    libnss3
    libnspr4
    libxss1
    libxtst6
    libasound2
    libdrm2
    libgbm1
    libatspi2.0-0
    libcups2
    tk
  )

  local need_install=0
  for pkg in "${required[@]}"; do
    if ! pkg_installed "$pkg"; then
      need_install=1
      break
    fi
  done

  if [ "$need_install" -eq 0 ]; then
    log "Electron Linux dependency set already installed"
    return
  fi

  log "Installing Electron Linux dependency set"
  sudo bash "$ROOT_DIR/scripts/testing/install_ci_linux_deps.sh"
}

ensure_needrestart_override() {
  local conf_file="/etc/needrestart/conf.d/actions_runner_services.conf"
  local conf_line='$nrconf{override_rc}{qr(^actions\.runner\..+\.service$)} = 0;'
  if [ -f "$conf_file" ] && grep -Fq "$conf_line" "$conf_file"; then
    log "needrestart override already configured"
    return
  fi
  log "Configuring needrestart override for runner services"
  echo "$conf_line" | sudo tee "$conf_file" >/dev/null
}

ensure_uv() {
  if have_cmd uv; then
    return
  fi
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  have_cmd uv || fail "uv was installed but is still unavailable in this shell."
}

resolve_runner_dir() {
  local candidates=()
  if [ -n "$RUNNER_DIR" ]; then
    candidates+=("$RUNNER_DIR")
  fi
  candidates+=(
    "/opt/actions-runner/splitshot-linux"
    "/opt/actions-runner"
    "$HOME/actions-runner/splitshot-linux"
    "$HOME/actions-runner"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    [ -n "$candidate" ] || continue
    [ -d "$candidate" ] || continue
    if [ -f "$candidate/.service" ] && [ -x "$candidate/svc.sh" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
    local found
    found="$(find "$candidate" -maxdepth 2 -type f -name .service 2>/dev/null | head -n 1 || true)"
    if [ -n "$found" ] && [ -x "$(dirname "$found")/svc.sh" ]; then
      printf '%s\n' "$(dirname "$found")"
      return 0
    fi
  done

  return 1
}

ensure_runner_service() {
  local dir="$1"
  cd "$dir"
  log "Using runner directory $dir"
  if sudo ./svc.sh status 2>/dev/null | grep -qi "running"; then
    log "Runner service already running"
    sudo ./svc.sh status
    return
  fi
  log "Starting runner service"
  sudo ./svc.sh start
  sudo ./svc.sh status
}

require_apt
ensure_packages git curl ca-certificates jq xvfb
ensure_ci_linux_deps
ensure_needrestart_override
ensure_uv

resolved_runner_dir="$(resolve_runner_dir)" || fail "Could not locate the existing GitHub Actions runner directory. Pass it as the first argument or set SPLITSHOT_RUNNER_DIR."
ensure_runner_service "$resolved_runner_dir"

log "bash: $(bash --version | head -n 1)"
log "git: $(git --version)"
report_optional_version "python3" python3 --version
report_optional_version "node" node --version
report_optional_version "npm" npm --version
log "uv: $(uv --version)"
log "ffmpeg: $(ffmpeg -version | head -n 1)"
