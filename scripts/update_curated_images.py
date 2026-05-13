"""Sync cases.curated.json images[] to actual files in images/cases/ (post-refetch).

Reads cases_image_truth.json for per-slug image_count; rewrites the images[]
arrays in cases.curated.json with the correct count and re-generated alt text.

Preserves all other fields (slug/title/category/summary/needs_review).
"""
import json
import os
import glob

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURATED  = os.path.join(ROOT, "_import", "review", "cases.curated.json")
TRUTH    = os.path.join(ROOT, "_import", "review", "cases_image_truth.json")
IMG_DIR  = os.path.join(ROOT, "images", "cases")


def main():
    with open(CURATED, encoding="utf-8") as f:
        cases = json.load(f)
    with open(TRUTH, encoding="utf-8") as f:
        truth = json.load(f)

    for c in cases:
        slug = c["slug"]
        if slug not in truth:
            print(f"  WARN  no truth entry for {slug}, leaving images as-is")
            continue
        # Probe actual on-disk count to be safe.
        on_disk = sorted(glob.glob(os.path.join(IMG_DIR, f"{slug}-*.webp")))
        on_disk = [p for p in on_disk if "@600w" not in p]
        n = len(on_disk)
        if n == 0:
            print(f"  ERR   no images on disk for {slug}!")
            continue

        c["images"] = []
        for idx in range(1, n + 1):
            c["images"].append({
                "src_filename_only": f"{slug}-{idx:02d}.webp",
                "alt_jp": f"{c['title']} の施工事例 {idx}" if n > 1 else f"{c['title']} の施工事例",
            })
        print(f"  ok    {slug:22s} -> {n} image{'s' if n>1 else ''}")

    with open(CURATED, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nwrote: {CURATED}")
    print(f"total cases: {len(cases)}")


if __name__ == "__main__":
    main()
