"""Stack BMP crops vertically into one image so several frames can be compared
with a single look. Only used for the T1-C evidence frames.

    montage.py <out.bmp> <x> <y> <w> <h> <src1.bmp> <src2.bmp> ...
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def read_bmp(path: Path) -> tuple[int, int, bytes]:
    raw = path.read_bytes()
    offset = struct.unpack_from("<I", raw, 10)[0]
    width, height = struct.unpack_from("<ii", raw, 18)
    stride = (width * 3 + 3) & ~3
    return width, abs(height), raw[offset : offset + stride * abs(height)]


def main(argv: list[str]) -> int:
    out = Path(argv[1])
    x, y, w, h = (int(v) for v in argv[2:6])
    sources = [Path(p) for p in argv[6:]]

    tile_stride = (w * 3 + 3) & ~3
    out_stride = tile_stride
    out_h = h * len(sources)
    canvas = bytearray(out_stride * out_h)

    for index, path in enumerate(sources):
        width, height, pixels = read_bmp(path)
        stride = (width * 3 + 3) & ~3
        for row in range(h):
            src_row = height - 1 - (y + row)  # source is bottom-up after crop.py? no: top-down
            src_row = y + row
            if src_row >= height:
                break
            src = src_row * stride + x * 3
            dst = (h * index + row) * out_stride
            canvas[dst : dst + w * 3] = pixels[src : src + w * 3]

    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(canvas), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, -out_h, 1, 24, 0, len(canvas), 0, 0, 0, 0)
    out.write_bytes(header + info + bytes(canvas))
    print("saved", out, f"{w}x{out_h}", "frames", len(sources))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
