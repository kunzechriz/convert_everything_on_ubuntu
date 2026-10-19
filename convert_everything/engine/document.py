import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from .base import BaseConverter, ConversionResult, get_unique_output_path

class DocumentConverter(BaseConverter):
    """Handles PDF operations: page extraction, compression, merging, and metadata."""

    def __init__(self, progress_callback=None):
        super().__init__(progress_callback)
        self.pdftoppm_bin = shutil.which("pdftoppm")
        self.gs_bin = shutil.which("gs")
        self.pdfunite_bin = shutil.which("pdfunite")
        self.pdfinfo_bin = shutil.which("pdfinfo")

    def get_pdf_info(self, pdf_path: Union[str, Path]) -> Dict[str, Union[int, str]]:
        """Extracts page count and basic info from a PDF."""
        p = Path(pdf_path).resolve()
        info = {"pages": 1, "title": p.stem, "size": p.stat().st_size}
        if not self.pdfinfo_bin:
            return info
        try:
            res = subprocess.run([self.pdfinfo_bin, str(p)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                match = re.search(r"^Pages:\s+(\d+)", res.stdout, re.MULTILINE)
                if match:
                    info["pages"] = int(match.group(1))
        except Exception:
            pass
        return info

    def extract_pages_to_images(
        self,
        pdf_path: Union[str, Path],
        target_ext: str = "png",
        output_dir: Optional[Union[str, Path]] = None,
        dpi: int = 150
    ) -> ConversionResult:
        """Extracts all pages of a PDF to separate PNG or JPG files."""
        start_time = time.time()
        in_p = Path(pdf_path).resolve()
        target_ext_clean = "png" if target_ext.lower().lstrip(".") == "png" else "jpeg"

        if not self.pdftoppm_bin:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error="pdftoppm ist nicht installiert (Paket: poppler-utils)."
            )

        if not in_p.exists():
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"PDF existiert nicht: {in_p}"
            )

        orig_size = in_p.stat().st_size
        out_dir = Path(output_dir).resolve() if output_dir else in_p.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        prefix = out_dir / in_p.stem
        self.notify_progress(20, f"Rendere PDF-Seiten für {in_p.name}...")

        flag = f"-{target_ext_clean}"
        cmd = [self.pdftoppm_bin, flag, "-r", str(dpi), str(in_p), str(prefix)]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error=f"pdftoppm Fehler: {proc.stderr}"
                )

            # Find generated files
            ext_glob = "png" if target_ext_clean == "png" else "jpg"
            generated = list(out_dir.glob(f"{in_p.stem}-*.{ext_glob}")) + list(out_dir.glob(f"{in_p.stem}-*.jpeg"))
            if not generated:
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error="Keine Bilddateien erzeugt."
                )

            duration = time.time() - start_time
            total_new_size = sum(f.stat().st_size for f in generated)
            self.notify_progress(100, f"{len(generated)} Seiten extrahiert")

            return ConversionResult(
                success=True,
                input_path=in_p,
                output_path=generated[0],  # pointer to first or parent dir
                original_size=orig_size,
                new_size=total_new_size,
                duration=duration
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"Fehler beim Rendern der PDF-Seiten: {str(e)}"
            )

    def compress_pdf(
        self,
        pdf_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        setting: str = "/ebook"  # /screen (low res), /ebook (balanced ~150dpi), /printer (300dpi)
    ) -> ConversionResult:
        """Compresses a PDF file using Ghostscript."""
        start_time = time.time()
        in_p = Path(pdf_path).resolve()

        if not self.gs_bin:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error="Ghostscript ('gs') ist nicht installiert."
            )

        orig_size = in_p.stat().st_size
        out_p = Path(output_path).resolve() if output_path else get_unique_output_path(
            in_p, "pdf", Path(output_dir) if output_dir else None
        )
        out_p.parent.mkdir(parents=True, exist_ok=True)

        self.notify_progress(20, f"Komprimiere PDF {in_p.name}...")

        cmd = [
            self.gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={str(out_p)}",
            str(in_p)
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 or not out_p.exists():
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error=f"Ghostscript Fehler: {proc.stderr}"
                )

            duration = time.time() - start_time
            new_size = out_p.stat().st_size
            self.notify_progress(100, "Fertig")

            return ConversionResult(
                success=True,
                input_path=in_p,
                output_path=out_p,
                original_size=orig_size,
                new_size=new_size,
                duration=duration
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"PDF Komprimierungsfehler: {str(e)}"
            )

    def merge_pdfs(
        self,
        pdf_paths: List[Union[str, Path]],
        output_path: Union[str, Path]
    ) -> ConversionResult:
        """Merges multiple PDF files in given order using pdfunite or Ghostscript."""
        start_time = time.time()
        valid_paths = [Path(p).resolve() for p in pdf_paths if Path(p).exists()]
        out_p = Path(output_path).resolve()

        if not valid_paths:
            return ConversionResult(
                success=False,
                input_path=Path("."),
                error="Keine gültigen PDF-Dateien zum Zusammenfügen angegeben."
            )

        orig_total = sum(p.stat().st_size for p in valid_paths)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        self.notify_progress(20, f"Füge {len(valid_paths)} PDFs zusammen...")

        # 1. Prefer pdfunite (fast and lossless)
        if self.pdfunite_bin:
            cmd = [self.pdfunite_bin] + [str(p) for p in valid_paths] + [str(out_p)]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode == 0 and out_p.exists():
                    duration = time.time() - start_time
                    new_size = out_p.stat().st_size
                    self.notify_progress(100, "Fertig")
                    return ConversionResult(
                        success=True,
                        input_path=valid_paths[0],
                        output_path=out_p,
                        original_size=orig_total,
                        new_size=new_size,
                        duration=duration
                    )
            except Exception:
                pass

        # 2. Ghostscript fallback
        if self.gs_bin:
            cmd = [
                self.gs_bin,
                "-dBATCH",
                "-dNOPAUSE",
                "-q",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={str(out_p)}"
            ] + [str(p) for p in valid_paths]

            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode == 0 and out_p.exists():
                    duration = time.time() - start_time
                    new_size = out_p.stat().st_size
                    self.notify_progress(100, "Fertig")
                    return ConversionResult(
                        success=True,
                        input_path=valid_paths[0],
                        output_path=out_p,
                        original_size=orig_total,
                        new_size=new_size,
                        duration=duration
                    )
            except Exception as e:
                return ConversionResult(
                    success=False,
                    input_path=valid_paths[0],
                    error=f"Ghostscript Zusammenfügen fehlgeschlagen: {str(e)}"
                )

        return ConversionResult(
            success=False,
            input_path=valid_paths[0],
            error="Weder pdfunite noch Ghostscript (gs) gefunden."
        )
