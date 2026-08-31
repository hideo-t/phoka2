# -*- coding: utf-8 -*-
"""翻訳作業用に原文を範囲指定で書き出す。

  python i18n/dump.py 0 100
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

d = json.load(io.open(os.path.join(config.STRINGS, "ja.json"), encoding="utf-8"))
a = int(sys.argv[1]); b = int(sys.argv[2])
for i, e in enumerate(d["entries"][a:b], a):
    print("%4d\t%s\t%s" % (i, e["kind"], e["ja"]))
