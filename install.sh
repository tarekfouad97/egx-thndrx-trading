#!/usr/bin/env bash
# EGX ThndrX Trading - macOS / Linux bootstrap: installs Python 3 if missing, then runs install.py.
#   bash install.sh            (add --yes to accept defaults)
set -euo pipefail
cd "$(dirname "$0")"

need_py() {
  command -v python3 >/dev/null 2>&1 || return 0
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' && return 1 || return 0
}

if need_py; then
  echo "Python 3.9+ not found - installing it..."
  if [[ "$(uname)" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      brew install python
    else
      PKG="python-3.12.7-macos11.pkg"
      echo "Downloading the official installer from python.org (needs your Mac password)..."
      curl -fsSLo "/tmp/$PKG" "https://www.python.org/ftp/python/3.12.7/$PKG"
      sudo installer -pkg "/tmp/$PKG" -target /
      export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"
    fi
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3
  else
    echo "Please install Python 3.9+ from https://www.python.org/downloads/ and run this again." && exit 1
  fi
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is optional (MP4 recap, design skills)."
  if [[ "$(uname)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    read -r -p "Install Node.js with Homebrew now? [y/N] " a || a=n
    [[ "${a:-n}" =~ ^[Yy]$ ]] && brew install node || true
  fi
fi

exec python3 install.py "$@"
