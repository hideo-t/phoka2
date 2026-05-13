"""Merge cases_raw + cases_summaries into the canonical curated.json
that downstream tools consume.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW       = os.path.join(ROOT, "_import", "raw", "cases_raw.json")
SUMS      = os.path.join(ROOT, "_import", "raw", "cases_summaries.json")
CURATED   = os.path.join(ROOT, "_import", "review", "cases.curated.json")


def main():
    with open(RAW, encoding="utf-8") as f:
        raw = {c["slug"]: c for c in json.load(f)}
    with open(SUMS, encoding="utf-8") as f:
        sums = {c["slug"]: c for c in json.load(f)}

    out = []
    for slug, c in raw.items():
        s = sums[slug]
        images = []
        for idx, img in enumerate(c["images"][:3], start=1):
            alt = img.get("alt_orig") or f"{c['display_title']} の施工事例 {idx}"
            images.append({
                "src_local": img["src_local"],
                "src_filename_only": img["local_file"],
                "alt_jp": alt,
            })
        out.append({
            "slug": slug,
            "title": c["display_title"],
            "category": c["category"],
            "summary": s["summary"],
            "needs_review": s["needs_review"],
            "images": images,
        })

    os.makedirs(os.path.dirname(CURATED), exist_ok=True)
    with open(CURATED, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote: {CURATED}")
    print(f"cases: {len(out)}  | needs_review: {sum(1 for c in out if c['needs_review'])}")


if __name__ == "__main__":
    main()
