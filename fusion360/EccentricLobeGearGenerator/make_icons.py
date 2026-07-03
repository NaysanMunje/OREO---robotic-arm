"""Generate 16x16 and 32x32 PNG icons for the Fusion add-in."""
import struct
import zlib
import os

def _chunk(tag, data):
    return (
        struct.pack('>I', len(data))
        + tag
        + data
        + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, width, height, rgba):
    r, g, b, a = rgba
    row = b'\x00' + bytes([r, g, b, a]) * width
    raw = row * height
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png = (
        b'\x89PNG\r\n\x1a\n'
        + _chunk(b'IHDR', ihdr)
        + _chunk(b'IDAT', zlib.compress(raw, 9))
        + _chunk(b'IEND', b'')
    )
    with open(path, 'wb') as f:
        f.write(png)


if __name__ == '__main__':
    res = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
    os.makedirs(res, exist_ok=True)
    color = (26, 127, 78, 255)  # green
    write_png(os.path.join(res, '16x16.png'), 16, 16, color)
    write_png(os.path.join(res, '32x32.png'), 32, 32, color)
    print('Icons written.')
