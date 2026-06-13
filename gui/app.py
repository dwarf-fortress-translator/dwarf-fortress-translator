"""
Dwarf Fortress Translator
Hotkey: Ctrl+Alt - select area -> translation in overlay
Hotkey: Ctrl+Shift+2 - show/hide control window
"""

import tkinter as tk
from tkinter import ttk, colorchooser, font, messagebox
import threading
import logging
import time
import os
import re
import cv2
import numpy as np
from PIL import ImageGrab, ImageTk
from datetime import datetime
from config import load_settings, save_settings
from ocr import OCRProcessor
from translator import WordTranslator
from gui.hotkeys import HotkeyManager
from ocr_manager import OCRManager
from database import TranslationCache
from tkinter import font


log = logging.getLogger("ocr_translator")


class GameOverlay:


    def __init__(self, root, display_time=10000, show_original=True, max_width=500, max_height=400, auto_height=True,
                 bg_color="#1e1e1e", orig_color="#4CAF50", trans_color="#2196F3",
                 border_color="#444", alpha=0.92, font_family="Segoe UI", font_size=11):
        self.root = root
        self.window = None
        self.text_widget = None
        self.after_id = None
        self.display_time = display_time
        self.show_original = show_original
        self.max_width = max_width
        self.max_height = max_height
        self.auto_height = auto_height
        self.bg_color = bg_color
        self.orig_color = orig_color
        self.trans_color = trans_color
        self.border_color = border_color
        self.alpha = alpha
        self.font_family = font_family
        self.font_size = font_size

    def set_display_time(self, ms):
        self.display_time = ms

    def set_show_original(self, show):
        self.show_original = show

    def set_max_width(self, width):
        self.max_width = width

    def set_max_height(self, height):
        self.max_height = height

    def set_auto_height(self, auto):
        self.auto_height = auto

    def set_colors(self, bg_color, orig_color, trans_color, border_color, alpha):
        self.bg_color = bg_color
        self.orig_color = orig_color
        self.trans_color = trans_color
        self.border_color = border_color
        self.alpha = alpha

        if self.window:
            self.window.configure(bg=self.bg_color)
            self.window.configure(highlightbackground=self.border_color)
            if self.text_widget:
                self.text_widget.tag_configure("original", foreground=self.orig_color)
                self.text_widget.tag_configure("translated", foreground=self.trans_color)
            self.window.attributes("-alpha", self.alpha)

    def get_text_height(self, text):

        f = font.Font(family=self.font_family, size=self.font_size)
        lines = text.split('\n')
        line_height = f.metrics('linespace')
        total_height = len(lines) * line_height
        return total_height

    def set_font(self, font_family, font_size):
        self.font_family = font_family
        self.font_size = font_size

        if self.text_widget:
            self.text_widget.config(font=(self.font_family, self.font_size))

    def show(self, original, translated, x, y):
        if self.window is None:
            self.window = tk.Toplevel(self.root)
            self.window.overrideredirect(True)
            self.window.attributes("-topmost", True)
            self.window.attributes("-alpha", self.alpha)
            self.window.configure(bg=self.bg_color)
            self.window.configure(highlightbackground=self.border_color, highlightthickness=1)

            frame = tk.Frame(self.window, bg=self.bg_color)
            frame.pack(fill='both', expand=True, padx=2, pady=2)

            self.text_widget = tk.Text(
                frame,
                fg='#d4d4d4',
                bg=self.bg_color,
                font=(self.font_family, self.font_size),
                wrap=tk.WORD,
                padx=8,
                pady=4,
                relief='flat',
                highlightthickness=0,
                cursor="hand2"
            )
            self.text_widget.pack(side='left', fill='both', expand=True)

            self.text_widget.tag_configure("original", foreground=self.orig_color)
            self.text_widget.tag_configure("translated", foreground=self.trans_color)

            self.text_widget.config(state='disabled')

            def _on_mousewheel(event):
                self.text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.text_widget.bind("<MouseWheel>", _on_mousewheel)

            self.text_widget.bind("<Button-1>", lambda e: self.hide())
            self.window.bind("<Button-1>", lambda e: self.hide())

        self.text_widget.config(state='normal')
        self.text_widget.delete("1.0", tk.END)

        if self.show_original:
            self.text_widget.insert("1.0", f"📖 ", ("original",))
            self.text_widget.insert("end", f"{original}\n\n", ("original",))
            self.text_widget.insert("end", f"🌐 ", ("translated",))
            self.text_widget.insert("end", f"{translated}", ("translated",))
        else:
            self.text_widget.insert("1.0", f"🌐 ", ("translated",))
            self.text_widget.insert("end", f"{translated}", ("translated",))

        self.text_widget.config(state='disabled')
        self.window.update_idletasks()
        self.text_widget.update()  # Принудительное обновление
        self.window.update()  # Обновление окна

        # Расчёт высоты под текст
        lines = max(1, self.text_widget.count("1.0", "end", "displaylines")[0])
        line_height = self.font_size + 10
        text_height = lines * line_height

        if self.auto_height:
            # Авто-высота: точно по тексту, без ограничений
            height = max(80, text_height + 20)
        else:
            # Фиксированная максимальная высота
            height = min(max(80, text_height + 20), self.max_height)
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        # Корректируем X
        if x + self.max_width > screen_width:
            x = screen_width - self.max_width - 10
        if x < 0:
            x = 10

        # Корректируем Y
        new_y = y - height - 10
        if new_y < 0:
            new_y = y + 30
        if new_y + height > screen_height:
            new_y = screen_height - height - 10

        self.window.geometry(f"{self.max_width}x{height}+{x}+{new_y}")

        # self.window.geometry(f"{self.max_width}x{height}+{x + 15}+{y - height - 10}")
        self.window.deiconify()

        self.window.attributes("-alpha", 0)
        for i in range(1, 11):
            self.window.attributes("-alpha", i / 10 * self.alpha)
            self.window.update()
            time.sleep(0.008)

        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(self.display_time, self.hide)

    def hide(self):
        if self.window:
            try:
                self.window.withdraw()
            except:
                pass


