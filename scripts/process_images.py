"""Convert case images from JPEG (parkhomes_data/images/) to WebP variants.

Output:
  images/cases/{slug}-{idx:02d}.webp        (max width 1200)
  images/cases/{slug}-{idx:02d}@600w.webp   (max width 600)

Settings: quality=82, method=6, aspect ratio preserved, alpha not used.
"""
import json
import os
import sys
from PIL import Image

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURATED  = os.path.join(ROOT, "_import", "review", "cases.curated.json")
OUT_DIR  = os.path.join(ROOT, "images", "cases")

MAX_W_LARGE = 1200
MAX_W_SMALL = 600
QUALITY = 82
METHOD = 6


def fit_width(img: Image.Image, max_w: int) -> Image.Image:
    w, h = img.size
    if w <= max_w:
        return img
    new_h = round(h * max_w / w)
    return img.resize((max_w, new_h), Image.LANCZOS)


def save_webp(img: Image.Image, out_path: str):
    img.save(out_path, "WEBP", quality=QUALITY, method=METHOD)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(CURATED, encoding="utf-8") as f:
        cases = json.load(f)

    total_bytes_out = 0
    total_files = 0
    for c in cases:
        slug = c["slug"]
        for idx, img_meta in enumerate(c["images"], start=1):
            src = img_meta["src_local"]
            if not os.path.exists(src):
                print(f"  MISS  {slug}-{idx:02d}: {src}", file=sys.stderr)
                continue
            try:
                im = Image.open(src)
                if im.mode != "RGB":
                    im = im.convert("RGB")
            except Exception as e:
                print(f"  ERR   {slug}-{idx:02d}: {e}", file=sys.stderr)
                continue

            large = fit_width(im, MAX_W_LARGE)
            small = fit_width(im, MAX_W_SMALL)

            p_large = os.path.join(OUT_DIR, f"{slug}-{idx:02d}.webp")
            p_small = os.path.join(OUT_DIR, f"{slug}-{idx:02d}@600w.webp")
            save_webp(large, p_large)
            save_webp(small, p_small)

            for p in (p_large, p_small):
                sz = os.path.getsize(p)
                total_bytes_out += sz
                total_files += 1
            print(
                f"  ok    {slug}-{idx:02d}  src {im.size[0]}x{im.size[1]}  "
                f"-> {large.size[0]}x{large.size[1]} ({os.path.getsize(p_large)//1024}KB) "
                f"+ {small.size[0]}x{small.size[1]} ({os.path.getsize(p_small)//1024}KB)"
            )

    print(f"\nwrote: {total_files} files, total {total_bytes_out//1024} KB ({total_bytes_out/1024/1024:.2f} MB) to {OUT_DIR}")


if __name__ == "__main__":
    main()
