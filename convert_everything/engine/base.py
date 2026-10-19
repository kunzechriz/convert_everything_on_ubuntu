from dataclasses import dataclass
from pathlib import Path
import os
import time
from typing import Optional, Callable

def format_bytes(bytes_count: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"

@dataclass
class ConversionResult:
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    original_size: int = 0
    new_size: int = 0
    duration: float = 0.0
    error: Optional[str] = None

    @property
    def size_change_str(self) -> str:
        """Returns string like '1.4 MB ➔ 450 KB (-67.8%)' or '450 KB ➔ 1.2 MB (+166%)'."""
        if not self.success or not self.output_path or not self.output_path.exists():
            return ""
        orig_str = format_bytes(self.original_size)
        new_str = format_bytes(self.new_size)
        if self.original_size > 0:
            diff = self.new_size - self.original_size
            pct = (diff / self.original_size) * 100
            sign = "+" if pct > 0 else ""
            return f"{orig_str} ➔ {new_str} ({sign}{pct:.1f}%)"
        return f"{orig_str} ➔ {new_str}"

def get_unique_output_path(input_path: Path, target_ext: str, output_dir: Optional[Path] = None) -> Path:
    """
    Returns an output path. If the output path equals the input path or already exists,
    adds a numerical suffix, e.g. 'photo (1).webp'.
    """
    out_dir = output_dir if output_dir else input_path.parent
    clean_ext = target_ext.lower().lstrip(".")
    base_stem = input_path.stem
    
    # Target path
    candidate = out_dir / f"{base_stem}.{clean_ext}"
    if candidate != input_path and not candidate.exists():
        return candidate
        
    counter = 1
    while True:
        candidate = out_dir / f"{base_stem} ({counter}).{clean_ext}"
        if candidate != input_path and not candidate.exists():
            return candidate
        counter += 1

class BaseConverter:
    """Base class for all converter engines."""
    
    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        self.progress_callback = progress_callback

    def notify_progress(self, percent: float, status: str = ""):
        if self.progress_callback:
            self.progress_callback(percent, status)