class SelectionOverlay:


    def __init__(self, on_selection_complete):
        self.on_complete = on_selection_complete
        self.is_selecting = False
        self.selection_window = None
        self.canvas = None
        self.start_x = self.start_y = None
        self.rect = None
        self.tk_image = None

    def start(self):
        self.is_selecting = True
        screenshot = ImageGrab.grab(all_screens=True)

        self.selection_window = tk.Toplevel()
        self.selection_window.attributes("-fullscreen", True)
        self.selection_window.attributes("-topmost", True)
        self.selection_window.overrideredirect(True)

        self.canvas = tk.Canvas(self.selection_window, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.tk_image = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")

        self.canvas.bind("<ButtonPress-1>", self._mouse_down)
        self.canvas.bind("<B1-Motion>", self._mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._mouse_up)
        self.selection_window.bind("<Escape>", lambda e: self._cancel())

    def _mouse_down(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def _mouse_move(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def _mouse_up(self, e):
        x1, y1 = min(self.start_x, e.x), min(self.start_y, e.y)
        x2, y2 = max(self.start_x, e.x), max(self.start_y, e.y)
        self.selection_window.destroy()
        self.is_selecting = False
        self.on_complete(x1, y1, x2, y2)

    def _cancel(self):
        if self.selection_window:
            self.selection_window.destroy()
        self.is_selecting = False


class HistoryTab:


    def __init__(self, parent, cache):
        self.cache = cache
        self.parent = parent
        self.show_original = True

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        # Верхняя панель с кнопками
        top_frame = tk.Frame(self.parent)
        top_frame.pack(fill='x', pady=5, padx=5)

        # Поиск
        tk.Label(top_frame, text="Search:").pack(side='left')
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._load_history())

        tk.Button(top_frame, text="Clear", command=self._clear_search).pack(side='left', padx=2)

        # Кнопка показа/скрытия оригинала
        self.show_original_btn = tk.Button(top_frame, text="Hide Original", command=self._toggle_original)
        self.show_original_btn.pack(side='left', padx=10)

        # Кнопки управления историей
        tk.Button(top_frame, text="Copy All", command=self._copy_all).pack(side='right', padx=2)
        tk.Button(top_frame, text="Clear All", command=self._clear_all).pack(side='right', padx=2)
        tk.Button(top_frame, text="Refresh", command=self._load_history).pack(side='right', padx=2)

        # Текстовое поле с прокруткой
        text_frame = tk.Frame(self.parent)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            relief='sunken',
            bd=1
        )

        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Настройка тегов для цветов
        self.text_widget.tag_configure("date", foreground="#888888")
        self.text_widget.tag_configure("original_title", foreground="#4CAF50", font=('Segoe UI', 10, 'bold'))
        self.text_widget.tag_configure("translated_title", foreground="#2196F3", font=('Segoe UI', 10, 'bold'))
        self.text_widget.tag_configure("original_text", foreground="#4CAF50")
        self.text_widget.tag_configure("translated_text", foreground="#2196F3")
        self.text_widget.tag_configure("separator", foreground="#444444")

    def _toggle_original(self):

        self.show_original = not self.show_original
        if self.show_original:
            self.show_original_btn.config(text="Hide Original")
        else:
            self.show_original_btn.config(text="Show Original")
        self._load_history()

    def _load_history(self):

        self.text_widget.config(state='normal')
        self.text_widget.delete("1.0", tk.END)

        search = self.search_var.get().lower()
        rows = self.cache.get_history(search)

        if not rows:
            self.text_widget.insert("1.0", "📭 No translations yet.\n\nPress Ctrl+Alt to select text and translate.", ("date",))
            self.text_widget.config(state='disabled')
            return

        for i, (src, tr, fav, created) in enumerate(rows):
            # Дата
            date_str = created[:19] if created else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.text_widget.insert("end", f"[{date_str}]\n", ("date",))

            # Оригинал
            if self.show_original:
                self.text_widget.insert("end", "📖 ", ("original_title",))
                self.text_widget.insert("end", f"{src}\n", ("original_text",))

            # Перевод
            self.text_widget.insert("end", "🌐 ", ("translated_title",))
            self.text_widget.insert("end", f"{tr}\n", ("translated_text",))

            # Разделитель между записями
            if i < len(rows) - 1:
                self.text_widget.insert("end", "─" * 80 + "\n", ("separator",))

        self.text_widget.config(state='disabled')
        self.text_widget.see("1.0")

    def _clear_search(self):
        self.search_var.set("")
        self._load_history()

    def _copy_all(self):

        self.text_widget.config(state='normal')
        text = self.text_widget.get("1.0", tk.END)
        self.text_widget.config(state='disabled')

        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        messagebox.showinfo("Copied", "All history copied to clipboard")

    def _clear_all(self):

        if messagebox.askyesno("Clear History", "Delete all translation history?"):
            self.cache._clear_all()
            self._load_history()


class ControlWindow:


    def __init__(self, root, on_translate, on_lang_change, on_time_change,
                 on_engine_change, on_gemini_keys_change, on_gemini_prompt_change,
                 on_show_original_change, on_overlay_width_change, on_overlay_height_change, on_auto_height_change,
                 on_active_key_change, on_file_path_change, on_colors_change,
                 on_font_change, cache):
        self.root = root
        self.on_translate = on_translate
        self.on_file_path_change = on_file_path_change
        self.on_lang_change = on_lang_change
        self.on_time_change = on_time_change
        self.on_engine_change = on_engine_change
        self.on_gemini_keys_change = on_gemini_keys_change
        self.on_gemini_prompt_change = on_gemini_prompt_change
        self.on_show_original_change = on_show_original_change
        self.on_overlay_width_change = on_overlay_width_change
        self.on_overlay_height_change = on_overlay_height_change
        self.on_auto_height_change = on_auto_height_change
        self.on_active_key_change = on_active_key_change
        self.on_colors_change = on_colors_change
        self.on_font_change = on_font_change
        self.cache = cache

        self.root.title("Dwarf Fortress Translator")

        # Загружаем сохранённые размеры и позицию
        settings = load_settings()
        width = settings.get("window_width", 1050)
        height = settings.get("window_height", 750)
        x = settings.get("window_x", 50)
        y = settings.get("window_y", 50)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 500)

        # Привязываем событие изменения размера и перемещения
        self.root.bind("<Configure>", self._on_window_configure)

        # self.root.attributes("-topmost", True)

        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._build_ui()
        self._load_settings()

    def _on_window_configure(self, event):

        if event.widget == self.root and self.root.winfo_viewable():
            geometry = self.root.geometry()
            match = re.match(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", geometry)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                x = int(match.group(3))
                y = int(match.group(4))

                settings = load_settings()
                settings["window_width"] = width
                settings["window_height"] = height
                settings["window_x"] = x
                settings["window_y"] = y
                save_settings(settings)

    def _pick_color(self, color_var, entry):
        color = colorchooser.askcolor(title="Choose color", color=color_var.get())
        if color[1]:
            color_var.set(color[1])
            entry.delete(0, tk.END)
            entry.insert(0, color[1])
            self._on_colors_change()

    def _on_colors_change(self):
        if self.on_colors_change:
            self.on_colors_change(
                self.bg_color_var.get(),
                self.orig_color_var.get(),
                self.trans_color_var.get(),
                self.border_color_var.get(),
                int(self.alpha_var.get()) / 100
            )

    def _on_alpha_change(self):
        self._on_colors_change()

    def _reset_colors(self):
        self.bg_color_var.set("#1e1e1e")
        self.orig_color_var.set("#4CAF50")
        self.trans_color_var.set("#2196F3")
        self.border_color_var.set("#444")
        self.alpha_var.set("92")
        self._on_colors_change()

    def _on_font_change(self, event=None):
        if self.on_font_change:
            try:
                size = int(self.font_size_var.get())
                if size < 8:
                    size = 8
                if size > 30:
                    size = 30
                self.font_size_var.set(str(size))
            except:
                size = 11
                self.font_size_var.set("11")
            self.on_font_change(self.font_family_var.get(), size)

    def _reset_font(self):
        self.font_family_var.set("Segoe UI")
        self.font_size_var.set("11")
        self._on_font_change()

    def _select_batch_file(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select MD file",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.file_path_label.config(text=os.path.basename(file_path), fg='white')
            settings = load_settings()
            settings["batch_file_path"] = file_path
            save_settings(settings)
            if self.on_file_path_change:
                self.on_file_path_change(file_path)

    def _build_ui(self):
        # Заголовок
        title = tk.Label(self.root, text="OCR Translator", font=('Segoe UI', 14, 'bold'))
        title.pack(pady=10)

        # Статус
        self.status_var = tk.StringVar(value="● Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, fg="green", font=('Segoe UI', 10))
        self.status_label.pack()

        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=10, pady=5)

        # Основной контейнер с двумя панелями
        main_paned = ttk.PanedWindow(self.root, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=10, pady=5)

        # Левая панель - настройки
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=35)

        # Правая панель - история
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=65)

        # === Левая панель (настройки) ===
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill='both', expand=True)

        # Вкладка OCR
        ocr_frame = ttk.Frame(notebook)
        notebook.add(ocr_frame, text="⚙️ OCR Engine")
        self._build_ocr_tab(ocr_frame)

        # Вкладка Gemini
        gemini_frame = ttk.Frame(notebook)
        notebook.add(gemini_frame, text="🤖 Gemini API")
        self._build_gemini_tab(gemini_frame)

        # Вкладка Overlay
        overlay_frame = ttk.Frame(notebook)
        notebook.add(overlay_frame, text="🎨 Overlay")
        self._build_overlay_tab(overlay_frame)

        # Вкладка General
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="⚡ General")
        self._build_general_tab(general_frame)

        # === Правая панель (история) ===
        history_frame = ttk.LabelFrame(right_frame, text="📜 Translation History")
        history_frame.pack(fill='both', expand=True)

        self.history_tab = HistoryTab(history_frame, self.cache)

        # Кнопка выхода
        exit_btn = tk.Button(self.root, text="Exit", command=self._exit, bg='#f44336', fg='white')
        exit_btn.pack(pady=10)

    def _build_ocr_tab(self, parent):
        frame = tk.LabelFrame(parent, text="OCR Engine Selection", padx=15, pady=15)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(frame, text="Choose OCR Engine:", font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 10))

        self.ocr_engine_var = tk.StringVar(value="tesseract")

        tesseract_radio = tk.Radiobutton(frame, text="🖥️ Tesseract (local, fast, offline)",
                                         variable=self.ocr_engine_var, value="tesseract",
                                         command=self._on_ocr_engine_change)
        tesseract_radio.pack(anchor='w', pady=5)

        gemini_radio = tk.Radiobutton(frame, text="🌐 Gemini API (online, accurate, needs API key)",
                                      variable=self.ocr_engine_var, value="gemini",
                                      command=self._on_ocr_engine_change)
        gemini_radio.pack(anchor='w', pady=5)

        info = tk.Label(frame, text="\n\n💡 Tesseract works offline but may misread pixel font.\n⚠️ Gemini API is experimental. May have bugs or rate limits.\n    Requires internet and API key.",
                        font=('Segoe UI', 8), fg='gray', justify='left')
        info.pack(pady=10)

    def _build_gemini_tab(self, parent):
        frame = tk.LabelFrame(parent, text="Gemini API Configuration", padx=15, pady=15)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(frame, text="API Keys (one per line):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')

        key_frame = tk.Frame(frame)
        key_frame.pack(fill='x', pady=5)

        self.keys_text = tk.Text(key_frame, height=5, width=40)
        self.keys_text.pack(side='left', fill='x', expand=True)

        scroll = tk.Scrollbar(key_frame, command=self.keys_text.yview)
        scroll.pack(side='right', fill='y')
        self.keys_text.config(yscrollcommand=scroll.set)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill='x', pady=5)

        tk.Button(btn_frame, text="+ Add Key", command=self._add_gemini_key).pack(side='left', padx=2)
        tk.Button(btn_frame, text="− Remove Selected", command=self._remove_gemini_key).pack(side='left', padx=2)
        tk.Button(btn_frame, text="💾 Save Keys", command=self._save_gemini_keys).pack(side='left', padx=2)

        tk.Label(frame, text="Active API Key:", font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(10, 0))
        self.active_key_var = tk.StringVar(value="")
        self.key_combo = ttk.Combobox(frame, textvariable=self.active_key_var, width=50, state="readonly")
        self.key_combo.pack(anchor='w', pady=5)
        self.key_combo.bind("<<ComboboxSelected>>", self._on_active_key_change)

        tk.Label(frame, text="Custom Prompt:", font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(10, 0))

        prompt_frame = tk.Frame(frame)
        prompt_frame.pack(fill='x', pady=5)

        self.prompt_text = tk.Text(prompt_frame, height=6, width=40)
        self.prompt_text.pack(side='left', fill='x', expand=True)

        prompt_scroll = tk.Scrollbar(prompt_frame, command=self.prompt_text.yview)
        prompt_scroll.pack(side='right', fill='y')
        self.prompt_text.config(yscrollcommand=prompt_scroll.set)

        tk.Button(frame, text="💾 Save Prompt", command=self._save_gemini_prompt).pack(pady=5)

    def _build_overlay_tab(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Show original
        self.show_original_var = tk.BooleanVar(value=True)
        show_original_cb = tk.Checkbutton(scrollable_frame, text="Show original text in overlay",
                                          variable=self.show_original_var,
                                          command=self._on_show_original_change)
        show_original_cb.pack(anchor='w', pady=5)

        # Font Settings
        font_frame = tk.LabelFrame(scrollable_frame, text="🔤 Font Settings", padx=15, pady=10)
        font_frame.pack(fill='x', pady=10)

        # Font family
        tk.Label(font_frame, text="Font Family:").grid(row=0, column=0, sticky='w', padx=5)
        self.font_family_var = tk.StringVar(value="Segoe UI")
        available_fonts = list(font.families())
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.font_family_var,
                                        values=available_fonts, width=30, state="readonly")
        self.font_combo.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_change)

        # Font size
        tk.Label(font_frame, text="Font Size:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.font_size_var = tk.StringVar(value="11")
        size_spin = tk.Spinbox(font_frame, from_=8, to=30, textvariable=self.font_size_var,
                                width=8, command=self._on_font_change)
        size_spin.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        # Reset font
        tk.Button(font_frame, text="Reset Font", command=self._reset_font).grid(row=2, column=0, columnspan=2, pady=5)

        # Colors
        colors_frame = tk.LabelFrame(scrollable_frame, text="🎨 Colors", padx=15, pady=10)
        colors_frame.pack(fill='x', pady=10)

        # Background
        bg_frame = tk.Frame(colors_frame)
        bg_frame.pack(fill='x', pady=2)
        tk.Label(bg_frame, text="Background:", width=15, anchor='w').pack(side='left')
        self.bg_color_var = tk.StringVar(value="#1e1e1e")
        bg_entry = tk.Entry(bg_frame, textvariable=self.bg_color_var, width=10)
        bg_entry.pack(side='left', padx=5)
        tk.Button(bg_frame, text="Pick", command=lambda: self._pick_color(self.bg_color_var, bg_entry)).pack(side='left', padx=2)

        # Original text
        orig_frame = tk.Frame(colors_frame)
        orig_frame.pack(fill='x', pady=2)
        tk.Label(orig_frame, text="Original text:", width=15, anchor='w').pack(side='left')
        self.orig_color_var = tk.StringVar(value="#4CAF50")
        orig_entry = tk.Entry(orig_frame, textvariable=self.orig_color_var, width=10)
        orig_entry.pack(side='left', padx=5)
        tk.Button(orig_frame, text="Pick", command=lambda: self._pick_color(self.orig_color_var, orig_entry)).pack(side='left', padx=2)

        # Translated text
        trans_frame = tk.Frame(colors_frame)
        trans_frame.pack(fill='x', pady=2)
        tk.Label(trans_frame, text="Translated text:", width=15, anchor='w').pack(side='left')
        self.trans_color_var = tk.StringVar(value="#2196F3")
        trans_entry = tk.Entry(trans_frame, textvariable=self.trans_color_var, width=10)
        trans_entry.pack(side='left', padx=5)
        tk.Button(trans_frame, text="Pick", command=lambda: self._pick_color(self.trans_color_var, trans_entry)).pack(side='left', padx=2)

        # Border
        border_frame = tk.Frame(colors_frame)
        border_frame.pack(fill='x', pady=2)
        tk.Label(border_frame, text="Border:", width=15, anchor='w').pack(side='left')
        self.border_color_var = tk.StringVar(value="#444")
        border_entry = tk.Entry(border_frame, textvariable=self.border_color_var, width=10)
        border_entry.pack(side='left', padx=5)
        tk.Button(border_frame, text="Pick", command=lambda: self._pick_color(self.border_color_var, border_entry)).pack(side='left', padx=2)

        # Opacity
        alpha_frame = tk.Frame(colors_frame)
        alpha_frame.pack(fill='x', pady=2)
        tk.Label(alpha_frame, text="Opacity (0-100):", width=15, anchor='w').pack(side='left')
        self.alpha_var = tk.StringVar(value="92")
        alpha_spin = tk.Spinbox(alpha_frame, from_=30, to=100, textvariable=self.alpha_var, width=8, command=self._on_alpha_change)
        alpha_spin.pack(side='left', padx=5)

        # Reset colors
        tk.Button(colors_frame, text="Reset Colors", command=self._reset_colors).pack(pady=5)

        # Overlay width
        width_frame = tk.Frame(scrollable_frame)
        width_frame.pack(fill='x', pady=(10, 0))
        tk.Label(width_frame, text="Overlay max width (pixels):", anchor='w').pack(side='left')
        self.overlay_width_var = tk.StringVar(value="500")
        width_spin = tk.Spinbox(width_frame, from_=300, to=1000, textvariable=self.overlay_width_var,
                                 width=8, command=self._on_overlay_width_change)
        width_spin.pack(side='left', padx=5)
        tk.Label(width_frame, text="(300-1000)", fg='gray').pack(side='left', padx=5)

        # Overlay max height with auto checkbox
        height_frame = tk.Frame(scrollable_frame)
        height_frame.pack(fill='x', pady=(10, 0))
        tk.Label(height_frame, text="Overlay max height (pixels):", anchor='w').pack(side='left')
        self.overlay_height_var = tk.StringVar(value="400")
        height_spin = tk.Spinbox(height_frame, from_=100, to=800, textvariable=self.overlay_height_var,
                                  width=8, command=self._on_overlay_height_change)
        height_spin.pack(side='left', padx=5)
        tk.Label(height_frame, text="(100-800)", fg='gray').pack(side='left', padx=5)

        # Auto height checkbox
        self.auto_height_var = tk.BooleanVar(value=True)
        auto_height_cb = tk.Checkbutton(height_frame, text="Auto height",
                                         variable=self.auto_height_var,
                                         command=self._on_auto_height_change)
        auto_height_cb.pack(side='left', padx=10)

        # Display time
        tk.Label(scrollable_frame, text="Display time (seconds):", anchor='w').pack(fill='x', pady=(10, 0))
        time_frame = tk.Frame(scrollable_frame)
        time_frame.pack(anchor='w', fill='x')

        self.time_var = tk.StringVar(value="10")
        time_entry = tk.Entry(time_frame, textvariable=self.time_var, width=8)
        time_entry.pack(side='left')

        def on_time_enter(event=None):
            try:
                val = int(self.time_var.get())
                if val < 1:
                    val = 1
                if val > 300:
                    val = 300
                self.time_var.set(str(val))
                self.on_time_change(val * 1000)
            except:
                self.time_var.set("10")
                self.on_time_change(10000)

        time_entry.bind("<Return>", on_time_enter)
        time_entry.bind("<FocusOut>", on_time_enter)

        tk.Label(time_frame, text="seconds (1-300)", fg='gray').pack(side='left', padx=5)

    def _build_general_tab(self, parent):
        frame = tk.LabelFrame(parent, text="General Settings", padx=15, pady=15)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(frame, text="Target Language:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')


        from config import TARGET_LANGUAGES
        lang_items = sorted(TARGET_LANGUAGES.items(), key=lambda x: x[1])
        lang_values = [code for code, name in lang_items]
        lang_display = [name for code, name in lang_items]

        self.lang_var = tk.StringVar(value="ru")
        lang_combo = ttk.Combobox(frame, textvariable=self.lang_var, values=lang_display, width=25, state="readonly")
        lang_combo.pack(anchor='w', pady=5)

        # Сохраняем соответствие между отображаемым названием и кодом
        self.lang_display_to_code = {name: code for code, name in lang_items}

        def on_lang_select(event=None):
            selected_display = self.lang_var.get()
            lang_code = self.lang_display_to_code.get(selected_display, "ru")
            self.on_lang_change(lang_code)

        lang_combo.bind("<<ComboboxSelected>>", on_lang_select)


        current_code = self.lang_var.get()
        for name, code in self.lang_display_to_code.items():
            if code == current_code:
                self.lang_var.set(name)
                break

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        tk.Label(frame, text="MD File (Ctrl+Num0):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.file_path_var = tk.StringVar(value="")
        file_frame = tk.Frame(frame)
        file_frame.pack(fill='x', pady=5)

        self.file_path_label = tk.Label(file_frame, text="No file selected", fg='gray', anchor='w')
        self.file_path_label.pack(side='left', fill='x', expand=True)

        tk.Button(file_frame, text="Browse", command=self._select_batch_file).pack(side='right', padx=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        info = tk.Label(frame,
                        text="⌨️ Hotkeys:\n\n• Ctrl+Alt - Select area for translation\n• Ctrl+Shift+2 - Show/hide this window\n• Ctrl+Num0 - Translate selected MD file\n\n💡 Click overlay to close it",
                        font=('Segoe UI', 9), fg='gray', justify='left')
        info.pack(pady=10)

    def _on_overlay_width_change(self):
        try:
            width = int(self.overlay_width_var.get())
            self.on_overlay_width_change(width)
        except:
            pass

    def _on_overlay_height_change(self):
        try:
            height = int(self.overlay_height_var.get())
            self.on_overlay_height_change(height)
        except:
            pass

    def _on_auto_height_change(self):
        auto = self.auto_height_var.get()
        self.on_auto_height_change(auto)

        if auto:

            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    continue

                pass

    def _load_settings(self):
        settings = load_settings()
        from config import TARGET_LANGUAGES


        current_lang_code = settings.get("target_lang", "uk")
        self.current_lang_code = current_lang_code


        lang_name = TARGET_LANGUAGES.get(current_lang_code, "Russian (Русский)")
        self.lang_var.set(lang_name)

        time_sec = settings.get("overlay_display_time", 10)
        self.time_var.set(str(time_sec))
        self.ocr_engine_var.set(settings.get("ocr_engine", "tesseract"))
        self.show_original_var.set(settings.get("show_original_text", True))
        self.overlay_width_var.set(str(settings.get("overlay_width", 500)))
        self.overlay_height_var.set(str(settings.get("overlay_max_height", 400)))
        self.auto_height_var.set(settings.get("overlay_auto_height", True))

        self.font_family_var.set(settings.get("overlay_font_family", "Segoe UI"))
        self.font_size_var.set(str(settings.get("overlay_font_size", 11)))

        self.bg_color_var.set(settings.get("overlay_bg_color", "#1e1e1e"))
        self.orig_color_var.set(settings.get("overlay_original_color", "#4CAF50"))
        self.trans_color_var.set(settings.get("overlay_translated_color", "#2196F3"))
        self.border_color_var.set(settings.get("overlay_border_color", "#444"))
        self.alpha_var.set(str(settings.get("overlay_alpha", 92)))

        file_path = settings.get("batch_file_path", "")
        self.file_path_var.set(file_path)
        if file_path:
            self.file_path_label.config(text=os.path.basename(file_path), fg='white')
        else:
            self.file_path_label.config(text="No file selected", fg='gray')

        keys = settings.get("gemini_api_keys", [])
        self.keys_text.delete("1.0", tk.END)
        self.keys_text.insert("1.0", "\n".join(keys))
        self._update_key_combo()

        prompt = settings.get("gemini_prompt", "")
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", prompt)

    def _on_ocr_engine_change(self):
        self.on_engine_change(self.ocr_engine_var.get())

    def _on_show_original_change(self):
        self.on_show_original_change(self.show_original_var.get())

    def _on_active_key_change(self, event=None):
        selected = self.active_key_var.get()
        keys = [k.strip() for k in self.keys_text.get("1.0", tk.END).split('\n') if k.strip()]
        if selected in keys:
            idx = keys.index(selected)
            self.on_active_key_change(idx)

    def _update_key_combo(self):
        keys = [k.strip() for k in self.keys_text.get("1.0", tk.END).split('\n') if k.strip()]
        self.key_combo['values'] = keys
        if keys:
            self.key_combo.set(keys[0])

    def _save_gemini_keys(self):
        keys_text = self.keys_text.get("1.0", tk.END).strip()
        keys = [k.strip() for k in keys_text.split('\n') if k.strip()]
        self.on_gemini_keys_change(keys)
        self._update_key_combo()

    def _save_gemini_prompt(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        self.on_gemini_prompt_change(prompt)

    def _add_gemini_key(self):
        import tkinter.simpledialog
        key = tkinter.simpledialog.askstring("Add API Key", "Enter Gemini API Key:")
        if key:
            current = self.keys_text.get("1.0", tk.END).strip()
            if current:
                self.keys_text.insert(tk.END, f"\n{key}")
            else:
                self.keys_text.insert("1.0", key)

    def _remove_gemini_key(self):
        try:
            sel = self.keys_text.tag_ranges("sel")
            if sel:
                self.keys_text.delete("sel.first", "sel.last")
        except:
            pass

    def set_status(self, text, is_error=False):
        self.status_var.set(text)
        self.status_label.config(fg="red" if is_error else "green")

    def show(self):
        self.root.deiconify()
        self.root.lift()

    def hide(self):
        self.root.withdraw()

    def _exit(self):

        selected_display = self.lang_var.get()
        lang_code = self.lang_display_to_code.get(selected_display, "ru")


        geometry = self.root.geometry()
        match = re.match(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", geometry)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            x = int(match.group(3))
            y = int(match.group(4))
        else:
            width = 1050
            height = 750
            x = 50
            y = 50

        settings = {
            "target_lang": lang_code,
            "overlay_display_time": int(self.time_var.get()),
            "ocr_engine": self.ocr_engine_var.get(),
            "show_original_text": self.show_original_var.get(),
            "overlay_width": int(self.overlay_width_var.get()),
            "overlay_max_height": int(self.overlay_height_var.get()),
            "overlay_auto_height": self.auto_height_var.get(),
            "overlay_font_family": self.font_family_var.get(),
            "overlay_font_size": int(self.font_size_var.get()),
            "overlay_bg_color": self.bg_color_var.get(),
            "overlay_original_color": self.orig_color_var.get(),
            "overlay_translated_color": self.trans_color_var.get(),
            "overlay_border_color": self.border_color_var.get(),
            "overlay_alpha": int(self.alpha_var.get()),
            "batch_file_path": self.file_path_var.get(),
            "window_width": width,
            "window_height": height,
            "window_x": x,
            "window_y": y,
        }
        save_settings(settings)
        self.root.quit()
        self.root.destroy()
        import os
        os._exit(0)

class OCRTranslateApp:
    """Minimal OCR translation with control window."""

    def __init__(self):
        settings = load_settings()
        target_lang = settings.get("target_lang", "ru")
        display_time = settings.get("overlay_display_time", 10) * 1000
        ocr_engine = settings.get("ocr_engine", "tesseract")
        gemini_keys = settings.get("gemini_api_keys", [])
        gemini_prompt = settings.get("gemini_prompt", None)
        show_original = settings.get("show_original_text", True)
        overlay_width = settings.get("overlay_width", 500)
        overlay_max_height = settings.get("overlay_max_height", 400)
        overlay_auto_height = settings.get("overlay_auto_height", True)

        bg_color = settings.get("overlay_bg_color", "#1e1e1e")
        orig_color = settings.get("overlay_original_color", "#4CAF50")
        trans_color = settings.get("overlay_translated_color", "#2196F3")
        border_color = settings.get("overlay_border_color", "#444")
        alpha = settings.get("overlay_alpha", 92) / 100

        font_family = settings.get("overlay_font_family", "Segoe UI")
        font_size = settings.get("overlay_font_size", 11)

        self.cache = TranslationCache()
        self.ocr_manager = OCRManager(
            engine=ocr_engine,
            gemini_keys=gemini_keys,
            gemini_prompt=gemini_prompt
        )

        self.translator = WordTranslator(target_lang=target_lang)

        self.root = tk.Tk()
        self.root.withdraw()

        self.overlay = GameOverlay(
            self.root, display_time, show_original, overlay_width, overlay_max_height, overlay_auto_height,
            bg_color, orig_color, trans_color, border_color, alpha,
            font_family, font_size
        )

        self.batch_file_path_var = tk.StringVar(value=settings.get("batch_file_path", ""))

        self.control = ControlWindow(
            tk.Toplevel(self.root),
            on_translate=self._start_selection,
            on_lang_change=self._change_language,
            on_time_change=self._change_display_time,
            on_engine_change=self._change_engine,
            on_gemini_keys_change=self._change_gemini_keys,
            on_gemini_prompt_change=self._change_gemini_prompt,
            on_show_original_change=self._change_show_original,
            on_overlay_width_change=self._change_overlay_width,
            on_overlay_height_change=self._change_overlay_height,
            on_auto_height_change=self._change_auto_height,
            on_active_key_change=self._change_active_key,
            on_file_path_change=self._change_file_path,
            on_colors_change=self._change_colors,
            on_font_change=self._change_font,
            cache=self.cache
        )

        try:
            self.hotkeys = HotkeyManager(
                on_selection_callback=self._start_selection,
                on_toggle_window_callback=self._toggle_window,
                on_file_callback=self._read_and_translate_file
            )
            log.info("Hotkeys initialized")
        except Exception as e:
            log.error(f"Failed to setup hotkeys: {e}")

    def _change_auto_height(self, auto):
        self.overlay.set_auto_height(auto)
        settings = load_settings()
        settings["overlay_auto_height"] = auto
        save_settings(settings)

    def _change_overlay_height(self, height):
        self.overlay.set_max_height(height)
        settings = load_settings()
        settings["overlay_max_height"] = height
        save_settings(settings)

    def _change_font(self, font_family, font_size):
        self.overlay.set_font(font_family, font_size)
        settings = load_settings()
        settings["overlay_font_family"] = font_family
        settings["overlay_font_size"] = font_size
        save_settings(settings)

    def _change_colors(self, bg, orig, trans, border, alpha):
        self.overlay.set_colors(bg, orig, trans, border, alpha)
        settings = load_settings()
        settings["overlay_bg_color"] = bg
        settings["overlay_original_color"] = orig
        settings["overlay_translated_color"] = trans
        settings["overlay_border_color"] = border
        settings["overlay_alpha"] = int(alpha * 100)
        save_settings(settings)

    def _change_file_path(self, file_path):
        self.batch_file_path_var.set(file_path)
        settings = load_settings()
        settings["batch_file_path"] = file_path
        save_settings(settings)
        log.info(f"Batch file path saved: {file_path}")

    def _change_language(self, lang):
        self.translator.set_target_language(lang)
        settings = load_settings()
        settings["target_lang"] = lang
        save_settings(settings)

    def _change_display_time(self, ms):
        self.overlay.set_display_time(ms)
        settings = load_settings()
        settings["overlay_display_time"] = ms // 1000
        save_settings(settings)
        if hasattr(self.control, 'time_var'):
            self.control.time_var.set(str(ms // 1000))

    def _change_engine(self, engine):
        self.ocr_manager.set_engine(engine)
        settings = load_settings()
        settings["ocr_engine"] = engine
        save_settings(settings)

    def _change_gemini_keys(self, keys):
        for key in keys:
            self.ocr_manager.add_gemini_key(key)
        settings = load_settings()
        settings["gemini_api_keys"] = keys
        save_settings(settings)

    def _change_gemini_prompt(self, prompt):
        self.ocr_manager.set_gemini_prompt(prompt)
        settings = load_settings()
        settings["gemini_prompt"] = prompt
        save_settings(settings)

    def _change_show_original(self, show):
        self.overlay.set_show_original(show)
        settings = load_settings()
        settings["show_original_text"] = show
        save_settings(settings)

    def _change_overlay_width(self, width):
        self.overlay.set_max_width(width)
        settings = load_settings()
        settings["overlay_width"] = width
        save_settings(settings)

    def _change_active_key(self, idx):
        if hasattr(self.ocr_manager, 'gemini'):
            self.ocr_manager.gemini.current_key_index = idx
            log.info(f"Active Gemini key changed to index: {idx}")

    def _toggle_window(self):
        if self.control.root.winfo_viewable():
            self.control.hide()
        else:
            self.control.show()

    def _start_selection(self):
        self.selection = SelectionOverlay(self._on_selection_complete)
        self.selection.start()

    def _on_selection_complete(self, x1, y1, x2, y2):
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        text = self.ocr_manager.process_region(x1, y1, x2, y2, self.translator.get_target_language())

        if text.strip():
            translated = self.translator.translate_text(text)
            self.cache.save_translation(text, translated, None)
            self.overlay.show(text, translated, center_x, center_y - 50)
            if hasattr(self.control, 'history_tab'):
                self.control.history_tab._load_history()

    def _read_and_translate_file(self):
        file_path = self.batch_file_path_var.get()

        if not file_path or not os.path.exists(file_path):
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Select MD file for translation",
                filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if file_path:
                self.batch_file_path_var.set(file_path)
                settings = load_settings()
                settings["batch_file_path"] = file_path
                save_settings(settings)
                if hasattr(self.control, 'file_path_label'):
                    self.control.file_path_label.config(text=os.path.basename(file_path), fg='white')
            else:
                self.control.set_status("No file selected", is_error=True)
                return

        try:
            self.control.set_status("Reading file...")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                self.control.set_status("File is empty", is_error=True)
                return

            content = content.replace('#', ' ')

            self.control.set_status("Translating...")

            translated = self.translator.translate_text(content)
            
            self.cache.save_translation(content, translated, None)

            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()

            self.overlay.show(content, translated, x, y - 100)

            self.control.set_status(f"File translated: {os.path.basename(file_path)}")
            
            if hasattr(self.control, 'history_tab'):
                self.control.history_tab._load_history()

        except Exception as e:
            log.error(f"File translation failed: {e}")
            self.control.set_status(f"Error: {e}", is_error=True)

    def shutdown(self):
        log.info("Shutting down...")
        try:
            import keyboard
            keyboard.unhook_all()
        except:
            pass
        try:
            self.control.root.destroy()
        except:
            pass
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        import os
        os._exit(0)

    def run(self):
        self.control.show()
        self.control.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()