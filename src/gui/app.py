"""Professional multi-page Tkinter GUI for Yellow Pages Scraper."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import tkinter as tk
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from config.settings import APP_VERSION, CSV_FILENAME, DATA_DIR, JSON_FILENAME, LOGS_DIR
from src.gui.theme import COLORS, FONT_LOG, FONT_SECTION, FONT_SMALL, FONT_STAT, FONT_UI, FONT_UI_BOLD, setup_styles
from src.scraper.orchestrator import ScraperOrchestrator
from src.storage.app_store import AppStore, export_file, import_csv_records, import_json_records

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("scraper", "◎  Scraper"),
    ("history", "◷  History"),
    ("settings", "⚙  Settings"),
    ("export", "⇪  Export / Import"),
    ("help", "❔  Help"),
]


class YellowPagesGUI:
    """Main application window with sidebar navigation."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Yellow Pages Scraper")
        self.root.geometry("1180x820")
        self.root.minsize(1020, 720)
        self.root.configure(bg=COLORS["bg"])

        self.store = AppStore()
        self.event_queue: queue.Queue = queue.Queue()
        self.scraper_thread: threading.Thread | None = None
        self.orchestrator: ScraperOrchestrator | None = None
        self.current_page = "scraper"
        self.nav_buttons: dict[str, ttk.Button] = {}
        self.pages: dict[str, tk.Frame] = {}
        self.session_id: str | None = None
        self._run_started_at: float | None = None
        self._last_stats: dict = {}
        self.auto_scroll_var = tk.BooleanVar(value=bool(self.store.settings.get("auto_scroll_logs", True)))

        self._setup_vars_from_settings()
        setup_styles(ttk.Style())
        self._build_shell()
        self._show_page("scraper")
        self._poll_events()
        self._tick_elapsed()
        self._append_log("INFO", "Application ready")

    def _setup_vars_from_settings(self) -> None:
        s = self.store.settings
        self.url_var = tk.StringVar(value=str(s.get("start_url", "")))
        self.output_var = tk.StringVar(value=str(s.get("output_dir", DATA_DIR)))
        self.headless_var = tk.BooleanVar(value=bool(s.get("headless", False)))
        self.download_images_var = tk.BooleanVar(value=bool(s.get("download_images", True)))
        self.max_pages_var = tk.StringVar(value=str(s.get("max_pages", 0)))
        self.delay_var = tk.StringVar(value=str(s.get("request_delay_seconds", 1.5)))
        self.timeout_var = tk.StringVar(value=str(s.get("page_load_timeout", 30)))
        self.wait_var = tk.StringVar(value=str(s.get("implicit_wait", 5)))
        self.gallery_scrolls_var = tk.StringVar(value=str(s.get("max_gallery_scrolls", 20)))
        self.status_title_var = tk.StringVar(value="Ready to Scrape")
        self.status_sub_var = tk.StringVar(value="Undetected Chrome")
        self.elapsed_var = tk.StringVar(value="00:00:00")
        self.preset_var = tk.StringVar(value="Load Preset")

    def _build_shell(self) -> None:
        shell = tk.Frame(self.root, bg=COLORS["bg"])
        shell.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(shell, bg=COLORS["sidebar"], width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.pack(fill=tk.X, padx=18, pady=(22, 28))
        tk.Label(
            brand,
            text="🔍  Yellow Pages Scraper",
            bg=COLORS["sidebar"],
            fg=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        for key, label in NAV_ITEMS:
            btn = ttk.Button(
                sidebar,
                text=label,
                style="Sidebar.TButton",
                command=lambda k=key: self._show_page(k),
            )
            btn.pack(fill=tk.X, padx=10, pady=2)
            self.nav_buttons[key] = btn

        footer = tk.Frame(sidebar, bg=COLORS["sidebar"])
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=20)
        tk.Label(footer, text=f"v{APP_VERSION}", bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"], font=FONT_SMALL).pack(anchor="w")
        status_row = tk.Frame(footer, bg=COLORS["sidebar"])
        status_row.pack(anchor="w", pady=(6, 0))
        tk.Label(status_row, text="●", bg=COLORS["sidebar"], fg=COLORS["success"], font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(
            status_row,
            text=" Production Ready",
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_muted"],
            font=FONT_SMALL,
        ).pack(side=tk.LEFT)

        self.content = tk.Frame(shell, bg=COLORS["bg"])
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pages["scraper"] = self._build_scraper_page(self.content)
        self.pages["history"] = self._build_history_page(self.content)
        self.pages["settings"] = self._build_settings_page(self.content)
        self.pages["export"] = self._build_export_page(self.content)
        self.pages["help"] = self._build_help_page(self.content)

        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_page(self, key: str) -> None:
        self.current_page = key
        for name, page in self.pages.items():
            if name == key:
                page.lift()
            style = "SidebarActive.TButton" if name == key else "Sidebar.TButton"
            if name in self.nav_buttons:
                self.nav_buttons[name].configure(style=style)
        if key == "history":
            self._refresh_history()
        elif key == "export":
            self._refresh_export_summary()

    # ------------------------------------------------------------------ cards
    def _card(self, parent: tk.Misc, title: str, subtitle: str = "", icon: str = "") -> tuple[tk.Frame, tk.Frame]:
        outer = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
        header = tk.Frame(outer, bg=COLORS["surface"])
        header.pack(fill=tk.X, padx=18, pady=(16, 8))
        left = tk.Frame(header, bg=COLORS["surface"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        title_row = tk.Frame(left, bg=COLORS["surface"])
        title_row.pack(anchor="w")
        if icon:
            tk.Label(title_row, text=icon, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_SECTION).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(title_row, text=title, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_SECTION).pack(side=tk.LEFT)
        if subtitle:
            tk.Label(left, text=subtitle, bg=COLORS["surface"], fg=COLORS["text_muted"], font=FONT_SMALL).pack(anchor="w", pady=(4, 0))
        body = tk.Frame(outer, bg=COLORS["surface"])
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 16))
        return outer, body

    def _labeled_entry(self, parent: tk.Misc, label: str, variable: tk.Variable, browse: bool = False) -> ttk.Entry:
        wrap = tk.Frame(parent, bg=COLORS["surface"])
        wrap.pack(fill=tk.X, pady=(0, 12))
        tk.Label(wrap, text=label, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_UI_BOLD).pack(anchor="w")
        row = tk.Frame(wrap, bg=COLORS["surface"])
        row.pack(fill=tk.X, pady=(6, 0))
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if browse:
            ttk.Button(row, text="Browse", style="Secondary.TButton", command=self._browse_output).pack(side=tk.LEFT, padx=(8, 0))
        return entry

    # --------------------------------------------------------------- scraper
    def _build_scraper_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=COLORS["bg"])
        canvas = tk.Canvas(page, bg=COLORS["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["bg"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        canvas.bind("<Configure>", _on_configure)

        header = tk.Frame(inner, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        left = tk.Frame(header, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(left, text="Yellow Pages Scraper", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(
            left,
            text="Extract business listings from Yellow Pages with resume support, CSV/JSON export and undetected Chrome.",
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
            font=FONT_UI,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        badge = tk.Frame(header, bg=COLORS["success_bg"], highlightbackground="#b7ebc9", highlightthickness=1, padx=12, pady=8)
        badge.pack(side=tk.RIGHT)
        tk.Label(badge, textvariable=self.status_title_var, bg=COLORS["success_bg"], fg=COLORS["success"], font=FONT_UI_BOLD).pack(anchor="w")
        status_dot = tk.Frame(badge, bg=COLORS["success_bg"])
        status_dot.pack(anchor="w")
        tk.Label(status_dot, text="●", bg=COLORS["success_bg"], fg=COLORS["success"], font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(status_dot, textvariable=self.status_sub_var, bg=COLORS["success_bg"], fg=COLORS["text_muted"], font=FONT_SMALL).pack(side=tk.LEFT)

        # Configuration card
        config_card, config_body = self._card(
            inner,
            "Configuration",
            "Set your scraping parameters and output preferences.",
            icon="⚙",
        )
        config_card.pack(fill=tk.X, padx=24, pady=8)

        top_actions = tk.Frame(config_card, bg=COLORS["surface"])
        # Rebuild header action into card header area by packing into config_card before body... already packed.
        # Add Load Preset next to title via overlay frame on config_card
        preset_bar = tk.Frame(config_card, bg=COLORS["surface"])
        preset_bar.place(relx=1.0, x=-18, y=16, anchor="ne")
        self.preset_combo = ttk.Combobox(preset_bar, textvariable=self.preset_var, state="readonly", width=18)
        self.preset_combo.pack(side=tk.LEFT)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
        ttk.Button(preset_bar, text="Load", style="Secondary.TButton", command=self._load_selected_preset).pack(side=tk.LEFT, padx=(6, 0))
        self._refresh_presets()

        self._labeled_entry(config_body, "Start URL", self.url_var)
        self._labeled_entry(config_body, "Output Folder", self.output_var, browse=True)

        options = tk.Frame(config_body, bg=COLORS["surface"])
        options.pack(fill=tk.X, pady=(4, 12))

        def option_block(parent, text, sub, var):
            box = tk.Frame(parent, bg=COLORS["surface2"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
            box.pack(side=tk.LEFT, padx=(0, 10))
            ttk.Checkbutton(box, text=text, variable=var).pack(anchor="w")
            tk.Label(box, text=sub, bg=COLORS["surface2"], fg=COLORS["text_muted"], font=FONT_SMALL).pack(anchor="w")

        option_block(options, "Headless mode", "Run browser in background.", self.headless_var)
        option_block(options, "Store gallery images locally", "Download and save business images.", self.download_images_var)

        pages_box = tk.Frame(options, bg=COLORS["surface2"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        pages_box.pack(side=tk.LEFT)
        tk.Label(pages_box, text="Max pages (0 = all)", bg=COLORS["surface2"], fg=COLORS["text"], font=FONT_UI_BOLD).pack(anchor="w")
        ttk.Entry(pages_box, textvariable=self.max_pages_var, width=10).pack(anchor="w", pady=(6, 0))

        controls = tk.Frame(config_body, bg=COLORS["surface"])
        controls.pack(fill=tk.X, pady=(4, 0))
        self.start_btn = ttk.Button(controls, text="▶  Start Scraping", style="Accent.TButton", command=self._start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.pause_btn = ttk.Button(controls, text="⏸  Pause", style="Secondary.TButton", command=self._pause_scraping, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.resume_btn = ttk.Button(controls, text="⏵  Resume", style="Secondary.TButton", command=self._resume_scraping, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(controls, text="■  Stop", style="Danger.TButton", command=self._stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="💾  Save Configuration", style="Ghost.TButton", command=self._save_configuration).pack(side=tk.RIGHT)

        # Progress card
        progress_card, progress_body = self._card(inner, "Progress", "Real-time scraping progress and statistics.", icon="▦")
        progress_card.pack(fill=tk.X, padx=24, pady=8)
        elapsed_wrap = tk.Frame(progress_card, bg=COLORS["surface"])
        elapsed_wrap.place(relx=1.0, x=-18, y=16, anchor="ne")
        tk.Label(elapsed_wrap, text="Elapsed Time", bg=COLORS["surface"], fg=COLORS["text_muted"], font=FONT_SMALL).pack(anchor="e")
        tk.Label(elapsed_wrap, textvariable=self.elapsed_var, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_UI_BOLD).pack(anchor="e")

        stats = tk.Frame(progress_body, bg=COLORS["surface"])
        stats.pack(fill=tk.X)
        self.stat_labels: dict[str, tk.Label] = {}
        for key, label, color in [
            ("scraped", "Scraped", COLORS["success"]),
            ("pending", "Pending", COLORS["info"]),
            ("failed", "Failed", COLORS["warning"]),
            ("page", "List Page", COLORS["purple"]),
            ("total", "Total Results", COLORS["text_muted"]),
        ]:
            card = tk.Frame(stats, bg=COLORS["surface2"], highlightbackground=COLORS["border"], highlightthickness=1, padx=14, pady=12)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            tk.Label(card, text=label, bg=COLORS["surface2"], fg=COLORS["text_muted"], font=FONT_SMALL).pack(anchor="w")
            val = tk.Label(card, text="0", bg=COLORS["surface2"], fg=color, font=FONT_STAT)
            val.pack(anchor="w", pady=(4, 0))
            self.stat_labels[key] = val

        self.progress_bar = ttk.Progressbar(progress_body, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(14, 0))

        # Activity log card
        log_card, log_body = self._card(inner, "Activity Log", "Live logs and system events.", icon="☰")
        log_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 24))
        log_tools = tk.Frame(log_card, bg=COLORS["surface"])
        log_tools.place(relx=1.0, x=-18, y=14, anchor="ne")
        ttk.Button(log_tools, text="Clear Logs", style="Secondary.TButton", command=self._clear_logs).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(log_tools, text="Auto-scroll", variable=self.auto_scroll_var).pack(side=tk.LEFT)

        log_frame = tk.Frame(log_body, bg=COLORS["log_bg"])
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(
            log_frame,
            height=14,
            bg=COLORS["log_bg"],
            fg=COLORS["log_fg"],
            insertbackground=COLORS["log_fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=FONT_LOG,
            padx=12,
            pady=10,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.tag_configure("INFO", foreground=COLORS["log_info"])
        self.log_text.tag_configure("SUCCESS", foreground=COLORS["log_success"])
        self.log_text.tag_configure("ERROR", foreground=COLORS["log_error"])
        self.log_text.tag_configure("WARN", foreground=COLORS["log_warn"])
        self.log_text.configure(state=tk.DISABLED)

        return page

    # --------------------------------------------------------------- history
    def _build_history_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=COLORS["bg"])
        header = tk.Frame(page, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        tk.Label(header, text="History", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Refresh", style="Secondary.TButton", command=self._refresh_history).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(header, text="Clear History", style="Danger.TButton", command=self._clear_history).pack(side=tk.RIGHT)

        card, body = self._card(page, "Scrape Sessions", "Past runs with status, counts, and quick restore.", icon="◷")
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 24))

        cols = ("started", "status", "url", "scraped", "failed", "output")
        self.history_tree = ttk.Treeview(body, columns=cols, show="headings", height=18)
        headings = {
            "started": ("Started", 150),
            "status": ("Status", 90),
            "url": ("Start URL", 320),
            "scraped": ("Scraped", 70),
            "failed": ("Failed", 70),
            "output": ("Output", 220),
        }
        for key, (title, width) in headings.items():
            self.history_tree.heading(key, text=title)
            self.history_tree.column(key, width=width, anchor="w")
        self.history_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.pack(fill=tk.X, padx=24, pady=(0, 20))
        ttk.Button(actions, text="Load Into Scraper", style="Accent.TButton", command=self._load_history_into_scraper).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Open Output Folder", style="Secondary.TButton", command=self._open_history_output).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Delete Selected", style="Ghost.TButton", command=self._delete_history_selected).pack(side=tk.LEFT)
        return page

    # -------------------------------------------------------------- settings
    def _build_settings_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=COLORS["bg"])
        tk.Label(page, text="Settings", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=24, pady=(20, 8))

        card, body = self._card(page, "Defaults & Performance", "Applied to new scrapes and saved as app defaults.", icon="⚙")
        card.pack(fill=tk.X, padx=24, pady=8)

        grid = tk.Frame(body, bg=COLORS["surface"])
        grid.pack(fill=tk.X)
        fields = [
            ("Default Start URL", self.url_var, 0, 0, 2),
            ("Default Output Folder", self.output_var, 1, 0, 2),
            ("Request delay (seconds)", self.delay_var, 2, 0, 1),
            ("Page load timeout (seconds)", self.timeout_var, 2, 1, 1),
            ("Implicit wait (seconds)", self.wait_var, 3, 0, 1),
            ("Max gallery scrolls", self.gallery_scrolls_var, 3, 1, 1),
        ]
        for label, var, row, col, span in fields:
            cell = tk.Frame(grid, bg=COLORS["surface"])
            cell.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0, 12), pady=6)
            tk.Label(cell, text=label, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_UI_BOLD).pack(anchor="w")
            ttk.Entry(cell, textvariable=var).pack(fill=tk.X, pady=(4, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        opts = tk.Frame(body, bg=COLORS["surface"])
        opts.pack(fill=tk.X, pady=(10, 0))
        ttk.Checkbutton(opts, text="Headless by default", variable=self.headless_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts, text="Store gallery images by default", variable=self.download_images_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts, text="Auto-scroll activity log", variable=self.auto_scroll_var).pack(anchor="w", pady=2)

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.pack(fill=tk.X, padx=24, pady=16)
        ttk.Button(actions, text="Save Settings", style="Accent.TButton", command=self._save_settings_page).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Reset to Defaults", style="Secondary.TButton", command=self._reset_settings).pack(side=tk.LEFT)
        return page

    # -------------------------------------------------------- export/import
    def _build_export_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=COLORS["bg"])
        tk.Label(page, text="Export / Import", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(
            anchor="w", padx=24, pady=(20, 8)
        )

        summary, summary_body = self._card(page, "Current Output", "Files in the selected output folder.", icon="📁")
        summary.pack(fill=tk.X, padx=24, pady=8)
        self.export_summary_var = tk.StringVar(value="")
        tk.Label(summary_body, textvariable=self.export_summary_var, bg=COLORS["surface"], fg=COLORS["text"], justify="left", font=FONT_UI).pack(
            anchor="w"
        )

        export_card, export_body = self._card(page, "Export", "Copy or package scraped data.", icon="⇪")
        export_card.pack(fill=tk.X, padx=24, pady=8)
        row = tk.Frame(export_body, bg=COLORS["surface"])
        row.pack(fill=tk.X)
        ttk.Button(row, text="Export CSV…", style="Accent.TButton", command=self._export_csv).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Export JSON…", style="Secondary.TButton", command=self._export_json).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Export Images ZIP…", style="Secondary.TButton", command=self._export_images_zip).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Open Output Folder", style="Ghost.TButton", command=self._open_output_folder).pack(side=tk.LEFT)

        import_card, import_body = self._card(page, "Import", "Merge external CSV/JSON into the current output folder.", icon="⇩")
        import_card.pack(fill=tk.X, padx=24, pady=8)
        row2 = tk.Frame(import_body, bg=COLORS["surface"])
        row2.pack(fill=tk.X)
        ttk.Button(row2, text="Import CSV…", style="Accent.TButton", command=self._import_csv).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row2, text="Import JSON…", style="Secondary.TButton", command=self._import_json).pack(side=tk.LEFT)

        preset_card, preset_body = self._card(page, "Presets", "Save and reuse scraper configurations.", icon="★")
        preset_card.pack(fill=tk.X, padx=24, pady=(8, 24))
        prow = tk.Frame(preset_body, bg=COLORS["surface"])
        prow.pack(fill=tk.X)
        ttk.Button(prow, text="Save Current as Preset…", style="Accent.TButton", command=self._save_preset_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(prow, text="Delete Selected Preset", style="Danger.TButton", command=self._delete_selected_preset).pack(side=tk.LEFT)
        return page

    # ------------------------------------------------------------------ help
    def _build_help_page(self, parent: tk.Misc) -> tk.Frame:
        page = tk.Frame(parent, bg=COLORS["bg"])
        tk.Label(page, text="Help", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=24, pady=(20, 8))
        card, body = self._card(page, "How to use", "Quick guide for scraping, resume, and exports.", icon="❔")
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 24))
        help_text = (
            "1. Open Scraper, set a Yellow Pages category/search URL and output folder.\n"
            "2. Optionally enable headless mode and local gallery image storage.\n"
            "3. Click Start Scraping. Use Pause / Resume / Stop as needed.\n"
            "4. Progress is saved to progress.json so you can resume the same URL later.\n"
            "5. Results are written to businesses.csv and businesses.json.\n"
            "6. Images (when enabled) are stored under images/{listing_id}/ with relative paths in exports.\n"
            "7. Use History to reload a past run's configuration.\n"
            "8. Use Export / Import to copy data out or merge external CSV/JSON files.\n"
            "9. Settings controls defaults and timing used for new runs.\n\n"
            f"Version {APP_VERSION}  •  Requires Google Chrome  •  Python 3.10+"
        )
        tk.Label(body, text=help_text, bg=COLORS["surface"], fg=COLORS["text"], justify="left", font=FONT_UI, anchor="nw").pack(
            fill=tk.BOTH, expand=True, anchor="nw"
        )
        return page

    # ----------------------------------------------------------------- helpers
    def _current_config(self) -> dict:
        max_pages_raw = self.max_pages_var.get().strip()
        max_pages = int(max_pages_raw) if max_pages_raw.isdigit() else 0
        return {
            "start_url": self.url_var.get().strip(),
            "output_dir": self.output_var.get().strip(),
            "headless": bool(self.headless_var.get()),
            "download_images": bool(self.download_images_var.get()),
            "max_pages": max_pages,
            "request_delay_seconds": float(self.delay_var.get() or 1.5),
            "page_load_timeout": int(float(self.timeout_var.get() or 30)),
            "implicit_wait": int(float(self.wait_var.get() or 5)),
            "max_gallery_scrolls": int(float(self.gallery_scrolls_var.get() or 20)),
            "auto_scroll_logs": bool(self.auto_scroll_var.get()),
        }

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(DATA_DIR))
        if folder:
            self.output_var.set(folder)

    def _append_log(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {level:<7} {message}\n"
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line, level if level in ("INFO", "SUCCESS", "ERROR", "WARN") else "INFO")
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_logs(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_running_state(self, running: bool, paused: bool = False) -> None:
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.pause_btn.configure(state=tk.NORMAL if running and not paused else tk.DISABLED)
        self.resume_btn.configure(state=tk.NORMAL if running and paused else tk.DISABLED)
        if running and not paused:
            self.progress_bar.start(12)
            self.status_title_var.set("🌐  Scraping…")
            self.status_sub_var.set("Running")
        elif running and paused:
            self.progress_bar.stop()
            self.status_title_var.set("🌐  Paused")
            self.status_sub_var.set("Paused")
        else:
            self.progress_bar.stop()
            self.status_title_var.set("🌐  Ready to Scrape")
            self.status_sub_var.set("Undetected Chrome")
            self._run_started_at = None

    def _tick_elapsed(self) -> None:
        if self._run_started_at is not None:
            elapsed = int(time.time() - self._run_started_at)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.elapsed_var.set(f"{h:02d}:{m:02d}:{s:02d}")
        self.root.after(500, self._tick_elapsed)

    # ----------------------------------------------------------- scrape actions
    def _start_scraping(self) -> None:
        cfg = self._current_config()
        if not cfg["start_url"]:
            messagebox.showerror("Validation", "Please enter a start URL.")
            return
        output_dir = Path(cfg["output_dir"])
        max_pages = cfg["max_pages"] if cfg["max_pages"] > 0 else None

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.store.save_settings(cfg)
        self.session_id = self.store.start_session(cfg)
        self._run_started_at = time.time()
        self.elapsed_var.set("00:00:00")
        self._set_running_state(True)
        self._append_log("INFO", f"Starting scrape: {cfg['start_url']}")

        def status_cb(msg: str) -> None:
            self.event_queue.put(("status", msg))

        def progress_cb(data: dict) -> None:
            self.event_queue.put(("progress", data))

        self.orchestrator = ScraperOrchestrator(
            start_url=cfg["start_url"],
            output_dir=output_dir,
            headless=cfg["headless"],
            max_pages=max_pages,
            download_images=cfg["download_images"],
            request_delay=cfg["request_delay_seconds"],
            max_gallery_scrolls=cfg["max_gallery_scrolls"],
            on_status=status_cb,
            on_progress=progress_cb,
        )

        def run_scraper() -> None:
            try:
                self.orchestrator.run()
            except Exception as exc:
                logger.exception("Scraper crashed")
                self.event_queue.put(("error", str(exc)))
            finally:
                self.event_queue.put(("done", None))

        self.scraper_thread = threading.Thread(target=run_scraper, daemon=True)
        self.scraper_thread.start()

    def _pause_scraping(self) -> None:
        if self.orchestrator:
            self.orchestrator.pause()
            self._set_running_state(True, paused=True)
            self._append_log("WARN", "Paused")
            if self.session_id:
                self.store.update_session(self.session_id, status="paused")

    def _resume_scraping(self) -> None:
        if self.orchestrator:
            self.orchestrator.resume()
            self._set_running_state(True, paused=False)
            self._append_log("INFO", "Resumed")
            if self.session_id:
                self.store.update_session(self.session_id, status="running")

    def _stop_scraping(self) -> None:
        if self.orchestrator:
            self.orchestrator.stop()
            self._append_log("WARN", "Stopping...")

    def _update_stats(self, data: dict) -> None:
        self._last_stats = data
        self.stat_labels["scraped"].configure(text=str(data.get("scraped_count", 0)))
        self.stat_labels["pending"].configure(text=str(data.get("pending_count", 0)))
        self.stat_labels["failed"].configure(text=str(data.get("failed_count", 0)))
        page = data.get("current_list_page", 0)
        total_pages = data.get("total_list_pages") or "?"
        self.stat_labels["page"].configure(text=f"{page} / {total_pages}")
        total_results = data.get("total_results")
        self.stat_labels["total"].configure(text=str(total_results) if total_results else "-")
        if self.session_id:
            self.store.update_session(
                self.session_id,
                scraped_count=data.get("scraped_count", 0),
                pending_count=data.get("pending_count", 0),
                failed_count=data.get("failed_count", 0),
                total_results=data.get("total_results"),
            )

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()
                if event_type == "status":
                    msg = str(payload)
                    level = "SUCCESS" if msg.lower().startswith("saved:") or "completed" in msg.lower() else "INFO"
                    if "fail" in msg.lower():
                        level = "ERROR"
                    self._append_log(level, msg)
                elif event_type == "progress":
                    self._update_stats(payload)
                    if payload.get("message"):
                        msg = payload["message"]
                        level = "SUCCESS" if msg.lower().startswith("saved:") else "INFO"
                        self._append_log(level, msg)
                elif event_type == "error":
                    self._append_log("ERROR", str(payload))
                    messagebox.showerror("Scraper Error", str(payload))
                    if self.session_id:
                        self.store.finish_session(self.session_id, "failed", self._last_stats)
                elif event_type == "done":
                    self._set_running_state(False)
                    status = (self._last_stats or {}).get("status") or "completed"
                    if status == "stopped":
                        final = "stopped"
                    elif status == "paused":
                        final = "paused"
                    else:
                        final = "completed"
                    if self.session_id:
                        self.store.finish_session(self.session_id, final, self._last_stats)
                    self._append_log("INFO", "Session ended.")
                    self._refresh_history()
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)

    # ------------------------------------------------ presets / config save
    def _refresh_presets(self) -> None:
        names = [p.get("name", "") for p in self.store.presets]
        self.preset_combo["values"] = names or ["(no presets)"]
        if names and self.preset_var.get() not in names:
            self.preset_var.set("Load Preset")

    def _on_preset_selected(self, _event=None) -> None:
        pass

    def _load_selected_preset(self) -> None:
        name = self.preset_var.get()
        preset = self.store.get_preset(name)
        if not preset:
            messagebox.showinfo("Presets", "Select a saved preset first.")
            return
        cfg = preset.get("config", {})
        self.url_var.set(cfg.get("start_url", ""))
        self.output_var.set(cfg.get("output_dir", str(DATA_DIR)))
        self.headless_var.set(bool(cfg.get("headless", False)))
        self.download_images_var.set(bool(cfg.get("download_images", True)))
        self.max_pages_var.set(str(cfg.get("max_pages", 0)))
        self._append_log("INFO", f"Loaded preset: {name}")

    def _save_configuration(self) -> None:
        self.store.save_settings(self._current_config())
        name = simpledialog.askstring("Save Preset", "Preset name (optional). Leave blank to save defaults only:")
        if name:
            try:
                self.store.upsert_preset(name, self._current_config())
                self._refresh_presets()
                self.preset_var.set(name)
                self._append_log("SUCCESS", f"Saved preset: {name}")
            except ValueError as exc:
                messagebox.showerror("Preset", str(exc))
                return
        messagebox.showinfo("Saved", "Configuration saved.")

    def _save_preset_dialog(self) -> None:
        name = simpledialog.askstring("Save Preset", "Preset name:")
        if not name:
            return
        try:
            self.store.upsert_preset(name, self._current_config())
            self._refresh_presets()
            self.preset_var.set(name)
            messagebox.showinfo("Presets", f"Saved preset '{name}'.")
        except ValueError as exc:
            messagebox.showerror("Preset", str(exc))

    def _delete_selected_preset(self) -> None:
        name = self.preset_var.get()
        if not self.store.get_preset(name):
            messagebox.showinfo("Presets", "Select a preset to delete.")
            return
        if messagebox.askyesno("Delete Preset", f"Delete preset '{name}'?"):
            self.store.delete_preset(name)
            self._refresh_presets()
            self.preset_var.set("Load Preset")

    def _save_settings_page(self) -> None:
        self.store.save_settings(self._current_config())
        messagebox.showinfo("Settings", "Settings saved.")
        self._append_log("SUCCESS", "Settings saved")

    def _reset_settings(self) -> None:
        from src.storage.app_store import default_settings

        defaults = default_settings()
        self.store.save_settings(defaults)
        self.url_var.set(defaults["start_url"])
        self.output_var.set(defaults["output_dir"])
        self.headless_var.set(defaults["headless"])
        self.download_images_var.set(defaults["download_images"])
        self.max_pages_var.set(str(defaults["max_pages"]))
        self.delay_var.set(str(defaults["request_delay_seconds"]))
        self.timeout_var.set(str(defaults["page_load_timeout"]))
        self.wait_var.set(str(defaults["implicit_wait"]))
        self.gallery_scrolls_var.set(str(defaults["max_gallery_scrolls"]))
        self.auto_scroll_var.set(True)
        messagebox.showinfo("Settings", "Defaults restored.")

    # ------------------------------------------------------------- history ops
    def _refresh_history(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self.store.load()
        for session in self.store.history:
            started = session.get("started_at", "")
            if started:
                started = started.replace("T", " ")[:19]
            self.history_tree.insert(
                "",
                tk.END,
                iid=session.get("id"),
                values=(
                    started,
                    session.get("status", ""),
                    session.get("start_url", ""),
                    session.get("scraped_count", 0),
                    session.get("failed_count", 0),
                    session.get("output_dir", ""),
                ),
            )

    def _selected_history(self) -> dict | None:
        selected = self.history_tree.selection()
        if not selected:
            return None
        sid = selected[0]
        for session in self.store.history:
            if session.get("id") == sid:
                return session
        return None

    def _load_history_into_scraper(self) -> None:
        session = self._selected_history()
        if not session:
            messagebox.showinfo("History", "Select a session first.")
            return
        self.url_var.set(session.get("start_url", ""))
        self.output_var.set(session.get("output_dir", str(DATA_DIR)))
        self.headless_var.set(bool(session.get("headless", False)))
        self.download_images_var.set(bool(session.get("download_images", True)))
        self.max_pages_var.set(str(session.get("max_pages", 0)))
        self._show_page("scraper")
        self._append_log("INFO", f"Loaded history session {session.get('id')}")

    def _open_history_output(self) -> None:
        session = self._selected_history()
        if not session:
            messagebox.showinfo("History", "Select a session first.")
            return
        path = Path(session.get("output_dir") or "")
        if not path.exists():
            messagebox.showerror("History", f"Folder not found:\n{path}")
            return
        self._open_path(path)

    def _delete_history_selected(self) -> None:
        session = self._selected_history()
        if not session:
            messagebox.showinfo("History", "Select a session first.")
            return
        if messagebox.askyesno("Delete", "Delete this history entry?"):
            self.store.delete_session(session["id"])
            self._refresh_history()

    def _clear_history(self) -> None:
        if messagebox.askyesno("Clear History", "Delete all history entries?"):
            self.store.clear_history()
            self._refresh_history()

    # -------------------------------------------------------- export / import
    def _output_dir(self) -> Path:
        return Path(self.output_var.get().strip() or DATA_DIR)

    def _refresh_export_summary(self) -> None:
        out = self._output_dir()
        csv_path = out / CSV_FILENAME
        json_path = out / JSON_FILENAME
        images = out / "images"
        lines = [
            f"Output folder: {out}",
            f"CSV: {'yes' if csv_path.exists() else 'missing'} ({csv_path})",
            f"JSON: {'yes' if json_path.exists() else 'missing'} ({json_path})",
            f"Images folder: {'yes' if images.exists() else 'missing'}",
        ]
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    lines.append(f"JSON records: {len(data)}")
            except Exception:
                pass
        self.export_summary_var.set("\n".join(lines))

    def _export_csv(self) -> None:
        src = self._output_dir() / CSV_FILENAME
        if not src.exists():
            messagebox.showerror("Export", "businesses.csv not found in output folder.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="businesses.csv")
        if dest:
            export_file(src, Path(dest))
            self._append_log("SUCCESS", f"Exported CSV to {dest}")
            messagebox.showinfo("Export", "CSV exported.")

    def _export_json(self) -> None:
        src = self._output_dir() / JSON_FILENAME
        if not src.exists():
            messagebox.showerror("Export", "businesses.json not found in output folder.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="businesses.json")
        if dest:
            export_file(src, Path(dest))
            self._append_log("SUCCESS", f"Exported JSON to {dest}")
            messagebox.showinfo("Export", "JSON exported.")

    def _export_images_zip(self) -> None:
        images = self._output_dir() / "images"
        if not images.exists():
            messagebox.showerror("Export", "No images folder found.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP", "*.zip")], initialfile="gallery_images.zip")
        if not dest:
            return
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in images.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(images.parent).as_posix())
        self._append_log("SUCCESS", f"Exported images ZIP to {dest}")
        messagebox.showinfo("Export", "Images ZIP exported.")

    def _import_csv(self) -> None:
        src = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not src:
            return
        try:
            count = import_csv_records(Path(src), self._output_dir() / CSV_FILENAME)
            self._append_log("SUCCESS", f"Imported {count} CSV row(s)")
            messagebox.showinfo("Import", f"Imported {count} row(s).")
            self._refresh_export_summary()
        except Exception as exc:
            messagebox.showerror("Import", str(exc))

    def _import_json(self) -> None:
        src = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not src:
            return
        try:
            count = import_json_records(Path(src), self._output_dir() / JSON_FILENAME)
            self._append_log("SUCCESS", f"Imported {count} JSON record(s)")
            messagebox.showinfo("Import", f"Imported {count} record(s).")
            self._refresh_export_summary()
        except Exception as exc:
            messagebox.showerror("Import", str(exc))

    def _open_output_folder(self) -> None:
        path = self._output_dir()
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def _open_path(self, path: Path) -> None:
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(path)])
            elif os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open Folder", str(exc))

    def run(self) -> None:
        self.root.mainloop()
