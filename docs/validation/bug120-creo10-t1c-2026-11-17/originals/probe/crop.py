"""Crop + integer-scale a BMP so a small dialog can be read/measured without PIL.

    crop.py <src.bmp> <dst.bmp> <x> <y> <w> <h> [scale]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def read_bmp(path: Path) -> tuple[int, int, bytes, int]:
    raw = path.read_bytes()
    data_offset = struct.unpack_from("<I", raw, 10)[0]
    width, height = struct.unpack_from("<ii", raw, 18)
    top_down = height < 0
    height = abs(height)
    return width, height, raw[data_offset:], (data_offset, top_down)


def main(argv: list[str]) -> int:
    src = Path(argv[1])
    dst = Path(argv[2])
    x, y, w, h = (int(v) for v in argv[3:7])
    scale = int(argv[7]) if len(argv) > 7 else 1

    width, height, pixels, _ = read_bmp(src)
    stride = (width * 3 + 3) & ~3

    out_stride = (w * scale * 3 + 3) & ~3
    out = bytearray(out_stride * h * scale)
    for row in range(h * scale):
        src_row = y + row // scale
        for col in range(w * scale):
            src_col = x + col // scale
            offset = src_row * stride + src_col * 3
            target = row * out_stride + col * 3
            out[target : target + 3] = pixels[offset : offset + 3]

    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(out), 0, 0, 54)
    info = struct.pack(
        "<IiiHHIIiiII", 40, w * scale, -(h * scale), 1, 24, 0, len(out), 0, 0, 0, 0
    )
    dst.write_bytes(header + info + bytes(out))
    print("saved", dst, f"{w*scale}x{h*scale}", "from", (x, y, w, h))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
