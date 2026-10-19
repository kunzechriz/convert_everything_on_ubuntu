#!/usr/bin/env bash
# ==============================================================================
# Convert Everything on Ubuntu - Uninstaller
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "${BLUE}${BOLD}   Convert Everything on Ubuntu - Deinstallation     ${NC}"
echo -e "${BLUE}${BOLD}=====================================================${NC}"

INSTALL_DIR="$HOME/.local/share/convert-everything"
BIN_FILE="$HOME/.local/bin/convert-everything"
EXT_FILE="$HOME/.local/share/nautilus-python/extensions/convert_everything_nautilus.py"
SCRIPT_FILE="$HOME/.local/share/nautilus/scripts/Convert-Everything"
DESKTOP_FILE="$HOME/.local/share/applications/convert-everything.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/convert-everything.svg"

echo -e "${YELLOW}Entferne installierte Dateien...${NC}"
rm -rf "$INSTALL_DIR"
rm -f "$BIN_FILE"
rm -f "$EXT_FILE"
rm -f "$SCRIPT_FILE"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"

# Update caches & restart nautilus
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" || true

if pgrep -x "nautilus" >/dev/null 2>&1; then
    echo "Starte Nautilus neu..."
    nautilus -q 2>/dev/null || true
fi

echo -e "\n${GREEN}${BOLD}✓ Convert Everything wurde vollständig deinstalliert.${NC}"
