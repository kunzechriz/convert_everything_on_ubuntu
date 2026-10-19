import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union
from PIL import Image

from .base import BaseConverter, ConversionResult, get_unique_output_path

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
    ".gif", ".ico", ".svg", ".avif", ".heic", ".psd", ".ppm", ".pgm"
}

class ImageConverter(BaseConverter):
    """Handles image format conversions using Pillow with ImageMagick fallback."""

    def convert(
        self,
        input_path: Union[str, Path],
        target_ext: str,
        output_dir: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        quality: int = 85,
        scale: Optional[float] = None,
        max_size: Optional[Tuple[int, int]] = None,
        lossless: bool = False,
    ) -> ConversionResult:
        start_time = time.time()
        in_p = Path(input_path).resolve()
        target_ext_clean = target_ext.lower().lstrip(".")

        if not in_p.exists():
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"Eingabedatei existiert nicht: {in_p}"
            )

        orig_size = in_p.stat().st_size
        out_p = Path(output_path).resolve() if output_path else get_unique_output_path(
            in_p, target_ext_clean, Path(output_dir) if output_dir else None
        )

        try:
            self.notify_progress(10, f"Öffne {in_p.name}...")
            
            # If input is SVG or HEIC/AVIF and Pillow might struggle, check ImageMagick
            in_ext = in_p.suffix.lower()
            if in_ext in [".svg", ".heic", ".avif"]:
                success = self._convert_via_imagemagick(in_p, out_p, quality)
                if success:
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

            # Pillow-based conversion
            with Image.open(in_p) as img:
                # Handle orientation tag from EXIF
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass

                # Resizing / Scaling
                w, h = img.size
                if scale and scale > 0 and scale != 1.0:
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                elif max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                self.notify_progress(50, f"Konvertiere in {target_ext_clean.upper()}...")

                save_kwargs = {}
                target_fmt = target_ext_clean.upper()

                if target_fmt in ["JPG", "JPEG"]:
                    # JPEG does not support RGBA or P with alpha
                    if img.mode in ("RGBA", "LA", "P"):
                        # Create white background
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[-1])
                        img = bg
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    save_kwargs["quality"] = quality
                    save_kwargs["optimize"] = True

                elif target_fmt == "WEBP":
                    save_kwargs["quality"] = quality
                    save_kwargs["lossless"] = lossless
                    save_kwargs["method"] = 6

                elif target_fmt == "PNG":
                    save_kwargs["optimize"] = True
                    save_kwargs["compress_level"] = 6

                elif target_fmt == "ICO":
                    # Generate standard icon sizes
                    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                    sizes = [s for s in sizes if s[0] <= max(img.size)]
                    if not sizes:
                        sizes = [(32, 32)]
                    save_kwargs["sizes"] = sizes

                elif target_fmt == "PDF":
                    if img.mode == "RGBA":
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[-1])
                        img = bg
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    save_kwargs["resolution"] = 100.0

                out_p.parent.mkdir(parents=True, exist_ok=True)
                img.save(out_p, **save_kwargs)

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
            # Fallback to ImageMagick if available
            magick_success = self._convert_via_imagemagick(in_p, out_p, quality)
            if magick_success and out_p.exists():
                duration = time.time() - start_time
                return ConversionResult(
                    success=True,
                    input_path=in_p,
                    output_path=out_p,
                    original_size=orig_size,
                    new_size=out_p.stat().st_size,
                    duration=duration
                )
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"Bildkonvertierungsfehler: {str(e)}"
            )

    def _convert_via_imagemagick(self, in_p: Path, out_p: Path, quality: int) -> bool:
        cmd_bin = shutil.which("magick") or shutil.which("convert")
        if not cmd_bin:
            return False
        try:
            out_p.parent.mkdir(parents=True, exist_ok=True)
            cmd = [cmd_bin, str(in_p), "-quality", str(quality), str(out_p)]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.returncode == 0 and out_p.exists()
        except Exception:
            return False

    @classmethod
    def merge_to_pdf(
        cls,
        image_paths: List[Union[str, Path]],
        output_pdf_path: Union[str, Path],
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """Merges multiple images into a single multi-page PDF."""
        start_time = time.time()
        out_p = Path(output_pdf_path).resolve()
        valid_paths = [Path(p).resolve() for p in image_paths if Path(p).exists()]
        if not valid_paths:
            return ConversionResult(
                success=False,
                input_path=Path("."),
                error="Keine gültigen Bilder zum Zusammenfügen angegeben."
            )

        total_orig_size = sum(p.stat().st_size for p in valid_paths)
        opened_images = []

        try:
            total = len(valid_paths)
            for idx, p in enumerate(valid_paths):
                if progress_callback:
                    progress_callback(int((idx / total) * 80), f"Lade {p.name}...")
                im = Image.open(p)
                # Convert to RGB
                if im.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    if im.mode == "P":
                        im = im.convert("RGBA")
                    bg.paste(im, mask=im.split()[-1] if "A" in im.mode else None)
                    opened_images.append(bg)
                elif im.mode != "RGB":
                    opened_images.append(im.convert("RGB"))
                else:
                    opened_images.append(im.copy())
                im.close()

            if progress_callback:
                progress_callback(90, "Speichere PDF...")

            first = opened_images[0]
            rest = opened_images[1:] if len(opened_images) > 1 else []
            out_p.parent.mkdir(parents=True, exist_ok=True)
            first.save(out_p, "PDF", resolution=100.0, save_all=True, append_images=rest)

            duration = time.time() - start_time
            new_size = out_p.stat().st_size
            if progress_callback:
                progress_callback(100, "Fertig")

            return ConversionResult(
                success=True,
                input_path=valid_paths[0],
                output_path=out_p,
                original_size=total_orig_size,
                new_size=new_size,
                duration=duration
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=valid_paths[0],
                error=f"Fehler beim Zusammenfügen zu PDF: {str(e)}"
            )
        finally:
            for im in opened_images:
                try:
                    im.close()
                except Exception:
                    pass
