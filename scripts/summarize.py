"""Generate per-case Japanese summaries via local llama.cpp server.

Server: http://127.0.0.1:8080 (Qwen3-Coder-30B-A3B, OpenAI-compatible).
Input:  _import/raw/cases_raw.json
Output: _import/raw/cases_summaries.json

A case with empty paras gets needs_review=true. Summary length target 30-60 chars.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_PATH  = os.path.join(ROOT, "_import", "raw", "cases_raw.json")
OUT_PATH = os.path.join(ROOT, "_import", "raw", "cases_summaries.json")
SERVER   = "http://127.0.0.1:8080/v1/chat/completions"

PROMPT_FMT = """以下のトレーラーハウス施工事例の説明を、30〜60字で簡潔にまとめてください。
形容詞を最小限に、用途・モデル名・特徴を中心に。1文で。句点も含めて60字以内。

タイトル: {title}
カテゴリ: {category}
原文: {paras}

出力は要約文1文のみ。前置きや末尾の補足は不要。"""


def call_llm(prompt, max_tokens=200):
    body = {
        "model": "qwen3-coder-30b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        SERVER,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    out = []
    for c in cases:
        paras_text = "\n".join(c["paras"]) if c["paras"] else "(本文情報なし — タイトルとカテゴリから推定してください)"
        prompt = PROMPT_FMT.format(
            title=c["display_title"],
            category=c["category"],
            paras=paras_text,
        )
        try:
            summary = call_llm(prompt)
        except Exception as e:
            print(f"  ERR  {c['slug']}: {e}", file=sys.stderr)
            summary = ""

        # Clean: strip enclosing quotes / labels
        summary = summary.strip().strip("「」\"' ").splitlines()[0].strip() if summary else ""

        needs_review = (not c["paras"]) or (not summary) or len(summary) < 15
        entry = {
            "slug": c["slug"],
            "display_title": c["display_title"],
            "category": c["category"],
            "summary": summary,
            "needs_review": needs_review,
            "had_paras": bool(c["paras"]),
            "summary_len": len(summary),
        }
        out.append(entry)
        flag = "REVIEW" if needs_review else "ok    "
        print(f"  {flag} {c['slug']:22s} [{len(summary):3d}文字] {summary}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nwrote: {OUT_PATH}")


if __name__ == "__main__":
    main()
