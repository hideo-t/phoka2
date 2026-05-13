"""Re-fetch case images from jimcdn using the human-verified truth mapping.

Source of truth: _import/review/cases_image_truth.json
For each slug, fetch min(3, len(image_urls)) source JPEGs, convert to two
WebP variants (1200w main, 600w mobile), and write to images/cases/{slug}-NN*.webp.

Robots.txt courtesy: 5s pause between fetches (Crawl-Delay).
"""
import io
import json
import os
import sys
import time
import urllib.request
from PIL import Image

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = os.path.join(ROOT, "_import", "review", "cases_image_truth.json")
OUT   = os.path.join(ROOT, "images", "cases")

MAX_PER_CASE = 3
MAX_W_LARGE  = 1200
MAX_W_SMALL  = 600
QUALITY      = 82
METHOD       = 6
CRAWL_DELAY  = 5.0

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
REFERER = "https://www.parkhomes-okinawa.com/"

# Jimdo CDN rejects bare /path/... requests; the public URLs all go through
# /transf/dimension=...:format=jpg/ so we wrap each raw URL to match.
DIMENSION = "1920x10000"


def to_transf_url(raw_url: str) -> str:
    marker = "/app/cms/image/path/"
    if "/transf/" in raw_url:
        return raw_url
    if marker not in raw_url:
        return raw_url
    return raw_url.replace(
        "/app/cms/image/path/",
        f"/app/cms/image/transf/dimension={DIMENSION}:format=jpg/path/",
    )


def fit_width(img: Image.Image, max_w: int) -> Image.Image:
    w, h = img.size
    if w <= max_w:
        return img
    new_h = round(h * max_w / w)
    return img.resize((max_w, new_h), Image.LANCZOS)


def fetch_jpeg(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": REFERER,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(TRUTH, encoding="utf-8") as f:
        truth = json.load(f)

    summary_rows = []
    total_files = 0
    total_bytes = 0

    for slug, data in truth.items():
        urls = data["image_urls"][:MAX_PER_CASE]
        n_target = min(MAX_PER_CASE, len(data["image_urls"]))
        print(f"=== {slug} ({n_target} image{'s' if n_target>1 else ''}) ===")
        ok = 0
        for idx, raw_url in enumerate(urls, start=1):
            url = to_transf_url(raw_url)
            try:
                raw = fetch_jpeg(url)
            except Exception as e:
                print(f"  ERR    {slug}-{idx:02d}  fetch failed: {e}", file=sys.stderr)
                continue

            try:
                im = Image.open(io.BytesIO(raw))
                if im.mode != "RGB":
                    im = im.convert("RGB")
            except Exception as e:
                print(f"  ERR    {slug}-{idx:02d}  open failed: {e}", file=sys.stderr)
                continue

            large = fit_width(im, MAX_W_LARGE)
            small = fit_width(im, MAX_W_SMALL)

            p_large = os.path.join(OUT, f"{slug}-{idx:02d}.webp")
            p_small = os.path.join(OUT, f"{slug}-{idx:02d}@600w.webp")
            large.save(p_large, "WEBP", quality=QUALITY, method=METHOD)
            small.save(p_small, "WEBP", quality=QUALITY, method=METHOD)

            sz_l = os.path.getsize(p_large)
            sz_s = os.path.getsize(p_small)
            total_bytes += sz_l + sz_s
            total_files += 2
            ok += 1
            print(
                f"  ok     {slug}-{idx:02d}  src {im.size[0]}x{im.size[1]}"
                f"  -> {large.size[0]}x{large.size[1]} ({sz_l//1024}KB)"
                f" + {small.size[0]}x{small.size[1]} ({sz_s//1024}KB)"
            )
            # Crawl delay only when more fetches will follow
            if idx < len(urls):
                time.sleep(CRAWL_DELAY)
        summary_rows.append((slug, ok, n_target))
        # Pause between cases too
        time.sleep(CRAWL_DELAY)

    print()
    print(f"--- summary: {total_files} files, {total_bytes/1024:.0f} KB ({total_bytes/1024/1024:.2f} MB) ---")
    for slug, ok, target in summary_rows:
        flag = "ok" if ok == target else "PARTIAL"
        print(f"  {flag:7s}  {slug:22s}  {ok}/{target} images fetched")


if __name__ == "__main__":
    main()
