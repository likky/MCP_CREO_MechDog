"""Capture the desktop to a BMP without extra dependencies (ctypes + GDI32).

Used only to keep a visual record of the dashboard being open after a locked run.
"""

from __future__ import annotations

import ctypes
import struct
import sys
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def capture(path: Path) -> None:
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    screen = user32.GetDC(0)
    memory = gdi32.CreateCompatibleDC(screen)
    bitmap = gdi32.CreateCompatibleBitmap(screen, width, height)
    gdi32.SelectObject(memory, bitmap)

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

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height  # top-down
    header.biPlanes = 1
    header.biBitCount = 24
    header.biCompression = 0

    stride = (width * 3 + 3) & ~3
    size = stride * height
    buffer = ctypes.create_string_buffer(size)
    gdi32.BitBlt(memory, 0, 0, width, height, screen, 0, 0, 0x00CC0020)
    gdi32.GetDIBits(memory, bitmap, 0, height, buffer, ctypes.byref(header), 0)

    file_header = struct.pack("<2sIHHI", b"BM", 14 + 40 + size, 0, 0, 14 + 40)
    # biHeight must stay negative here: the pixels above were requested top-down,
    # and a positive height in the file header makes every viewer show them flipped.
    info = struct.pack(
        "<IiiHHIIiiII",
        40, width, -height, 1, 24, 0, size, 0, 0, 0, 0,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_header + info + buffer.raw)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory)
    user32.ReleaseDC(0, screen)


if __name__ == "__main__":
    capture(Path(sys.argv[1]))
    print("saved", sys.argv[1])
