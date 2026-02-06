#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/build_wcp.sh

Environment variables:
  STEAM_USERNAME       Steam account username (required)
  STEAM_PASSWORD       Steam account password (required)
  STEAM_GUARD_CODE     Optional Steam Guard/TOTP code
  PROTON_VERSION       Proton version label (default: latest)
  WCP_VERSION          Version string for wcp.json (default: PROTON_VERSION or PROTON_VERSION-1 for X.Y)
  PROTON_NAME          Display name in wcp.json (default: "Proton <version>")
  WINE_VERSION         wine_version in wcp.json (default: "proton-<version>")
  PROTON_BRANCH        Optional Steam beta branch name
  PROTON_APP_ID        Steam app ID (default: 1493710)
  WCP_DESCRIPTION      Description in wcp.json
  WORK_DIR             Working directory (default: ./work)
  OUTPUT_DIR           Output directory (default: ./dist)
  WCP_FILENAME         Output filename (default: proton-<version>.wcp)
  STEAMCMD_BIN         SteamCMD binary (default: steamcmd)
  FILES_SEARCH_MAX_DEPTH  Max depth when locating Proton files/ (default: 4)
  METADATA_PATH        Optional metadata output path (default: <work>/metadata.json)
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

PROTON_VERSION_INPUT="${PROTON_VERSION:-}"
WCP_VERSION_INPUT="${WCP_VERSION:-}"
PROTON_NAME_INPUT="${PROTON_NAME:-}"
WINE_VERSION_INPUT="${WINE_VERSION:-}"
WCP_FILENAME_INPUT="${WCP_FILENAME:-}"
PROTON_BRANCH="${PROTON_BRANCH:-}"
PROTON_APP_ID="${PROTON_APP_ID:-1493710}"
WCP_DESCRIPTION="${WCP_DESCRIPTION:-Valve's Proton compatibility layer converted for Winlator}"
WORK_DIR="${WORK_DIR:-$(pwd)/work}"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
STEAMCMD_BIN="${STEAMCMD_BIN:-steamcmd}"
FILES_SEARCH_MAX_DEPTH="${FILES_SEARCH_MAX_DEPTH:-4}"
METADATA_PATH="${METADATA_PATH:-$WORK_DIR/metadata.json}"

: "${STEAM_USERNAME:?STEAM_USERNAME is required}"
: "${STEAM_PASSWORD:?STEAM_PASSWORD is required}"

if ! command -v "$STEAMCMD_BIN" >/dev/null 2>&1; then
  echo "steamcmd not found: $STEAMCMD_BIN" >&2
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required to package the .wcp archive" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to generate wcp.json" >&2
  exit 1
fi

download_dir="$WORK_DIR/proton"
stage_dir="$WORK_DIR/stage"

rm -rf "$download_dir" "$stage_dir"
mkdir -p "$download_dir" "$stage_dir" "$OUTPUT_DIR"

login_args=("$STEAM_USERNAME" "$STEAM_PASSWORD")
if [[ -n "${STEAM_GUARD_CODE:-}" ]]; then
  login_args+=("$STEAM_GUARD_CODE")
fi

app_update_args=(+app_update "$PROTON_APP_ID")
if [[ -n "$PROTON_BRANCH" ]]; then
  app_update_args+=("-beta" "$PROTON_BRANCH")
fi
app_update_args+=("validate")

"$STEAMCMD_BIN" \
  +@sSteamCmdForcePlatformType linux \
  +login "${login_args[@]}" \
  +force_install_dir "$download_dir" \
  "${app_update_args[@]}" \
  +quit

version_input="$PROTON_VERSION_INPUT"
# Empty or "latest" triggers automatic build ID detection.
if [[ -z "$version_input" || "$version_input" == "latest" ]]; then
  manifest_path="$download_dir/appmanifest_${PROTON_APP_ID}.acf"
  if [[ ! -f "$manifest_path" ]]; then
    manifest_path="$(find "$download_dir" -maxdepth 2 -name "appmanifest_${PROTON_APP_ID}.acf" -print -quit)"
  fi
  if [[ -n "$manifest_path" ]]; then
    resolved_version="$(sed -nE 's/^[[:space:]]*"buildid"[[:space:]]+"([0-9]+)".*/\1/p; q' "$manifest_path")"
    if [[ -z "$resolved_version" || ! "$resolved_version" =~ ^[0-9]+$ ]]; then
      echo "Found manifest at $manifest_path but could not extract build ID." >&2
      exit 1
    fi
  fi
  if [[ -z "$resolved_version" ]]; then
    echo "Unable to determine Proton build ID. Set PROTON_VERSION explicitly." >&2
    exit 1
  fi
