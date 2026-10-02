import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import ctypes

import tester
import cleaner


# ---------------- Константы ----------------
APP_NAME = "BatTestsRedactor"
APP_VERSION = "1.2.5"
APP_AUTHOR = "Завражин В.А., Кулаков В.С."
APP_DESCRIPTION = (
    "программа для удобного редактирования bat тестов и автоматического\n"
    "прогона набора тестов через .exe и сбора результатов в results.txt."
)

# ---------------- Конфиг ----------------
CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "BatTestsRedactor"
)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def save_config(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

def enable_hidpi():
    """Включает DPI-aware рендеринг на Windows"""
    if sys.platform != "win32":
        return "не Windows"

    # 0) Проверим: может, DPI-awareness уже установлен манифестом python.exe
    try:
        ctx = ctypes.windll.user32.GetThreadDpiAwarenessContext()
        aw = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctx)
        # aw: -1 = invalid, 0 = unaware, 1 = system, 2 = per-monitor
        if aw >= 2:
            return f"уже per-monitor (aw={aw})"
        if aw == 1:
            return f"уже system-aware (aw={aw})"
    except (AttributeError, OSError):
        pass

    # 1) per-monitor v2 (Win10 1703+) — самый точный
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(-4):
            return "per-monitor v2 ✓"
    except (AttributeError, OSError):
        pass

    # 2) per-monitor v1 (Win8.1+)
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return "per-monitor v1 ✓"
    except (AttributeError, OSError):
        pass

    # 3) system-aware (Vista+)
    try:
        if ctypes.windll.user32.SetProcessDPIAware():
            return "system-aware ✓"
    except (AttributeError, OSError):
        pass

    return "не удалось установить"


def apply_tk_scaling(root):
    """Подгоняет масштаб Tk под реальный DPI монитора (иначе шрифты будут крошечные)."""
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass

# Тёмная палитра
BG = "#1e1e1e"
BG_PANEL = "#252526"
BG_INPUT = "#2d2d30"
BG_HOVER = "#3e3e42"
FG = "#d4d4d4"
FG_DIM = "#858585"
ACCENT = "#0e639c"
ACCENT_HOV = "#1177bb"
BORDER = "#3c3c3c"
SELECT_BG = "#094771"

# Цвета подсветки в редакторе
COLOR_HEADER  = "#b180d7"   # фиолетовый — заголовок // ...
COLOR_COMMENT = "#12b818"   # зелёный — комментарий / ...
COLOR_EXPECTED = "#02a9f0"  # голубой — ожидаемый результат { ... }

# Цвета вердиктов
COLOR_PASS = "#4ec9b0"
COLOR_FAIL = "#f48771"

# Масштаб
DEFAULT_FONT_SIZE = 11
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 32


# ============= Тултипы =============
class ToolTip:
    DELAY_MS = 500

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _=None):
        self._cancel()
        self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _on_leave(self, _=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self.tipwindow is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            bg=BG_INPUT, fg=FG,
            relief=tk.SOLID, bd=1, highlightthickness=0,
            font=("Segoe UI", 9), padx=8, pady=4,
        ).pack()

    def _hide(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw is not None:
            try:
                tw.destroy()
            except Exception:
                pass


def enable_entry_clipboard(entry, root):
    """
    Ctrl+C/V/X/A для tk.Entry. Работает в любой раскладке.

    Как устроено:
      - явные бинды на <Control-v> и т.п. перехватывают событие раньше,
        чем class-binding Tk для Entry (иначе двойная вставка);
      - <KeyPress> остаётся как fallback для русской раскладки, где
        keysym не 'v', а 'Cyrillic_em' — явные бинды не сработают.
    """
    def _paste(e=None):
        try:
            text = root.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            entry.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        entry.insert("insert", text)
        entry.xview_moveto(1.0)
        return "break"

    def _copy(e=None):
        try:
            text = entry.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        root.clipboard_clear()
        root.clipboard_append(text)
        return "break"

    def _cut(e=None):
        try:
            text = entry.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        root.clipboard_clear()
        root.clipboard_append(text)
        entry.delete("sel.first", "sel.last")
        return "break"

    def _select_all(e=None):
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)
        return "break"

    def on_key(event):
        if not (event.state & 0x4):
            return None
        shift = bool(event.state & 0x1)
        kc = event.keycode
        if kc == 86 and not shift: return _paste()
        if kc == 67 and not shift: return _copy()
        if kc == 88 and not shift: return _cut()
        if kc == 65:               return _select_all()
        return None

    # Явные бинды — перехватывают раньше class-binding Entry
    for seq in ("<Control-v>", "<Control-V>"):
        entry.bind(seq, _paste)
    for seq in ("<Control-c>", "<Control-C>"):
        entry.bind(seq, _copy)
    for seq in ("<Control-x>", "<Control-X>"):
        entry.bind(seq, _cut)
    for seq in ("<Control-a>", "<Control-A>"):
        entry.bind(seq, _select_all)

    # Fallback для нелатинских раскладок (ключ по VK-коду)
    entry.bind("<KeyPress>", on_key)

