"""Baut docs/index.html aus template.html, data/top50.json und data/rohdaten/<platz>.json."""
import json, os, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = lambda *a: os.path.join(ROOT, *a)
base = json.load(open(p("data", "top50.json"), encoding="utf-8"))
meta = json.load(open(p("data", "meta.json"), encoding="utf-8"))
out = []
for b in base:
    f = p("data", "rohdaten", f"{b['pos']}.json")
    r = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    g = dict(b)
    for k, v in r.items():
        if k in ("pos", "id") or (k == "designers" and not v):
            continue
        g[k] = v
    for s in g.get("shops") or []:
        if s.get("found") and s.get("price") is None:
            s["found"] = False
    g.pop("descriptionEn", None); g.pop("notes", None)
    out.append(g)
html = open(p("template.html"), encoding="utf-8").read()
html = html.replace("/*DATA*/null", json.dumps(out, ensure_ascii=False)).replace("/*META*/null", json.dumps(meta, ensure_ascii=False))
os.makedirs(p("docs"), exist_ok=True)
open(p("docs", "index.html"), "w", encoding="utf-8").write("<!doctype html>\n<html lang=\"de\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" + html.replace("<style>", "<style>\nhtml,body{margin:0}img{max-width:100%}[hidden]{display:none!important}\n", 1) + "\n</html>\n")
json.dump(out, open(p("docs", "spiel2026-daten.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} Spiele -> docs/index.html")
