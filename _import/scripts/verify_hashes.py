"""Verify that the on-disk case images line up with the newest truth file.

Prefers cases_image_truth_v4.json (page1+page2 = 20 cases) over v2.
Asserts that for each slug, the number of *-NN.webp + *-NN@600w.webp pairs
present matches `len(top3)`. Exit 1 on any mismatch.
"""
import json
import os
import sys

ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRUTH_V4 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v4.json")
TRUTH_V2 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v2.json")
OUT      = os.path.join(ROOT, "images", "cases")


def pick_truth() -> str:
    return TRUTH_V4 if os.path.exists(TRUTH_V4) else TRUTH_V2


def main() -> int:
    truth_path = pick_truth()
    with open(truth_path, encoding="utf-8") as f:
        truth = json.load(f)

    errors = 0
    rows   = []
    page_counts = {}
    for case in truth["cases"]:
        slug   = case["slug"]
        target = len(case["top3"])
        ps     = case.get("page_source", 1)
        page_counts[ps] = page_counts.get(ps, 0) + 1
        missing, extra = [], []
        for nn in range(1, target + 1):
            for variant in ("", "@600w"):
                p = os.path.join(OUT, f"{slug}-{nn:02d}{variant}.webp")
                if not os.path.exists(p):
                    missing.append(os.path.basename(p))
        # Look for unexpected NN (e.g. -04 from a previous run)
        for nn in range(target + 1, target + 6):
            for variant in ("", "@600w"):
                p = os.path.join(OUT, f"{slug}-{nn:02d}{variant}.webp")
                if os.path.exists(p):
                    extra.append(os.path.basename(p))

        ok = not missing and not extra
        rows.append((slug, ps, target, missing, extra, ok))
        if not ok:
            errors += 1

    print(f"truth: {os.path.basename(truth_path)}  ({len(rows)} cases)")
    for slug, ps, target, missing, extra, ok in rows:
        flag = "ok  " if ok else "FAIL"
        details = ""
        if missing:
            details += f"  missing={missing}"
        if extra:
            details += f"  extra={extra}"
        print(f"  {flag}  p{ps}  {slug:26s}  target={target}{details}")

    print()
    page_summary = " / ".join(f"page{p}: {n} cases" for p, n in sorted(page_counts.items()))
    print(f"--- {len(rows)} cases verified ({page_summary}), {errors} failed ---")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