# ============= Кастомный диалог ввода =============
def dark_askstring(parent, title, prompt, initialvalue=""):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    w, h = 500, 150
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(dialog, text=prompt, bg=BG, fg=FG,
             font=("Segoe UI", 10)).pack(anchor="w", padx=15, pady=(15, 5))

    entry = tk.Entry(dialog, bg=BG_INPUT, fg=FG, insertbackground=FG,
                     bd=0, font=("Segoe UI", 11), highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=ACCENT)
    entry.pack(fill=tk.X, padx=15, ipady=6)
    entry.insert(0, initialvalue)
    entry.select_range(0, tk.END)
    entry.focus_set()
    enable_entry_clipboard(entry, dialog)

    result = {"value": None}

    def on_ok(_=None):
        result["value"] = entry.get().strip()
        dialog.destroy()

    def on_cancel(_=None):
        dialog.destroy()

    btns = tk.Frame(dialog, bg=BG)
    btns.pack(pady=15)
    ttk.Button(btns, text="OK", command=on_ok,
               style="Accent.TButton").pack(side=tk.LEFT, padx=5)
    ttk.Button(btns, text="Отмена", command=on_cancel).pack(side=tk.LEFT, padx=5)

    entry.bind("<Return>", on_ok)
    dialog.bind("<Escape>", on_cancel)

    parent.wait_window(dialog)
    return result["value"]


