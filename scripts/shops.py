"""Fragt Preis und Verfügbarkeit bei Spiele-Offensive, Spielefürst und Spieletastisch neu ab.

Liest data/top50.json und data/rohdaten/<platz>.json, aktualisiert dort die "shops"-Einträge
und schreibt den Zeitpunkt der Abfrage nach data/meta.json ("preiseStand").

Bereits bekannte Produktseiten werden direkt geprüft, für alle anderen Spiele wird in der
Shopsuche nach dem deutschen und dem englischen Titel gesucht. Schlägt eine Abfrage fehl
(Netzwerk, Sperre), bleibt der alte Eintrag stehen.

Aufruf: python3 scripts/shops.py [platz ...]
"""
import datetime
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from zoneinfo import ZoneInfo

from curl_cffi import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SHOPS = ["Spiele-Offensive", "Spielefürst", "Spieletastisch"]
ZUBEHOER = {"insert", "inserts", "sleeves", "kartenhullen", "promo", "promos", "playmat", "spielmatte",
            "coin", "coins", "munzen", "organizer", "upgrade", "metal", "deluxe", "set", "box"}
DELAY = 1.0

session = requests.Session(impersonate="chrome")


class FetchError(Exception):
    pass


def get(url, **kw):
    time.sleep(DELAY)
    try:
        r = session.get(url, timeout=30, **kw)
    except Exception as e:  # Netzwerkfehler
        raise FetchError(f"{url}: {e}")
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise FetchError(f"{url}: HTTP {r.status_code}")
    return r


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\[.*?\]|\|.*$", " ", s)
    s = re.sub(r"\b(de|en|dt|deutsch|englisch|multilingual|vorbestellung|retail|ausgabe|edition)\b", " ", s)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def matches(candidate, titles, expansion=False):
    c = norm(candidate)
    for t in titles:
        t = norm(t)
        if not t:
            continue
        if c == t:
            return True
        if c.startswith(t + " "):
            extra = set(c[len(t):].split())
            if not extra & ZUBEHOER and (expansion or "erweiterung" not in extra):
                return True
    return False


def edition_of(name, default=None):
    n = name.lower()
    if re.search(r"\(en\)|englisch|english", n):
        return "EN"
    if re.search(r"multilingual|\(ml\)", n):
        return "ML"
    if re.search(r"\(de\)|deutsch", n):
        return "DE"
    return default


def price_of(s):
    m = re.search(r"(\d+(?:\.\d{3})*),(\d\d)", s)
    return float(m.group(1).replace(".", "") + "." + m.group(2)) if m else None


# ---------------------------------------------------------------- Spiele-Offensive
SO = "https://www.spiele-offensive.de"


def so_decode(r):
    return r.content.decode("iso-8859-1")


def so_search(term):
    url = f"{SO}/index.php?cmd=suchergebnis&suchwort=" + urllib.parse.quote(term.encode("iso-8859-1", "ignore"))
    r = get(url)
    if r is None:
        return []
    page = so_decode(r)
    out = []
    for m in re.finditer(r'href="(/Spiel/[^"]+\.html)" class="alamain[^"]*"\s*>\s*<span>\s*<font>(.*?)</font>', page, re.S):
        out.append((text(m.group(2)), SO + m.group(1)))
    return out


def so_product(url):
    r = get(url)
    if r is None:
        return None
    page = so_decode(r)
    m = re.search(r"name='uebergabe\[1\]\[3\]' value='([\d.]+)'", page) or re.search(r'"value": "([\d.]+)"', page)
    if not m:
        raise FetchError(f"{url}: Preis nicht lesbar")
    name = re.search(r'"item_name": "(.*?)"', page)
    name = json.loads(f'"{name.group(1)}"') if name else ""
    avail = ""
    a = re.search(r"<div class='vfrei'>.*?</div>\s*<div[^>]*>(.*?)</div>\s*<div class='sellw'>", page, re.S)
    if a:
        avail = text(a.group(1))
    if not avail:
        b = re.search(r"title='[^']*in den Warenkorb legen\. ([^']+)'", page)
        avail = b.group(1) if b else ""
    low = avail.lower()
    now = bool(re.search(r"sofort lieferbar|auf lager", low)) and "vorbestell" not in low
    rel = (re.search(r"erwarten wir ca\. ([^.<]+)", avail) or re.search(r"voraussichtlich ab ([^.<]+?) (?:wieder )?lieferbar", avail)
           or re.search(r"erscheint (?:voraussichtlich )?([^.<]+)", avail))
    return {"productName": name, "url": url, "price": float(m.group(1)), "availabilityText": avail or None,
            "availableNow": now, "releaseDate": rel.group(1).strip() if rel and not now else None,
            "edition": edition_of(name, "DE")}


