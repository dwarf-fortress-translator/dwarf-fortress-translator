"""
OCR Translator - Main Entry Point
Dual Hotkeys: Ctrl+Alt for OCR selection, Ctrl+Num0 for batch processing
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import setup_logging
from utils import find_tesseract_or_fail
from database import init_db
from gui.app import OCRTranslateApp

def main():
    
    log = setup_logging()

    find_tesseract_or_fail()
    init_db()  # <-- ДОБАВЬТЕ ЭТУ СТРОКУ

    try:
        app = OCRTranslateApp()
        app.run()
    except Exception as e:
        log.exception("Unhandled exception in main loop")
        raise

if __name__ == "__main__":
    main()