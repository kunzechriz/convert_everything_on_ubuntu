# 🔄 Convert Everything on Ubuntu

> **Die ultimative Rechtsklick-Konvertierungs-Erweiterung für Ubuntu (Linux).**  
> Konvertiere Bilder, Audio, Video und PDFs direkt aus dem Nautilus-Dateimanager mit einem einzigen Klick – inklusive moderner GTK4/Libadwaita-Oberfläche, interaktivem PDF-Merger und Desktop-Benachrichtigungen.

[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%2B-E95420?logo=ubuntu\&logoColor=white)](https://ubuntu.com)
[![GNOME Nautilus](https://img.shields.io/badge/GNOME-Nautilus%2043%2B-4a86cf?logo=gnome\&logoColor=white)](https://apps.gnome.org/Nautilus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python\&logoColor=white)](https://python.org)
[![GTK4 & Libadwaita](https://img.shields.io/badge/UI-GTK4%20%2F%20Libadwaita-3584e4)](https://gnome.pages.gitlab.gnome.org/libadwaita/)

---

## ✨ Features

- 🖱️ **Natives Nautilus Rechtsklick-Menü:**  
  Rechtsklick auf beliebige Dateien ➔ `🔄 In Format umwandeln` ➔ Sofortige 1-Klick Aktionen (z.B. `➜ WebP`, `➜ MP3`, `➜ GIF`).
- 📑 **Interaktiver PDF Merger:**  
  Markiere mehrere PDFs ➔ `📑 PDFs zusammenfügen...` ➔ Intuitives Fenster zum **Anpassen der Seitenreihenfolge** (⬆️ / ⬇️ Pfeile), Hinzufügen weiterer Dateien und sofortiges verlustfreies Zusammenfügen.
- 🖼️ **Bilder zu PDF bündeln:**  
  Markiere beliebig viele Bilder und erstelle mit einem Klick ein einziges mehrseitiges PDF.
- ⚡ **Desktop-Benachrichtigungen mit Größenvergleich:**  
  Erhalte nach Abschluss sofortiges Feedback mit exaktem Vorher/Nachher-Größenvergleich (z.B. `1.4 MB ➔ 380 KB (-73%)`) und einem Button zum direkten Anzeigen im Ordner.
- 🎨 **Moderne GNOME / Libadwaita UI:**  
  Wunderschönes, natives Interface mit automatischem Dark/Light-Theme Support, Schiebereglern für Bildqualität, Skalierung (1080p, 720p, 50%) und Audio-Bitraten.
- 📦 **Umfassende Format-Unterstützung:**  
  Deckt nahezu alle gängigen Datei- und Medienformate ab.

---

## 📂 Unterstützte Formate

| Kategorie | Eingangsformate | Ausgangsformate & Funktionen |
| :--- | :--- | :--- |
| **Bilder** 🖼️ | PNG, JPG, JPEG, WEBP, BMP, TIFF, GIF, ICO, SVG, AVIF, HEIC, PSD | **PNG, JPG, WEBP, GIF, ICO, BMP, TIFF, PDF**<br>• Qualitätsregler & verlustfreie Komprimierung<br>• Skalierung (1080p, 720p, 50%, 25%)<br>• *Mehrere Bilder markieren ➔ In ein PDF zusammenfügen* |
| **Audio** 🎵 | MP3, WAV, FLAC, OGG, M4A, AAC, OPUS, WMA, AIFF | **MP3, WAV, FLAC, OGG, AAC, M4A, OPUS**<br>• Bitrate wählbar (320k, 256k, 192k, 128k)<br>• Audio-Normalisierung |
| **Video** 🎬 | MP4, MKV, WEBM, MOV, AVI, FLV, WMV, M4V, TS | **MP4 (H.264), WebM (VP9), MKV, GIF, MP3 / WAV**<br>• Hohe GIF-Qualität (2-Pass PaletteGen)<br>• Tonspur als MP3/WAV aus Videos extrahieren |
| **PDF & Docs** 📄 | PDF, Bilder | **PDFs zusammenfügen (mit anpassbarer Reihenfolge)**<br>**PDF ➔ Bilder (PNG/JPG je Seite extrahieren)**<br>**PDF komprimieren (Größe reduzieren)** |

---

## 🚀 Installation

### 1-Schritt Installation

Klone das Repository und starte das Installationsskript:

```bash
git clone https://github.com/kunzechriz/convert_everything_on_ubuntu.git
cd convert_everything_on_ubuntu
./install.sh
```

Das Skript prüft und installiert automatisch alle nötigen Abhängigkeiten (`python3-nautilus`, `ffmpeg`, `imagemagick`, `poppler-utils`, `libadwaita-1-0`), richtet das Rechtsklick-Menü ein und startet Nautilus neu.

Fertig! Die Funktion steht sofort im Dateimanager zur Verfügung.

---

## 💡 Benutzung

### 1. Über das Nautilus-Rechtsklick-Menü
1. Öffne den Ubuntu-Dateimanager (**Dateien** / Nautilus).
2. Klicke mit der rechten Maustaste auf eine oder mehrere Dateien.
3. Wähle **`🔄 In Format umwandeln`**:
   - Für Bilder: Wähle direkt `➜ WebP`, `➜ PNG`, `➜ JPG`, etc.
   - Für Videos: Wähle direkt `➜ MP4`, `➜ WebM`, `➜ GIF` oder `➜ MP3 (Tonspur extrahieren)`.
   - Für mehrere PDFs: Wähle **`📑 PDFs zusammenfügen (Reihenfolge anpassen)...`**.

### 2. PDF Merger (Reihenfolge anpassen)
Wenn du 2 oder mehr PDFs markierst und im Menü auswählst, öffnet sich der interaktive PDF-Merger:
- Verschiebe Dateien nach Belieben mit den ⬆️ / ⬇️ Buttons nach oben oder unten.
- Füge über das `+` Symbol weitere PDFs hinzu.
- Wähle Zieldateiname und Speicherort.
- Klicke auf **Zusammenfügen**!

### 3. Über die grafische Oberfläche (GUI)
Starte **Convert Everything** direkt aus dem Ubuntu-Anwendungsmenü (Super-Taste ➔ Convert Everything) oder über die Konsole:
```bash
convert-everything --gui
```
Hier kannst du Dateien per Drag & Drop hineinziehen, Qualitätsregler einstellen und Zielordner wählen.

### 4. Über das Terminal (CLI)
```bash
# Bild nach WebP umwandeln
convert-everything photo.png --to webp --quality 90

# Video in hochauflösendes GIF verwandeln
convert-everything clip.mp4 --to gif

# Tonspur aus Video extrahieren
convert-everything clip.mp4 --to mp3 --bitrate 320k

# PDF-Dateigröße komprimieren
convert-everything document.pdf --compress-pdf

# PDF-Seiten als PNGs extrahieren
convert-everything document.pdf --extract-pdf-images
```

---

## 🗑️ Deinstallation

Möchtest du das Tool wieder entfernen? Ein einziger Befehl reicht:

```bash
./uninstall.sh
```

---

## 🛠️ Technologien

- **Desktop-Integration:** `python3-nautilus` (GNOME Nautilus 43+ / 46 Python API)
- **Benutzeroberfläche:** Python `gi.repository.Adw` (Libadwaita 1) & `Gtk 4.0`
- **Konvertierungs-Engines:**
  - `FFmpeg`: Video-Transcoding, Audio-Extraktion, PaletteGen-GIFs
  - `Pillow` & `ImageMagick`: Raster- und Vektorgrafiken
  - `Poppler` (`pdfunite`, `pdftoppm`) & `Ghostscript`: PDF-Verarbeitung

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) lizenziert. Entwickelt von [Christian Kunze](https://github.com/kunzechriz).
