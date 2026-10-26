from __future__ import annotations

import ctypes
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox
from typing import Any, Callable
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from ctypes import wintypes

from .crypto import decrypt, derive_key, encrypt
from .gvas import GvasFile
from .integrity import check_checksum, refresh_checksum
from .prestige import state as prestige_state, apply_hero_prestige, rebuilt_ffwt
from .presets import PRESETS, apply_presets
from .i18n import I18N


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SAVE = ROOT_DIR
PARTY_SUFFIX = "NicoArnoEvilRaptorFireshineRobbo"
INT32_MAX = 2147483647
WM_DROPFILES = 0x0233
GWL_WNDPROC = -4

# --- color palette -------------------------------------------------------
BG          = "#1f232b"
BG_ALT      = "#262b35"
BG_PANEL    = "#2c313c"
BG_HOVER    = "#343a47"
BG_ACTIVE   = "#3d4555"
ACCENT      = "#d99947"   # warm western gold
ACCENT_HOV  = "#e8a85a"
TEXT        = "#e6e8ec"
TEXT_DIM    = "#9aa1ad"
BORDER      = "#3a4050"
DANGER      = "#d97a47"
SUCCESS     = "#7ab36b"


@dataclass
class EditRow:
    row_id: str
    cells: tuple[str, ...]
    getter: Callable[[], Any]
    setter: Callable[[Any], None]


def _load_key(save_path: Path) -> bytes:
    return derive_key(_seed_for_save(save_path))


def _seed_for_save(save_path: Path) -> str:
    match = re.match(r"^(\d+)", save_path.stem)
    if match is None:
        raise RuntimeError(f"Save filename must start with a SteamID: {save_path.name}")
    return match.group(1) + PARTY_SUFFIX


def _short_name(prop_name: str) -> str:
    return prop_name.split("_", 1)[0]


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return I18N.t("true") if value else I18N.t("false")
    if value is None:
        return ""
    return str(value)


def _parse_value(text: str, current: Any) -> Any:
    if isinstance(current, bool):
        v = text.strip().lower()
        if v in ("1", "true", "yes", "on"):  return True
        if v in ("0", "false", "no", "off"): return False
        raise ValueError("Boolean values must be true/false or 1/0.")
    if isinstance(current, int) and not isinstance(current, bool):
        v = int(text.strip())
        if v < -2147483648 or v > INT32_MAX:
            raise ValueError("Integer value must fit in a signed 32-bit range.")
        return v
    if isinstance(current, float):
        return float(text.strip())
    if current is None:
        return None if text == "" else text
    return text


