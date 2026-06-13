# Dwarf Fortress OCR Translator

Real-time screen capture and translation tool for Dwarf Fortress. Select any area on screen, get instant translation in a semi-transparent overlay.

## Features

- **Screen Selection** – Select any area with mouse (Ctrl+Alt)
- **Instant Overlay** – Translation appears above the game window
- **20+ Languages** – Translate to popular languages (Russian, Ukrainian, German, French, Spanish, Japanese, Chinese, etc.)
- **Two OCR Engines**:
  - **Tesseract** – Fast, offline, works with custom trained font
  - **Gemini API** – High accuracy, supports colored text (Beta)
- **History** – All translations saved with search and export
- **MD File Support** – Translate entire markdown files (Ctrl+Num0)
- **Customizable** – Font, colors, opacity, overlay size
- **Hotkeys**:
  - `Ctrl+Alt` – Select area for translation
  - `Ctrl+Shift+2` – Show/hide settings window
  - `Ctrl+Num0` – Translate selected MD file

## Requirements

- Windows 10/11 (Linux/Mac may work but not tested)
- Python 3.8+ (for source version)

## Installation

### Pre-built executable (Windows)
1. Download latest `Dwarf_Fortress_Translator.exe` from Releases
2. Run the executable

### From source
```bash
git clone https://github.com/YOUR_USERNAME/Dwarf-Fortress-OCR-Translator.git
cd Dwarf-Fortress-OCR-Translator
pip install -r requirements.txt
python main.py