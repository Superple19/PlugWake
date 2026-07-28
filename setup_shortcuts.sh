#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
DESKTOP="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
DESKTOP="${DESKTOP:-${XDG_DESKTOP_DIR:-$HOME/Desktop}}"
mkdir -p "$DESKTOP"

chmod +x "$ROOT/remote_on.sh" "$ROOT/remote_off.sh" "$ROOT/launch_gui.sh"

cat > "$DESKTOP/Remote On.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Remote On
Exec="$ROOT/remote_on.sh"
Icon=$ROOT/assets/icons/remote-on.png
Terminal=true
Categories=Utility;
EOF

cat > "$DESKTOP/Remote Off.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Remote Off
Exec="$ROOT/remote_off.sh"
Icon=$ROOT/assets/icons/remote-off.png
Terminal=true
Categories=Utility;
EOF

cat > "$DESKTOP/PlugWake.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=PlugWake
Exec="$ROOT/launch_gui.sh"
Icon=$ROOT/assets/icons/plugwake.png
Terminal=false
Categories=Utility;
EOF

chmod +x "$DESKTOP/Remote On.desktop" "$DESKTOP/Remote Off.desktop" "$DESKTOP/PlugWake.desktop"

echo "Created Linux desktop entries in $DESKTOP"
