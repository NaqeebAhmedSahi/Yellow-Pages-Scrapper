"""UI theme tokens and ttk styles for the desktop app."""

from __future__ import annotations

from tkinter import ttk

COLORS = {
    "sidebar": "#16182a",
    "sidebar_hover": "#22253c",
    "sidebar_active": "#252845",
    "sidebar_text": "#c8cde0",
    "sidebar_muted": "#8b90a8",
    "accent": "#f5c518",
    "accent_hover": "#ffd84d",
    "accent_dark": "#1a1a1a",
    "bg": "#eef1f6",
    "surface": "#ffffff",
    "surface2": "#f5f7fb",
    "border": "#e2e6ef",
    "text": "#1c2434",
    "text_muted": "#6b7287",
    "success": "#16a34a",
    "success_bg": "#e8f8ef",
    "danger": "#dc2626",
    "danger_bg": "#fdecec",
    "warning": "#ea580c",
    "info": "#2563eb",
    "info_bg": "#eaf1ff",
    "purple": "#7c3aed",
    "log_bg": "#0f172a",
    "log_fg": "#e2e8f0",
    "log_info": "#60a5fa",
    "log_success": "#4ade80",
    "log_error": "#f87171",
    "log_warn": "#fbbf24",
}

FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SECTION = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_STAT = ("Segoe UI", 18, "bold")
FONT_LOG = ("Consolas", 10)
FONT_SIDEBAR = ("Segoe UI", 11)
FONT_SIDEBAR_BOLD = ("Segoe UI", 11, "bold")


def setup_styles(style: ttk.Style) -> None:
    style.theme_use("clam")

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("MutedCard.TFrame", background=COLORS["surface2"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["text_muted"], font=FONT_SMALL)
    style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_TITLE)
    style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONT_SECTION)
    style.configure("Sidebar.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_text"], font=FONT_SIDEBAR)
    style.configure("SidebarMuted.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_muted"], font=FONT_SMALL)
    style.configure("SidebarBrand.TLabel", background=COLORS["sidebar"], foreground=COLORS["accent"], font=("Segoe UI", 12, "bold"))
    style.configure("StatValue.TLabel", background=COLORS["surface2"], foreground=COLORS["text"], font=FONT_STAT)
    style.configure("StatLabel.TLabel", background=COLORS["surface2"], foreground=COLORS["text_muted"], font=FONT_SMALL)

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface2"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=8,
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface2"],
        foreground=COLORS["text"],
        padding=6,
    )

    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["accent_dark"],
        font=FONT_UI_BOLD,
        padding=(14, 10),
        borderwidth=0,
    )
    style.map("Accent.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", "#f0e6b0")])

    style.configure(
        "Secondary.TButton",
        background=COLORS["surface2"],
        foreground=COLORS["text"],
        font=FONT_UI,
        padding=(12, 9),
        borderwidth=1,
    )
    style.map("Secondary.TButton", background=[("active", COLORS["border"]), ("disabled", COLORS["surface2"])])

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="#ffffff",
        font=FONT_UI_BOLD,
        padding=(12, 9),
        borderwidth=0,
    )
    style.map("Danger.TButton", background=[("active", "#b91c1c"), ("disabled", "#f3b4b4")])

    style.configure(
        "Ghost.TButton",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=FONT_UI,
        padding=(12, 9),
        borderwidth=1,
    )
    style.map("Ghost.TButton", background=[("active", COLORS["surface2"])])

    style.configure(
        "Sidebar.TButton",
        background=COLORS["sidebar"],
        foreground=COLORS["sidebar_text"],
        font=FONT_SIDEBAR,
        padding=(14, 12),
        anchor="w",
        borderwidth=0,
    )
    style.map(
        "Sidebar.TButton",
        background=[("active", COLORS["sidebar_hover"]), ("pressed", COLORS["sidebar_active"])],
        foreground=[("active", "#ffffff")],
    )

    style.configure(
        "SidebarActive.TButton",
        background=COLORS["sidebar_active"],
        foreground="#ffffff",
        font=FONT_SIDEBAR_BOLD,
        padding=(14, 12),
        anchor="w",
        borderwidth=0,
    )

    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=COLORS["border"],
        background=COLORS["accent"],
        thickness=8,
        borderwidth=0,
    )
    style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("TRadiobutton", background=COLORS["surface"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["surface2"], padding=(12, 8))
    style.map("TNotebook.Tab", background=[("selected", COLORS["surface"])])
