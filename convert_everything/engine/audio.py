import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Union

from .base import BaseConverter, ConversionResult, get_unique_output_path

SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac",
    ".opus", ".wma", ".aiff", ".aif", ".mka", ".alac", ".pcm"
}

class AudioConverter(BaseConverter):
    """Audio converter engine using ffmpeg."""

    def __init__(self, progress_callback=None):
        super().__init__(progress_callback)
        self.ffmpeg_bin = shutil.which("ffmpeg")

    def convert(
        self,
        input_path: Union[str, Path],
        target_ext: str,
        output_dir: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        bitrate: str = "320k",
        sample_rate: Optional[int] = None,
        normalize: bool = False,
    ) -> ConversionResult:
        start_time = time.time()
        in_p = Path(input_path).resolve()
        target_ext_clean = target_ext.lower().lstrip(".")

        if not self.ffmpeg_bin:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error="FFmpeg ist nicht installiert. Bitte mit 'sudo apt install ffmpeg' installieren."
            )

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
        out_p.parent.mkdir(parents=True, exist_ok=True)

        self.notify_progress(10, f"Konvertiere Audio {in_p.name}...")

        cmd = [self.ffmpeg_bin, "-y", "-i", str(in_p)]

        if normalize:
            cmd.extend(["-af", "loudnorm"])

        if sample_rate:
            cmd.extend(["-ar", str(sample_rate)])

        # Target-specific codec settings
        if target_ext_clean == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
        elif target_ext_clean == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif target_ext_clean == "flac":
            cmd.extend(["-c:a", "flac", "-compression_level", "8"])
        elif target_ext_clean == "ogg":
            cmd.extend(["-c:a", "libvorbis", "-q:a", "6"])
        elif target_ext_clean in ["m4a", "aac"]:
            cmd.extend(["-c:a", "aac", "-b:a", bitrate])
        elif target_ext_clean == "opus":
            cmd.extend(["-c:a", "libopus", "-b:a", "160k"])
        else:
            # Let ffmpeg auto-detect codec based on extension
            cmd.extend(["-b:a", bitrate])

        cmd.append(str(out_p))

        try:
            self.notify_progress(40, "Verarbeite Audio...")
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if proc.returncode != 0 or not out_p.exists():
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error=f"FFmpeg Fehler: {proc.stderr[-400:] if proc.stderr else 'Unbekannter Fehler'}"
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
                error=f"Audiokonvertierungsfehler: {str(e)}"
            )
