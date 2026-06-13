"""
Utility functions for OCR Translator
"""
import re
import hashlib
import subprocess
import shutil
import os
import sys
import tempfile
import logging
import tkinter as tk
from tkinter import messagebox

log = logging.getLogger("ocr_translator")


def normalize_text(text: str) -> str:
    
    return " ".join(text.lower().strip().split())


def text_hash(text: str) -> str:
    
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def remove_hashes(text: str) -> str:
    
    return text.replace('#', '')


def make_title(text: str) -> str:
    
    text = text.strip()
    if "." in text:
        title = text.split(".", 1)[0].strip() + "..."
    else:
        title = (text[:60] + "...") if len(text) > 60 else text
    return title


def play_audio_file_ffplay(file_path: str):
    
    from config import ffplay_exe


    ffplay_cmd = None

    if ffplay_exe and os.path.exists(ffplay_exe):
        ffplay_cmd = ffplay_exe
        log.debug(f"Using local ffplay: {ffplay_cmd}")

    if not ffplay_cmd:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_ffplay = os.path.join(script_dir, "ffmpeg", "ffplay.exe")
        if os.path.exists(local_ffplay):
            ffplay_cmd = local_ffplay
            log.debug(f"Using local ffplay: {ffplay_cmd}")

    if not ffplay_cmd:
        from config import resource_path
        local_ffplay = resource_path(os.path.join("ffmpeg", "ffplay.exe"))
        if os.path.exists(local_ffplay):
            ffplay_cmd = local_ffplay
            log.debug(f"Using resource_path ffplay: {ffplay_cmd}")

    if not ffplay_cmd:
        ffplay_cmd = shutil.which("ffplay")
        if ffplay_cmd:
            log.debug(f"Using ffplay from PATH: {ffplay_cmd}")

    if not ffplay_cmd or not os.path.exists(ffplay_cmd):
        log.warning("ffplay not found in local ffmpeg folder or PATH")
        return

    try:
        subprocess.run(
            [ffplay_cmd, "-nodisp", "-autoexit", file_path],
            check=True,
            capture_output=True,
            timeout=300
        )
    except subprocess.CalledProcessError as e:
        log.error("ffplay error: %s", e)
    except FileNotFoundError:
        log.warning("ffplay executable not found")
    except Exception as e:
        log.exception("Playback error: %s", e)


def normalize_volume_for_edge_tts(v: str) -> str:
    
    if v is None:
        return "+0%"
    v = str(v).strip()
    if v == "":
        return "+0%"
    if v.lower().endswith("db"):
        v = v[:-2].strip()
    if v.endswith("%"):
        if re.match(r'^[+-]?\d+%$', v):
            if not v.startswith(("+", "-")):
                v = "+" + v
            return v
        else:
            return "+0%"
    if re.match(r'^[+-]?\d+$', v):
        if not v.startswith(("+", "-")):
            v = "+" + v
        return v + "%"
    return "+0%"


def audio_cache_path_for(text: str, voice: str, rate: str, pitch: str, volume: str) -> str:
    
    from config import AUDIO_CACHE_DIR
    
    key_src = f"{voice}|{rate}|{pitch}|{volume}|{text}"
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()
    return os.path.join(AUDIO_CACHE_DIR, f"{key}.mp3")


def find_tesseract_or_fail():
    
    import pytesseract
    
    tess_cmd = shutil.which("tesseract")
    if not tess_cmd:
        candidate = r"tesseract-ocr5\tesseract.exe"
        if os.path.isfile(candidate):
            tess_cmd = candidate
    if not tess_cmd:
        log.error("Tesseract executable not found.")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Tesseract not found",
                "Tesseract OCR executable was not found.\n\n"
                "Please install Tesseract and add it to PATH."
            )
        except Exception:
            pass
        sys.exit(1)
    pytesseract.pytesseract.tesseract_cmd = tess_cmd
    log.debug("Using tesseract at: %s", tess_cmd)