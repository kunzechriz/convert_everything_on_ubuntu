import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from ..engine.base import format_bytes
from ..engine.document import DocumentConverter
from ..notify import send_notification

class PdfRow(Adw.ActionRow):
    def __init__(self, file_path: Path, on_move_up, on_move_down, on_remove):
        super().__init__()
        self.file_path = file_path
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.on_remove = on_remove

        self.set_title(file_path.name)
        
        # Determine page count & size
        converter = DocumentConverter()
        info = converter.get_pdf_info(file_path)
        pages = info.get("pages", 1)
        size_str = format_bytes(file_path.stat().st_size)
        self.set_subtitle(f"{pages} Seite{'n' if pages != 1 else ''} • {size_str}")

        # Leading icon
        icon = Gtk.Image.new_from_icon_name("application-pdf")
        icon.set_pixel_size(24)
        self.add_prefix(icon)

        # Trailing buttons: Up, Down, Remove
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        btn_up = Gtk.Button.new_from_icon_name("go-up-symbolic")
        btn_up.set_tooltip_text("Nach oben verschieben")
        btn_up.add_css_class("flat")
        btn_up.connect("clicked", lambda b: self.on_move_up(self))
        box.append(btn_up)

        btn_down = Gtk.Button.new_from_icon_name("go-down-symbolic")
        btn_down.set_tooltip_text("Nach unten verschieben")
        btn_down.add_css_class("flat")
        btn_down.connect("clicked", lambda b: self.on_move_down(self))
        box.append(btn_down)

        btn_del = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        btn_del.set_tooltip_text("Entfernen")
        btn_del.add_css_class("flat")
        btn_del.add_css_class("destructive-action")
        btn_del.connect("clicked", lambda b: self.on_remove(self))
        box.append(btn_del)

        self.add_suffix(box)