# ==================== Главное окно ====================
class TesterGUI:
    # Физические VK-коды клавиш (Windows) — не зависят от раскладки
    VK_A = 65
    VK_C = 67
    VK_V = 86
    VK_X = 88
    VK_Y = 89
    VK_Z = 90
    VK_BACKSLASH = 220
    VK_SLASH = 191

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME}  v{APP_VERSION}")
        self.root.geometry("1200x720")
        self.root.minsize(900, 520)
        self.root.configure(bg=BG)

        # --- Конфиг ---
        self.config = load_config()

        self.current_file = None
        self._dirty = False
        self._suppress_modified = False

        # Состояние подсветки/сворачивания
        self.test_ranges = []
        self.folded_headers = set()
        self._gutter_after = None
        self._refresh_after = None

        # Масштаб — берём из конфига, но зажимаем в допустимый диапазон
        saved_font = self.config.get("font_size", DEFAULT_FONT_SIZE)
        try:
            saved_font = int(saved_font)
        except (TypeError, ValueError):
            saved_font = DEFAULT_FONT_SIZE
        self.font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, saved_font))
        self._status_after = None

        # Панель результатов
        self.results_test_lines = []
        self._hover_test = None

        self._setup_style()
        self._build_ui()
        self._bind_events()
        self._update_title()

        # Применяем загруженный шрифт и восстанавливаем последний файл
        self._update_fonts()
        self._restore_last_file()

    # ---------- Стили ----------
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=FG,
                        fieldbackground=BG_INPUT, bordercolor=BORDER)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=BG_PANEL)

        style.configure("TLabel", background=BG, foreground=FG,
                        font=("Segoe UI", 10))
        style.configure("Dim.TLabel", background=BG, foreground=FG_DIM,
                        font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=BG, foreground=FG,
                        font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=BG, foreground=FG_DIM,
                        font=("Segoe UI", 11))

        style.configure("TButton", background=BG_INPUT, foreground=FG,
                        borderwidth=0, focuscolor=BG_INPUT,
                        padding=(14, 7), font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("active", BG_HOVER), ("pressed", "#4a4a4a")],
                  foreground=[("active", FG)])

        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        borderwidth=0, padding=(14, 7), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", ACCENT_HOV), ("pressed", "#0a4d7a")],
                  foreground=[("active", "white")])

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[2, 6, 2, 0])
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_DIM,
                        padding=[22, 9], borderwidth=0, font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", FG)])

        style.configure("Vertical.TScrollbar", background=BG_INPUT, troughcolor=BG,
                        borderwidth=0, arrowcolor=FG)
        style.configure("Horizontal.TScrollbar", background=BG_INPUT, troughcolor=BG,
                        borderwidth=0, arrowcolor=FG)

    # ---------- Построение UI ----------
    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        editor = ttk.Frame(self.notebook)
        self.notebook.add(editor, text="  Редактор  ")
        self._build_editor(editor)

        help_tab = ttk.Frame(self.notebook)
        self.notebook.add(help_tab, text="  Справка  ")
        self._build_help(help_tab)

        about_tab = ttk.Frame(self.notebook)
        self.notebook.add(about_tab, text="  О программе  ")
        self._build_about(about_tab)

        self.status = tk.Label(self.root, text="Готово", bg=BG_PANEL, fg=FG_DIM,
                               anchor="w", padx=12, pady=4,
                               font=("Segoe UI", 9))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_editor(self, parent):
        # Горизонтальный разделитель: слева — редактор, справа — результаты
        paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL, bg=BORDER,
                               sashwidth=5, sashrelief=tk.FLAT, bd=0)
        paned.pack(fill=tk.BOTH, expand=True, pady=(6, 6), padx=6)

        left = tk.Frame(paned, bg=BG)
        right = tk.Frame(paned, bg=BG)

        paned.add(left, minsize=400, stretch="always")
        paned.add(right, minsize=260, stretch="always")

        self._build_editor_content(left)
        self._build_results_panel(right)

    def _build_editor_content(self, parent):
        # Тулбар
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        btns = [
            ("📂  Открыть",         self.open_file,    "Открыть файл с тестами\nCtrl+O"),
            ("💾  Сохранить",       self.save_file,    "Сохранить изменения\nCtrl+S"),
            ("💾  Сохранить как…",  self.save_file_as, "Сохранить под новым именем\nCtrl+Shift+S"),
            ("✏  Переименовать",    self.rename_file,  "Переименовать текущий файл"),
        ]
        for text, cmd, tip in btns:
            b = ttk.Button(toolbar, text=text, command=cmd)
            b.pack(side=tk.LEFT, padx=(0, 6))
            ToolTip(b, tip)

        run_btn = ttk.Button(toolbar, text="▶  Запустить", command=self.run_tester,
                             style="Accent.TButton")
        run_btn.pack(side=tk.RIGHT)
        ToolTip(run_btn, "Прогнать тесты через .exe\nF5")

        # Информация о файле
        info = tk.Frame(parent, bg=BG)
        info.pack(fill=tk.X, pady=(0, 6))
        self.file_label = tk.Label(info, text="Файл не выбран",
                                   bg=BG, fg=FG_DIM, anchor="w",
                                   font=("Consolas", 10))
        self.file_label.pack(side=tk.LEFT)
        self.mod_label = tk.Label(info, text="", bg=BG, fg="#d19a3a",
                                  anchor="e", font=("Segoe UI", 10, "bold"))
        self.mod_label.pack(side=tk.RIGHT)

        # Контейнер с рамкой
        container = tk.Frame(parent, bg=BORDER, bd=1)
        container.pack(fill=tk.BOTH, expand=True)

        self.gutter = tk.Canvas(container, width=60, bg="#1a1a1a",
                                highlightthickness=0, bd=0)
        self.gutter.grid(row=0, column=0, sticky="ns")

        self.text = tk.Text(
            container,
            bg=BG_PANEL, fg=FG,
            insertbackground=FG,
            selectbackground=SELECT_BG,
            selectforeground="white",
            font=("Consolas", self.font_size),
            wrap=tk.NONE,
            undo=True,
            bd=0, padx=10, pady=10,
            highlightthickness=0,
        )

        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.text.xview)

        def _on_yscroll(first, last):
            vsb.set(first, last)
            self._schedule_gutter_redraw()

        vsb.configure(command=self.text.yview)
        self.text.configure(yscrollcommand=_on_yscroll, xscrollcommand=hsb.set)

        self.text.grid(row=0, column=1, sticky="nsew")
        vsb.grid(row=0, column=2, sticky="ns")
        hsb.grid(row=1, column=1, sticky="ew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        # Теги подсветки
        self.text.tag_configure("test_header", foreground=COLOR_HEADER)
        self.text.tag_configure("test_comment", foreground=COLOR_COMMENT)
        self.text.tag_configure("test_expected", foreground=COLOR_EXPECTED)
        self.text.tag_configure("folded", elide=True)

        # Gutter
        self.gutter.bind("<Button-1>", self._on_gutter_click)
        self.text.bind("<Configure>", self._on_text_configure, add="+")

        # Зум колесом
        self.text.bind("<Control-MouseWheel>", self._on_zoom_wheel)
        self.text.bind("<Control-Button-4>", lambda e: self._apply_zoom(+1))
        self.text.bind("<Control-Button-5>", lambda e: self._apply_zoom(-1))

    def _build_results_panel(self, parent):
        # --- Заголовок панели: используем grid, он надёжнее в PanedWindow ---
        header = tk.Frame(parent, bg=BG)
        header.pack(fill=tk.X, padx=8, pady=(0, 4))
        header.grid_columnconfigure(0, weight=1, minsize=1)
        header.grid_columnconfigure(1, weight=0)

        tk.Label(header, text="Результаты", bg=BG, fg=FG,
                 font=("Segoe UI", 11, "bold"),
                 anchor="w"
                 ).grid(row=0, column=0, sticky="ew")

        self.results_summary = tk.Label(
            header, text="", bg=BG, fg=FG_DIM,
            font=("Segoe UI", 9),
            anchor="e"
        )
        self.results_summary.grid(row=0, column=1, sticky="e")

        # --- Контейнер с рамкой ---
        container = tk.Frame(parent, bg=BORDER, bd=1)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        self.results_text = tk.Text(
            container,
            bg=BG_PANEL, fg=FG,
            insertbackground=FG,
            selectbackground=SELECT_BG,
            selectforeground="white",
            font=("Consolas", 10),
            wrap=tk.WORD,
            bd=0, padx=10, pady=10,
            highlightthickness=0,
            cursor="arrow",
            state="disabled",
        )

        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL,
                            command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=vsb.set)

        self.results_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Теги
        self.results_text.tag_configure("pass", foreground=COLOR_PASS,
                                        font=("Consolas", 10, "bold"))
        self.results_text.tag_configure("fail", foreground=COLOR_FAIL,
                                        font=("Consolas", 10, "bold"))
        self.results_text.tag_configure("test_name", foreground=FG,
                                        font=("Consolas", 10, "bold"))
        self.results_text.tag_configure("details", foreground=FG_DIM,
                                        font=("Consolas", 10))
        self.results_text.tag_configure("hover", background="#2a2d2e")

        self._show_results([])

        self.results_text.bind("<Button-1>", self._on_results_click)
        self.results_text.bind("<Motion>", self._on_results_motion)
        self.results_text.bind("<Leave>", lambda e: self._clear_hover())

    def _build_help(self, parent):
        text = tk.Text(parent, bg=BG, fg=FG, font=("Segoe UI", 11),
                       wrap=tk.WORD, bd=0, padx=25, pady=20,
                       insertbackground=FG, highlightthickness=0)
        text.pack(fill=tk.BOTH, expand=True)

        help_text = """КАК ПОЛЬЗОВАТЬСЯ ПРОГРАММОЙ

1. Формат файла с тестами
─────────────────────────
Каждый тест описывается тремя блоками:

    // Название теста
    / Комментарий (не обязательно)
    <тело теста — входные данные для программы>
    {
    <ожидаемый результат>
    }

• Строка, начинающаяся с  //  — заголовок теста (фиолетовый)
• Блок  { ... }  (маркеры на отдельных строках) — ожидаемый
  результат (голубой). Если в тесте несколько таких блоков —
  берётся ПОСЛЕДНИЙ, так что фигурные скобки во входных данных
  не помешают.
• Строка, начинающаяся с  /   — обычный комментарий (зелёный),
  попадает в results.txt.
• Прочие непустые строки — входные данные для программы.

Пример:

    // Тест 1: проверка суммы
    / комментарий к тесту
    2 3
    {
    5
    }

    // Тест 2: с фигурными скобками во входе
    {abc} {def}
    5
    {
    abc def
    }


2. Пошаговый запуск
────────────────────
1) Откройте существующий файл тестов (кнопка «Открыть») или создайте
   новый (кнопка «Сохранить как…»).
2) Отредактируйте содержимое во вкладке «Редактор».
3) Нажмите «Сохранить».
4) Нажмите «▶ Запустить» — появится окно, где нужно указать путь
   к папке с .exe-файлом вашей программы. В следующий раз эта
   папка подставится автоматически.
5) После прогона справа появится панель результатов: зелёные ✓ для
   пройденных тестов, красные ✗ для проваленных.

3. Подсветка и сворачивание
────────────────────
• Заголовки // — фиолетовые, ожидания { } — голубые,
  комментарии / — зелёные.
• Слева от редактора показан номер каждого теста.
• Клик по номеру теста слева сворачивает или разворачивает
  его тело (треугольник ▶ / ▼).

4. Панель результатов
────────────────────
• Появляется справа после прогона (F5).
• Клик по любому тесту в панели переходит к нему в редакторе.
• Ховер подсвечивает строку теста.
• Сводка «Пройдено: N / M» — в правом верхнем углу панели.
• Если тест провален — видны блоки «Ожидалось» и «Получено»
  (даже если программа ничего не вывела).

5. Масштаб рабочей области
────────────────────
• Ctrl + колесо мыши — увеличить / уменьшить шрифт.
• Ctrl + «+»         — увеличить шрифт.
• Ctrl + «−»         — уменьшить шрифт.
• Ctrl + 0           — сбросить масштаб к исходному (11 pt).
• Масштаб сохраняется между запусками программы.

6. Работа с файлами
────────────────────
• Открыть — загрузить файл тестов.
• Сохранить — сохранить изменения в текущий файл.
• Сохранить как… — сохранить под новым именем.
• Переименовать — переименовать текущий файл.
• Последний открытый файл автоматически открывается при
  следующем запуске.

7. Горячие клавиши
────────────────────
Ctrl+S             — сохранить
Ctrl+Shift+S       — сохранить как
Ctrl+O             — открыть
Ctrl+N             — создать новый файл
Ctrl+V / C / X / A — работа с буфером и выделением
Ctrl+Z / Y         — отменить / вернуть
Ctrl+Shift+\\       — закомментировать/раскомментировать строки
F5                 — запустить тесты
Ctrl + / − / 0     — масштаб
Подсказку с горячей клавишей можно увидеть, наведя курсор на кнопку.

8. Сохранение настроек
────────────────────
Программа запоминает:
• последний открытый файл тестов;
• последнюю папку с .exe;
• размер шрифта (масштаб).

Настройки хранятся в:
%APPDATA%\\BatTestsRedactor\\config.json

9. Примечания
────────────────────
• Файлы test*.txt, start.bat и results.txt создаются в папке с .exe.
• Перед каждым прогоном results.txt очищается автоматически.
• Если в папке несколько .exe — будет использован первый найденный.
"""
        text.insert("1.0", help_text)
        text.configure(state="disabled")

    def _build_about(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)

        tk.Label(frame, text=APP_NAME, bg=BG, fg=FG,
                 font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(frame, text=f"Версия {APP_VERSION}", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 13)).pack(anchor="w", pady=(0, 20))

        sep = tk.Frame(frame, bg=BORDER, height=1)
        sep.pack(fill=tk.X, pady=(0, 20))

        tk.Label(frame, text=APP_DESCRIPTION, bg=BG, fg=FG,
                 font=("Segoe UI", 11), justify="left").pack(anchor="w", pady=(0, 20))

        info = [
            ("Авторы", APP_AUTHOR),
        ]
        for k, v in info:
            row = tk.Frame(frame, bg=BG)
            row.pack(fill=tk.X, pady=3, anchor="w")
            tk.Label(row, text=f"{k}:", bg=BG, fg=FG_DIM,
                     width=14, anchor="w",
                     font=("Segoe UI", 10)).pack(side=tk.LEFT)
            tk.Label(row, text=v, bg=BG, fg=FG,
                     font=("Segoe UI", 10)).pack(side=tk.LEFT)

        tk.Label(frame, text=f"© 2026 {APP_AUTHOR}", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(side=tk.BOTTOM, anchor="w", pady=(30, 0))

    # ---------- Привязки ----------
    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.text.bind("<<Modified>>", self._on_modified)

        # Файлы
        self.root.bind("<Control-s>", lambda e: (self.save_file(), "break")[1])
        self.root.bind("<Control-Shift-S>", lambda e: (self.save_file_as(), "break")[1])
        self.root.bind("<Control-Shift-s>", lambda e: (self.save_file_as(), "break")[1])
        self.root.bind("<Control-o>", lambda e: (self.open_file(), "break")[1])
        self.root.bind("<Control-n>", lambda e: (self.new_file(), "break")[1])
        self.root.bind("<F5>",       lambda e: (self.run_tester(), "break")[1])

        # Зум с клавиатуры
        self.root.bind("<Control-plus>",  lambda e: (self._apply_zoom(+1), "break")[1])
        self.root.bind("<Control-equal>", lambda e: (self._apply_zoom(+1), "break")[1])
        self.root.bind("<Control-minus>", lambda e: (self._apply_zoom(-1), "break")[1])
        self.root.bind("<Control-0>",     lambda e: (self._reset_zoom(),  "break")[1])

        # Обработка Ctrl+... через физические коды клавиш (работает в любой раскладке)
        self.text.bind("<KeyPress>", self._on_key_press)

        # Enter — перехватываем для случая свёрнутого заголовка
        self.text.bind("<Return>",   self._on_return_key)
        self.text.bind("<KP_Enter>", self._on_return_key)

    # ---------- Масштаб ----------
    def _on_zoom_wheel(self, event):
        if event.delta > 0:
            self._apply_zoom(+1)
        elif event.delta < 0:
            self._apply_zoom(-1)
        return "break"

    def _apply_zoom(self, delta):
        new_size = self.font_size + delta
        new_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, new_size))
        if new_size == self.font_size:
            return
        self.font_size = new_size
        self._update_fonts()
        self._persist_config()
        self._flash_status(f"Масштаб: {new_size} pt")

    def _reset_zoom(self):
        if self.font_size == DEFAULT_FONT_SIZE:
            self._flash_status(f"Масштаб уже {DEFAULT_FONT_SIZE} pt")
            return
        self.font_size = DEFAULT_FONT_SIZE
        self._update_fonts()
        self._persist_config()
        self._flash_status(f"Масштаб сброшен: {DEFAULT_FONT_SIZE} pt")

    def _update_fonts(self):
        self.text.configure(font=("Consolas", self.font_size))
        self._schedule_gutter_redraw()

    def _flash_status(self, message, timeout_ms=1800):
        self.status.config(text=message)
        if self._status_after is not None:
            try:
                self.root.after_cancel(self._status_after)
            except Exception:
                pass
        self._status_after = self.root.after(
            timeout_ms,
            lambda: (self.status.config(text="Готово"),
                     setattr(self, "_status_after", None))
        )

    # ---------- Конфиг ----------
    def _persist_config(self):
        self.config["font_size"] = self.font_size
        if self.current_file:
            self.config["last_file"] = self.current_file
        save_config(self.config)

    def _restore_last_file(self):
        last = self.config.get("last_file")
        if not last or not os.path.exists(last):
            return
        try:
            with open(last, "r", encoding="utf-8") as f:
                content = f.read()

            self._suppress_modified = True
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content)
            self.text.edit_reset()
            self.text.edit_modified(False)
            self._suppress_modified = False
            self._dirty = False

            self.mod_label.config(text="")
            self.current_file = last
            self._update_file_label()
            self._update_title()
            self._show_results([])
            self._refresh_view()
            self._flash_status(f"Восстановлен файл: {os.path.basename(last)}")
        except Exception:
            pass

    # ---------- Работа с текстом ----------
    def _on_modified(self, _=None):
        if self._suppress_modified:
            return
        if self.text.edit_modified():
            self._dirty = True
            self.mod_label.config(text="● изменено")
            self._update_title()
            self.text.edit_modified(False)
            self._schedule_refresh_view()

    def _schedule_refresh_view(self):
        if self._refresh_after is not None:
            try:
                self.root.after_cancel(self._refresh_after)
            except Exception:
                pass
        self._refresh_after = self.root.after(30, self._do_refresh_view)

    def _do_refresh_view(self):
        self._refresh_after = None
        self._refresh_view()

    # ---- Универсальный обработчик Ctrl+... ----
    def _on_key_press(self, event):
        if not (event.state & 0x4):   # Ctrl не зажат
            return None
        shift = bool(event.state & 0x1)
        kc = event.keycode

        if kc == self.VK_V and not shift:
            return self._on_paste(event)
        if kc == self.VK_C and not shift:
            return self._on_copy(event)
        if kc == self.VK_X and not shift:
            return self._on_cut(event)
        if kc == self.VK_A:
            return self._on_select_all(event)
        if kc == self.VK_Z:
            if shift:
                self.text.edit_redo()
            else:
                self.text.edit_undo()
            return "break"
        if kc == self.VK_Y:
            self.text.edit_redo()
            return "break"
        if shift and kc in (self.VK_BACKSLASH, self.VK_SLASH):
            return self._toggle_comment(event)
        return None

    def _on_paste(self, event=None):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        self.text.insert("insert", text)
        self.text.see("insert")
        return "break"

    def _on_copy(self, event=None):
        try:
            text = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        return "break"

    def _on_cut(self, event=None):
        try:
            text = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.text.delete("sel.first", "sel.last")
        return "break"

    def _on_select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        self.text.see("insert")
        return "break"

    def _on_return_key(self, event=None):
        try:
            insert_line_1based = int(self.text.index("insert").split(".")[0])
        except (tk.TclError, ValueError):
            return None

        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")
        total = len(lines)

        for start, end in self.test_ranges:
            if start + 1 != insert_line_1based:
                continue
            header_text = lines[start] if start < total else ""
            if header_text not in self.folded_headers:
                continue

            if end < total:
                target = f"{end + 1}.0"
                self.text.insert(target, "\n")
                self.text.mark_set("insert", target)
            else:
                self.text.insert("end-1c", "\n")
                self.text.mark_set("insert", "end-1c")
            self.text.see("insert")
            return "break"

        return None

    def _toggle_comment(self, event=None):
        try:
            sel_start = self.text.index("sel.first")
            sel_end   = self.text.index("sel.last")
        except tk.TclError:
            sel_start = self.text.index("insert linestart")
            sel_end   = self.text.index("insert lineend")

        start_line = int(sel_start.split(".")[0])
        end_line   = int(sel_end.split(".")[0])
        end_col    = int(sel_end.split(".")[1])
        if end_col == 0 and end_line > start_line:
            end_line -= 1

        lines = [self.text.get(f"{i}.0", f"{i}.end")
                 for i in range(start_line, end_line + 1)]

        need_comment = any(not l.startswith("/") for l in lines)

        self.text.edit_separator()
        for i, line in zip(range(start_line, end_line + 1), lines):
            if need_comment:
                if not line.startswith("/"):
                    self.text.insert(f"{i}.0", "/ ")
            else:
                if line.startswith("/ "):
                    self.text.delete(f"{i}.0", f"{i}.2")
                elif line.startswith("/"):
                    self.text.delete(f"{i}.0", f"{i}.1")
        self.text.edit_separator()

        self._refresh_view()
        return "break"

    def _set_text(self, content):
        self._suppress_modified = True
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._suppress_modified = False
        self._dirty = False
        self.mod_label.config(text="")
        self.folded_headers.clear()
        self._show_results([])     # сброс панели результатов
        self._refresh_view()

    def _get_text(self):
        return self.text.get("1.0", tk.END).rstrip("\n") + "\n"

    # ---------- Подсветка / сворачивание ----------
    def _refresh_view(self):
        self._apply_syntax_highlighting()
        self._compute_test_ranges()
        self._apply_folding()
        self._schedule_gutter_redraw()

    def _apply_syntax_highlighting(self):
        self.text.tag_remove("test_header", "1.0", tk.END)
        self.text.tag_remove("test_comment", "1.0", tk.END)
        self.text.tag_remove("test_expected", "1.0", tk.END)

        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")

        # Базовые теги
        for i, line in enumerate(lines, start=1):
            if line.startswith("//"):
                self.text.tag_add("test_header", f"{i}.0", f"{i}.end")
            elif line.startswith("/"):
                self.text.tag_add("test_comment", f"{i}.0", f"{i}.end")

        # Находим границы тестов (по // заголовкам)
        test_starts = [i for i, l in enumerate(lines) if l.startswith("//")]

        # Для каждого теста ищем ПОСЛЕДНИЙ блок { ... }
        for t_idx, start in enumerate(test_starts):
            end = test_starts[t_idx + 1] if t_idx + 1 < len(test_starts) else len(lines)

            open_idx = -1
            for i in range(start, end):
                if lines[i].strip() == "{":
                    open_idx = i

            if open_idx == -1:
                continue

            close_idx = -1
            for i in range(open_idx + 1, end):
                if lines[i].strip() == "}":
                    close_idx = i
                    break

            if close_idx == -1:
                continue

            # Открывающий маркер
            self.text.tag_add("test_expected",
                              f"{open_idx + 1}.0", f"{open_idx + 1}.end")
            # Содержимое блока
            for i in range(open_idx + 1, close_idx):
                self.text.tag_add("test_expected",
                                  f"{i + 1}.0", f"{i + 1}.end")
            # Закрывающий маркер
            self.text.tag_add("test_expected",
                              f"{close_idx + 1}.0", f"{close_idx + 1}.end")

    def _compute_test_ranges(self):
        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")
        ranges = []
        current_start = None
        for i, line in enumerate(lines):
            if line.startswith("//"):
                if current_start is not None:
                    ranges.append((current_start, i))
                current_start = i
        if current_start is not None:
            ranges.append((current_start, len(lines)))
        self.test_ranges = ranges

    def _apply_folding(self):
        self.text.tag_remove("folded", "1.0", tk.END)

        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")

        existing_headers = {l for l in lines if l.startswith("//")}
        self.folded_headers &= existing_headers

        for start, end in self.test_ranges:
            header_text = lines[start] if start < len(lines) else ""
            if header_text not in self.folded_headers:
                continue
            if end <= start + 1:
                continue
            from_idx = f"{start + 2}.0"
            to_idx = f"{end + 1}.0" if end < len(lines) else "end"
            try:
                self.text.tag_add("folded", from_idx, to_idx)
            except tk.TclError:
                pass

    # ---------- Gutter ----------
    def _schedule_gutter_redraw(self, delay=8):
        if self._gutter_after is not None:
            try:
                self.root.after_cancel(self._gutter_after)
            except Exception:
                pass
        self._gutter_after = self.root.after(delay, self._redraw_gutter)

    def _on_text_configure(self, event=None):
        # Ресайз — перерисовываем gutter без задержки
        self._schedule_gutter_redraw(delay=0)

    def _redraw_gutter(self):
        self._gutter_after = None
        g = self.gutter
        g.delete("all")

        try:
            width = g.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            width = 60

        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")

        gutter_font_size = max(MIN_FONT_SIZE - 1, self.font_size - 1)

        for idx, (start, end) in enumerate(self.test_ranges):
            line_num = start + 1
            try:
                info = self.text.dlineinfo(f"{line_num}.0")
            except tk.TclError:
                continue
            if info is None:
                continue

            x, y, w, h, baseline = info
            header_text = lines[start] if start < len(lines) else ""
            is_folded = header_text in self.folded_headers
            can_fold = (end > start + 1)

            if can_fold:
                icon = "▶" if is_folded else "▼"
                label = f"{icon} {idx + 1}"
            else:
                label = f"   {idx + 1}"

            g.create_text(
                width - 6, y + h // 2,
                anchor="e", text=label,
                fill=COLOR_HEADER,
                font=("Consolas", gutter_font_size, "bold"),
                tags=(f"test_{idx}",),
            )

    def _on_gutter_click(self, event):
        for idx, (start, end) in enumerate(self.test_ranges):
            line_num = start + 1
            try:
                info = self.text.dlineinfo(f"{line_num}.0")
            except tk.TclError:
                continue
            if info is None:
                continue
            x, y, w, h, baseline = info
            if y <= event.y <= y + h:
                self._toggle_fold(idx)
                return

    def _toggle_fold(self, idx):
        if idx < 0 or idx >= len(self.test_ranges):
            return
        start, end = self.test_ranges[idx]
        if end <= start + 1:
            return

        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n")
        header_text = lines[start]

        if header_text in self.folded_headers:
            self.folded_headers.discard(header_text)
        else:
            self.folded_headers.add(header_text)

        self._apply_folding()
        self._schedule_gutter_redraw()

    # ---------- Панель результатов ----------
    def _clear_hover(self):
        if self._hover_test is not None:
            s, e, _ = self._hover_test
            self.results_text.tag_remove("hover", f"{s}.0", f"{e + 1}.0")
            self._hover_test = None
        self.results_text.config(cursor="arrow")

    def _show_results(self, results):
        self._clear_hover()
        self.results_test_lines = []

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)

        if not results:
            self.results_text.insert(
                tk.END,
                "Нет результатов.\n\nЗапустите тесты (F5) — "
                "здесь появится отчёт по каждому тесту.",
                "details"
            )
            self.results_summary.config(text="", fg=FG_DIM)
            self.results_text.configure(state="disabled")
            return

        passed = sum(1 for r in results if r['ok'])
        total = len(results)
        self.results_summary.config(
            text=f"Пройдено: {passed} / {total}",
            fg=(COLOR_PASS if passed == total else "#d19a3a"),
        )

        # --- Считаем строки ВРУЧНУЮ: никаких index("end-1c") ---
        current_line = 1

        for res in results:
            start_line = current_line

            mark = "✓ " if res['ok'] else "✗ "
            tag = "pass" if res['ok'] else "fail"

            # Строка заголовка теста
            self.results_text.insert(tk.END, mark, tag)
            self.results_text.insert(
                tk.END, f"Тест {res['num']}: {res['name']}\n", "test_name"
            )
            current_line += 1

            if not res['ok']:
                # Ожидалось
                self.results_text.insert(tk.END, "   Ожидалось:\n", "details")
                current_line += 1

                if res['expected']:
                    body = self._indent_result(res['expected'])
                else:
                    body = "      (пусто)\n"
                self.results_text.insert(tk.END, body, "details")
                current_line += body.count("\n")

                # Получено — показываем ВСЕГДА при провале, даже если пусто
                self.results_text.insert(tk.END, "   Получено:\n", "details")
                current_line += 1

                if res['real']:
                    body = self._indent_result(res['real'])
                else:
                    body = "      (пусто)\n"
                self.results_text.insert(tk.END, body, "details")
                current_line += body.count("\n")

            # Пустая строка-разделитель
            self.results_text.insert(tk.END, "\n")
            end_line = current_line - 1
            current_line += 1

            self.results_test_lines.append((start_line, end_line, res['num']))

        self.results_text.configure(state="disabled")

    @staticmethod
    def _indent_result(text):
        lines = text.rstrip("\n").split("\n")
        return "\n".join("      " + line for line in lines) + "\n"

    def _show_results_error(self, message):
        self._clear_hover()
        self.results_test_lines = []
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, f"⚠ {message}", "fail")
        self.results_text.configure(state="disabled")
        self.results_summary.config(text="", fg=FG_DIM)

    def _on_results_click(self, event):
        line_int = int(self.results_text.index(f"@{event.x},{event.y}").split(".")[0])
        target_num = None
        for start, end, num in self.results_test_lines:
            if start <= line_int <= end:
                target_num = num
                break
        if target_num is None:
            return "break"

        idx = target_num - 1
        if 0 <= idx < len(self.test_ranges):
            editor_line = self.test_ranges[idx][0] + 1
            self.text.mark_set("insert", f"{editor_line}.0")
            self.text.see(f"{editor_line}.0")
            self.text.focus_set()
            self._flash_status(f"Переход к тесту {target_num}")
        return "break"

    def _on_results_motion(self, event):
        line_int = int(self.results_text.index(f"@{event.x},{event.y}").split(".")[0])
        target = None
        for start, end, num in self.results_test_lines:
            if start <= line_int <= end:
                target = (start, end, num)
                break

        if target == self._hover_test:
            return

        if self._hover_test is not None:
            s, e, _ = self._hover_test
            self.results_text.tag_remove("hover", f"{s}.0", f"{e + 1}.0")

        self._hover_test = target
        if target is not None:
            s, e, _ = target
            self.results_text.tag_add("hover", f"{s}.0", f"{e + 1}.0")
            self.results_text.config(cursor="hand2")
        else:
            self.results_text.config(cursor="arrow")

    # ---------- Файловые операции ----------
    def new_file(self):
        if not self._confirm_discard():
            return
        self._set_text("")
        self.current_file = None
        self._update_file_label()
        self._update_title()
        self._flash_status("Создан новый файл")

    def open_file(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Открыть файл с тестами",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._set_text(f.read())
            self.current_file = path
            self._update_file_label()
            self._update_title()
            self._persist_config()
            self._flash_status(f"Открыт: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self._get_text())
            self._dirty = False
            self.mod_label.config(text="")
            self._update_title()
            self._flash_status(f"Сохранено: {self.current_file}")
            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")
            return False

    def save_file_as(self):
        initial = os.path.basename(self.current_file) if self.current_file else "all_tests.txt"
        path = filedialog.asksaveasfilename(
            title="Сохранить как",
            initialfile=initial,
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if not path:
            return False
        self.current_file = path
        ok = self.save_file()
        if ok:
            self._update_file_label()
            self._persist_config()
        return ok

    def rename_file(self):
        if not self.current_file:
            messagebox.showinfo("Переименование", "Сначала сохраните файл.")
            return
        new_name = dark_askstring(
            self.root, "Переименовать файл",
            "Новое имя файла:",
            initialvalue=os.path.basename(self.current_file)
        )
        if not new_name:
            return
        if self._dirty:
            if not self.save_file():
                return
        new_path = os.path.join(os.path.dirname(self.current_file), new_name)
        try:
            if os.path.abspath(new_path) != os.path.abspath(self.current_file):
                os.rename(self.current_file, new_path)
            self.current_file = new_path
            self._update_file_label()
            self._update_title()
            self._flash_status(f"Переименовано в: {new_name}")
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось переименовать:\n{e}")

    def _update_file_label(self):
        if self.current_file:
            self.file_label.config(text=self.current_file, fg=FG)
        else:
            self.file_label.config(text="Файл не выбран", fg=FG_DIM)

    def _update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else "Без имени"
        star = " *" if self._dirty else ""
        self.root.title(f"{name}{star} — {APP_NAME} v{APP_VERSION}")

    # ---------- Запуск ----------
    def run_tester(self):
        if not self.current_file:
            messagebox.showwarning("Внимание",
                                   "Сначала сохраните файл с тестами (Сохранить как…).")
            return
        if self._dirty:
            if not self.save_file():
                return

        debug_path = self._ask_debug_path()
        if not debug_path:
            return

        if not os.path.isdir(debug_path):
            messagebox.showerror("Ошибка", f"Папка не найдена:\n{debug_path}")
            return

        self.status.config(text="Выполняется прогон тестов…")
        self.root.update_idletasks()

        try:
            tester.run_tester(self.current_file, debug_path)
            self.status.config(text="Готово. Смотрите панель результатов справа.")
        except (ValueError, FileNotFoundError) as e:
            self.status.config(text="Ошибка при запуске")
            messagebox.showerror("Ошибка", str(e))
            return
        except Exception as e:
            self.status.config(text="Ошибка при запуске")
            messagebox.showerror("Ошибка", f"Не удалось выполнить прогон:\n{e}")
            return

        # Автоматический анализ результатов
        try:
            results_path = os.path.join(os.path.normpath(debug_path), 'results.txt')
            analysis = cleaner.analyze(results_path, self.current_file)
            self._show_results(analysis)
        except FileNotFoundError as e:
            self._show_results_error(str(e))
        except Exception as e:
            self._show_results_error(f"Не удалось проанализировать результаты: {e}")

    def _ask_debug_path(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Папка с .exe файлом")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        w, h = 580, 210
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(dialog, text="Укажите папку, в которой лежит .exe файл вашей программы:",
                 bg=BG, fg=FG, font=("Segoe UI", 11), wraplength=w - 30,
                 justify="left").pack(anchor="w", padx=18, pady=(18, 6))

        tk.Label(dialog, text="(обычно это папка Debug — но подойдёт любая, где есть .exe)",
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 8))

        entry = tk.Entry(dialog, bg=BG_INPUT, fg=FG, insertbackground=FG,
                         bd=0, font=("Consolas", 10),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.pack(fill=tk.X, padx=18, ipady=6)

        # Подставляем последнюю использованную папку из конфига
        last_folder = self.config.get("last_exe_folder", "")
        if last_folder and os.path.isdir(last_folder):
            entry.insert(0, last_folder)
            entry.select_range(0, tk.END)

        entry.focus_set()
        enable_entry_clipboard(entry, dialog)

        result = {"path": None}

        def browse():
            initial = entry.get().strip() or None
            p = filedialog.askdirectory(
                title="Выберите папку с .exe файлом",
                initialdir=initial if initial and os.path.isdir(initial) else None,
            )
            if p:
                entry.delete(0, tk.END)
                entry.insert(0, p)

        def on_ok(_=None):
            result["path"] = entry.get().strip()
            if result["path"]:
                self.config["last_exe_folder"] = result["path"]
                save_config(self.config)
            dialog.destroy()

        def on_cancel(_=None):
            dialog.destroy()

        btns = tk.Frame(dialog, bg=BG)
        btns.pack(pady=18, fill=tk.X, padx=18)
        ttk.Button(btns, text="Обзор…", command=browse).pack(side=tk.LEFT)
        ttk.Button(btns, text="Отмена", command=on_cancel).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text="▶ Запустить", command=on_ok,
                   style="Accent.TButton").pack(side=tk.RIGHT)

        entry.bind("<Return>", on_ok)
        dialog.bind("<Escape>", on_cancel)

        self.root.wait_window(dialog)
        return result["path"]

    # ---------- Закрытие ----------
    def _confirm_discard(self):
        if not self._dirty:
            return True
        ans = messagebox.askyesnocancel(
            "Несохранённые изменения",
            "Сохранить текущий файл перед продолжением?"
        )
        if ans is None:
            return False
        if ans:
            return bool(self.save_file())
        return True

    def _on_close(self):
        if self._confirm_discard():
            self._persist_config()
            self.root.destroy()


# ==================== Точка входа ====================
def resource_path(relative_path):
    """Возвращает путь к ресурсу — работает и в .exe, и в исходниках."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    res = enable_hidpi()
    print(f"[HiDPI] {res}")

    root = tk.Tk()
    apply_tk_scaling(root)

    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    tk_scale = root.tk.call("tk", "scaling")
    print(f"[DPI] system={dpi} ({(dpi/96)*100:.0f}%), tk_scaling={tk_scale}")

    try:
        root.iconbitmap(resource_path("app.ico"))
    except Exception as e:
        print("Иконка не загружена:", e)
    app = TesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()