import os
import shutil
import subprocess
from pathlib import Path
from typing import List

from gi.repository import Nautilus, GObject

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
    ".gif", ".ico", ".svg", ".avif", ".heic", ".psd"
}
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma", ".aiff"
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".wmv", ".m4v"
}

CLI_BIN = shutil.which("convert-everything") or str(Path.home() / ".local/bin/convert-everything")

class ConvertEverythingExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def get_file_items(self, files: List[Nautilus.FileInfo]) -> List[Nautilus.MenuItem]:
        if not files:
            return []

        # Extract local filesystem paths
        file_paths: List[str] = []
        for f in files:
            if f.is_directory():
                continue
            loc = f.get_location()
            if loc:
                p = loc.get_path()
                if p:
                    file_paths.append(p)

        if not file_paths:
            return []

        first_ext = Path(file_paths[0]).suffix.lower()
        is_all_pdf = all(Path(p).suffix.lower() == ".pdf" for p in file_paths)
        is_all_images = all(Path(p).suffix.lower() in IMAGE_EXTENSIONS for p in file_paths)
        is_all_audio = all(Path(p).suffix.lower() in AUDIO_EXTENSIONS for p in file_paths)
        is_all_video = all(Path(p).suffix.lower() in VIDEO_EXTENSIONS for p in file_paths)

        # Root Menu Item
        root_menu_item = Nautilus.MenuItem(
            name="ConvertEverything::Root",
            label="🔄 In Format umwandeln",
            tip="Convert Everything - Datei(en) konvertieren",
            icon="emblem-default"
        )

        submenu = Nautilus.Menu()
        root_menu_item.set_submenu(submenu)

        # 1. Multi-PDF Merge Feature
        if is_all_pdf and len(file_paths) >= 2:
            merge_pdf_item = Nautilus.MenuItem(
                name="ConvertEverything::MergePdfs",
                label="📑 PDFs zusammenfügen (Reihenfolge anpassen)...",
                tip="PDFs in gewünschter Reihenfolge zusammenfügen"
            )
            merge_pdf_item.connect("activate", self._on_merge_pdfs_dialog, file_paths)
            submenu.append_item(merge_pdf_item)

        # 2. Multi-Images to Single PDF
        if is_all_images and len(file_paths) >= 2:
            merge_img_item = Nautilus.MenuItem(
                name="ConvertEverything::MergeImagesPdf",
                label="📑 Bilder in ein gemeinsames PDF zusammenfügen",
                tip="Alle markierten Bilder zu einer PDF bündeln"
            )
            merge_img_item.connect("activate", self._on_merge_images_to_pdf, file_paths)
            submenu.append_item(merge_img_item)

        # 3. Quick conversion items depending on types
        if is_all_images:
            for fmt_name, fmt_ext in [("WebP (.webp)", "webp"), ("PNG (.png)", "png"), ("JPEG (.jpg)", "jpg"), ("PDF (.pdf)", "pdf"), ("Icon (.ico)", "ico")]:
                if len(file_paths) == 1 and first_ext == f".{fmt_ext}":
                    continue
                item = Nautilus.MenuItem(
                    name=f"ConvertEverything::Img_{fmt_ext}",
                    label=f"➜ In {fmt_name}",
                    tip=f"Konvertiere in {fmt_name}"
                )
                item.connect("activate", self._on_quick_convert, file_paths, fmt_ext)
                submenu.append_item(item)

        elif is_all_audio:
            for fmt_name, fmt_ext in [("MP3 (320 kbps)", "mp3"), ("WAV (Lossless)", "wav"), ("FLAC (Lossless)", "flac"), ("OGG Vorbis", "ogg"), ("M4A / AAC", "m4a")]:
                if len(file_paths) == 1 and first_ext == f".{fmt_ext}":
                    continue
                item = Nautilus.MenuItem(
                    name=f"ConvertEverything::Aud_{fmt_ext}",
                    label=f"➜ In {fmt_name}",
                    tip=f"Konvertiere in {fmt_name}"
                )
                item.connect("activate", self._on_quick_convert, file_paths, fmt_ext)
                submenu.append_item(item)

        elif is_all_video:
            for fmt_name, fmt_ext in [("MP4 (H.264 / AAC)", "mp4"), ("WebM (Web)", "webm"), ("GIF (Animation)", "gif"), ("MP3 (Audio extrahieren)", "mp3"), ("MKV", "mkv")]:
                item = Nautilus.MenuItem(
                    name=f"ConvertEverything::Vid_{fmt_ext}",
                    label=f"➜ In {fmt_name}",
                    tip=f"Konvertiere in {fmt_name}"
                )
                item.connect("activate", self._on_quick_convert, file_paths, fmt_ext)
                submenu.append_item(item)

        elif is_all_pdf:
            # Single PDF options
            extract_png_item = Nautilus.MenuItem(
                name="ConvertEverything::PdfExtractPng",
                label="➜ In Bilder extrahieren (PNG)",
                tip="Jede PDF-Seite als PNG speichern"
            )
            extract_png_item.connect("activate", self._on_extract_pdf, file_paths, "png")
            submenu.append_item(extract_png_item)

            compress_pdf_item = Nautilus.MenuItem(
                name="ConvertEverything::PdfCompress",
                label="➜ PDF komprimieren (Größe reduzieren)",
                tip="Dateigröße des PDFs verringern"
            )
            compress_pdf_item.connect("activate", self._on_compress_pdf, file_paths)
            submenu.append_item(compress_pdf_item)

        # 4. Advanced Options / Open GUI
        adv_item = Nautilus.MenuItem(
            name="ConvertEverything::Advanced",
            label="⚙️ Erweiterte Optionen / GUI...",
            tip="Erweitertes Einstellungsfenster öffnen"
        )
        adv_item.connect("activate", self._on_open_gui, file_paths)
        submenu.append_item(adv_item)

        return [root_menu_item]

    def _run_detached(self, cmd: List[str]):
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    def _on_quick_convert(self, menu_item, files: List[str], target_format: str):
        cmd = [CLI_BIN, "--to", target_format] + files
        self._run_detached(cmd)

    def _on_merge_pdfs_dialog(self, menu_item, files: List[str]):
        cmd = [CLI_BIN, "--pdf-merge-dialog"] + files
        self._run_detached(cmd)

    def _on_merge_images_to_pdf(self, menu_item, files: List[str]):
        cmd = [CLI_BIN, "--merge-images-to-pdf"] + files
        self._run_detached(cmd)

    def _on_extract_pdf(self, menu_item, files: List[str], fmt: str):
        cmd = [CLI_BIN, "--extract-pdf-images", "--to", fmt] + files
        self._run_detached(cmd)

    def _on_compress_pdf(self, menu_item, files: List[str]):
        cmd = [CLI_BIN, "--compress-pdf"] + files
        self._run_detached(cmd)

    def _on_open_gui(self, menu_item, files: List[str]):
        cmd = [CLI_BIN, "--gui"] + files
        self._run_detached(cmd)
