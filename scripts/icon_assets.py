"""Deterministic ICO container: original PNG entries, no resampling or redesign."""
from pathlib import Path
import struct


def windows_icon(icons: Path, output: Path):
    entries = [(n, (icons / f"PNG/Default/IliasSync-Default-{n}.png").read_bytes())
               for n in (16, 32, 64, 128, 256)]
    offset = 6 + 16 * len(entries)
    directory = []
    for size, data in entries:
        directory.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(struct.pack("<HHH", 0, 1, len(entries)) + b"".join(directory)
                       + b"".join(data for _, data in entries))
    return output
