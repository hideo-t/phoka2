"""Render cases/index.html from curated.json.

The phoka2 site uses inlined per-page CSS (no shared style.css), so we
inject the new card/filter rules into the existing <style> block of
cases/index.html and replace the section body in place.

Reading the existing file lets us preserve nav/footer/scripts the
template page already ships.
"""
import json
import os
import re

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURATED  = os.path.join(ROOT, "_import", "review", "cases.curated.json")
TRUTH_V4 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v4.json")
TRUTH_V2 = os.path.join(ROOT, "_import", "review", "cases_image_truth_v2.json")
TARGET   = os.path.join(ROOT, "cases", "index.html")

NEW_CSS_BLOCK = """
/* === Cases page (PR#1) === */
.cases-grid{gap:24px}
.case-card{display:flex;flex-direction:column;overflow:hidden;padding:0;background:var(--bg-alt);border:1px solid var(--border);border-radius:var(--rl);transition:.3s}
.case-card:hover{transform:translateY(-4px);box-shadow:0 8px 32px rgba(0,0,0,.12)}
.case-card picture{display:block;overflow:hidden}
.case-card img{width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;display:block;transition:.3s}
.case-card:hover img{transform:scale(1.04)}
.case-card__body{padding:18px 20px 22px}
.case-card__badge{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;background:var(--primary);color:#fff;margin-bottom:8px;font-weight:600}
.case-card h3{margin:0 0 8px;font-size:17px;color:var(--primary-dark);font-weight:700}
.case-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.7}
.case-card__needs-review{display:inline-block;font-size:10px;padding:1px 8px;border-radius:999px;background:#fef3c7;color:#92400e;margin:0 0 8px;font-weight:600}
.case-filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:32px;justify-content:center}
.case-filter{background:transparent;border:1px solid var(--border);padding:6px 14px;border-radius:999px;cursor:pointer;font-size:13px;color:var(--text);transition:.2s;font-family:inherit}
.case-filter:hover{background:var(--bg)}
.case-filter.active{background:var(--primary);color:#fff;border-color:var(--primary)}
/* PR#3: sub-image grid + remaining badge */
.case-card__subs{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px 6px 0}
.case-card__subs picture{display:block;overflow:hidden;border-radius:6px}
.case-card__subs img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;transition:.3s}
.case-card:hover .case-card__subs img{transform:scale(1.04)}
.case-card__remaining{display:inline-block;margin-left:8px;font-size:11px;color:var(--muted);background:var(--border);padding:2px 8px;border-radius:999px;font-weight:500}
@media(max-width:480px){.case-card__subs{grid-template-columns:1fr 1fr;gap:4px;padding:4px 4px 0}}
/* PR#4: series label chip (e.g. その1/その2) on duplicate-titled cards */
.case-card__series{display:inline-block;margin-left:6px;font-size:11px;color:var(--primary);background:rgba(21,96,168,.08);padding:1px 8px;border-radius:999px;font-weight:600;vertical-align:middle}
"""

FILTER_JS = """<script>
document.querySelectorAll('.case-filter').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.case-filter').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const cat=btn.dataset.cat;
    document.querySelectorAll('.case-card').forEach(card=>{
      card.style.display=(cat==='all'||card.dataset.cat===cat)?'':'none';
    });
  });
});
</script>"""


def render_filters(categories):
    parts = ['<button class="case-filter active" data-cat="all">すべて</button>']
    for c in categories:
        parts.append(f'<button class="case-filter" data-cat="{c}">{c}</button>')
    return "\n      ".join(parts)


def render_sub_picture(slug: str, idx: int, title: str) -> str:
    """One <picture> for a sub-image (used inside .case-card__subs)."""
    big   = f"images/cases/{slug}-{idx:02d}.webp"
    small = f"images/cases/{slug}-{idx:02d}@600w.webp"
    return (
        '    <picture>\n'
        f'      <source srcset="{small} 600w, {big} 1200w" sizes="(max-width:768px) 50vw, 260px" type="image/webp">\n'
        f'      <img src="{big}" loading="lazy" alt="{title} の施工事例 {idx}" width="600" height="450">\n'
        '    </picture>'
    )


def render_card(case, image_count: int, remaining: int, series_label: str | None):
    s = case["slug"]
    img1_1200 = f"images/cases/{s}-01.webp"
    img1_600  = f"images/cases/{s}-01@600w.webp"
    # needs-review chip lives outside <h3> so the heading text stays clean
    # for accessibility tools and SEO.
    review_chip = '\n          <span class="case-card__needs-review">要レビュー</span>' if case["needs_review"] else ""
    summary = case["summary"] or "（説明文準備中）"

    # Sub-image block (max 2: -02 and -03) only when the source had >=2 images.
    sub_html = ""
    if image_count >= 2:
        pics = [render_sub_picture(s, 2, case["title"])]
        if image_count >= 3:
            pics.append(render_sub_picture(s, 3, case["title"]))
        sub_html = "\n\n        <div class=\"case-card__subs\">\n" + "\n".join(pics) + "\n        </div>"

    remaining_chip = ""
    if remaining > 0:
        remaining_chip = f'\n          <span class="case-card__remaining">ほか{remaining}枚</span>'

    series_chip = ""
    if series_label:
        series_chip = f' <span class="case-card__series">{series_label}</span>'

    # alt for the main img is "<title> [series] の施工事例 1"
    alt_main = case["images"][0]["alt_jp"]
    if series_label and series_label not in alt_main:
        alt_main = f"{case['title']} {series_label} の施工事例 1"

    return f'''      <article class="card case-card" data-cat="{case["category"]}">
        <picture>
          <source srcset="{img1_600} 600w, {img1_1200} 1200w" sizes="(max-width:768px) 100vw, 540px" type="image/webp">
          <img src="{img1_1200}" loading="lazy" alt="{alt_main}" width="1200" height="900">
        </picture>{sub_html}

        <div class="case-card__body">
          <span class="case-card__badge">{case["category"]}</span>
          <h3>{case["title"]}{series_chip}</h3>{review_chip}
          <p>{summary}</p>{remaining_chip}
        </div>
      </article>'''


