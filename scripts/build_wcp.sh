#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/build_wcp.sh

Environment variables:
  STEAM_USERNAME       Steam account username (required)
  STEAM_PASSWORD       Steam account password (required)
  STEAM_GUARD_CODE     Optional Steam Guard/TOTP code
  PROTON_VERSION       Proton version label (default: 10.0)
  WCP_VERSION          Version string for wcp.json (default: PROTON_VERSION)
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
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

PROTON_VERSION="${PROTON_VERSION:-10.0}"
WCP_VERSION="${WCP_VERSION:-$PROTON_VERSION}"
PROTON_NAME="${PROTON_NAME:-Proton $PROTON_VERSION}"
WINE_VERSION="${WINE_VERSION:-proton-$PROTON_VERSION}"
PROTON_BRANCH="${PROTON_BRANCH:-}"
PROTON_APP_ID="${PROTON_APP_ID:-1493710}"
WCP_DESCRIPTION="${WCP_DESCRIPTION:-Valve Proton compatibility layer converted for Winlator}"
WORK_DIR="${WORK_DIR:-$(pwd)/work}"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
WCP_FILENAME="${WCP_FILENAME:-proton-${PROTON_VERSION}.wcp}"
STEAMCMD_BIN="${STEAMCMD_BIN:-steamcmd}"
FILES_SEARCH_MAX_DEPTH="${FILES_SEARCH_MAX_DEPTH:-4}"

if [[ "$WCP_FILENAME" != *.wcp ]]; then
  WCP_FILENAME="${WCP_FILENAME}.wcp"
fi

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

proton_root="$download_dir"
if [[ ! -d "$proton_root/files" ]]; then
  files_dir=""
  shopt -s nullglob
  files_candidates=("$download_dir"/*/files "$download_dir"/*/*/files)
  shopt -u nullglob
  if ((${#files_candidates[@]} > 0)); then
    files_dir="${files_candidates[0]}"
  else
    files_dir="$(find "$download_dir" -maxdepth "$FILES_SEARCH_MAX_DEPTH" -type d -name files -print -quit)"
  fi
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

cp -a "$files_dir/." "$stage_dir/"

cat >"$stage_dir/wcp.json" <<EOF
{
  "name": "$PROTON_NAME",
  "version": "$WCP_VERSION",
  "description": "$WCP_DESCRIPTION",
  "wine_version": "$WINE_VERSION"
}
EOF

wcp_path="$OUTPUT_DIR/$WCP_FILENAME"
rm -f "$wcp_path"
(
  cd "$stage_dir"
  zip -r -9 -X "$wcp_path" .
)

echo "WCP package created at $wcp_path"
