"""Burst-capture a screen region so a short-lived dashboard state can be caught.

    burst.py <outdir> <x> <y> <w> <h> <count> <interval_ms>

Only the region is captured, so frames stay small enough to take many of them.
"""

from __future__ import annotations

import ctypes
import struct
import sys
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()

SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def grab(x: int, y: int, w: int, h: int, path: Path) -> None:
    screen = user32.GetDC(0)
    memory = gdi32.CreateCompatibleDC(screen)
    bitmap = gdi32.CreateCompatibleBitmap(screen, w, h)
    gdi32.SelectObject(memory, bitmap)
    gdi32.BitBlt(memory, 0, 0, w, h, screen, x, y, 0x00CC0020)

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = w
    header.biHeight = -h
    header.biPlanes = 1
    header.biBitCount = 24
    header.biCompression = 0

    stride = (w * 3 + 3) & ~3
    buffer = ctypes.create_string_buffer(stride * h)
    gdi32.GetDIBits(memory, bitmap, 0, h, buffer, ctypes.byref(header), 0)
    file_header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(buffer), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 24, 0, len(buffer), 0, 0, 0, 0)
    path.write_bytes(file_header + info + buffer.raw)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory)
    user32.ReleaseDC(0, screen)


def main(argv: list[str]) -> int:
    outdir = Path(argv[1])
    x, y, w, h = (int(v) for v in argv[2:6])
    count = int(argv[6])
    interval = int(argv[7]) / 1000.0
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("b_*.bmp"):
        old.unlink()
    started = time.time()
    for index in range(count):
        grab(x, y, w, h, outdir / f"b_{index:03d}.bmp")
        time.sleep(interval)
    print(f"{count} frames in {time.time() - started:.1f}s -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
