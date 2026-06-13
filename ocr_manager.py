"""
OCR Manager - switch between Tesseract and Gemini
"""

import logging
import cv2
import numpy as np
from tkinter import messagebox
from ocr import OCRProcessor
from ocr_gemini import GeminiOCR

log = logging.getLogger("ocr_translator")


class OCRManager:
    

    ENGINE_TESSERACT = "tesseract"
    ENGINE_GEMINI = "gemini"

    def __init__(self, engine=ENGINE_TESSERACT, gemini_keys=None, gemini_prompt=None, show_beta_warning=True):
        self.tesseract = OCRProcessor()
        self.gemini = GeminiOCR(gemini_keys or [], gemini_prompt)
        self.current_engine = engine
        self.show_beta_warning = show_beta_warning

    def set_engine(self, engine, parent=None):
        
        if engine in [self.ENGINE_TESSERACT, self.ENGINE_GEMINI]:

            if engine == self.ENGINE_GEMINI and self.show_beta_warning and parent:
                self.show_beta_warning = False
                messagebox.showwarning(
                    "Gemini API (Beta)",
                    "⚠️ Gemini API is experimental.\n\n"
                    "Possible issues:\n"
                    "- Rate limits (429 errors)\n"
                    "- API key required\n"
                    "- May have bugs\n\n"
                    "Use at your own discretion."
                )
            self.current_engine = engine
            log.info(f"OCR engine changed to: {engine}")
        else:
            raise ValueError(f"Unknown engine: {engine}")

    def add_gemini_key(self, key):
        
        self.gemini.add_api_key(key)

    def set_gemini_prompt(self, prompt):
        
        self.gemini.set_prompt(prompt)

    def capture_region(self, x1, y1, x2, y2):
        
        from PIL import ImageGrab
        screenshot = ImageGrab.grab(all_screens=True)
        region = screenshot.crop((x1, y1, x2, y2))
        return np.array(region)

    def extract_text(self, image_array, target_lang="en") -> str:
        
        if self.current_engine == self.ENGINE_GEMINI:
            return self.gemini.extract_text(image_array, target_lang)
        else:
            processed = self.tesseract.preprocess_image(image_array)
            text = self.tesseract.extract_text(processed, lang="eng+dwarf_font", psm=6)
            from ocr import apply_char_fixes
            return apply_char_fixes(text)
    
    def process_region(self, x1, y1, x2, y2, target_lang="en") -> str:
        
        img_array = self.capture_region(x1, y1, x2, y2)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return self.extract_text(img_array, target_lang)