"""
OCR processing for screen capture.

Built on the original working version with targeted improvements:
  - English-only recognition (no Cyrillic ambiguity causing H/B swaps).
  - Remove black background (DF has black background).
  - Convert any colored text to white on black.
  - 4x INTER_NEAREST upscale after threshold (better char height for Tesseract).
  - White border added so glyphs don't touch image edges.
  - PSM 8 for single-word captures, PSM 7 for lines, PSM 6 for blocks.
  - Post-OCR correction map for recurring pixel-font misreads.
  - DEBUG_SAVE flag to write preprocessed image to disk for troubleshooting.
"""

import cv2
import numpy as np
import pytesseract
import logging
import re
from PIL import ImageGrab

log = logging.getLogger("ocr_translator")

DEBUG_SAVE: bool = False

_CHAR_FIXES: dict = {

    "Ву": "By",
    "ву": "by",
    "heen": "been",
    "hut ": "but ",
    "Hut ": "But ",
    "hy ": "by ",
    "Hy ": "By ",
    "tlie": "the",
    "tbe": "the",
    "anil": "and",
    "aud": "and",
    "lie ": "he ",
    "Lie ": "He ",
    "lier": "her",
    "Lier": "Her",
    "liis": "his",
    "Liis": "His",
    "witli": "with",
    "witb": "with",
    "tliis": "this",
    "tbis": "this",
    "ol ": "of ",
    "Ol ": "Of ",
    "lias": "has",
    "Lias": "Has",
    "iiot": "not",
    "doos": "does",

    "hlind": "blind",
    "hear": "bear",
    "hlack": "black",
    "hroken": "broken",
    "hridge": "bridge",
    "hody": "body",
    "hlood": "blood",
    "hone": "bone",
    "hranch": "branch",
    "hlow": "blow",
    "hlock": "block",
    "hlue": "blue",
    "hlade": "blade",
    "hlast": "blast",
    "hless": "bless",
    "hloom": "bloom",
    "hrown": "brown",
    "hefore": "before",
    "hehind": "behind",
    "hegin": "begin",
    "helow": "below",
    "hetween": "between",
    "heneath": "beneath",
    "hecome": "become",
    "hegan": "began",
    "heings": "beings",
    "heasts": "beasts",
    "heautiful": "beautiful",
    "hecause": "because",
    "helieve": "believe",
    "heings": "beings",
    "huilding": "building",
    "hury": "bury",
    "hutton": "button",
    "head": "bead",
    "heak": "beak",
    "heam": "beam",
    "heart": "beart",
    "heetle": "beetle",
    "hefore": "before",
    "helly": "belly",
    "helow": "below",
    "helt": "belt",
    "hench": "bench",
    "hend": "bend",
    "heneficial": "beneficial",
    "henefit": "benefit",
    "herry": "berry",
    "hest": "best",
    "hestow": "bestow",
    "hetray": "betray",
    "hetter": "better",
    "hetween": "between",
    "heware": "beware",
    "heyond": "beyond",
    "hib": "bib",
    "hide": "bide",
    "hifold": "bifold",
    "hig": "big",
    "hill": "bill",
    "hin": "bin",
    "hind": "bind",
    "hird": "bird",
    "hirth": "birth",
    "histro": "bistro",
    "hite": "bite",
    "hitter": "bitter",
    "hizarre": "bizarre",
    "hlab": "blab",
    "hlack": "black",
    "hlade": "blade",
    "hlame": "blame",
    "hlast": "blast",
    "hlaze": "blaze",
    "hleach": "bleach",
    "hleak": "bleak",
    "hleed": "bleed",
    "hlend": "blend",
    "hless": "bless",
    "hlight": "blight",
    "hlimp": "blimp",
    "hling": "bling",
    "hlink": "blink",
    "hlip": "blip",
    "hliss": "bliss",
    "hloat": "bloat",
    "hlock": "block",
    "hlog": "blog",
    "hlood": "blood",
    "hloom": "bloom",
    "hlossom": "blossom",
    "hlot": "blot",
    "hlow": "blow",
    "hlue": "blue",
    "hluff": "bluff",
    "hlunder": "blunder",
    "hlunt": "blunt",
    "hlur": "blur",
    "hlush": "blush",
    "hoar": "boar",
    "hoard": "board",
    "hoast": "boast",
    "hoastful": "boastful",
    "hoasty": "boasty",
    "hoatie": "boatie",
    "hob": "bob",
    "hody": "body",
    "hog": "bog",
    "hoil": "boil",
    "hoiler": "boiler",
    "hok": "bok",
    "hold": "bold",
    "hole": "bole",
    "holl": "boll",
    "holo": "bolo",
    "holt": "bolt",
    "homb": "bomb",
    "hona": "bona",
    "hond": "bond",
    "hone": "bone",
    "honk": "bonk",
    "hony": "bony",
    "hook": "book",
    "hoom": "boom",
    "hoon": "boon",
    "hoor": "boor",
    "hoost": "boost",
    "hoot": "boot",
    "hop": "bop",
    "horax": "borax",
    "horder": "border",
    "hore": "bore",
    "horn": "born",
    "horough": "borough",
    "hosom": "bosom",
    "hoss": "boss",
    "host": "bost",
    "hot": "bot",
    "both": "both",
    "houlder": "boulder",
    "hound": "bound",
    "hountiful": "bountiful",
    "hourbon": "bourbon",
    "hout": "bout",
    "how": "bow",
    "hox": "box",
    "hracer": "brazer",
    "hrain": "brain",
    "hrake": "brake",
    "hran": "bran",
    "hranch": "branch",
    "hrand": "brand",
    "hrasier": "brasier",
    "hrass": "brass",
    "hrave": "brave",
    "hrawl": "brawl",
    "hray": "bray",
    "hreach": "breach",
    "hread": "bread",
    "hreak": "break",
    "hreast": "breast",
    "hreath": "breath",
    "hreccia": "breccia",
    "hreed": "breed",
    "hreeze": "breeze",
    "hrew": "brew",
    "hrib": "brib",
    "hrick": "brick",
    "hridge": "bridge",
    "hrief": "brief",
    "hright": "bright",
    "hrilliant": "brilliant",
    "hrim": "brim",
    "hring": "bring",
    "hrink": "brink",
    "hrisk": "brisk",
    "hristle": "bristle",
    "hrit": "brit",
    "hroad": "broad",
    "hroken": "broken",
    "hronze": "bronze",
    "hrook": "brook",
    "hroom": "broom",
    "hroth": "broth",
    "hroud": "broud",
    "hrow": "brow",
    "hrown": "brown",
    "hruce": "bruce",
    "hruck": "bruck",
    "hrutal": "brutal",
    "hb": "bb",
    "hba": "bba",
    "hbe": "bbe",
    "hbi": "bbi",
    "hbo": "bbo",
    "hbu": "bbu",
    "hby": "bby",
    "hklind": "blind",
    "lind": "blind",
    "Elue": "blue",
	"?": ".",
}


