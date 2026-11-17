#!/usr/bin/env python3
"""On-screen jukebox status box (macro pad key F24).

Started by jukebox-status.py when F24 is pressed; F24 again closes it, and it
closes by itself after SHOW_SECONDS. It floats over Fruitbox without taking
the keyboard, so the keypad and macro pad keep working while it is up.

Test from SSH:
  DISPLAY=:0 python3 /usr/local/bin/jukebox-status-overlay.py http://127.0.0.1/api/summary
"""
VERSION = "1.0"   # bump on every change; the status page shows it

import json, re, subprocess, sys, time, urllib.request

SHOW_SECONDS = 0      # 0 = stay up until the key is pressed again; or seconds before it closes itself
SCREEN = "primary"     # "primary" = the main (ultrawide) screen, or an output name like HDMI-2
WIDTH_PCT = 55        # width, % of the screen; the height fits the contents

BG, PANEL, LINE, TEXT, DIM, RED, AMBER, OK = ("#120d0b", "#1d1512", "#3a2a22", "#f3e9df",
                                              "#b29d8c", "#e8392b", "#ffb627", "#7ed957")


def screen_box():
    """x, y, w, h of the screen to draw on."""
    try:
        xr = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=4).stdout
    except (OSError, subprocess.SubprocessError):
        xr = ""
    found = None
    for ln in xr.splitlines():
        m = re.match(r"^(\S+) connected( primary)?\s*(\d+)x(\d+)\+(\d+)\+(\d+)", ln)
        if not m:
            continue
        box = tuple(int(m.group(i)) for i in (5, 6, 3, 4))
        if (SCREEN == "primary" and m.group(2)) or m.group(1) == SCREEN:
            return box
        found = found or box
    return found


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except Exception as ex:
        return {"problems": [f"Status page not answering: {ex}"], "rows": []}


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1/api/summary"
    import threading
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()                         # stay hidden until it's placed (no stray window)
    root.overrideredirect(True)             # no title bar, no keyboard focus
    sx, sy, sw, sh = screen_box() or (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    w = sw * WIDTH_PCT // 100
    k = sw / 3440                           # sizes below are for the 3440-wide main screen
    px = lambda n: -max(10, int(n * k))     # negative = pixels, so it looks the same on any Pi
    f_title = ("DejaVu Sans", px(34), "bold")
    f_head = ("DejaVu Sans", px(24), "bold")
    f_text = ("DejaVu Sans", px(20))
    root.configure(bg=LINE)
    root.attributes("-topmost", True)

    outer = tk.Frame(root, bg=BG)
    outer.pack(fill="both", expand=True, padx=3, pady=3)
    top = tk.Frame(outer, bg=BG)
    top.pack(fill="x", padx=20, pady=(12, 4))
    tk.Label(top, text="JUKEBOX STATUS", font=f_title, fg=AMBER, bg=BG).pack(side="left")
    clock = tk.Label(top, font=f_text, fg=DIM, bg=BG)
    clock.pack(side="right")
    body = tk.Frame(outer, bg=BG)
    body.pack(fill="both", expand=True, padx=14, pady=(4, 14))
    for c in range(3):
        body.grid_columnconfigure(c, weight=1, uniform="col")
    started = time.monotonic()
    COLOURS = {"ok": "#8fae7e", "warn": "#c9a45c", "bad": "#c9675c"}
    cells = {}                              # (section, row) -> value label, updated in place
    state = {"probs": None, "layout": None, "data": None, "placed": False}
    pb = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=2)
    pb.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

    def build(rows):
        for c in list(body.winfo_children()):
            if c is not pb:
                c.destroy()
        cells.clear()
        for i, (title, items) in enumerate(rows):
            box = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
            box.grid(row=1 + i // 3, column=i % 3, sticky="nsew", padx=5, pady=5)
            tk.Label(box, text=title.upper(), font=f_head, fg=AMBER, bg=PANEL, anchor="w").grid(
                row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 2))
            for r, row in enumerate(items, 1):
                tk.Label(box, text=row[0], font=f_text, fg=DIM, bg=PANEL, anchor="w").grid(
                    row=r, column=0, sticky="nw", padx=(10, 8))
                v = tk.Label(box, font=f_text, bg=PANEL, anchor="w", justify="left",
                             wraplength=int(w / 3 * 0.5))
                v.grid(row=r, column=1, sticky="w", padx=(0, 10))
                cells[(i, r)] = v
            tk.Frame(box, bg=PANEL, height=6).grid(row=len(items) + 1, column=0)

    def show(data):
        probs = data.get("problems") or []
        if probs != state["probs"]:             # only rebuilt when the list changes
            state["probs"] = probs
            for c in pb.winfo_children():
                c.destroy()
            pb.configure(highlightbackground="#5e4632" if probs else LINE)
            for p in probs[:6] or ["Nothing wrong found."]:
                tk.Label(pb, text=("•  " + p) if probs else p, font=f_text, bg=PANEL, anchor="w",
                         fg=COLOURS["warn"] if probs else COLOURS["ok"], justify="left",
                         wraplength=w - 100).pack(fill="x", padx=12, pady=1)
        rows = data.get("rows", [])
        layout = [(t, [r[0] for r in items]) for t, items in rows]
        if layout != state["layout"]:
            state["layout"] = layout
            build(rows)
        for i, (title, items) in enumerate(rows):
            for r, row in enumerate(items, 1):
                cells[(i, r)].configure(text=str(row[1]),
                                        fg=COLOURS.get(row[2] if len(row) > 2 else None, TEXT))
        if not state["placed"]:                 # centre it once its size is known, then show it
            root.update_idletasks()
            h = root.winfo_reqheight()
            root.geometry(f"{w}x{h}+{sx + (sw - w) // 2}+{sy + max(0, (sh - h) // 2)}")
            root.deiconify()
            state["placed"] = True
        root.lift()

    def fetcher():                              # network fetch off the screen thread: no blank redraws
        while True:
            state["data"] = fetch(url)
            time.sleep(3)

    def tick():
        left = SHOW_SECONDS - int(time.monotonic() - started)
        if SHOW_SECONDS and left <= 0:
            root.destroy()
            return
        note = f"closes in {left} s  (press again to close)" if SHOW_SECONDS else "press the i key again to close"
        clock.configure(text=time.strftime("%H:%M:%S") + "   ·   " + note)
        if state["data"] is not None:
            data, state["data"] = state["data"], None
            show(data)
        root.after(250, tick)

    threading.Thread(target=fetcher, daemon=True).start()
    tick()
    root.mainloop()


if __name__ == "__main__":
    main()
