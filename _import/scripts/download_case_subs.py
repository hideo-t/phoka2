"""Download missing case sub-images (-02, -03) per truth_v2.

Skip-if-exists: never overwrite files already on disk (PR#2's -01 stays).
Crawl-Delay: 5s between fetches per robots.txt.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from PIL import Image

ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRUTH = os.path.join(ROOT, "_import", "review", "cases_image_truth_v2.json")
OUT   = os.path.join(ROOT, "images", "cases")

MAX_W_LARGE = 1200
MAX_W_SMALL = 600
QUALITY     = 82
METHOD      = 6
CRAWL_DELAY = 5.0


def load_truth():
    with open(TRUTH, encoding="utf-8") as f:
        return json.load(f)


def build_url(tmpl: str, path: str, h: str, v: str) -> str:
    return tmpl.format(path=path, hash=h, version=v)


def fit_width(img: Image.Image, max_w: int) -> Image.Image:
    w, h = img.size
    if w <= max_w:
        return img
    new_h = round(h * max_w / w)
    return img.resize((max_w, new_h), Image.LANCZOS)


def _ascii_url(u: str) -> str:
    """Percent-encode non-ASCII chars in the path so HTTP headers stay latin-1 safe."""
    parts = urllib.parse.urlsplit(u)
    quoted_path = urllib.parse.quote(parts.path, safe="/")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, quoted_path, parts.query, parts.fragment))


def fetch_jpeg(url: str, ua: str, referer: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "image/*,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": _ascii_url(referer),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def save_webp_pair(raw: bytes, slug: str, nn: int):
    im = Image.open(io.BytesIO(raw))
    if im.mode != "RGB":
        im = im.convert("RGB")
    large = fit_width(im, MAX_W_LARGE)
    small = fit_width(im, MAX_W_SMALL)
    p_large = os.path.join(OUT, f"{slug}-{nn:02d}.webp")
    p_small = os.path.join(OUT, f"{slug}-{nn:02d}@600w.webp")
    large.save(p_large, "WEBP", quality=QUALITY, method=METHOD)
    small.save(p_small, "WEBP", quality=QUALITY, method=METHOD)
    return im.size, large.size, small.size, os.path.getsize(p_large), os.path.getsize(p_small)


def main():
    truth = load_truth()
    tmpl  = truth["url_template"]
    path  = truth["jimdo_path_prefix"]
    ua    = truth["user_agent"]
    referer = truth["referer"]
    delay = float(truth.get("crawl_delay_seconds", 5))

    os.makedirs(OUT, exist_ok=True)

    n_skip = 0
    n_fetched = 0
    n_target_subs = 0
    first_fetch = True

    for case in truth["cases"]:
        slug = case["slug"]
        urls = case["top3"]
        print(f"=== {slug}  (top3={len(urls)}, total_on_orig={case['total_count']}) ===")
        for idx, item in enumerate(urls, start=1):
            p_large = os.path.join(OUT, f"{slug}-{idx:02d}.webp")
            p_small = os.path.join(OUT, f"{slug}-{idx:02d}@600w.webp")
            if idx >= 2:
                n_target_subs += 1
            if os.path.exists(p_large) and os.path.exists(p_small):
                print(f"  skip   {slug}-{idx:02d}  (exists)")
                n_skip += 1
                continue

            url = build_url(tmpl, path, item["hash"], item["version"])
            # Honor Crawl-Delay before every fetch except the very first
            if not first_fetch:
                time.sleep(delay)
            first_fetch = False
            try:
                raw = fetch_jpeg(url, ua, referer)
            except Exception as e:
                print(f"  ERR    {slug}-{idx:02d}  fetch failed: {e}", file=sys.stderr)
                continue
            try:
                src_sz, l_sz, s_sz, l_b, s_b = save_webp_pair(raw, slug, idx)
            except Exception as e:
                print(f"  ERR    {slug}-{idx:02d}  decode failed: {e}", file=sys.stderr)
                continue
            n_fetched += 1
            print(
                f"  ok     {slug}-{idx:02d}  src {src_sz[0]}x{src_sz[1]}"
                f" -> {l_sz[0]}x{l_sz[1]} ({l_b//1024}KB) + {s_sz[0]}x{s_sz[1]} ({s_b//1024}KB)"
            )

    print()
    print(f"--- summary ---")
    print(f"  fetched: {n_fetched}")
    print(f"  skipped (already on disk): {n_skip}")
    print(f"  sub-image slots to fill (-02/-03): {n_target_subs}")


if __name__ == "__main__":
    main()
