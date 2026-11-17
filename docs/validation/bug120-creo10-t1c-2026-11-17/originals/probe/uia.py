"""Minimal UI probe for the T1-C cancel sequence (pywin32, no external deps).

Only used to (a) keep a visual record of the Creo dialogs and (b) answer the
second-level "confirm cancel" prompt that Creo raises after `dashInst0.Quit`.

Usage:
    uia.py windows [pid]
    uia.py children "<title substring>"
    uia.py click "<title substring>" "<button text substring>"
    uia.py shot <path.bmp>
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import win32api
import win32con
import win32gui
import win32process

# Creo draws its dialogs with custom controls and runs at 100%+ scaling.
# Declare per-monitor DPI awareness so rects, screenshots and SetCursorPos all
# speak the same (physical) pixel language.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # pragma: no cover - older Windows
    ctypes.windll.user32.SetProcessDPIAware()

CREO_PID = 21724


def visible_windows(pid: int | None = None) -> list[dict]:
    found: list[dict] = []

    def visit(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        wnd_pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        if pid is not None and wnd_pid != pid:
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        found.append(
            {
                "hwnd": hwnd,
                "title": title,
                "class": win32gui.GetClassName(hwnd),
                "pid": wnd_pid,
                "rect": [left, top, right, bottom],
            }
        )
        return True

    win32gui.EnumWindows(visit, None)
    return found


def find_window(title_part: str) -> int:
    needle = title_part.lower()
    candidates = [w for w in visible_windows() if needle in w["title"].lower()]
    if not candidates:
        raise SystemExit(f"no visible window matches {title_part!r}")
    # Prefer the smallest (dialogs beat the main frame).
    candidates.sort(key=lambda w: (w["rect"][2] - w["rect"][0]) * (w["rect"][3] - w["rect"][1]))
    return candidates[0]["hwnd"]


def children(hwnd: int) -> list[dict]:
    found: list[dict] = []

    def visit(child, _):
        left, top, right, bottom = win32gui.GetWindowRect(child)
        found.append(
            {
                "hwnd": child,
                "class": win32gui.GetClassName(child),
                "text": win32gui.GetWindowText(child),
                "id": win32gui.GetDlgCtrlID(child),
                "rect": [left, top, right, bottom],
            }
        )
        return True

    win32gui.EnumChildWindows(hwnd, visit, None)
    return found


def click_button(hwnd: int, text_part: str) -> dict:
    needle = text_part.lower()
    for item in children(hwnd):
        if needle in item["text"].lower():
            target = item["hwnd"]
            left, top, right, bottom = item["rect"]
            center = ((left + right) // 2, (top + bottom) // 2)
            win32gui.SetForegroundWindow(hwnd)
            win32api.SetCursorPos(center)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return {"clicked": item["text"], "hwnd": target, "at": list(center)}
    raise SystemExit(f"no child of hwnd {hwnd} matches {text_part!r}")


def shot(path: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from capture import capture

    capture(path)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    command = argv[1]
    if command == "windows":
        pid = int(argv[2]) if len(argv) > 2 else CREO_PID
        import json

        print(json.dumps(visible_windows(pid), ensure_ascii=False, indent=2))
    elif command == "children":
        hwnd = find_window(argv[2])
        print("window", hwnd, win32gui.GetWindowText(hwnd))
        for item in children(hwnd):
            print(" ", item)
    elif command == "click":
        hwnd = find_window(argv[2])
        print(click_button(hwnd, argv[3]))
    elif command == "focus":
        hwnd = find_window(argv[2])
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        print({"focused": win32gui.GetWindowText(hwnd)})
    elif command == "clickat":
        # Creo's dialogs are custom-drawn: no child HWNDs to target, so the
        # caller has to pass a pixel position read off the screenshot.
        x, y = int(argv[2]), int(argv[3])
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print({"clicked_at": [x, y]})
    elif command == "shot":
        shot(Path(argv[2]))
        print("saved", argv[2])
    else:
        raise SystemExit(f"unknown command {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
