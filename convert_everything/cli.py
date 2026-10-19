import argparse
import sys
from pathlib import Path
from typing import List

from .engine.base import format_bytes, ConversionResult
from .engine.image import ImageConverter, SUPPORTED_IMAGE_EXTENSIONS
from .engine.audio import AudioConverter, SUPPORTED_AUDIO_EXTENSIONS
from .engine.video import VideoConverter, SUPPORTED_VIDEO_EXTENSIONS
from .engine.document import DocumentConverter
from .notify import send_notification

def main():
    parser = argparse.ArgumentParser(
        prog="convert-everything",
        description="Convert Everything on Ubuntu - Unified File Converter"
    )
    parser.add_argument("files", nargs="*", help="Dateien zum Konvertieren")
    parser.add_argument("--to", dest="target_format", help="Zielformat (z.B. webp, png, mp3, mp4, etc.)")
    parser.add_argument("--quality", type=int, default=85, help="Qualität (1-100 für Bilder/Video)")
    parser.add_argument("--scale", type=float, default=None, help="Skalierungsfaktor (z.B. 0.5)")
    parser.add_argument("--bitrate", default="320k", help="Audio-Bitrate (z.B. 320k, 192k)")
    parser.add_argument("--output-dir", help="Ausgabeverzeichnis")
    parser.add_argument("--output-name", help="Ausgabedateiname")
    parser.add_argument("--merge-images-to-pdf", action="store_true", help="Bilder zu einem gemeinsamen PDF zusammenfügen")
    parser.add_argument("--compress-pdf", action="store_true", help="PDF-Dateigröße reduzieren")
    parser.add_argument("--extract-pdf-images", action="store_true", help="PDF-Seiten als Bilder extrahieren")
    parser.add_argument("--pdf-merge-dialog", action="store_true", help="Öffnet den PDF Merger Dialog zur Sortierung")
    parser.add_argument("--gui", action="store_true", help="Öffnet die GTK4 Libadwaita Benutzeroberfläche")

    args = parser.parse_args()

    # 1. Open PDF Merger Dialog
    if args.pdf_merge_dialog:
        from .ui.pdf_merger import run_pdf_merger
        run_pdf_merger(args.files)
        return

    # 2. Open Main GUI if requested or no target format provided
    if args.gui or (not args.target_format and not args.merge_images_to_pdf and not args.compress_pdf and not args.extract_pdf_images):
        from .ui.dialog import run_gui
        run_gui(args.files)
        return

    if not args.files:
        print("Keine Dateien übergeben. Nutze --help für Hilfe oder starte ohne Parameter für die GUI.")
        sys.exit(1)

    file_paths = [Path(f).resolve() for f in args.files if Path(f).exists()]
    if not file_paths:
        print("Fehler: Keine der angegebenen Dateien existiert.")
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve() if args.output_dir else None

    # 3. Merge Images to PDF
    if args.merge_images_to_pdf:
        target_pdf = out_dir / (args.output_name or "bilder_zusammengefuehrt.pdf") if out_dir else file_paths[0].parent / (args.output_name or "bilder_zusammengefuehrt.pdf")
        send_notification("PDF-Erstellung", f"Füge {len(file_paths)} Bilder zusammen...")
        res = ImageConverter.merge_to_pdf(file_paths, target_pdf)
        _handle_result(res, f"{len(file_paths)} Bilder zu PDF zusammengefügt")
        return

    # 4. Compress PDF
    if args.compress_pdf:
        doc_conv = DocumentConverter()
        for p in file_paths:
            send_notification("PDF-Komprimierung", f"Komprimiere {p.name}...")
            res = doc_conv.compress_pdf(p, output_dir=out_dir)
            _handle_result(res, f"PDF komprimiert")
        return

    # 5. Extract PDF pages to images
    if args.extract_pdf_images:
        doc_conv = DocumentConverter()
        for p in file_paths:
            send_notification("PDF-Extraktion", f"Extrahiere Seiten von {p.name}...")
            res = doc_conv.extract_pages_to_images(p, target_ext=args.target_format or "png", output_dir=out_dir)
            _handle_result(res, f"PDF-Seiten extrahiert")
        return

    # 6. Target format conversions
    target_ext = args.target_format.lower().lstrip(".")
    img_conv = ImageConverter()
    aud_conv = AudioConverter()
    vid_conv = VideoConverter()

    for p in file_paths:
        suf = p.suffix.lower()
        res = None

        if suf in SUPPORTED_IMAGE_EXTENSIONS:
            res = img_conv.convert(
                p,
                target_ext=target_ext,
                output_dir=out_dir,
                quality=args.quality,
                scale=args.scale
            )
        elif suf in SUPPORTED_AUDIO_EXTENSIONS:
            res = aud_conv.convert(
                p,
                target_ext=target_ext,
                output_dir=out_dir,
                bitrate=args.bitrate
            )
        elif suf in SUPPORTED_VIDEO_EXTENSIONS:
            res = vid_conv.convert(
                p,
                target_ext=target_ext,
                output_dir=out_dir,
                crf=23
            )
        elif suf == ".pdf":
            if target_ext in ["png", "jpg", "jpeg"]:
                res = DocumentConverter().extract_pages_to_images(p, target_ext=target_ext, output_dir=out_dir)
            else:
                res = DocumentConverter().compress_pdf(p, output_dir=out_dir)
        else:
            # Try ImageMagick / ffmpeg fallback based on target
            if target_ext in ["png", "jpg", "webp"]:
                res = img_conv.convert(p, target_ext=target_ext, output_dir=out_dir)
            else:
                res = vid_conv.convert(p, target_ext=target_ext, output_dir=out_dir)

        if res:
            _handle_result(res, f"Konvertierung nach {target_ext.upper()}")

def _handle_result(res: ConversionResult, title: str):
    if res.success and res.output_path:
        msg = f"{res.output_path.name} fertiggestellt!\n{res.size_change_str}"
        print(f"[SUCCESS] {msg}")
        send_notification(
            title=title,
            message=msg,
            target_file=res.output_path
        )
    else:
        err_msg = f"Fehler: {res.error}"
        print(f"[ERROR] {err_msg}", file=sys.stderr)
        send_notification(
            title=f"{title} fehlgeschlagen",
            message=res.error or "Unbekannter Fehler",
            urgency="critical"
        )

if __name__ == "__main__":
    main()
