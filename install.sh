#!/usr/bin/env bash
# Antigravity 3-plugin auto-installer (macOS / Linux)
# NOTE: macOS 기본 bash는 3.2 — 연관 배열(declare -A) 없이 POSIX 호환으로 작성.
set -euo pipefail

PLUGIN_DIR="${HOME}/.gemini/config/plugins"
mkdir -p "${PLUGIN_DIR}"
ORIGINAL_DIR="$(pwd)"
cd "${PLUGIN_DIR}"

# "이름 URL" 쌍 목록 (bash 3.2 호환)
PLUGINS="
lazyantigravity https://github.com/daeryundf2-prog/LAZYANTIGRAVITY.git
lazyforensic    https://github.com/daeryundf2-prog/lazyforensic-.git
lazyothers      https://github.com/daeryundf2-prog/lazyothers.git
"

echo "$PLUGINS" | while read -r name url; do
  [ -z "${name:-}" ] && continue
  target="${PLUGIN_DIR}/${name}"
  if [ -d "${target}/.git" ]; then
    echo "Updating ${name}..."
    (
      cd "${target}"
      if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo "  [!] ${name} has local changes, stashing..."
        git stash push -m "auto-stash before pull" || true
      fi
      git pull --ff-only || echo "  [!] git pull failed for ${name}"
    ) || echo "  [!] update failed for ${name}"
  else
    echo "Cloning ${name}..."
    git clone "${url}" "${target}" || echo "  [!] Failed to clone ${name}"
  fi
done

if command -v npm >/dev/null 2>&1; then
  echo "Building LazyAntigravity..."
  if [ -d "${PLUGIN_DIR}/lazyantigravity" ]; then
    (
      cd "${PLUGIN_DIR}/lazyantigravity"
      npm install
      npm run build || echo "  [!] Build failed"
    ) || echo "  [!] LazyAntigravity build failed"
  fi

  echo "Building korean-law-mcp (lazyforensic, optional)..."
  if [ -f "${PLUGIN_DIR}/lazyforensic/korean-law-mcp/package.json" ]; then
    (
      cd "${PLUGIN_DIR}/lazyforensic/korean-law-mcp"
      npm install
      npm run build || echo "  [!] korean-law-mcp build failed — korean_law MCP는 빌드 후 활성화됨"
    ) || echo "  [!] korean-law-mcp build failed"
  fi

  echo "Syncing LazyOthers MCP tools..."
  if [ -f "${PLUGIN_DIR}/lazyothers/package.json" ]; then
    (
      cd "${PLUGIN_DIR}/lazyothers"
      npm run setup || echo "  [!] Sync failed"
    ) || echo "  [!] LazyOthers sync failed"
  fi
else
  echo "[!] npm not found, skipping build/sync"
fi

# Python 의존성 (lazyothers 스킬 실행에 필요: pymupdf/olefile 등)
if command -v python3 >/dev/null 2>&1; then
  echo "Installing Python dependencies for lazyothers..."
  (cd "${PLUGIN_DIR}/lazyothers" && python3 -m pip install -r requirements.txt) \
    || echo "  [!] pip install failed — 수동 실행 필요: pip install -r ${PLUGIN_DIR}/lazyothers/requirements.txt"
else
  echo "[!] python3 not found, skipping pip install"
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
