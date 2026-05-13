"""Extract 12 case studies from site_data.json into _import/raw/cases_raw.json.

Notes on data shape:
- site_data.json has flat per-page records (no per-case structure).
- Case-1 page (idx=16) lists ~46 cases as 【...】 section titles, 252 images flat.
- We map each slug to its original title, then take a position-based image slice.
- paras (per-case prose) is mostly absent; we fall back to title+category and mark
  needs_review=true so a human can fill in copy later.
"""
import json
import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_JSON = r"C:\Users\hidex\parkhomes_data\site_data.json"
IMAGES_DIR = r"C:\Users\hidex\parkhomes_data\images"
OUT = os.path.join(ROOT, "_import", "raw", "cases_raw.json")

# slug -> original title (as it appears between 【】 in idx=16 full_text)
# Anonymization happens at display time, not here — we keep original tracking.
SLUG_TO_TITLE = {
    "plus-garden-cafe":   "PLUS GARDEN CAFE",
    "miyako-rehab":       "宮古島リハビリ温泉病院",
    "resor-tech-2022":    "RESOR TECH  EXPO2022  IN OKINAWA",
    "crystal-villa-ingya":"クリスタルヴィラ　インギャートレーラーハウス",
    "pool-resort-okinawa":"ザ・プールリゾート沖縄　様",
    "senaga-glamping":    "瀬長島グランピング場",
    "miyako-showroom":    "パークホームズ宮古島展示場",
    "taei-japan-rental":  "タエイジャパン様",
    "guts-rental":        "ガッツレンタカー様",
    "sesoko-villa":       "瀬底島S邸",         # anonymize at render
    "onna-villa":         "恩納村　柴崎邸",     # anonymize at render
    "toyosaki-chura":     "豊崎パーク美ら11M",
}

# Display-side mappings (anonymized title and human-readable display title + category).
SLUG_META = {
    "plus-garden-cafe":   {"display_title": "PLUS GARDEN CAFE",            "category": "カフェ"},
    "miyako-rehab":       {"display_title": "宮古島リハビリ温泉病院",        "category": "医療施設"},
    "resor-tech-2022":    {"display_title": "RESOR TECH EXPO 2022 IN OKINAWA","category": "イベント"},
    "crystal-villa-ingya":{"display_title": "クリスタルヴィラ インギャー",   "category": "宿泊施設"},
    "pool-resort-okinawa":{"display_title": "ザ・プールリゾート沖縄",        "category": "宿泊施設"},
    "senaga-glamping":    {"display_title": "瀬長島グランピング場",          "category": "グランピング"},
    "miyako-showroom":    {"display_title": "パークホームズ宮古島展示場",     "category": "自社施設"},
    "taei-japan-rental":  {"display_title": "タエイジャパン",                "category": "レンタカー"},
    "guts-rental":        {"display_title": "ガッツレンタカー",              "category": "レンタカー"},
    "sesoko-villa":       {"display_title": "本部町瀬底島のお客様",          "category": "個人邸"},
    "onna-villa":         {"display_title": "恩納村のお客様",                "category": "個人邸"},
    "toyosaki-chura":     {"display_title": "豊崎パーク美ら 11M",            "category": "自社施設"},
}


def load_data():
    with open(SITE_JSON, encoding="utf-8") as f:
        return json.load(f)


def collect_titles_in_order(full_text):
    """Return list of section titles (text between 【 and 】) in document order."""
    # Use re.findall with [^】]+? to be lenient on whitespace inside
    return re.findall(r"【([^【】]+?)】", full_text)


def normalize(s):
    return re.sub(r"\s+", "", s)


def find_title_index(titles_in_order, target):
    """Find best match of target in the ordered title list. Returns -1 if not found."""
    nt = normalize(target)
    for i, t in enumerate(titles_in_order):
        if normalize(t) == nt:
            return i
    # Fallback: substring match (lenient — case-1 titles sometimes have extra spaces)
    for i, t in enumerate(titles_in_order):
        nti = normalize(t)
        if nt in nti or nti in nt:
            return i
    return -1


def pick_images(images, position, total_titles, max_n=3):
    """Position-based slice. Filters out small/thumbnail images first.

    case-1 has 252 images flat. We exclude tiny banner + thumbnail-strip images
    (those with dimension=300x300:mode=crop, size <30KB) and keep the gallery
    shots (typically dimension=940x10000, 80-200KB).
    """
    def is_main(img):
        src = img.get("original_src", "")
        # crop thumbnails: low utility
        if "mode=crop" in src:
            return False
        if img.get("size_bytes", 0) < 30_000:
            return False
        return True

    mains = [img for img in images if is_main(img)]
    if not mains:
        return []

    # Roughly partition mains among the title slots.
    if total_titles <= 0:
        per = 6
        start = 0
    else:
        per = max(1, len(mains) // total_titles)
        start = position * per
    sliced = mains[start:start + max_n]
    # If we ran off the end, take from the tail.
    if len(sliced) < max_n:
        sliced = mains[max(0, len(mains) - max_n):]
    return sliced[:max_n]


def main():
    data = load_data()
    # Source pages
    p16 = data["pages"][16]  # 設置事例 (case-1), 252 images, primary list
    p17 = data["pages"][17]  # 設置事例 2, 40 images, supplemental list

    titles16 = collect_titles_in_order(p16["full_text"])
    titles17 = collect_titles_in_order(p17["full_text"])

    out = []
    for slug, original in SLUG_TO_TITLE.items():
        idx = find_title_index(titles16, original)
        source_page = 16
        if idx < 0:
            idx = find_title_index(titles17, original)
            source_page = 17 if idx >= 0 else 16

        page = data["pages"][source_page]
        titles_here = titles16 if source_page == 16 else titles17

        # paras: pull any non-empty context_text from images on this page that
        # mention the original title. Rare hit, but free signal when present.
        nt = normalize(original)
        paras = []
        for img in page["images"]:
            ctx = img.get("context_text", "")
            if ctx and nt in normalize(ctx):
                if ctx not in paras:
                    paras.append(ctx)

        images = pick_images(page["images"], max(0, idx), len(titles_here), max_n=3)

        meta = SLUG_META[slug]
        out.append({
            "slug": slug,
            "original_title": original,
            "display_title": meta["display_title"],
            "category": meta["category"],
            "title_index_on_source": idx,
            "source_page_index": source_page,
            "source_page_url": page["url"],
            "paras": paras,
            "images": [
                {
                    "local_file": img["local_file"],
                    "src_local": os.path.join(IMAGES_DIR, img["local_file"]),
                    "size_bytes": img.get("size_bytes"),
                    "alt_orig": img.get("alt", ""),
                } for img in images
            ],
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Summary report
    for c in out:
        print(
            f"  {c['slug']:22s} | idx={c['title_index_on_source']:3d}/{('p16' if c['source_page_index']==16 else 'p17')} "
            f"| paras={len(c['paras'])} imgs={len(c['images'])} | {c['display_title']}"
        )
    print(f"\nwrote: {OUT}")
    print(f"cases extracted: {len(out)}/12")


if __name__ == "__main__":
    main()
