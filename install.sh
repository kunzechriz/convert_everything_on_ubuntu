#!/usr/bin/env bash
# ==============================================================================
# Convert Everything on Ubuntu - Installer
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "${BLUE}${BOLD}   Convert Everything on Ubuntu - Installation       ${NC}"
echo -e "${BLUE}${BOLD}=====================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Dependency Check
echo -e "\n${YELLOW}🔍 1. Prüfe System-Abhängigkeiten...${NC}"
MISSING_PKGS=()

check_pkg() {
    local pkg="$1"
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING_PKGS+=("$pkg")
    fi
}

check_pkg "python3-nautilus"
check_pkg "ffmpeg"
check_pkg "imagemagick"
check_pkg "poppler-utils"
check_pkg "ghostscript"
check_pkg "python3-pil"
check_pkg "libnotify-bin"
check_pkg "gir1.2-adw-1"
check_pkg "gir1.2-gtk-4.0"

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Folgende benötigte System-Pakete fehlen:${NC} ${MISSING_PKGS[*]}"
    echo -e "Versuche automatische Installation via sudo apt..."
    if command -v sudo >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y "${MISSING_PKGS[@]}"
    else
        echo -e "${RED}Fehler: 'sudo' ist nicht verfügbar. Bitte installiere folgende Pakete manuell:${NC}"
        echo "sudo apt install -y ${MISSING_PKGS[*]}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Alle System-Abhängigkeiten sind bereits installiert!${NC}"
fi

# 2. Setup Directories
echo -e "\n${YELLOW}📁 2. Richte Benutzerverzeichnisse ein...${NC}"
INSTALL_DIR="$HOME/.local/share/convert-everything"
BIN_DIR="$HOME/.local/bin"
EXT_DIR="$HOME/.local/share/nautilus-python/extensions"
SCRIPT_DIR_NAUTILUS="$HOME/.local/share/nautilus/scripts"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$EXT_DIR"
mkdir -p "$SCRIPT_DIR_NAUTILUS"
mkdir -p "$APPS_DIR"
mkdir -p "$ICONS_DIR"

# 3. Copy Application Files
echo -e "\n${YELLOW}📦 3. Installiere Anwendungsdateien...${NC}"
rm -rf "$INSTALL_DIR/convert_everything"
cp -r "$SCRIPT_DIR/convert_everything" "$INSTALL_DIR/"

# Install executable wrapper
cat << 'EOF' > "$BIN_DIR/convert-everything"
#!/usr/bin/env python3
import sys
from pathlib import Path

share_root = Path.home() / ".local/share/convert-everything"
if share_root.is_dir():
    sys.path.insert(0, str(share_root))

from convert_everything.cli import main

if __name__ == "__main__":
    main()
EOF
chmod +x "$BIN_DIR/convert-everything"

# Install Nautilus Extension
cp "$SCRIPT_DIR/extension/convert_everything_nautilus.py" "$EXT_DIR/convert_everything_nautilus.py"

# Install Nautilus Script fallback
cp "$SCRIPT_DIR/scripts/Convert-Everything" "$SCRIPT_DIR_NAUTILUS/Convert-Everything"
chmod +x "$SCRIPT_DIR_NAUTILUS/Convert-Everything"

# Install Desktop Entry & Icon
cp "$SCRIPT_DIR/data/convert-everything.desktop" "$APPS_DIR/convert-everything.desktop"
cp "$SCRIPT_DIR/data/icons/convert-everything.svg" "$ICONS_DIR/convert-everything.svg"

# 4. Update Caches & Restart Nautilus
echo -e "\n${YELLOW}🔄 4. Aktualisiere Desktop-Caches und starte Nautilus neu...${NC}"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" || true

# Restart Nautilus
if pgrep -x "nautilus" >/dev/null 2>&1; then
    echo "Starte Nautilus Dateimanager neu..."
    nautilus -q 2>/dev/null || killall nautilus 2>/dev/null || true
fi

# 5. Check PATH
echo -e "\n${GREEN}${BOLD}=====================================================${NC}"
echo -e "${GREEN}${BOLD}   ✓ Installation erfolgreich abgeschlossen!         ${NC}"
echo -e "${GREEN}${BOLD}=====================================================${NC}"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "\n${YELLOW}Hinweis:${NC} '$HOME/.local/bin' ist noch nicht in deinem PATH."
    echo -e "Füge folgende Zeile zu deiner ~/.bashrc hinzu:"
    echo -e "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo -e "\n${BOLD}So nutzt du Convert Everything:${NC}"
echo -e "1. Öffne den Dateimanager (Dateien / Nautilus)."
echo -e "2. Mache einen ${BOLD}Rechtsklick${NC} auf ein Bild, Audio, Video oder eine PDF."
echo -e "3. Wähle ${BOLD}'🔄 In Format umwandeln'${NC} für 1-Klick Aktionen oder erweiterte Optionen."
echo -e "4. Markiere mehrere PDFs ➔ ${BOLD}'📑 PDFs zusammenfügen (Reihenfolge anpassen)...'${NC}"
echo -e "\nDu kannst die App auch direkt aus dem Ubuntu-Anwendungsmenü starten!"
