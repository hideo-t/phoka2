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
.case-card__needs-review{display:inline-block;font-size:10px;padding:1px 8px;border-radius:999px;background:#fef3c7;color:#92400e;margin-left:6px;font-weight:600}
.case-filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:32px;justify-content:center}
.case-filter{background:transparent;border:1px solid var(--border);padding:6px 14px;border-radius:999px;cursor:pointer;font-size:13px;color:var(--text);transition:.2s;font-family:inherit}
.case-filter:hover{background:var(--bg)}
.case-filter.active{background:var(--primary);color:#fff;border-color:var(--primary)}
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


def render_card(case):
    s = case["slug"]
    img1_1200 = f"images/cases/{s}-01.webp"
    img1_600  = f"images/cases/{s}-01@600w.webp"
    review_badge = ' <span class="case-card__needs-review">要レビュー</span>' if case["needs_review"] else ""
    summary = case["summary"] or "（説明文準備中）"
    return f'''      <article class="card case-card" data-cat="{case["category"]}">
        <picture>
          <source srcset="{img1_600} 600w, {img1_1200} 1200w" sizes="(max-width:768px) 100vw, 540px" type="image/webp">
          <img src="{img1_1200}" loading="lazy" alt="{case["images"][0]["alt_jp"]}" width="1200" height="900">
        </picture>
        <div class="case-card__body">
          <span class="case-card__badge">{case["category"]}</span>
          <h3>{case["title"]}{review_badge}</h3>
          <p>{summary}</p>
        </div>
      </article>'''


def main():
    with open(CURATED, encoding="utf-8") as f:
        cases = json.load(f)
    # Preserve curated order, but stable-sort by category for a nicer initial layout.
    # (Filter buttons reorder visually; without filter, viewer sees grouped cards.)
    cases_sorted = sorted(cases, key=lambda c: (c["category"], c["slug"]))

    # Categories preserving first-appearance order from sorted list.
    seen = []
    for c in cases_sorted:
        if c["category"] not in seen:
            seen.append(c["category"])

    with open(TARGET, encoding="utf-8") as f:
        html = f.read()

    # 1) Inject CSS into the existing <style>...</style> block (only the cases page's).
    if "/* === Cases page (PR#1) === */" not in html:
        html = re.sub(
            r"(<style>[\s\S]*?)(</style>)",
            lambda m: m.group(1) + NEW_CSS_BLOCK + m.group(2),
            html,
            count=1,
        )

    # 2) Replace the body of the first <section class="section section-alt">...</section>.
    cards_html = "\n".join(render_card(c) for c in cases_sorted)
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