def main():
    with open(CURATED, encoding="utf-8") as f:
        cases = json.load(f)

    # Truth v4 (preferred) carries image_count, remaining, series_label,
    # page_source, and the canonical category order.
    truth_by_slug = {}
    category_order = []
    truth_path = TRUTH_V4 if os.path.exists(TRUTH_V4) else TRUTH_V2
    if os.path.exists(truth_path):
        with open(truth_path, encoding="utf-8") as f:
            tv = json.load(f)
        for c in tv["cases"]:
            truth_by_slug[c["slug"]] = {
                "image_count":  len(c["top3"]),
                "remaining":    c.get("remaining", 0),
                "series_label": c.get("series_label"),
                "page_source":  c.get("page_source", 1),
            }
        category_order = tv.get("categories") or []

    # Order rule (per PR#4 spec):
    #   page 1 cases keep their existing displayed order (sort by category,slug),
    #   page 2 cases appended in truth-file order.
    truth_order = {c["slug"]: i for i, c in enumerate(tv["cases"])} if truth_path else {}

    def order_key(c):
        meta = truth_by_slug.get(c["slug"], {})
        ps = meta.get("page_source", 1)
        if ps == 1:
            return (1, c["category"], c["slug"])
        return (2, truth_order.get(c["slug"], 9999), 0)

    cases_sorted = sorted(cases, key=order_key)

    # Filter buttons: prefer truth_v4's canonical category list, otherwise
    # derive from first-appearance order.
    if category_order:
        # Only include categories actually represented in the current cases.
        present = {c["category"] for c in cases_sorted}
        seen = [cat for cat in category_order if cat in present]
        # Append any extra categories not in the truth list (defensive).
        for c in cases_sorted:
            if c["category"] not in seen:
                seen.append(c["category"])
    else:
        seen = []
        for c in cases_sorted:
            if c["category"] not in seen:
                seen.append(c["category"])

    with open(TARGET, encoding="utf-8") as f:
        html = f.read()

    # 1) Inject CSS into the existing <style>...</style> block (only the cases page's).
    # Idempotent: if a previous render injected the block, replace it so edits
    # to NEW_CSS_BLOCK propagate on re-run.
    css_marker = "/* === Cases page (PR#1) === */"
    if css_marker in html:
        html = re.sub(
            rf"{re.escape(css_marker)}[\s\S]*?(?=</style>)",
            NEW_CSS_BLOCK.lstrip("\n"),
            html,
            count=1,
        )
    else:
        html = re.sub(
            r"(<style>[\s\S]*?)(</style>)",
            lambda m: m.group(1) + NEW_CSS_BLOCK + m.group(2),
            html,
            count=1,
        )

    # 2) Replace the body of the first <section class="section section-alt">...</section>.
    def _card(c):
        tv = truth_by_slug.get(c["slug"], {})
        img_count = tv.get("image_count", len(c.get("images", [])))
        remaining = tv.get("remaining", 0)
        series   = tv.get("series_label")
        return render_card(c, img_count, remaining, series)

    cards_html = "\n".join(_card(c) for c in cases_sorted)
    filters_html = render_filters(seen)
    new_section = f'''<section class="section section-alt">
  <div class="container">
    <div class="section-eyebrow">CASES</div>
    <h2 class="section-title">設置事例</h2>
    <p class="section-sub">沖縄県内外でのトレーラーハウス施工事例を、カテゴリ別にご紹介します。</p>

    <div class="case-filters">
      {filters_html}
    </div>

    <div class="grid-2 cases-grid">
{cards_html}
    </div>

    <div style="text-align:center;margin-top:48px">
      <a href="https://hideo-t.github.io/phoka2/contact/" class="btn btn-primary">設置のご相談はこちら →</a>
    </div>
  </div>
</section>'''

    html = re.sub(
        r'<section class="section section-alt">[\s\S]*?</section>',
        lambda m: new_section,
        html,
        count=1,
    )

    # 3) Insert filter JS just before </body> (idempotent).
    if "document.querySelectorAll('.case-filter')" not in html:
        html = html.replace("</body>", FILTER_JS + "\n</body>", 1)

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    print(f"wrote: {TARGET}")
    print(f"cases: {len(cases_sorted)} (categories: {', '.join(seen)})")


if __name__ == "__main__":
    main()
