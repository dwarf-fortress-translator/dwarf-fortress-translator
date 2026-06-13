"""
Hotkey management - Ctrl+Alt, Ctrl+Shift+2, Ctrl+Num0
"""

import logging
import threading

log = logging.getLogger("ocr_translator")


class HotkeyManager:
    

    def __init__(self, on_selection_callback, on_toggle_window_callback, on_file_callback):
        self.on_selection = on_selection_callback
        self.on_toggle_window = on_toggle_window_callback
        self.on_file = on_file_callback
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        try:
            import keyboard
            log.info("Setting up hotkeys...")

            keyboard.add_hotkey('ctrl+alt', self._on_selection)
            log.info("Hotkey registered: Ctrl+Alt (Selection)")

            keyboard.add_hotkey('ctrl+shift+2', self._on_toggle_window)
            log.info("Hotkey registered: Ctrl+Shift+2 (Toggle Window)")

            keyboard.add_hotkey('ctrl+num 0', self._on_file)
            log.info("Hotkey registered: Ctrl+Num0 (Read MD file)")

        except ImportError:
            log.error("'keyboard' library not installed. Install with: pip install keyboard")
            raise
        except Exception as e:
            log.exception(f"Failed to setup hotkeys: {e}")
            raise

    def _on_selection(self):
        log.debug("Hotkey triggered: Ctrl+Alt")
        threading.Thread(target=self.on_selection, daemon=True).start()

    def _on_toggle_window(self):
        log.debug("Hotkey triggered: Ctrl+Shift+2")
        threading.Thread(target=self.on_toggle_window, daemon=True).start()

    def _on_file(self):
        log.debug("Hotkey triggered: Ctrl+Num0")
        threading.Thread(target=self.on_file, daemon=True).start()