class PdfMergerWindow(Adw.ApplicationWindow):
    def __init__(self, app, files: Optional[List[str]] = None):
        super().__init__(application=app, title="PDFs zusammenfügen")
        self.set_default_size(580, 560)

        self.file_paths: List[Path] = [Path(f).resolve() for f in (files or []) if Path(f).suffix.lower() == ".pdf"]
        default_dir = self.file_paths[0].parent if self.file_paths else Path.home()
        self.output_directory = default_dir

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Add File Button in Header
        btn_add = Gtk.Button.new_from_icon_name("list-add-symbolic")
        btn_add.set_tooltip_text("Weitere PDF hinzufügen")
        btn_add.connect("clicked", self.on_add_file_dialog)
        header.pack_start(btn_add)

        # Merge Button in Header
        self.btn_merge = Gtk.Button(label="Zusammenfügen")
        self.btn_merge.add_css_class("suggested-action")
        self.btn_merge.connect("clicked", self.on_start_merge)
        header.pack_end(self.btn_merge)

        # Content in ScrolledWindow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(680)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(content_box)

        # Preference Group for PDF List
        self.group_list = Adw.PreferencesGroup()
        self.group_list.set_title("Reihenfolge der PDFs")
        self.group_list.set_description("Passe mit den Pfeilen die Reihenfolge an, wie die PDFs zusammengefügt werden.")
        content_box.append(self.group_list)

        # Preference Group for Output Settings
        group_out = Adw.PreferencesGroup()
        group_out.set_title("Ausgabe")
        content_box.append(group_out)

        # Output Filename Row
        self.row_name = Adw.EntryRow()
        self.row_name.set_title("Zieldateiname")
        self.row_name.set_text("zusammengefuehrt.pdf")
        group_out.add(self.row_name)

        # Output Directory Row
        self.row_dir = Adw.ActionRow()
        self.row_dir.set_title("Speicherort")
        self.row_dir.set_subtitle(str(self.output_directory))
        btn_choose_dir = Gtk.Button(label="Ändern...")
        btn_choose_dir.add_css_class("flat")
        btn_choose_dir.connect("clicked", self.on_choose_directory)
        self.row_dir.add_suffix(btn_choose_dir)
        group_out.add(self.row_dir)

        # Progress bar (hidden initially)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_top(8)
        self.progress_bar.set_visible(False)
        content_box.append(self.progress_bar)

        self.rows: List[PdfRow] = []
        self.rebuild_rows()

    def rebuild_rows(self):
        # Remove all existing rows
        for row in self.rows:
            self.group_list.remove(row)
        self.rows.clear()

        if not self.file_paths:
            self.btn_merge.set_sensitive(False)
            empty_row = Adw.ActionRow()
            empty_row.set_title("Keine PDFs ausgewählt")
            empty_row.set_subtitle("Klicke oben links auf '+' um PDFs hinzuzufügen.")
            self.group_list.add(empty_row)
            self.rows.append(empty_row)
            return

        self.btn_merge.set_sensitive(len(self.file_paths) >= 2)

        for path in self.file_paths:
            row = PdfRow(path, self.move_up, self.move_down, self.remove_item)
            self.group_list.add(row)
            self.rows.append(row)

    def move_up(self, row: PdfRow):
        idx = self.file_paths.index(row.file_path)
        if idx > 0:
            self.file_paths[idx], self.file_paths[idx - 1] = self.file_paths[idx - 1], self.file_paths[idx]
            self.rebuild_rows()

    def move_down(self, row: PdfRow):
        idx = self.file_paths.index(row.file_path)
        if idx < len(self.file_paths) - 1:
            self.file_paths[idx], self.file_paths[idx + 1] = self.file_paths[idx + 1], self.file_paths[idx]
            self.rebuild_rows()

    def remove_item(self, row: PdfRow):
        if row.file_path in self.file_paths:
            self.file_paths.remove(row.file_path)
            self.rebuild_rows()

    def on_add_file_dialog(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("PDF-Dateien auswählen")
        
        pdf_filter = Gtk.FileFilter()
        pdf_filter.set_name("PDF-Dokumente")
        pdf_filter.add_pattern("*.pdf")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(pdf_filter)
        dialog.set_filters(filters)

        dialog.open_multiple(self, None, self._on_add_files_finish)

    def _on_add_files_finish(self, dialog, result):
        try:
            files_list = dialog.open_multiple_finish(result)
            for gfile in files_list:
                p = Path(gfile.get_path()).resolve()
                if p not in self.file_paths:
                    self.file_paths.append(p)
            self.rebuild_rows()
        except Exception:
            pass

    def on_choose_directory(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Speicherordner auswählen")
        dialog.select_folder(self, None, self._on_choose_directory_finish)

    def _on_choose_directory_finish(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.output_directory = Path(folder.get_path()).resolve()
                self.row_dir.set_subtitle(str(self.output_directory))
        except Exception:
            pass

    def on_start_merge(self, button):
        if len(self.file_paths) < 2:
            self.toast_overlay.add_toast(Adw.Toast(title="Bitte wähle mindestens 2 PDFs aus."))
            return

        name = self.row_name.get_text().strip()
        if not name.endswith(".pdf"):
            name += ".pdf"

        out_path = self.output_directory / name
        self.btn_merge.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.pulse()

        def _worker():
            converter = DocumentConverter()
            result = converter.merge_pdfs(self.file_paths, out_path)
            GLib.idle_add(self._on_merge_done, result)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_merge_done(self, result):
        self.progress_bar.set_visible(False)
        self.btn_merge.set_sensitive(True)

        if result.success:
            msg = f"{len(self.file_paths)} PDFs erfolgreich zusammengefügt! ({format_bytes(result.new_size)})"
            send_notification(
                "PDFs zusammengefügt",
                f"{result.output_path.name} gespeichert ({format_bytes(result.new_size)})",
                target_file=result.output_path
            )
            self.toast_overlay.add_toast(Adw.Toast(title="Erfolgreich zusammengefügt!"))
            # Close dialog after 1 second
            GLib.timeout_add(1000, self.close)
        else:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Fehler: {result.error}"))


class PdfMergerApp(Adw.Application):
    def __init__(self, files=None):
        super().__init__(application_id="io.github.kunzechriz.convert_everything.pdfmerger")
        self.initial_files = files

    def do_activate(self):
        win = PdfMergerWindow(self, self.initial_files)
        win.present()

def run_pdf_merger(files: Optional[List[str]] = None):
    app = PdfMergerApp(files)
    app.run([])

if __name__ == "__main__":
    run_pdf_merger(sys.argv[1:])
