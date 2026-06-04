#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MP3 Downloader"
ENTRYPOINT="mp3_downloader_gui.py"
ICON_PNG="Images/icon.png"
ICONSET_DIR="build/icon.iconset"
ICON_ICNS="build/icon.icns"
PYTHON_BIN="${PYTHON:-python3}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-build/pyinstaller-config}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must be run on macOS." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller is not installed. Run:" >&2
  echo "  $PYTHON_BIN -m pip install -r requirements-build.txt" >&2
  exit 1
fi

if [[ ! -f "$ICON_PNG" ]]; then
  echo "Missing app icon: $ICON_PNG" >&2
  exit 1
fi

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

icon_width="$(sips -g pixelWidth "$ICON_PNG" | awk '/pixelWidth/ { print $2 }')"
icon_height="$(sips -g pixelHeight "$ICON_PNG" | awk '/pixelHeight/ { print $2 }')"

for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null

  retina_size="$((size * 2))"
  if (( icon_width >= retina_size && icon_height >= retina_size )); then
    sips -z "$retina_size" "$retina_size" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
  fi
done

pyinstaller_args=(
  --noconfirm
  --clean
  --windowed
  --name "$APP_NAME"
  --add-data "$ICON_PNG:Images"
)

if iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"; then
  pyinstaller_args+=(--icon "$ICON_ICNS")
else
  echo "Could not create $ICON_ICNS, so the app bundle will use the default macOS icon." >&2
fi

if command -v ffmpeg >/dev/null 2>&1; then
  pyinstaller_args+=(--add-binary "$(command -v ffmpeg):.")
else
  echo "ffmpeg was not found in PATH, so it will not be bundled." >&2
  echo "The built app will require ffmpeg to be installed separately." >&2
fi

"$PYTHON_BIN" -m PyInstaller "${pyinstaller_args[@]}" "$ENTRYPOINT"

echo
echo "Built: dist/$APP_NAME.app"