# ---------------------------------------------------------------- Spielefürst (Shopify)
SF = "https://spielefuerst.de"


def sf_search(term):
    r = get(f"{SF}/search/suggest.json", params={"q": term, "resources[type]": "product", "resources[limit]": "8"})
    if r is None:
        return []
    prods = r.json()["resources"]["results"]["products"]
    return [(p["title"], SF + "/products/" + p["handle"]) for p in prods]


def sf_product(url):
    handle = url.rstrip("/").split("/products/")[-1].split("?")[0]
    r = get(f"{SF}/products/{handle}.js")
    if r is None:
        return None
    p = r.json()
    tags = [t.lower() for t in p.get("tags", [])]
    preorder = "vorbestellartikel" in tags or "vorbestellung" in p["title"].lower()
    if p.get("available") and not preorder:
        avail, now = "sofort lieferbar", True
    elif p.get("available"):
        avail, now = "Vorbestellung", False
    else:
        avail, now = "derzeit nicht verfügbar", False
    lang = "DE" if "sprache: deutsch" in tags else ("EN" if "sprache: englisch" in tags else None)
    return {"productName": p["title"].split(" | ")[0], "url": f"{SF}/products/{handle}", "price": p["price"] / 100,
            "availabilityText": avail, "availableNow": now, "releaseDate": None, "edition": lang or edition_of(p["title"])}


# ---------------------------------------------------------------- Spieletastisch (Tapestry)
ST = "https://www.spieletastisch.de"


def st_search(term):
    r = get(ST + "/")
    if r is None:
        return []
    form = re.search(r'<form[^>]*action="([^"]+)"[^>]*id="form"[^>]*>(.*?)</form>', r.text, re.S)
    if not form:
        raise FetchError("Spieletastisch: Suchformular nicht gefunden")
    fields = dict(re.findall(r'<input value="([^"]*)" name="([^"]+)" type="hidden"', form.group(2)))
    data = {name: html.unescape(value) for value, name in fields.items()}
    data["textfield"] = term
    time.sleep(DELAY)
    try:
        res = session.post(urllib.parse.urljoin(ST, html.unescape(form.group(1))), data=data, timeout=30)
    except Exception as e:
        raise FetchError(f"Spieletastisch-Suche: {e}")
    if res.status_code != 200:
        raise FetchError(f"Spieletastisch-Suche: HTTP {res.status_code}")
    out, seen = [], set()
    for m in re.finditer(r'href="((?:https://www\.spieletastisch\.de)?/produkte/[^"]+)"(.*?)</a>', res.text, re.S):
        href = urllib.parse.urljoin(ST, m.group(1))
        title = re.search(r'class="card-title[^"]*"[^>]*>(.*?)</', m.group(2), re.S)
        name = text(title.group(1)) if title else text(m.group(2))
        if href not in seen and name:
            seen.add(href)
            out.append((name, href))
    return out


def st_product(url):
    r = get(url)
    if r is None or "/produkte/" not in str(r.url):
        return None
    page = r.text
    price = re.search(r'class="price-current[^"]*">\s*([\d.,]+)\s*€', page)
    name = re.search(r'<h3[^>]*>\s*([^<]+?)\s*</h3>\s*<div class="prices', page)
    if not price or not name:
        raise FetchError(f"{url}: Preis nicht lesbar")
    dot = re.search(r'<i title="([^"]*)" class="game-availability-dot[^"]*text-(\w+)"', page)
    rel = re.search(r'Erscheinungsdatum:\s*</div>\s*<div class="game-details-property">\s*([^<]+?)\s*</div>', page)
    avail = html.unescape(dot.group(1)) if dot else None
    now = bool(dot and dot.group(2) == "success")
    return {"productName": html.unescape(name.group(1)), "url": url, "price": price_of(price.group(1)),
            "availabilityText": avail, "availableNow": now,
            "releaseDate": rel.group(1) if rel and not now else None,
            "edition": edition_of(name.group(1))}


