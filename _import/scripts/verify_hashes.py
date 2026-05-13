"""Verify that the on-disk case images line up with cases_image_truth_v2.json.

Asserts that for each slug, the number of *-NN.webp + *-NN@600w.webp pairs
present matches `len(top3)`. Exit 1 on any mismatch.
"""
import json
import os
import sys

ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRUTH = os.path.join(ROOT, "_import", "review", "cases_image_truth_v2.json")
OUT   = os.path.join(ROOT, "images", "cases")


def main() -> int:
    with open(TRUTH, encoding="utf-8") as f:
        truth = json.load(f)

    errors = 0
    rows   = []
    for case in truth["cases"]:
        slug   = case["slug"]
        target = len(case["top3"])
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
        rows.append((slug, target, missing, extra, ok))
        if not ok:
            errors += 1

    for slug, target, missing, extra, ok in rows:
        flag = "ok  " if ok else "FAIL"
        details = ""
        if missing:
            details += f"  missing={missing}"
        if extra:
            details += f"  extra={extra}"
        print(f"  {flag}  {slug:22s}  target={target}{details}")

    print()
    print(f"--- {len(rows)} cases verified, {errors} failed ---")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
