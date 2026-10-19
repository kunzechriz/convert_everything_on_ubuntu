import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

ICON_PATH = Path.home() / ".local/share/icons/hicolor/scalable/apps/convert-everything.svg"

def send_notification(
    title: str,
    message: str,
    urgency: str = "normal",
    icon: Optional[str] = None,
    target_file: Optional[Path] = None
):
    """
    Sends a desktop notification using notify-send.
    If target_file is provided, allows clicking to reveal in Nautilus.
    """
    if not shutil.which("notify-send"):
        return

    icon_to_use = icon or (str(ICON_PATH) if ICON_PATH.exists() else "emblem-default")

    def _notify():
        cmd = [
            "notify-send",
            "-a", "Convert Everything",
            "-u", urgency,
            "-i", icon_to_use,
            title,
            message
        ]

        # If target file exists and nautilus is available, offer action
        if target_file and Path(target_file).exists() and shutil.which("nautilus"):
            action_cmd = cmd + ["-A", "open=Im Ordner anzeigen"]
            try:
                proc = subprocess.run(action_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.stdout.strip() == "open":
                    # Reveal in file manager
                    subprocess.Popen(["nautilus", "--select", str(target_file)])
                return
            except Exception:
                pass

        # Fallback normal send
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    thread = threading.Thread(target=_notify, daemon=True)
    thread.start()