HANDLERS = {
    "Spiele-Offensive": (so_search, so_product),
    "Spielefürst": (sf_search, sf_product),
    "Spieletastisch": (st_search, st_product),
}


def titles_for(game):
    t = [game.get("germanTitle"), game.get("name")]
    if game.get("germanEdition", {}) and game["germanEdition"].get("name"):
        t.append(re.sub(r"\s*(Name Pending)?\s*[-‐–]\s*German edition.*$", "", game["germanEdition"]["name"], flags=re.I))
    if ":" in (game.get("name") or "") and game.get("expansionFor"):
        t.append(game["name"].split(":", 1)[1].strip())
    out = []
    for x in t:
        x = (x or "").strip()
        if x and x not in out:
            out.append(x)
    return out


def plausible(hit, game):
    """Neu gefundene Produkte mit Erscheinungsjahr vor dem Spiel sind meist ein anderes Spiel gleichen Namens."""
    year = re.search(r"(20\d\d)", hit.get("releaseDate") or "")
    return not (year and game.get("yearPublished") and int(year.group(1)) < int(game["yearPublished"]))


def check(game, shop, old):
    search, product = HANDLERS[shop]
    titles = titles_for(game)
    exp = bool(game.get("expansionFor"))
    if old.get("found") and old.get("url") and re.search(r"/(Spiel|products|produkte)/.+", old["url"]):
        hit = product(old["url"])
        if hit:
            return hit
    seen = set()
    for t in titles:
        for name, url in search(t):
            if url in seen or not matches(name, titles, exp):
                continue
            seen.add(url)
            try:
                hit = product(url)
            except FetchError:
                continue
            if hit and matches(hit["productName"] or name, titles, exp) and plausible(hit, game):
                return hit
    return None


def main():
    only = {int(a) for a in sys.argv[1:]}
    top = json.load(open(os.path.join(DATA, "top50.json"), encoding="utf-8"))
    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    stamp = now.isoformat(timespec="minutes")
    fehler = 0
    for base in top:
        if only and base["pos"] not in only:
            continue
        path = os.path.join(DATA, "rohdaten", f"{base['pos']}.json")
        raw = json.load(open(path, encoding="utf-8"))
        game = {**base, **raw}
        old = {s["shop"]: s for s in raw.get("shops", [])}
        new = []
        for shop in SHOPS:
            prev = old.get(shop, {"shop": shop, "found": False})
            try:
                hit = check(game, shop, prev)
            except FetchError as e:
                fehler += 1
                print(f"  ! {base['pos']:>2} {shop}: {e}")
                new.append(prev)
                continue
            if hit:
                entry = {"shop": shop, "found": True, **hit, "checkedAt": stamp}
            else:
                entry = {"shop": shop, "found": False, "productName": None, "edition": None, "url": None,
                         "price": None, "availabilityText": None, "availableNow": False, "releaseDate": None,
                         "checkedAt": stamp}
            new.append(entry)
            was = f"{prev.get('price')}" if prev.get("found") else "–"
            is_ = f"{entry.get('price')} {'sofort' if entry.get('availableNow') else (entry.get('releaseDate') or entry.get('availabilityText') or '')}" if entry["found"] else "–"
            print(f"{base['pos']:>2} {base['name'][:34]:34} {shop:17} {was:>8} -> {is_}")
        raw["shops"] = new
        json.dump(raw, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    meta_path = os.path.join(DATA, "meta.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    meta["preiseStand"] = now.strftime("%-d.%-m.%Y, %H:%M Uhr")
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Fertig, {fehler} Abfragen fehlgeschlagen.")
    if fehler > 30:
        sys.exit(1)


if __name__ == "__main__":
    main()
