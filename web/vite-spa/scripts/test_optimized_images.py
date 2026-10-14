"""Verify built WebP files really exist, have dimensions, and save bytes."""
from pathlib import Path
from PIL import Image
from generate_responsive_images import ROOT, IMAGES, SIZES, SOURCE, OUTPUT


def main():
    total_src = 0
    total_768 = 0
    for name in IMAGES:
        original = SOURCE / f"{name}.jpeg"
        with Image.open(original) as raw:
            assert raw.format == "JPEG" and raw.size == (1024, 1024), name
        total_src += original.stat().st_size
        for size in SIZES:
            file = OUTPUT / f"{name}-{size}.webp"
            assert file.exists(), f"Missing optimized asset: {file}"
            with Image.open(file) as image:
                assert image.format == "WEBP" and image.size == (size, size), file
            assert file.stat().st_size > 100, file
        total_768 += (OUTPUT / f"{name}-768.webp").stat().st_size
    print(f"REAL image proof: 9 WebP assets verified; 768w sources={total_768}, originals={total_src}")
    assert total_768 < total_src * 0.8, "Optimized responsive assets are not materially smaller"


if __name__ == "__main__":
    main()
