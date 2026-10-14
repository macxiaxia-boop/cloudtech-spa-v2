"""Generate actual responsive WebP assets from the original GitHub-tracked JPEGs.

Source images remain untouched. Generation fails visibly rather than pointing
the browser at missing optimized files. Works with Pillow 10-12.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public" / "images"
OUTPUT = SOURCE / "optimized"
IMAGES = ("ai-team", "dashboard-preview", "opc-hero")
SIZES = (480, 768, 1024)


def generate(source: Path, target_dir: Path, basename: str) -> dict[int, int]:
    if not source.is_file():
        raise FileNotFoundError(f"Missing original source: {source}")
    target_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    with Image.open(source) as raw:
        if raw.format not in {"JPEG", "PNG"}:
            raise ValueError(f"Unsupported image format: {source}")
        original = ImageOps.exif_transpose(raw).convert("RGB")
        if original.size != (1024, 1024):
            raise ValueError(f"Reaudit source dimensions before resizing {source}: {original.size}")
        for width in SIZES:
            optimized = original.resize((width, width), Image.Resampling.LANCZOS)
            dest = target_dir / f"{basename}-{width}.webp"
            optimized.save(dest, "WEBP", quality=70, method=6, exact=False)
            with Image.open(dest) as output_check:
                if output_check.format != "WEBP" or output_check.size != (width, width):
                    raise RuntimeError(f"Invalid output: {dest}")
            written[width] = dest.stat().st_size
    return written


def main() -> None:
    total_before = 0
    total_after = 0
    for name in IMAGES:
        original = SOURCE / f"{name}.jpeg"
        stats = generate(original, OUTPUT, name)
        source_bytes = original.stat().st_size
        total_before += source_bytes
        total_after += stats[768]
        print(f"{name}: JPEG={source_bytes}, WebP480/768/1024={stats[480]}/{stats[768]}/{stats[1024]}")
    print(f"Responsive WebP 768w transfer vs three original JPEGs: {total_after}/{total_before} bytes")


if __name__ == "__main__":
    main()
