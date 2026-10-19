import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Union

from .base import BaseConverter, ConversionResult, get_unique_output_path

SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv",
    ".wmv", ".m4v", ".ts", ".3gp", ".ogv"
}

class VideoConverter(BaseConverter):
    """Video converter engine using ffmpeg with GIF palettegen and audio extraction."""

    def __init__(self, progress_callback=None):
        super().__init__(progress_callback)
        self.ffmpeg_bin = shutil.which("ffmpeg")

    def convert(
        self,
        input_path: Union[str, Path],
        target_ext: str,
        output_dir: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        crf: int = 23,
        preset: str = "medium",
        scale: Optional[str] = None,
        gif_fps: int = 15,
        gif_width: int = 480,
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

        self.notify_progress(10, f"Starte Videokonvertierung für {in_p.name}...")

        # 1. High-Quality Animated GIF conversion via 2-Pass Palette
        if target_ext_clean == "gif":
            return self._convert_to_gif(in_p, out_p, orig_size, start_time, gif_fps, gif_width)

        # 2. Extract Audio from Video directly
        audio_formats = {"mp3", "wav", "flac", "ogg", "m4a", "aac"}
        if target_ext_clean in audio_formats:
            return self._extract_audio(in_p, out_p, target_ext_clean, orig_size, start_time)

        # 3. Standard Video conversion
        cmd = [self.ffmpeg_bin, "-y", "-i", str(in_p)]

        video_filters = []
        if scale:
            video_filters.append(f"scale={scale}")

        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

        if target_ext_clean == "mp4":
            cmd.extend([
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p"
            ])
        elif target_ext_clean == "webm":
            cmd.extend([
                "-c:v", "libvpx-vp9",
                "-crf", str(crf + 7),
                "-b:v", "0",
                "-c:a", "libopus",
                "-b:a", "128k"
            ])
        elif target_ext_clean == "mkv":
            cmd.extend([
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-c:a", "copy"
            ])
        else:
            cmd.extend(["-c:v", "libx264", "-c:a", "aac"])

        cmd.append(str(out_p))

        try:
            self.notify_progress(30, "Konvertiere Video...")
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
                error=f"Videokonvertierungsfehler: {str(e)}"
            )

    def _convert_to_gif(
        self, in_p: Path, out_p: Path, orig_size: int, start_time: float, fps: int, width: int
    ) -> ConversionResult:
        """2-Pass palette generation for ultra sharp GIFs without dithering artifacts."""
        self.notify_progress(20, "Generiere Farbpalette für GIF...")
        filter_str = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        cmd = [
            self.ffmpeg_bin, "-y", "-i", str(in_p),
            "-vf", filter_str,
            str(out_p)
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 or not out_p.exists():
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error=f"GIF Fehler: {proc.stderr[-400:] if proc.stderr else 'Unbekannt'}"
                )
            duration = time.time() - start_time
            return ConversionResult(
                success=True,
                input_path=in_p,
                output_path=out_p,
                original_size=orig_size,
                new_size=out_p.stat().st_size,
                duration=duration
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"GIF Konvertierungsfehler: {str(e)}"
            )

    def _extract_audio(
        self, in_p: Path, out_p: Path, target_ext: str, orig_size: int, start_time: float
    ) -> ConversionResult:
        """Extracts audio track from video."""
        self.notify_progress(20, f"Extrahiere Tonspur als {target_ext.upper()}...")
        cmd = [self.ffmpeg_bin, "-y", "-i", str(in_p), "-vn"]
        if target_ext == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
        elif target_ext == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif target_ext == "flac":
            cmd.extend(["-c:a", "flac"])
        elif target_ext in ["m4a", "aac"]:
            cmd.extend(["-c:a", "aac", "-b:a", "256k"])
        cmd.append(str(out_p))

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 or not out_p.exists():
                return ConversionResult(
                    success=False,
                    input_path=in_p,
                    error=f"Audioextraktions-Fehler: {proc.stderr[-400:] if proc.stderr else 'Unbekannt'}"
                )
            duration = time.time() - start_time
            return ConversionResult(
                success=True,
                input_path=in_p,
                output_path=out_p,
                original_size=orig_size,
                new_size=out_p.stat().st_size,
                duration=duration
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=in_p,
                error=f"Audioextraktions-Fehler: {str(e)}"
            )
