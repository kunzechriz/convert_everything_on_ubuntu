import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from ..engine.base import format_bytes, ConversionResult
from ..engine.image import ImageConverter, SUPPORTED_IMAGE_EXTENSIONS
from ..engine.audio import AudioConverter, SUPPORTED_AUDIO_EXTENSIONS
from ..engine.video import VideoConverter, SUPPORTED_VIDEO_EXTENSIONS
from ..engine.document import DocumentConverter
from ..notify import send_notification

IMAGE_TARGETS = ["PNG", "JPG", "WEBP", "PDF", "ICO", "GIF", "BMP", "TIFF"]
AUDIO_TARGETS = ["MP3", "WAV", "FLAC", "OGG", "M4A", "AAC", "OPUS"]
VIDEO_TARGETS = ["MP4", "WEBM", "MKV", "GIF", "MP3 (Audio)", "WAV (Audio)"]
DOC_TARGETS = ["PDF (Bilder extrahieren)", "PDF (Komprimieren)"]

class MainConverterWindow(Adw.ApplicationWindow):
    def __init__(self, app, files: Optional[List[str]] = None):
        super().__init__(application=app, title="Convert Everything")
        self.set_default_size(680, 640)

        self.file_paths: List[Path] = [Path(f).resolve() for f in (files or []) if Path(f).exists()]
        default_dir = self.file_paths[0].parent if self.file_paths else Path.home()
        self.output_directory = default_dir

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        btn_add = Gtk.Button.new_from_icon_name("list-add-symbolic")
        btn_add.set_tooltip_text("Dateien hinzufügen")
        btn_add.connect("clicked", self.on_add_files_dialog)
        header.pack_start(btn_add)

        self.btn_convert = Gtk.Button(label="Konvertieren")
        self.btn_convert.add_css_class("suggested-action")
        self.btn_convert.connect("clicked", self.on_start_conversion)
        header.pack_end(self.btn_convert)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(content_box)

        # Files group
        self.group_files = Adw.PreferencesGroup()
        self.group_files.set_title("Ausgewählte Dateien")
        content_box.append(self.group_files)

        # Target options group
        self.group_options = Adw.PreferencesGroup()
        self.group_options.set_title("Zielformat & Einstellungen")
        content_box.append(self.group_options)

        # Category Row (Image, Audio, Video, Document)
        self.row_category = Adw.ComboRow()
        self.row_category.set_title("Kategorie")
        cat_model = Gtk.StringList.new(["Bilder 🖼️", "Audio 🎵", "Video 🎬", "Dokumente & PDF 📄"])
        self.row_category.set_model(cat_model)
        self.row_category.connect("notify::selected", self.on_category_changed)
        self.group_options.add(self.row_category)

        # Target Format Row
        self.row_format = Adw.ComboRow()
        self.row_format.set_title("Zielformat")
        self.group_options.add(self.row_format)

        # Quality Slider (Images & Video)
        self.row_quality = Adw.ActionRow()
        self.row_quality.set_title("Qualität")
        self.scale_quality = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 5)
        self.scale_quality.set_value(85)
        self.scale_quality.set_hexpand(True)
        self.scale_quality.set_draw_value(True)
        self.scale_quality.set_value_pos(Gtk.PositionType.RIGHT)
        self.row_quality.add_suffix(self.scale_quality)
        self.group_options.add(self.row_quality)

        # Audio Bitrate Row
        self.row_bitrate = Adw.ComboRow()
        self.row_bitrate.set_title("Audio-Bitrate")
        bitrate_model = Gtk.StringList.new(["320 kbps (Beste Qualität)", "256 kbps (Sehr gut)", "192 kbps (Standard)", "128 kbps (Kompakt)"])
        self.row_bitrate.set_model(bitrate_model)
        self.row_bitrate.set_selected(0)
        self.group_options.add(self.row_bitrate)

        # Resolution / Scale
        self.row_scale = Adw.ComboRow()
        self.row_scale.set_title("Skalierung / Bildgröße")
        scale_model = Gtk.StringList.new(["100% (Originalgröße)", "75%", "50%", "25%", "Full HD (1080p)", "HD (720p)"])
        self.row_scale.set_model(scale_model)
        self.row_scale.set_selected(0)
        self.group_options.add(self.row_scale)

        # Output folder row
        group_output = Adw.PreferencesGroup()
        group_output.set_title("Speicherort")
        content_box.append(group_output)

        self.row_dir = Adw.ActionRow()
        self.row_dir.set_title("Zielverzeichnis")
        self.row_dir.set_subtitle(str(self.output_directory))
        btn_dir = Gtk.Button(label="Ändern...")
        btn_dir.add_css_class("flat")
        btn_dir.connect("clicked", self.on_choose_directory)
        self.row_dir.add_suffix(btn_dir)
        group_output.add(self.row_dir)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_top(8)
        self.progress_bar.set_visible(False)
        content_box.append(self.progress_bar)

        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("dim-label")
        content_box.append(self.status_label)

        self.rows: List[Adw.ActionRow] = []
        self.rebuild_file_rows()
        self.auto_detect_category()
        self.update_options_visibility()

    def rebuild_file_rows(self):
        for r in self.rows:
            self.group_files.remove(r)
        self.rows.clear()

        if not self.file_paths:
            self.btn_convert.set_sensitive(False)
            empty = Adw.ActionRow()
            empty.set_title("Keine Dateien geladen")
            empty.set_subtitle("Klicke oben auf '+', um Dateien hinzuzufügen.")
            self.group_files.add(empty)
            self.rows.append(empty)
            return

        self.btn_convert.set_sensitive(True)
        for p in self.file_paths:
            row = Adw.ActionRow()
            row.set_title(p.name)
            size_str = format_bytes(p.stat().st_size)
            row.set_subtitle(f"{p.suffix.upper().lstrip('.')} • {size_str}")

            icon_name = "image-x-generic"
            suf = p.suffix.lower()
            if suf in SUPPORTED_AUDIO_EXTENSIONS:
                icon_name = "audio-x-generic"
            elif suf in SUPPORTED_VIDEO_EXTENSIONS:
                icon_name = "video-x-generic"
            elif suf == ".pdf":
                icon_name = "application-pdf"

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(24)
            row.add_prefix(icon)

            btn_del = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
            btn_del.add_css_class("flat")
            btn_del.add_css_class("destructive-action")
            btn_del.connect("clicked", lambda b, path=p: self.remove_file(path))
            row.add_suffix(btn_del)

            self.group_files.add(row)
            self.rows.append(row)

    def remove_file(self, p: Path):
        if p in self.file_paths:
            self.file_paths.remove(p)
            self.rebuild_file_rows()
            self.auto_detect_category()

    def auto_detect_category(self):
        if not self.file_paths:
            return
        ext = self.file_paths[0].suffix.lower()
        if ext in SUPPORTED_AUDIO_EXTENSIONS:
            self.row_category.set_selected(1)
        elif ext in SUPPORTED_VIDEO_EXTENSIONS:
            self.row_category.set_selected(2)
        elif ext == ".pdf":
            self.row_category.set_selected(3)
        else:
            self.row_category.set_selected(0)
        self.on_category_changed()

    def on_category_changed(self, *args):
        idx = self.row_category.get_selected()
        targets = []
        if idx == 0:  # Image
            targets = IMAGE_TARGETS
        elif idx == 1:  # Audio
            targets = AUDIO_TARGETS
        elif idx == 2:  # Video
            targets = VIDEO_TARGETS
        elif idx == 3:  # Document
            targets = DOC_TARGETS

        model = Gtk.StringList.new(targets)
        self.row_format.set_model(model)
        self.row_format.set_selected(0)
        self.update_options_visibility()

    def update_options_visibility(self):
        cat = self.row_category.get_selected()
        self.row_quality.set_visible(cat in [0, 2])
        self.row_scale.set_visible(cat in [0, 2])
        self.row_bitrate.set_visible(cat in [1, 2])

    def on_add_files_dialog(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Dateien hinzufügen")
        dialog.open_multiple(self, None, self._on_add_files_finish)

    def _on_add_files_finish(self, dialog, result):
        try:
            files_list = dialog.open_multiple_finish(result)
            for gfile in files_list:
                p = Path(gfile.get_path()).resolve()
                if p not in self.file_paths:
                    self.file_paths.append(p)
            self.rebuild_file_rows()
            self.auto_detect_category()
        except Exception:
            pass

    def on_choose_directory(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Zielverzeichnis wählen")
        dialog.select_folder(self, None, self._on_choose_directory_finish)

    def _on_choose_directory_finish(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.output_directory = Path(folder.get_path()).resolve()
                self.row_dir.set_subtitle(str(self.output_directory))
        except Exception:
            pass

    def on_start_conversion(self, button):
        if not self.file_paths:
            return

        cat = self.row_category.get_selected()
        fmt_item = self.row_format.get_selected_item()
        fmt = fmt_item.get_string() if fmt_item else "PNG"

        quality = int(self.scale_quality.get_value())
        scale_idx = self.row_scale.get_selected()
        scale_val = None
        if scale_idx == 1:
            scale_val = 0.75
        elif scale_idx == 2:
            scale_val = 0.5
        elif scale_idx == 3:
            scale_val = 0.25

        bitrates = ["320k", "256k", "192k", "128k"]
        bitrate = bitrates[self.row_bitrate.get_selected()]

        self.btn_convert.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)

        def _worker():
            total = len(self.file_paths)
            results: List[ConversionResult] = []

            for idx, file_path in enumerate(self.file_paths):
                pct = idx / total
                GLib.idle_add(self.progress_bar.set_fraction, pct)
                GLib.idle_add(self.status_label.set_text, f"Konvertiere {file_path.name} ({idx+1}/{total})...")

                res = None
                if cat == 0:  # Image
                    conv = ImageConverter()
                    res = conv.convert(
                        file_path,
                        target_ext=fmt.lower(),
                        output_dir=self.output_directory,
                        quality=quality,
                        scale=scale_val
                    )
                elif cat == 1:  # Audio
                    conv = AudioConverter()
                    res = conv.convert(
                        file_path,
                        target_ext=fmt.lower(),
                        output_dir=self.output_directory,
                        bitrate=bitrate
                    )
                elif cat == 2:  # Video
                    conv = VideoConverter()
                    clean_fmt = fmt.split()[0].lower()
                    res = conv.convert(
                        file_path,
                        target_ext=clean_fmt,
                        output_dir=self.output_directory,
                        crf=23
                    )
                elif cat == 3:  # Document / PDF
                    conv = DocumentConverter()
                    if "extrahieren" in fmt.lower():
                        res = conv.extract_pages_to_images(file_path, target_ext="png", output_dir=self.output_directory)
                    else:
                        res = conv.compress_pdf(file_path, output_dir=self.output_directory)

                if res:
                    results.append(res)

            GLib.idle_add(self._on_all_done, results)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_all_done(self, results: List[ConversionResult]):
        self.progress_bar.set_fraction(1.0)
        self.btn_convert.set_sensitive(True)
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        if successes:
            first_out = successes[0].output_path
            summary_msg = f"{len(successes)} Datei(en) erfolgreich umgewandelt!"
            if len(successes) == 1:
                summary_msg = f"{first_out.name}: {successes[0].size_change_str}"

            send_notification(
                "Konvertierung abgeschlossen",
                summary_msg,
                target_file=first_out
            )
            self.toast_overlay.add_toast(Adw.Toast(title=summary_msg))
            self.status_label.set_text(summary_msg)
        
        if failures:
            err_msg = f"{len(failures)} Fehler bei Konvertierung: {failures[0].error}"
            self.toast_overlay.add_toast(Adw.Toast(title=err_msg))


class MainConverterApp(Adw.Application):
    def __init__(self, files=None):
        super().__init__(application_id="io.github.kunzechriz.convert_everything.gui")
        self.initial_files = files

    def do_activate(self):
        win = MainConverterWindow(self, self.initial_files)
        win.present()

def run_gui(files: Optional[List[str]] = None):
    app = MainConverterApp(files)
    app.run([])

if __name__ == "__main__":
    run_gui(sys.argv[1:])
