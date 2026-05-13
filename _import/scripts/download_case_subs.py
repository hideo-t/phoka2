"""Download missing case images per truth_v{N}.

Reads the newest truth file present (prefers v4 -> v2). Truth v2 carries a
single top-level "referer"; truth v4 carries "referer_by_page_source" keyed
by stringified page_source so different source pages get their correct
HTTP Referer.

Skip-if-exists: never overwrite files already on disk.
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
TRUTH_V4 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v4.json")
TRUTH_V2 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v2.json")
OUT      = os.path.join(ROOT, "images", "cases")

MAX_W_LARGE = 1200
MAX_W_SMALL = 600
QUALITY     = 82
METHOD      = 6
CRAWL_DELAY = 5.0


def load_truth():
    path = TRUTH_V4 if os.path.exists(TRUTH_V4) else TRUTH_V2
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def resolve_referer(truth: dict, case: dict) -> str:
    """v2 has a single top-level 'referer'; v4 has 'referer_by_page_source'."""
    rbps = truth.get("referer_by_page_source")
    if rbps:
        return rbps.get(str(case.get("page_source", "1")), next(iter(rbps.values())))
    return truth["referer"]


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
    truth, truth_path = load_truth()
    tmpl  = truth["url_template"]
    path  = truth["jimdo_path_prefix"]
    ua    = truth["user_agent"]
    delay = float(truth.get("crawl_delay_seconds", 5))

    os.makedirs(OUT, exist_ok=True)
    print(f"truth: {os.path.basename(truth_path)}  ({len(truth['cases'])} cases)")

    n_skip = 0
    n_fetched = 0
    n_target_subs = 0
    first_fetch = True

    for case in truth["cases"]:
        slug = case["slug"]
        urls = case["top3"]
        referer = resolve_referer(truth, case)
        ps = case.get("page_source", 1)
        print(f"=== {slug}  page={ps} top3={len(urls)} total={case['total_count']} ===")
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

    # Final disk inventory
    total_on_disk = sum(1 for f in os.listdir(OUT) if f.endswith(".webp"))
    expected = 2 * sum(len(c["top3"]) for c in truth["cases"])
    print()
    print(f"--- summary ---")
    print(f"  fetched: {n_fetched}")
    print(f"  skipped (already on disk): {n_skip}")
    print(f"  sub-image slots considered (-02/-03): {n_target_subs}")
    print(f"  total WebP on disk: {total_on_disk}  (expected: {expected})")


if __name__ == "__main__":
    main()
