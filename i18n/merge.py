# -*- coding: utf-8 -*-
"""翻訳メモリ（原文キー）から、ビルドが読む言語別辞書を組み立てる。

  i18n/strings/_tr/<lang>.json   … 編集する翻訳メモリ。{日本語原文: 訳文}
  i18n/strings/<lang>.json       … ここが生成する。ja.json に在るキーだけを残す

原文そのものをキーにしているので、抽出のやり直しで並び順が変わっても
訳文は失われない。ja.json に無くなったキーはメモリ側に残し、出力からのみ落とす。

  python i18n/merge.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

TR = os.path.join(config.STRINGS, "_tr")


def load(lang):
    p = os.path.join(TR, lang + ".json")
    if not os.path.exists(p):
        return {}
    return json.load(io.open(p, encoding="utf-8"))


def main():
    src = json.load(io.open(os.path.join(config.STRINGS, "ja.json"), encoding="utf-8"))
    keys = [e["ja"] for e in src["entries"]]
    missing_all = None

    for lang in config.LANGS:
        memory = load(lang)
        table = {k: memory[k] for k in keys
                 if isinstance(memory.get(k), str) and memory[k].strip()}
        io.open(os.path.join(config.STRINGS, lang + ".json"), "w", encoding="utf-8").write(
            json.dumps(table, ensure_ascii=False, indent=1))
        missing = [k for k in keys if k not in table]
        stale = len(memory) - len([k for k in memory if k in set(keys)])
        print("%-8s 訳あり %4d / %d   未訳 %d   メモリ内の不要キー %d"
              % (lang, len(table), len(keys), len(missing), stale))
        missing_all = set(missing) if missing_all is None else (missing_all & set(missing))

    if missing_all:
        print("\n全言語で未訳のキー %d 件:" % len(missing_all))
        for k in [k for k in keys if k in missing_all][:20]:
            print("  %r" % k[:90])


if __name__ == "__main__":
    main()