# =========================================================================
# main app
# =========================================================================
class SaveEditor(tk.Tk):
    NAV_KEYS = [
        ("presets",   "presets"),
        ("prestige",  "Prestige"),
        ("currencies", "Currencies"),
        ("overview",  "overview"),
        ("inventory", "inventory"),
        ("levels",    "levels"),
        ("upgrades",  "upgrades"),
        ("jokers",    "jokers"),
        ("rewards",   "rewards"),
        ("other",     "other"),
    ]
    TABLE_HEADER_KEYS = {
        "overview":  ("field", "value"),
        "inventory": ("item", "amount"),
        "currencies": ("item", "amount"),
        "levels":    ("counter", "linked_inv", "value"),
        "upgrades":  ("item", "upgrade", "value"),
        "jokers":    ("item", "slot", "value"),
        "rewards":   ("index", "challenge"),
        "other":     ("path", "value"),
    }

    def __init__(self):
        super().__init__()
        self.title("FarFarWest Save Editor")
        self.geometry("1180x740")
        self.minsize(960, 600)
        self.configure(bg=BG)

        self.key: bytes | None = None
        self.save_path: Path | None = None
        self.gvas: GvasFile | None = None
        self.tables: dict[str, dict[str, Any]] = {}
        self.pages: dict[str, ttk.Frame] = {}
        self.nav_buttons: dict[str, tk.Label] = {}
        self.current_page: str = "presets"
        self.preset_vars: dict[str, tk.BooleanVar] = {}
        self.file_label_var = tk.StringVar(value=I18N.t("no_save"))
        self.status_var = tk.StringVar(value=I18N.t("status_default"))
        self.lang_var = tk.StringVar(value=I18N.get_current_lang())

        self._drop_wndproc = None
        self._drop_old_procs: dict[int, int] = {}
        self._drop_hwnds: set[int] = set()

        self._init_styles()
        self._build_ui()
        self._install_file_drop()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        default = self._default_save_path()
        if default is not None:
            self.load_save(default)
        self._show_page("presets")
        self.update_title()

    def update_title(self):
        self.title(I18N.t("title"))

    def _on_lang_change(self, lang):
        I18N.set_language(lang)
        self.update_title()
        # Refresh all UI components with new translations
        # In a real app we'd destroy and rebuild, or update all stringvars.
        # Here we'll just rebuild the core UI parts.
        for widget in self.winfo_children():
            widget.destroy()
        self.pages.clear()
        self.nav_buttons.clear()
        self.tables.clear()
        self._build_ui()
        self._show_page(self.current_page)
        if self.gvas:
            self.rebuild_rows()
            self.file_label_var.set(self.save_path.name if self.save_path else I18N.t("no_save"))
        else:
            self.file_label_var.set(I18N.t("no_save"))
            self.status_var.set(I18N.t("status_default"))

    def _default_save_path(self) -> Path | None:
        if not DEFAULT_SAVE.exists():
            return None
        candidates = [
            p for p in DEFAULT_SAVE.glob("*.save")
            if re.match(r"^\d+$", p.stem)  # SteamID-only, not backups
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    # ---- styling --------------------------------------------------------
    def _init_styles(self):
        base = tkfont.nametofont("TkDefaultFont")
        base.configure(family="Segoe UI", size=10)
        self.option_add("*Font", base)
        self.heading_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.title_font   = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.small_font   = tkfont.Font(family="Segoe UI", size=9)
        self.mono_font    = tkfont.Font(family="Consolas", size=10)

        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass

        s.configure(".", background=BG, foreground=TEXT, fieldbackground=BG_PANEL,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=BG_PANEL)
        s.configure("Card.TFrame", background=BG_ALT, relief="flat", borderwidth=1)
        s.configure("Sidebar.TFrame", background=BG_ALT)

        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT)
        s.configure("Card.TLabel", background=BG_ALT, foreground=TEXT)
        s.configure("CardDim.TLabel", background=BG_ALT, foreground=TEXT_DIM, font=self.small_font)
        s.configure("Heading.TLabel", background=BG, foreground=TEXT, font=self.heading_font)
        s.configure("Sub.TLabel", background=BG, foreground=TEXT_DIM, font=self.small_font)
        s.configure("File.TLabel", background=BG, foreground=ACCENT, font=self.title_font)
        s.configure("Status.TLabel", background=BG_ALT, foreground=TEXT_DIM, padding=(12, 6))

        s.configure("TButton", background=BG_PANEL, foreground=TEXT, padding=(14, 7),
                    borderwidth=0, relief="flat", focusthickness=0)
        s.map("TButton",
              background=[("active", BG_HOVER), ("pressed", BG_ACTIVE)],
              foreground=[("disabled", TEXT_DIM)])
        s.configure("Accent.TButton", background=ACCENT, foreground="#1b1b1b",
                    padding=(16, 8), font=self.title_font)
        s.map("Accent.TButton", background=[("active", ACCENT_HOV), ("pressed", ACCENT_HOV)])
        s.configure("Ghost.TButton", background=BG, foreground=TEXT_DIM, padding=(10, 5))
        s.map("Ghost.TButton", background=[("active", BG_PANEL)], foreground=[("active", TEXT)])

        s.configure("TEntry", fieldbackground=BG_PANEL, foreground=TEXT,
                    insertcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        s.configure("Card.TCheckbutton", background=BG_ALT, foreground=TEXT,
                    focuscolor=BG_ALT, padding=(0, 0))
        s.map("Card.TCheckbutton",
              background=[("active", BG_ALT)],
              indicatorcolor=[("selected", ACCENT), ("!selected", BG_PANEL)])

        s.configure("TSeparator", background=BORDER)
        s.configure("Vertical.TScrollbar", background=BG_PANEL, troughcolor=BG,
                    bordercolor=BG, arrowcolor=TEXT_DIM)

        s.configure("Treeview",
                    background=BG_PANEL, fieldbackground=BG_PANEL, foreground=TEXT,
                    rowheight=26, bordercolor=BORDER, borderwidth=0)
        s.configure("Treeview.Heading",
                    background=BG_ALT, foreground=TEXT_DIM, relief="flat", padding=(8, 6))
        s.map("Treeview.Heading", background=[("active", BG_HOVER)])
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#1b1b1b")])

    # ---- layout ---------------------------------------------------------
    def _build_ui(self):
        # top header bar
        header = ttk.Frame(self, padding=(20, 14))
        header.pack(fill=X)
        self.header_label = ttk.Label(header, text=I18N.t("title"), style="Heading.TLabel")
        self.header_label.pack(side=LEFT)
        ttk.Label(header, textvariable=self.file_label_var, style="File.TLabel").pack(side=LEFT, padx=(18, 0))

        ttk.Button(header, text=I18N.t("save_as"), command=self.save_as, style="Ghost.TButton").pack(side=RIGHT)
        ttk.Button(header, text=I18N.t("save"),    command=self.save_current, style="Accent.TButton").pack(side=RIGHT, padx=(0, 8))
        ttk.Button(header, text=I18N.t("open"),    command=self.open_save, style="Ghost.TButton").pack(side=RIGHT, padx=(0, 8))

        # lang dropdown
        lang_frame = ttk.Frame(header)
        lang_frame.pack(side=RIGHT, padx=(0, 18))
        lang_menu = ttk.OptionMenu(lang_frame, self.lang_var, I18N.get_current_lang(), "en", "zh", "ru", command=self._on_lang_change)
        lang_menu.pack()

        # body: sidebar + content
        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True, padx=20, pady=(0, 0))

        sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        self.content_holder = ttk.Frame(body, style="Panel.TFrame", padding=(16, 16))
        self.content_holder.pack(side=LEFT, fill=BOTH, expand=True, padx=(12, 0))

        # build pages
        self._build_presets_page()
        for key, _ in self.NAV_KEYS:
            if key == "presets":
                continue
            if key == "prestige":
                self._build_prestige_page()
                continue
            self._build_table_page(key, tuple(I18N.t(k) for k in self.TABLE_HEADER_KEYS[key]))

        # status
        status = ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        status.pack(fill=X, pady=(12, 0))

    def _build_sidebar(self, parent):
        ttk.Label(parent, text=I18N.t("navigate"), background=BG_ALT, foreground=TEXT_DIM,
                  font=self.small_font).pack(anchor="w", padx=18, pady=(18, 8))
        for key, key_label in self.NAV_KEYS:
            btn = tk.Label(parent, text=I18N.t(key_label), anchor="w", padx=18, pady=10,
                           bg=BG_ALT, fg=TEXT, font=self.title_font, cursor="hand2")
            btn.pack(fill=X)
            btn.bind("<Button-1>", lambda _e, k=key: self._show_page(k))
            btn.bind("<Enter>",    lambda _e, b=btn, k=key: self._nav_hover(b, k, True))
            btn.bind("<Leave>",    lambda _e, b=btn, k=key: self._nav_hover(b, k, False))
            self.nav_buttons[key] = btn

        ttk.Label(parent, text=I18N.t("drop_hint"),
                  background=BG_ALT, foreground=TEXT_DIM,
                  font=self.small_font, justify="left"
                  ).pack(side="bottom", anchor="w", padx=18, pady=18)

    def _nav_hover(self, btn: tk.Label, key: str, hovering: bool):
        if key == self.current_page:
            return
        btn.configure(bg=BG_HOVER if hovering else BG_ALT)

    def _show_page(self, key: str):
        self.current_page = key
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(bg=ACCENT, fg="#1b1b1b")
            else:
                btn.configure(bg=BG_ALT, fg=TEXT)
        for pkey, frame in self.pages.items():
            frame.pack_forget()
        self.pages[key].pack(fill=BOTH, expand=True)

    # ---- one-step Hero prestige ---------------------------------------
    def _build_prestige_page(self):
        page = ttk.Frame(self.content_holder, style="Panel.TFrame")
        self.pages["prestige"] = page
        ttk.Label(page, text="Hero Prestige", style="Heading.TLabel").pack(anchor="w", pady=(0,12))
        self.prestige_summary = tk.StringVar(value="Open a save to view Hero prestige.")
        ttk.Label(page, textvariable=self.prestige_summary, style="Panel.TLabel").pack(anchor="w", pady=(0,14))
        ttk.Label(page, text="Perform ONE prestige at a time. Allocate exactly five tokens.", style="Panel.TLabel").pack(anchor="w", pady=(0,8))
        self.prestige_joker = tk.BooleanVar(value=True)
        ttk.Checkbutton(page, text="+1 Hero Joker slot (5 tokens; maximum 2)", variable=self.prestige_joker).pack(anchor="w", pady=4)
        self.prestige_upgrades=tk.StringVar(value="0")
        self.prestige_tickets=tk.StringVar(value="0")
        self.prestige_gold=tk.StringVar(value="0")
        self.prestige_souls=tk.StringVar(value="0")
        for label,variable in (("Hero upgrade slots (2 tokens each, max 6)",self.prestige_upgrades),
                               ("XP tickets (1 token each)",self.prestige_tickets),
                               ("500 gold packs (1 token each)",self.prestige_gold),
                               ("1,000 souls packs (1 token each)",self.prestige_souls)):
            line=ttk.Frame(page, style="Panel.TFrame")
            line.pack(anchor="w",fill=X,pady=3)
            ttk.Label(line,text=label,style="Panel.TLabel",width=35).pack(side=LEFT)
            tk.Spinbox(line,from_=0,to=5,width=5,textvariable=variable).pack(side=LEFT)
        ttk.Label(page,text="Allocate exactly five tokens. Back up your save before editing.",style="Panel.TLabel").pack(anchor="w",pady=(12,5))
        ttk.Label(page,text="The game may require level 100. This tool does not enforce level eligibility.",style="Panel.TLabel").pack(anchor="w",pady=5)
        ttk.Button(page,text="Apply one prestige (then click Save)",style="Accent.TButton",command=self._apply_prestige).pack(anchor="w",pady=14)
        ttk.Label(page,text="Back up your save. Test upgrades only on a BACKUP; other rewards have been verified in-game.",style="Panel.TLabel").pack(anchor="w")

    def _refresh_prestige(self):
        if self.gvas is not None and hasattr(self,"prestige_summary"):
            data=prestige_state(self.gvas)
            self.prestige_summary.set(f"Current Hero prestige: {data['prestige']} / 15     Extra Joker slots: {data['joker']} / 2     Extra upgrade slots: {data['upgrade_slots']} / 6     Hero XP: {data['xp']}")

    def _apply_prestige(self):
        if self.gvas is None:
            messagebox.showwarning("No save", "Open a save first.")
            return
        import copy
        candidate=copy.deepcopy(self.gvas)
        try:
            before,after=apply_hero_prestige(candidate,self.prestige_joker.get(),
                                              int(self.prestige_tickets.get()),
                                              int(self.prestige_gold.get()),
                                              int(self.prestige_souls.get()),
                                              int(self.prestige_upgrades.get()))
            payload=rebuilt_ffwt(candidate)
            check_checksum(payload)
            if GvasFile.parse(payload).serialize()!=payload:
                raise ValueError("Prestige output failed round-trip verification")
            if not messagebox.askyesno("Confirm prestige edit",f"Prestige {before['prestige']} → {after['prestige']}\nHero XP → 1\n\nApply to editor? You must then click Save."):
                return
            self.gvas=candidate
            self.rebuild_rows()
            self._refresh_prestige()
            self.status_var.set("Prestige changes staged. Click Save to write the file.")
        except Exception as exc:
            messagebox.showerror("Prestige edit refused",str(exc))

    # ---- presets page ---------------------------------------------------
    def _build_presets_page(self):
        page = ttk.Frame(self.content_holder, style="Panel.TFrame")
        self.pages["presets"] = page

        head = ttk.Frame(page, style="Panel.TFrame")
        head.pack(fill=X, pady=(0, 10))
        ttk.Label(head, text=I18N.t("presets"), style="Panel.TLabel",
                  font=self.heading_font).pack(side=LEFT)
        ttk.Label(head,
                  text=I18N.t("preset_hint"),
                  style="Panel.TLabel", foreground=TEXT_DIM, font=self.small_font
                  ).pack(side=LEFT, padx=(14, 0), pady=(6, 0))

        actions = ttk.Frame(page, style="Panel.TFrame")
        actions.pack(fill=X, pady=(0, 14))
        ttk.Button(actions, text=I18N.t("apply_selected"), style="Accent.TButton",
                   command=self.apply_selected_presets).pack(side=LEFT)
        ttk.Button(actions, text=I18N.t("select_all"),  style="Ghost.TButton",
                   command=lambda: self._set_all_preset_vars(True)).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text=I18N.t("clear"),       style="Ghost.TButton",
                   command=lambda: self._set_all_preset_vars(False)).pack(side=LEFT, padx=(4, 0))

        # scrollable card list
        scroll_wrap = ttk.Frame(page, style="Panel.TFrame")
        scroll_wrap.pack(fill=BOTH, expand=True)
        canvas = tk.Canvas(scroll_wrap, bg=BG_PANEL, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        sb.pack(side=RIGHT, fill=Y)

        cards = ttk.Frame(canvas, style="Panel.TFrame")
        cards_window = canvas.create_window((0, 0), window=cards, anchor="nw")
        cards.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(cards_window, width=e.width))

        def on_mw(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<MouseWheel>", on_mw)
        cards.bind("<MouseWheel>", on_mw)

        for preset in PRESETS:
            self._build_preset_card(cards, preset, on_mw)

    def _build_preset_card(self, parent, preset, mw_handler):
        card = tk.Frame(parent, bg=BG_ALT, highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=BORDER)
        card.pack(fill=X, pady=6, padx=2)

        var = tk.BooleanVar(value=False)
        self.preset_vars[preset.key] = var

        chk = ttk.Checkbutton(card, variable=var, style="Card.TCheckbutton")
        chk.pack(side=LEFT, padx=(14, 10), pady=14)

        text = tk.Frame(card, bg=BG_ALT)
        text.pack(side=LEFT, fill=X, expand=True, pady=10)
        tk.Label(text, text=I18N.t(preset.name), bg=BG_ALT, fg=TEXT,
                 font=self.title_font, anchor="w").pack(anchor="w")
        tk.Label(text, text=I18N.t(preset.description), bg=BG_ALT, fg=TEXT_DIM,
                 font=self.small_font, anchor="w", justify="left",
                 wraplength=820).pack(anchor="w", pady=(2, 0))

        def toggle(_e=None, v=var):
            v.set(not v.get())
        for w in (card, text, *text.winfo_children()):
            w.bind("<Button-1>", toggle)
            w.bind("<MouseWheel>", mw_handler)
        card.bind("<MouseWheel>", mw_handler)

    def _set_all_preset_vars(self, value: bool):
        for v in self.preset_vars.values():
            v.set(value)

    def apply_selected_presets(self):
        if self.gvas is None:
            messagebox.showinfo(I18N.t("no_save"), I18N.t("msg_no_save"))
            return
        keys = [k for k, v in self.preset_vars.items() if v.get()]
        if not keys:
            messagebox.showinfo(I18N.t("msg_no_selection"), I18N.t("msg_nothing_selected"))
            return
        log = apply_presets(self._player_props(), keys)
        self.rebuild_rows()
        msg = "\n".join(log)
        self.status_var.set(I18N.t("status_default")) # or some generic update
        messagebox.showinfo(I18N.t("msg_presets_applied"), msg + "\n\n" + I18N.t("msg_click_save"))

    # ---- table pages ----------------------------------------------------
    def _build_table_page(self, key: str, columns: tuple[str, ...]):
        page = ttk.Frame(self.content_holder, style="Panel.TFrame")
        self.pages[key] = page

        head = ttk.Frame(page, style="Panel.TFrame")
        head.pack(fill=X, pady=(0, 10))
        ttk.Label(head, text=I18N.t(key), style="Panel.TLabel",
                  font=self.heading_font).pack(side=LEFT)

        search_var = tk.StringVar()
        ttk.Label(head, text=I18N.t("search"), style="Panel.TLabel",
                  foreground=TEXT_DIM).pack(side=LEFT, padx=(20, 6))
        search = ttk.Entry(head, textvariable=search_var, width=32)
        search.pack(side=LEFT)

        body = ttk.Frame(page, style="Panel.TFrame")
        body.pack(fill=BOTH, expand=True)

        # left: tree
        table_frame = ttk.Frame(body, style="Panel.TFrame")
        table_frame.pack(side=LEFT, fill=BOTH, expand=True)
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for i, column in enumerate(columns):
            tree.heading(column, text=column)
            width = 320 if i == 0 else 220
            anchor = "e" if column.lower() in ("value", "amount") else "w"
            tree.column(column, width=width, anchor=anchor, stretch=True)
        tree.tag_configure("alt", background=BG_ALT)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        sb.pack(side=RIGHT, fill=Y)
        tree.configure(yscrollcommand=sb.set)

        # right: edit panel
        editor = tk.Frame(body, bg=BG_ALT, width=300, highlightthickness=1,
                          highlightbackground=BORDER)
        editor.pack(side=RIGHT, fill=Y, padx=(14, 0))
        editor.pack_propagate(False)

        selected_var = tk.StringVar()
        type_var     = tk.StringVar()
        value_var    = tk.StringVar()

        pad = {"padx": 16}
        tk.Label(editor, text=I18N.t("edit_value"), bg=BG_ALT, fg=TEXT_DIM,
                 font=self.small_font).pack(anchor="w", pady=(16, 4), **pad)

        tk.Label(editor, text=I18N.t("field"), bg=BG_ALT, fg=TEXT_DIM,
                 font=self.small_font).pack(anchor="w", **pad)
        ttk.Entry(editor, textvariable=selected_var, state="readonly").pack(fill=X, pady=(2, 10), **pad)

        tk.Label(editor, text=I18N.t("type"), bg=BG_ALT, fg=TEXT_DIM,
                 font=self.small_font).pack(anchor="w", **pad)
        ttk.Entry(editor, textvariable=type_var, state="readonly").pack(fill=X, pady=(2, 10), **pad)

        tk.Label(editor, text=I18N.t("value"), bg=BG_ALT, fg=TEXT_DIM,
                 font=self.small_font).pack(anchor="w", **pad)
        value_entry = ttk.Entry(editor, textvariable=value_var, font=self.mono_font)
        value_entry.pack(fill=X, pady=(2, 12), **pad)
        ttk.Button(editor, text=I18N.t("apply"), style="Accent.TButton",
                   command=lambda k=key: self.apply_table_value(k)
                   ).pack(fill=X, **pad)

        ttk.Separator(editor, orient="horizontal").pack(fill=X, pady=18, padx=12)
        tk.Label(editor,
                 text=I18N.t("backup_hint"),
                 bg=BG_ALT, fg=TEXT_DIM, font=self.small_font, justify="left",
                 wraplength=260).pack(anchor="w", **pad)

        info = {
            "tree": tree, "columns": columns, "rows": [],
            "search_var": search_var, "selected_var": selected_var,
            "type_var": type_var, "value_var": value_var,
            "value_entry": value_entry, "selected_row": None,
        }
        self.tables[key] = info

        search.bind("<KeyRelease>", lambda _e, k=key: self.refresh_table(k))
        tree.bind("<<TreeviewSelect>>", lambda _e, k=key: self.on_table_select(k))
        tree.bind("<Double-1>", lambda _e, e=value_entry: e.focus_set())
        value_entry.bind("<Return>", lambda _e, k=key: self.apply_table_value(k))

    # ---- file ops -------------------------------------------------------
    def open_save(self):
        path = filedialog.askopenfilename(
            title=I18N.t("open"),
            initialdir=str(ROOT_DIR),
            filetypes=[(I18N.t("save"), "*.save"), (I18N.t("other"), "*.*")],
        )
        if path:
            self.load_save(Path(path))

    def load_save(self, path: Path):
        try:
            self.key = _load_key(path)
            original_encrypted = path.read_bytes()
            plaintext = decrypt(original_encrypted, self.key)
            check_checksum(plaintext)
            self.gvas = GvasFile.parse(plaintext)
            if self.gvas.serialize() != plaintext:
                raise ValueError("Save parser does not round-trip this file exactly; refusing to edit.")
            self._source_encrypted = original_encrypted
            self._source_plaintext = plaintext
            self.save_path = path
            self.file_label_var.set(path.name)
            self.rebuild_rows()
            self._refresh_prestige()
            total = sum(len(info["rows"]) for info in self.tables.values())
            self.status_var.set(I18N.t("msg_loaded", name=path.name, total=total))
        except Exception as exc:
            messagebox.showerror(I18N.t("msg_load_failed"), str(exc))
            self.status_var.set(f"{I18N.t('msg_load_failed')}: {exc}")

    def save_current(self):
        if not self._apply_pending_selected_edit():
            return
        if self.save_path is None:
            self.save_as()
            return
        self._save_to(self.save_path, make_backup=True)

    def save_as(self):
        if not self._apply_pending_selected_edit():
            return
        path = filedialog.asksaveasfilename(
            title=I18N.t("save_as"),
            initialdir=str(ROOT_DIR),
            initialfile=self.save_path.name if self.save_path else "edited.save",
            defaultextension=".save",
            filetypes=[(I18N.t("save"), "*.save"), (I18N.t("other"), "*.*")],
        )
        if path:
            self._save_to(Path(path), make_backup=Path(path).exists())

    def _save_to(self, path: Path, make_backup: bool):
        if self.gvas is None:
            messagebox.showinfo(I18N.t("msg_nothing_to_save"), I18N.t("msg_no_save"))
            return
        if self.key is None:
            messagebox.showerror(I18N.t("save_failed"), I18N.t("msg_no_key"))
            return
        try:
            # v11: regenerate FFWT footer/padding even when game-format records grow.
            plaintext = rebuilt_ffwt(self.gvas)
            check_checksum(plaintext)
            parsed_again = GvasFile.parse(plaintext)
            if parsed_again.serialize() != plaintext:
                raise ValueError("Generated save failed parser verification. Original left untouched.")
            original = getattr(self, "_source_encrypted", None)
            original_plain = getattr(self, "_source_plaintext", None)
            if original is None or original_plain is None:
                raise ValueError("No original encrypted save recorded. Reopen the save first.")
            if path == self.save_path and path.exists() and path.read_bytes() != original:
                raise ValueError("The game or another program changed this save since opening it. Reopen the latest save before editing.")
            if path == self.save_path and plaintext == original_plain:
                self.status_var.set("No changes detected; original encrypted save left untouched.")
                return
            # Preserve the original IV. This is a conservative compatibility
            # experiment, NOT evidence the game's integrity checks require it.
            encrypted = encrypt(plaintext, self.key, iv=original[:16])
            if decrypt(encrypted, self.key) != plaintext:
                raise ValueError("Encrypted save failed read-back verification.")
            # New game-format prestige records legitimately change file length.
            if make_backup and path.exists():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup = path.with_name(f"{path.stem}.backup_gui_{stamp}{path.suffix}")
                shutil.copy2(path, backup)
            tmp = path.with_name(path.name + ".tmp")
            try:
                tmp.write_bytes(encrypted)
                if decrypt(tmp.read_bytes(), self.key) != plaintext:
                    raise ValueError("Temporary save failed disk read-back verification.")
                tmp.replace(path)
            finally:
                if tmp.exists():
                    tmp.unlink()
            self._source_encrypted = encrypted
            self._source_plaintext = plaintext
            self.save_path = path
            self.file_label_var.set(path.name)
            self.status_var.set(I18N.t("msg_saved", name=path.name))
        except Exception as exc:
            messagebox.showerror(I18N.t("save_failed"), str(exc))
            self.status_var.set(f"{I18N.t('save_failed')}: {exc}")

    # ---- table data plumbing -------------------------------------------
    def rebuild_rows(self, keep_selection: tuple[str, str] | None = None):
        if self.gvas is None:
            return
        builders = {
            "overview":  self._overview_rows,
            "inventory": self._inventory_rows,
            "currencies": self._currency_rows,
            "levels":    self._level_rows,
            "upgrades":  self._upgrade_rows,
            "jokers":    self._joker_rows,
            "rewards":   self._reward_rows,
            "other":     self._other_rows,
        }
        for key, builder in builders.items():
            self.tables[key]["rows"] = builder()
            self.refresh_table(key)
        if keep_selection:
            key, row_id = keep_selection
            tree = self.tables[key]["tree"]
            if tree.exists(row_id):
                tree.selection_set(row_id)
                tree.see(row_id)

    def refresh_table(self, key: str):
        info = self.tables[key]
        tree: ttk.Treeview = info["tree"]
        query = info["search_var"].get().strip().lower()
        selected = info.get("selected_row")
        tree.delete(*tree.get_children())
        for i, row in enumerate(info["rows"]):
            searchable = " ".join(row.cells + (_display_value(row.getter()),)).lower()
            if query and query not in searchable:
                continue
            values = row.cells[:-1] + (_display_value(row.getter()),)
            tags = ("alt",) if i % 2 else ()
            tree.insert("", END, iid=row.row_id, values=values, tags=tags)
            if selected and selected.row_id == row.row_id:
                tree.selection_set(row.row_id)

    def on_table_select(self, key: str):
        info = self.tables[key]
        selected = info["tree"].selection()
        if not selected:
            return
        row = self._row_by_id(key, selected[0])
        if row is None:
            return
        value = row.getter()
        info["selected_row"] = row
        info["selected_var"].set(" / ".join(row.cells[:-1]) if len(row.cells) > 1 else row.cells[0])
        info["type_var"].set(type(value).__name__)
        info["value_var"].set(_display_value(value))

    def apply_table_value(self, key: str, silent: bool = False) -> bool:
        info = self.tables[key]
        row: EditRow | None = info.get("selected_row")
        if row is None:
            if not silent:
                messagebox.showinfo(I18N.t("msg_no_selection"), I18N.t("msg_select_row"))
            return True
        try:
            current = row.getter()
            new_value = _parse_value(info["value_var"].get(), current)
            row.setter(new_value)
        except Exception as exc:
            if not silent:
                messagebox.showerror(I18N.t("msg_invalid_value"), str(exc))
            return False
        self.rebuild_rows((key, row.row_id))
        if not silent:
            self.status_var.set(I18N.t("msg_updated", field=' / '.join(row.cells[:-1])))
        return True

    def _apply_pending_selected_edit(self) -> bool:
        for table_key, info in self.tables.items():
            tree = info["tree"]
            if tree.selection():
                row = info.get("selected_row")
                if row is not None and info["value_var"].get() != _display_value(row.getter()):
                    return self.apply_table_value(table_key, silent=True)
        return True

    def _row_by_id(self, key: str, row_id: str) -> EditRow | None:
        return next((row for row in self.tables[key]["rows"] if row.row_id == row_id), None)

    # ---- row builders (unchanged behavior) ------------------------------
    def _player_props(self) -> list[dict]:
        if self.gvas is None:
            return []
        for prop in self.gvas.properties:
            if prop["_name"] == "playerProgress":
                return prop["value"]
        return []

    def _find_prop(self, prefix: str) -> dict | None:
        return next((p for p in self._player_props() if p["_name"].startswith(prefix)), None)

    def _overview_rows(self):
        rows = []
        container_types = {"ArrayProperty", "MapProperty", "StructProperty", "SetProperty"}
        for prop in self._player_props():
            if prop["_type"] in container_types or not _is_scalar(prop.get("value")):
                continue
            name = _short_name(prop["_name"])
            rows.append(EditRow(
                f"overview:{name}",
                (name, _display_value(prop["value"])),
                lambda p=prop: p["value"],
                lambda value, p=prop: p.__setitem__("value", value),
            ))
        return rows

    def _inventory_rows(self):
        inventory = self._find_prop("runtimeInventory")
        rows = []
        if not inventory:
            return rows
        for idx, item_props in enumerate(inventory["value"]):
            name_prop = next((p for p in item_props if _short_name(p["_name"]) == "name"), None)
            amount_prop = next((p for p in item_props if _short_name(p["_name"]) == "amount"), None)
            if not name_prop or not amount_prop:
                continue
            name = str(name_prop["value"])
            rows.append(EditRow(
                f"inventory:{idx}",
                (name, _display_value(amount_prop["value"])),
                lambda p=amount_prop: p["value"],
                lambda value, n=name, p=amount_prop: self._set_inventory_amount(n, p, value),
            ))
        return rows

    def _currency_rows(self):
        """Only display game-created money records. Never guess currency IDs."""
        inventory = self._find_prop("runtimeInventory")
        rows = []
        if not inventory:
            return rows
        for idx, item_props in enumerate(inventory["value"]):
            name_prop = next((p for p in item_props if _short_name(p["_name"]) == "name"), None)
            amount_prop = next((p for p in item_props if _short_name(p["_name"]) == "amount"), None)
            if not name_prop or not amount_prop:
                continue
            name = str(name_prop["value"])
            if not (name.lower().startswith("money") or "candle" in name.lower()):
                continue
            rows.append(EditRow(
                f"currency:{idx}",
                (name, _display_value(amount_prop["value"])),
                lambda p=amount_prop: p["value"],
                lambda value, n=name, p=amount_prop: self._set_inventory_amount(n, p, value),
            ))
        return rows

    def _level_rows(self):
        challenges = self._find_prop("challenges")
        rows = []
        if not challenges:
            return rows
        for item in challenges["value"]["items"]:
            key = str(item["key"])
            linked = ""
            amount_prop = None
            if key.startswith("item") and key.endswith("Lvl"):
                amount_prop = self._find_inventory_amount_prop(key[:-3])
                if amount_prop is not None:
                    linked = _display_value(amount_prop["value"])

            # Frost/Cactus are special in Frostburn-era saves: itemIceLvl and
            # itemCactusLvl are challenge/progression counters and may be stale.
            # Once the game has created itemIce/itemCactus in runtimeInventory,
            # the actual in-game level is derived from that XP amount. Display
            # and edit the effective XP-backed level instead of the counter.
            if key in ("itemIceLvl", "itemCactusLvl") and amount_prop is not None:
                rows.append(EditRow(
                    f"levels:{key}",
                    (key, linked, _display_value(self._level_from_amount(int(amount_prop["value"])))),
                    lambda p=amount_prop: self._level_from_amount(int(p["value"])),
                    lambda value, it=item, p=amount_prop: self._set_effective_magic_level(it, p, value),
                ))
                continue

            rows.append(EditRow(
                f"levels:{key}",
                (key, linked, _display_value(item["value"])),
                lambda it=item: it["value"],
                lambda value, it=item: self._set_challenge_value(it, value),
            ))
        return rows

    def _upgrade_rows(self):
        upgrades = self._find_prop("itemsUpgrades")
        rows = []
        if not upgrades:
            return rows
        for item in upgrades["value"]["items"]:
            item_name = str(item["key"])
            tweaks = next((p for p in item["value"] if _short_name(p["_name"]) == "tweaks"), None)
            if not tweaks:
                continue
            for tweak in tweaks["value"]["items"]:
                upgrade_name = str(tweak["key"])
                rows.append(EditRow(
                    f"upgrades:{item_name}:{upgrade_name}",
                    (item_name, upgrade_name, _display_value(tweak["value"])),
                    lambda it=tweak: it["value"],
                    lambda value, it=tweak: it.__setitem__("value", value),
                ))
        return rows

    def _joker_rows(self):
        jokers = self._find_prop("itemJokers")
        rows = []
        if not jokers:
            return rows
        for item in jokers["value"]["items"]:
            item_name = str(item["key"])
            for prop in item["value"]:
                short = _short_name(prop["_name"])
                value = prop.get("value")
                if _is_scalar(value):
                    rows.append(EditRow(
                        f"jokers:{item_name}:{short}",
                        (item_name, short, _display_value(value)),
                        lambda p=prop: p["value"],
                        lambda new, p=prop: p.__setitem__("value", new),
                    ))
                elif isinstance(value, list):
                    for idx, joker_name in enumerate(value):
                        rows.append(EditRow(
                            f"jokers:{item_name}:{short}:{idx}",
                            (item_name, f"{short}[{idx}]", _display_value(joker_name)),
                            lambda v=value, i=idx: v[i],
                            lambda new, v=value, i=idx: v.__setitem__(i, new),
                        ))
        return rows

    def _reward_rows(self):
        rewards = self._find_prop("rewardedChallenges")
        rows = []
        if not rewards:
            return rows
        for idx, value in enumerate(rewards["value"]):
            rows.append(EditRow(
                f"rewards:{idx}",
                (str(idx), _display_value(value)),
                lambda v=rewards["value"], i=idx: v[i],
                lambda new, v=rewards["value"], i=idx: v.__setitem__(i, new),
            ))
        return rows

    def _other_rows(self):
        covered = {
            "versionId", "selectedPlayerSkin", "selectedMountSkin", "specialWeaponElement",
            "selectedSpellA", "selectedSpellB", "selectedSpellC", "unlockedDifficulties",
            "selectedEmoteA", "selectedEmoteB", "selectedEmoteC", "selectedEmoteD",
            "selectedItemA", "selectedItemB", "itemsUpgrades", "itemJokers",
            "runtimeInventory", "challenges", "rewardedChallenges", "title",
        }
        rows: list[EditRow] = []
        for prop in self._player_props():
            if _short_name(prop["_name"]) not in covered:
                self._collect_scalar_rows(prop.get("value"), _short_name(prop["_name"]), rows)
        if not rows:
            rows.append(EditRow("other:none", (I18N.t("msg_no_uncategorized"), ""), lambda: "", lambda _v: None))
        return rows

    def _collect_scalar_rows(self, value, path: str, rows: list[EditRow]):
        if _is_scalar(value):
            rows.append(EditRow(f"other:{path}", (path, _display_value(value)), lambda v=value: v, lambda _v: None))
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                item_path = f"{path}[{idx}]"
                if _is_scalar(item):
                    rows.append(EditRow(
                        f"other:{item_path}",
                        (item_path, _display_value(item)),
                        lambda v=value, i=idx: v[i],
                        lambda new, v=value, i=idx: v.__setitem__(i, new),
                    ))
                elif isinstance(item, list):
                    for prop in item:
                        self._collect_scalar_rows(prop.get("value"), f"{item_path}.{_short_name(prop['_name'])}", rows)
                else:
                    self._collect_scalar_rows(item, item_path, rows)
        elif isinstance(value, dict):
            for key, item in value.items():
                self._collect_scalar_rows(item, f"{path}.{key}", rows)

    def _set_challenge_value(self, item: dict, value):
        item["value"] = value
        key = str(item.get("key", ""))
        if key.startswith("item") and key.endswith("Lvl") and isinstance(value, int):
            item_name = key[:-3]
            amount_prop = self._find_inventory_amount_prop(item_name)
            if amount_prop is not None:
                old_amount = int(amount_prop.get("value", 0))
                new_amount = self._amount_for_level(value, old_amount)
                amount_prop["value"] = min(new_amount, INT32_MAX)
            elif item_name in ("itemIce", "itemCactus"):
                # Do not invent a runtimeInventory row. v6 proved that doing
                # so makes the game reject otherwise valid saves.
                self.status_var.set(
                    f"{item_name}: level counter changed, but no game-created XP record exists; "
                    "XP was left untouched to keep the save valid."
                )

    def _set_effective_magic_level(self, challenge_item: dict, amount_prop: dict, value):
        """Set a Frost/Cactus level through its game-created XP record.

        Never creates inventory entries.  The XP remainder is preserved so a
        level edit does not unnecessarily erase legitimate progress within the
        level.  The challenge counter is synchronized for consistency, but the
        runtimeInventory amount is the authoritative gameplay value.
        """
        level = max(1, int(value))
        old_amount = int(amount_prop.get("value", 0))
        amount_prop["value"] = min(self._amount_for_level(level, old_amount), INT32_MAX)
        challenge_item["value"] = level

    def _set_inventory_amount(self, item_name: str, amount_prop: dict, value):
        amount_prop["value"] = value
        if not isinstance(value, int):
            return
        level_item = self._find_challenge_item(f"{item_name}Lvl")
        if level_item is not None:
            level_item["value"] = self._level_from_amount(value)

    def _level_from_amount(self, amount: int) -> int:
        return max(1, (max(amount, 0) + 999) // 1000)

    def _amount_for_level(self, level: int, current_amount: int) -> int:
        progress_into_level = max(current_amount, 0) % 1000
        if progress_into_level == 0 and current_amount > 0:
            progress_into_level = 1000
        return max(level - 1, 0) * 1000 + progress_into_level

    def _find_inventory_amount_prop(self, item_name: str) -> dict | None:
        # Never synthesize runtimeInventory entries. Frostburn-era saves may
        # use either the legacy internal Ice name or the displayed Frost name,
        # so recognize both only when the game has already created the record.
        aliases = {
            "itemIce": ("itemIce", "itemFrost"),
            "itemFrost": ("itemFrost", "itemIce"),
            "itemCactus": ("itemCactus",),
        }.get(item_name, (item_name,))
        inventory = self._find_prop("runtimeInventory")
        if not inventory:
            return None
        for item_props in inventory["value"]:
            name_prop = next((p for p in item_props if _short_name(p["_name"]) == "name"), None)
            if name_prop and name_prop.get("value") in aliases:
                return next((p for p in item_props if _short_name(p["_name"]) == "amount"), None)
        return None

    def _find_challenge_item(self, key: str) -> dict | None:
        challenges = self._find_prop("challenges")
        if not challenges:
            return None
        return next((item for item in challenges["value"]["items"] if item.get("key") == key), None)

    # ---- file drop (Windows shell32 hook) -------------------------------
    def _install_file_drop(self):
        if sys.platform != "win32":
            self.status_var.set(I18N.t("msg_drag_drop_hint"))
            return

        self.update_idletasks()
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        lresult_type = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
        wndproc_type = ctypes.WINFUNCTYPE(
            lresult_type, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        )
        user32.CallWindowProcW.restype = lresult_type
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM]
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            set_window_long = user32.SetWindowLongPtrW
        else:
            set_window_long = user32.SetWindowLongW
        set_window_long.restype = ctypes.c_void_p
        set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                path = self._query_drop_path(wparam)
                shell32.DragFinish(wparam)
                if path:
                    self.after(0, lambda p=path: self._load_dropped_file(p))
                return 0
            old_proc = self._drop_old_procs.get(int(hwnd))
            if old_proc:
                return user32.CallWindowProcW(old_proc, hwnd, msg, wparam, lparam)
            return 0

        self._drop_wndproc = wndproc_type(wndproc)
        new_proc = ctypes.cast(self._drop_wndproc, ctypes.c_void_p)
        hwnd = int(self.winfo_id())
        if hwnd in self._drop_hwnds:
            return
        old_proc = set_window_long(hwnd, GWL_WNDPROC, new_proc)
        if old_proc:
            self._drop_old_procs[hwnd] = int(old_proc)
            self._drop_hwnds.add(hwnd)
            shell32.DragAcceptFiles(hwnd, True)

    def _query_drop_path(self, hdrop) -> str:
        shell32 = ctypes.windll.shell32
        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        if count < 1:
            return ""
        length = shell32.DragQueryFileW(hdrop, 0, None, 0) + 1
        buf = ctypes.create_unicode_buffer(length)
        shell32.DragQueryFileW(hdrop, 0, buf, length)
        return buf.value

    def _load_dropped_file(self, path: str):
        save_path = Path(path)
        if save_path.suffix.lower() != ".save":
            messagebox.showwarning(I18N.t("msg_unsupported_file"), I18N.t("msg_drop_save_only"))
            return
        self.load_save(save_path)

    def _on_close(self):
        if sys.platform == "win32" and self._drop_wndproc is not None:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                set_window_long = user32.SetWindowLongPtrW
            else:
                set_window_long = user32.SetWindowLongW
            set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            for hwnd, old_proc in list(self._drop_old_procs.items()):
                shell32.DragAcceptFiles(hwnd, False)
                set_window_long(hwnd, GWL_WNDPROC, ctypes.c_void_p(old_proc))
        self.destroy()


def main():
    SaveEditor().mainloop()


if __name__ == "__main__":
    main()
