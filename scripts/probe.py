import re, json, requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
H={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"de-DE,de;q=0.9,en;q=0.8"}
def show(label, html, pats, w=350, n=3):
    print(f"\n===== {label} len={len(html)}")
    for p in pats:
        for m in list(re.finditer(p, html, re.I))[:n]:
            print(f"--- [{p}] @{m.start()}"); print(re.sub(r'\s+',' ',html[max(0,m.start()-w):m.start()+w]))
u="https://www.spiele-offensive.de/index.php?cmd=suchergebnis&suchwort=Gaudi"
r=requests.get(u,headers=H); print("SO requests",r.status_code); print(r.text[:600])
try:
    from curl_cffi import requests as cr
    for imp in ["chrome","safari","firefox"]:
        r=cr.get(u,impersonate=imp); print("SO curl_cffi",imp,r.status_code,len(r.text))
        if r.status_code==200:
            t=r.content.decode('iso-8859-1')
            show("SO search", t, [r'/Spiel/[^"]+\.html', r'lieferbar|Vorbestell|erscheint', r'&euro;|€'])
            links=re.findall(r'href="(?:https://www\.spiele-offensive\.de)?(/Spiel/[^"]+\.html)"', t); print("links",links[:8])
            if links:
                p=cr.get("https://www.spiele-offensive.de"+links[0],impersonate=imp).content.decode('iso-8859-1')
                show("SO product", p, [r'itemprop="price"|"price"', r'application/ld\+json', r'lieferbar|Vorbestell|erscheint'])
            break
except Exception as e: print("curl_cffi err",e)
p=requests.get("https://www.spieletastisch.de/produkte/12254-gaudi-gaudi-de",headers=H).text
show("ST product", p, [r'\d+,\d\d\s*(&nbsp;)?(€|&euro;)', r'Erscheinungsdatum', r'lieferbar', r'og:|product:'], 300, 4)
j=requests.get("https://spielefuerst.de/products/greenwood.js",headers=H); print("\nSF js",j.status_code,j.text[:300])
j=requests.get("https://spielefuerst.de/search/suggest.json?q=Greenwood&resources[type]=product",headers=H).json()
for x in j["resources"]["results"]["products"]: print("SF", x["title"], x["price"], x["available"], x["url"], x.get("tags"))
