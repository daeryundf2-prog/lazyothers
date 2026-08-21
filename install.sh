#!/usr/bin/env bash
# Antigravity 3-plugin auto-installer (macOS / Linux parity for install.ps1)
set -euo pipefail

PLUGIN_DIR="${HOME}/.gemini/config/plugins"
mkdir -p "${PLUGIN_DIR}"
ORIGINAL_DIR="$(pwd)"
cd "${PLUGIN_DIR}"

declare -A REPOS=(
  ["lazyantigravity"]="https://github.com/daeryundf2-prog/LAZYANTIGRAVITY.git"
  ["lazyforensic"]="https://github.com/daeryundf2-prog/lazyforensic.git"
  ["lazyothers"]="https://github.com/daeryundf2-prog/lazyothers.git"
)

for name in "${!REPOS[@]}"; do
  url="${REPOS[$name]}"
  target="${PLUGIN_DIR}/${name}"
  if [ -d "${target}/.git" ]; then
    echo "Updating ${name}..."
    pushd "${target}" >/dev/null
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      echo "  [!] ${name} has local changes, stashing..."
      git stash push -m "auto-stash before pull" || true
    fi
    git pull --ff-only || echo "  [!] git pull failed for ${name}"
    popd >/dev/null
  else
    echo "Cloning ${name}..."
    git clone "${url}" "${name}" || echo "  [!] Failed to clone ${name}"
  fi
done

if command -v npm >/dev/null 2>&1; then
  echo "Building LazyAntigravity..."
  if [ -d "${PLUGIN_DIR}/lazyantigravity" ]; then
    pushd "${PLUGIN_DIR}/lazyantigravity" >/dev/null
    npm install
    npm run build || echo "  [!] Build failed"
    popd >/dev/null
  fi
  echo "Syncing LazyOthers MCP tools..."
  if [ -f "${PLUGIN_DIR}/lazyothers/package.json" ]; then
    pushd "${PLUGIN_DIR}/lazyothers" >/dev/null
    npm run setup || echo "  [!] Sync failed"
    popd >/dev/null
  fi
else
  echo "[!] npm not found, skipping build/sync"
fi

# Merge config.json (do not overwrite)
CONFIG_PATH="${HOME}/.gemini/config/config.json"
mkdir -p "$(dirname "${CONFIG_PATH}")"
if command -v python3 >/dev/null 2>&1; then
  python3 << 'PY'
import json, os
config_path = os.path.expanduser("~/.gemini/config/config.json")
default_plugins = {
    "lazyantigravity": {"enabled": True},
    "lazyforensic": {"enabled": True},
    "lazyothers": {"enabled": True},
}
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Failed to parse existing config.json: {e}, backing up")
        import shutil
        shutil.copy(config_path, config_path + ".bak")
        data = {}
    data.setdefault("plugins", {})
    for k, v in default_plugins.items():
        data["plugins"][k] = v
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Merged plugins into {config_path}")
else:
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"plugins": default_plugins}, f, ensure_ascii=False, indent=2)
    print(f"Created {config_path}")
PY
else
  echo "[!] python3 not found, skipping config merge — create ${CONFIG_PATH} manually"
fi

cd "${ORIGINAL_DIR}"
echo "=========================================="
echo "  Setup Completed Successfully! (PASS)"
echo "=========================================="