else
  # Manual version inputs may use user-defined non-numeric labels (e.g., stable or experimental-v2).
  resolved_version="$version_input"
fi

PROTON_VERSION="$resolved_version"
if [[ -z "$WCP_VERSION_INPUT" ]]; then
  if [[ "$PROTON_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
    WCP_VERSION="${PROTON_VERSION}-1"
  else
    WCP_VERSION="$PROTON_VERSION"
  fi
else
  WCP_VERSION="$WCP_VERSION_INPUT"
fi

proton_display_version="$PROTON_VERSION"
if [[ "$proton_display_version" == *-* ]]; then
  proton_display_version="${proton_display_version%%-*}"
fi

PROTON_NAME="${PROTON_NAME_INPUT:-Proton $proton_display_version}"
WINE_VERSION="${WINE_VERSION_INPUT:-proton-$proton_display_version}"
WCP_FILENAME="${WCP_FILENAME_INPUT:-proton-${PROTON_VERSION}.wcp}"

if [[ "$WCP_FILENAME" != *.wcp ]]; then
  WCP_FILENAME="${WCP_FILENAME}.wcp"
fi

mkdir -p "$(dirname "$METADATA_PATH")"
METADATA_PATH="$METADATA_PATH" \
PROTON_VERSION="$PROTON_VERSION" \
WCP_VERSION="$WCP_VERSION" \
WCP_FILENAME="$WCP_FILENAME" \
python3 - <<'PY'
import json
import os
from pathlib import Path

data = {
    "proton_version": os.environ["PROTON_VERSION"],
    "wcp_version": os.environ["WCP_VERSION"],
    "wcp_filename": os.environ["WCP_FILENAME"],
}

path = Path(os.environ["METADATA_PATH"])
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

proton_root="$download_dir"
if [[ ! -d "$proton_root/files" ]]; then
  files_dir="$(find "$download_dir" -maxdepth "$FILES_SEARCH_MAX_DEPTH" -type d -name files -print -quit)"
  if [[ -z "$files_dir" ]]; then
    echo "Unable to locate Proton files directory in $download_dir" >&2
    exit 1
  fi
  proton_root="$(dirname "$files_dir")"
fi

files_dir="$proton_root/files"
if [[ ! -d "$files_dir" ]]; then
  echo "Missing files directory at $files_dir" >&2
  exit 1
fi

mkdir -p "$stage_dir/bin" "$stage_dir/lib" "$stage_dir/share"
if [[ -d "$files_dir/bin" ]]; then
  cp -a "$files_dir/bin/." "$stage_dir/bin/"
fi
if [[ -d "$files_dir/lib" ]]; then
  cp -a "$files_dir/lib/." "$stage_dir/lib/"
fi
if [[ -d "$files_dir/lib64" ]]; then
  cp -a "$files_dir/lib64/." "$stage_dir/lib/"
fi
if [[ -d "$files_dir/share" ]]; then
  cp -a "$files_dir/share/." "$stage_dir/share/"
fi

WCP_JSON_PATH="$stage_dir/wcp.json" \
PROTON_NAME="$PROTON_NAME" \
WCP_VERSION="$WCP_VERSION" \
WCP_DESCRIPTION="$WCP_DESCRIPTION" \
WINE_VERSION="$WINE_VERSION" \
python3 - <<'PY'
import json
import os
from pathlib import Path

data = {
    "name": os.environ["PROTON_NAME"],
    "version": os.environ["WCP_VERSION"],
    "description": os.environ["WCP_DESCRIPTION"],
    "wine_version": os.environ["WINE_VERSION"],
}

path = Path(os.environ["WCP_JSON_PATH"])
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

wcp_path="$OUTPUT_DIR/$WCP_FILENAME"
rm -f "$wcp_path"
(
  cd "$stage_dir"
  zip -r -9 -X "$wcp_path" .
)

echo "WCP package created at $wcp_path"
