"""Professional Tkinter GUI for Yellow Pages Scraper."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config.settings import DATA_DIR, DEFAULT_START_URL, LOGS_DIR
from src.scraper.orchestrator import ScraperOrchestrator

logger = logging.getLogger(__name__)


class YellowPagesGUI:
    """Main application window."""

    COLORS = {
        "bg": "#0f1419",
        "surface": "#1a2332",
        "surface2": "#243044",
        "accent": "#ffd400",
        "accent_hover": "#ffe566",
        "text": "#e7ecf3",
        "text_muted": "#8b9cb3",
        "success": "#3dd68c",
        "danger": "#f07178",
        "border": "#2d3a4f",
    }

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Yellow Pages Scraper")
        self.root.geometry("980x720")
        self.root.minsize(860, 640)
        self.root.configure(bg=self.COLORS["bg"])

        self.event_queue: queue.Queue = queue.Queue()
        self.scraper_thread: threading.Thread | None = None
        self.orchestrator: ScraperOrchestrator | None = None

        self._setup_styles()
        self._build_ui()
        self._poll_events()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.COLORS["bg"], foreground=self.COLORS["text"])
        style.configure("TFrame", background=self.COLORS["bg"])
        style.configure("Card.TFrame", background=self.COLORS["surface"])
        style.configure("TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"])
        style.configure("Card.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["text"])
        style.configure("Muted.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["text_muted"])
        style.configure(
            "Title.TLabel",
            background=self.COLORS["bg"],
            foreground=self.COLORS["accent"],
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Header.TLabel",
            background=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure("TEntry", fieldbackground=self.COLORS["surface2"], foreground=self.COLORS["text"])
        style.configure(
            "Accent.TButton",
            background=self.COLORS["accent"],
            foreground="#1a1a1a",
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )
        style.map("Accent.TButton", background=[("active", self.COLORS["accent_hover"])])
        style.configure(
            "Secondary.TButton",
            background=self.COLORS["surface2"],
            foreground=self.COLORS["text"],
            padding=8,
        )
        style.configure("Horizontal.TProgressbar", troughcolor=self.COLORS["surface2"], background=self.COLORS["accent"])

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(20, 16, 20, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Yellow Pages Scraper", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Production scraper with resume support, CSV/JSON export, and undetected Chrome",
            foreground=self.COLORS["text_muted"],
            background=self.COLORS["bg"],
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, pady=(4, 0))

        config_card = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        config_card.pack(fill=tk.X, padx=20, pady=8)
        ttk.Label(config_card, text="Configuration", style="Header.TLabel").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 12))

        ttk.Label(config_card, text="Start URL", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W)
        self.url_var = tk.StringVar(value=DEFAULT_START_URL)
        url_entry = ttk.Entry(config_card, textvariable=self.url_var, width=72)
        url_entry.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(4, 10))

        ttk.Label(config_card, text="Output Folder", style="Card.TLabel").grid(row=3, column=0, sticky=tk.W)
        self.output_var = tk.StringVar(value=str(DATA_DIR))
        ttk.Entry(config_card, textvariable=self.output_var, width=52).grid(row=4, column=0, sticky=tk.EW, pady=(4, 10))
        ttk.Button(config_card, text="Browse", style="Secondary.TButton", command=self._browse_output).grid(row=4, column=1, padx=(8, 0))

        options = ttk.Frame(config_card, style="Card.TFrame")
        options.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Headless mode", variable=self.headless_var, style="Card.TCheckbutton").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(options, text="Max pages (0 = all)", style="Card.TLabel").pack(side=tk.LEFT)
        self.max_pages_var = tk.StringVar(value="0")
        ttk.Entry(options, textvariable=self.max_pages_var, width=8).pack(side=tk.LEFT, padx=(8, 0))

        config_card.columnconfigure(0, weight=1)

        controls = ttk.Frame(self.root, padding=(20, 4))
        controls.pack(fill=tk.X)
        self.start_btn = ttk.Button(controls, text="Start Scraping", style="Accent.TButton", command=self._start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.pause_btn = ttk.Button(controls, text="Pause", style="Secondary.TButton", command=self._pause_scraping, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.resume_btn = ttk.Button(controls, text="Resume", style="Secondary.TButton", command=self._resume_scraping, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(controls, text="Stop", style="Secondary.TButton", command=self._stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        stats_card = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        stats_card.pack(fill=tk.X, padx=20, pady=8)
        ttk.Label(stats_card, text="Progress", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))

        stats_grid = ttk.Frame(stats_card, style="Card.TFrame")
        stats_grid.pack(fill=tk.X)
        self.stat_labels = {}
        for idx, (key, label) in enumerate(
            [
                ("scraped", "Scraped"),
                ("pending", "Pending"),
                ("failed", "Failed"),
                ("page", "List Page"),
                ("total", "Total Results"),
            ]
        ):
            frame = ttk.Frame(stats_grid, style="Card.TFrame")
            frame.grid(row=0, column=idx, padx=(0, 24), sticky=tk.W)
            ttk.Label(frame, text=label, style="Muted.TLabel").pack(anchor=tk.W)
            val = ttk.Label(frame, text="0", style="Header.TLabel", font=("Segoe UI", 16, "bold"))
            val.pack(anchor=tk.W)
            self.stat_labels[key] = val

        self.progress_bar = ttk.Progressbar(stats_card, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(14, 0))

        log_card = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        log_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(8, 20))
        ttk.Label(log_card, text="Activity Log", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))

        log_frame = ttk.Frame(log_card, style="Card.TFrame")
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(
            log_frame,
            height=14,
            bg=self.COLORS["surface2"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        footer = ttk.Label(
            self.root,
            text="Output: businesses.csv | businesses.json | progress.json",
            foreground=self.COLORS["text_muted"],
            background=self.COLORS["bg"],
            font=("Segoe UI", 9),
        )
        footer.pack(pady=(0, 10))

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def _set_running_state(self, running: bool, paused: bool = False) -> None:
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.pause_btn.configure(state=tk.NORMAL if running and not paused else tk.DISABLED)
        self.resume_btn.configure(state=tk.NORMAL if running and paused else tk.DISABLED)
        if running and not paused:
            self.progress_bar.start(12)
        else:
            self.progress_bar.stop()

    def _start_scraping(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Validation", "Please enter a start URL.")
            return

        output_dir = Path(self.output_var.get().strip())
        max_pages_raw = self.max_pages_var.get().strip()
        max_pages = int(max_pages_raw) if max_pages_raw.isdigit() and int(max_pages_raw) > 0 else None

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._set_running_state(True)
        self._log(f"Starting scrape: {url}")

        def status_cb(msg: str) -> None:
            self.event_queue.put(("status", msg))

        def progress_cb(data: dict) -> None:
            self.event_queue.put(("progress", data))

        self.orchestrator = ScraperOrchestrator(
            start_url=url,
            output_dir=output_dir,
            headless=self.headless_var.get(),
            max_pages=max_pages,
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
            self._log("Paused")

    def _resume_scraping(self) -> None:
        if self.orchestrator:
            self.orchestrator.resume()
            self._set_running_state(True, paused=False)
            self._log("Resumed")

    def _stop_scraping(self) -> None:
        if self.orchestrator:
            self.orchestrator.stop()
            self._log("Stopping...")

    def _update_stats(self, data: dict) -> None:
        self.stat_labels["scraped"].configure(text=str(data.get("scraped_count", 0)))
        self.stat_labels["pending"].configure(text=str(data.get("pending_count", 0)))
        self.stat_labels["failed"].configure(text=str(data.get("failed_count", 0)))
        page = data.get("current_list_page", 0)
        total_pages = data.get("total_list_pages") or "?"
        self.stat_labels["page"].configure(text=f"{page} / {total_pages}")
        total_results = data.get("total_results")
        self.stat_labels["total"].configure(text=str(total_results) if total_results else "-")

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()
                if event_type == "status":
                    self._log(str(payload))
                elif event_type == "progress":
                    self._update_stats(payload)
                    if payload.get("message"):
                        self._log(payload["message"])
                elif event_type == "error":
                    self._log(f"ERROR: {payload}")
                    messagebox.showerror("Scraper Error", str(payload))
                elif event_type == "done":
                    self._set_running_state(False)
                    self._log("Session ended.")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)

    def run(self) -> None:
        self.root.mainloop()
