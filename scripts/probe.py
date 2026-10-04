import re, requests, urllib.parse
H={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36","Accept-Language":"de-DE,de;q=0.9"}
s=requests.Session(); s.headers.update(H)
def show(label, html, pats, w=500):
    print(f"\n===== {label} len={len(html)}")
    for p in pats:
        for m in list(re.finditer(p, html, re.I))[:2]:
            print(f"--- [{p}] @{m.start()}"); print(re.sub(r'\s+',' ',html[max(0,m.start()-w):m.start()+w]))
# Spiele-Offensive search + product
r=s.get("https://www.spiele-offensive.de/index.php?cmd=suchergebnis&suchwort="+urllib.parse.quote("Gaudi".encode('latin-1')))
r.encoding='iso-8859-1'; print("SO search",r.status_code,r.url)
show("SO search", r.text, [r'/Spiel/[^"]+\.html', r'lieferbar', r'&euro;|€'])
r=s.get("https://www.spiele-offensive.de/Spiel/Gaudi-1035458.html"); r.encoding='iso-8859-1'
print("SO prod",r.status_code,r.url)
links=re.findall(r'href="(https://www\.spiele-offensive\.de/Spiel/[^"]+)"', s.get("https://www.spiele-offensive.de/index.php?cmd=suchergebnis&suchwort=Gaudi").text)
print("SO links",links[:10])
if links:
    r=s.get(links[0]); r.encoding='iso-8859-1'
    show("SO product "+links[0], r.text, [r'itemprop="price"', r'"price"', r'lieferbar|Vorbestell|erscheint', r'application/ld\+json'], 400)
# Spieletastisch product + search form
r=s.get("https://www.spieletastisch.de/produkte/12254-gaudi-gaudi-de")
show("ST product", r.text, [r'itemprop="price"', r'application/ld\+json', r'lieferbar|Vorbestell|Erscheinungsdatum'], 400)
r=s.get("https://www.spieletastisch.de/")
m=re.search(r'<form[^>]*id="form"[\s\S]*?</form>', r.text); print("\nST form:", m.group(0)[:3000] if m else None)