def apply_char_fixes(text: str) -> str:
    
    for wrong, right in _CHAR_FIXES.items():
        text = text.replace(wrong, right)
    return text


class OCRProcessor:
    

    def capture_screen(self):
        
        return ImageGrab.grab(all_screens=True)

    def capture_region(self, x1, y1, x2, y2):
        
        screenshot = ImageGrab.grab(all_screens=True)
        return screenshot.crop((x1, y1, x2, y2))

    def preprocess_image(self, image_array, upscale: int = 4, border: int = 10):
        """
        Preprocess image for OCR.
        
        Strategy: Remove black background, keep all non-black pixels as white text.
        This works for any colored text (white, yellow, red, green, pink, etc.)
        on black background.

        Args:
            image_array: BGR numpy array.
            upscale:     Scale factor (default 4).
            border:      White border thickness in pixels (default 10).

        Returns:
            Preprocessed single-channel numpy array.
        """

        b, g, r = cv2.split(image_array)
        mask = (r > 50) | (g > 50) | (b > 50)

        result = np.zeros_like(image_array)
        result[mask] = 255  # White text on black background

        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

        gray = cv2.bitwise_not(gray)

        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        if upscale > 1:
            h, w = gray.shape[:2]
            gray = cv2.resize(
                gray,
                (w * upscale, h * upscale),
                interpolation=cv2.INTER_NEAREST,
            )

        if border > 0:
            gray = cv2.copyMakeBorder(
                gray, border, border, border, border,
                cv2.BORDER_CONSTANT,
                value=255,
            )
        
        return gray

    def extract_text(self, image, lang: str = "eng+dwarf_font", psm: int = 6) -> str:
        if DEBUG_SAVE:
            cv2.imwrite("debug_ocr.png", image)
            log.debug("Saved debug_ocr.png")

        try:
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=f"--oem 3 --psm {psm}",
            ).strip()
            log.debug("OCR extracted %d characters", len(text))
        except Exception as e:
            log.exception("OCR failed: %s", e)
            return ""

        text = apply_char_fixes(text)

        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def process_region(self, x1, y1, x2, y2, lang: str = "eng+dwarf_font") -> str:
        
        region = self.capture_region(x1, y1, x2, y2)
        img_array = np.array(region)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        processed = self.preprocess_image(img_array)
        return self.extract_text(processed, lang=lang, psm=6)

    def process_word(self, x1, y1, x2, y2) -> str:
        
        region = self.capture_region(x1, y1, x2, y2)
        img_array = np.array(region)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        processed = self.preprocess_image(img_array)
        return self.extract_text(processed, lang="eng+dwarf_font", psm=8)

    def process_line(self, x1, y1, x2, y2) -> str:
        
        region = self.capture_region(x1, y1, x2, y2)
        img_array = np.array(region)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        processed = self.preprocess_image(img_array)
        return self.extract_text(processed, lang="eng+dwarf_font", psm=7)

    def process_block(self, x1, y1, x2, y2) -> str:
        
        region = self.capture_region(x1, y1, x2, y2)
        img_array = np.array(region)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        processed = self.preprocess_image(img_array, upscale=3)
        return self.extract_text(processed, lang="eng+dwarf_font", psm=6)