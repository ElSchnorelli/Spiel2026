# Spiel 2026 Top 50

Web-App zu den 50 meistgesuchten Spielen der SPIEL Essen 2026 laut
[BGG Most-Wanted-Tracker](https://boardgamegeek.com/geeklist/381572/spiel-26-most-wanted-games-tracker):
BGG-Bewertung, Komplexität, deutsche Ausgabe (BGG-Reiter „Versions") und Preis/Verfügbarkeit bei
Spiele-Offensive, Spielefürst und Spieletastisch.

Die fertige Seite liegt in `docs/index.html` und wird per GitHub Pages veröffentlicht.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `data/top50.json` | Top 50 aus der Geekliste (Platz, BGG-ID, Name, Autoren, Coverbild) |
| `data/rohdaten/<platz>.json` | Pro Spiel: BGG-Werte, deutsche Ausgabe, Shoptreffer, Notizen zu unsicheren Werten |
| `data/meta.json` | Datenstand |
| `template.html` | Oberfläche (Filter, Sortierung, Shoptabelle) |
| `scripts/build.py` | baut `docs/index.html`, `docs/daten.json` und `docs/spiel2026-daten.json` |
| `scripts/shops.py` | fragt Preise und Verfügbarkeit in den drei Shops neu ab |

## Preise und Verfügbarkeit abfragen

Der Button „Verfügbarkeit jetzt abfragen“ auf der Seite startet den Workflow
`.github/workflows/aktualisieren.yml`. Er ruft `scripts/shops.py` auf, das alle drei Shops abfragt
(bekannte Produktseiten direkt, sonst über die Shopsuche), committet die neuen Daten und veröffentlicht
die Seite neu. Das dauert etwa 7 bis 10 Minuten.

Damit der Button den Workflow starten darf, braucht er einmalig einen Fine-grained Token mit Zugriff
nur auf dieses Repo und der Berechtigung „Actions: Read and write“. Der Token wird nur im Browser
(localStorage) gespeichert. Ohne Token lässt sich der Workflow auch direkt unter
Actions → „Verfügbarkeit abfragen“ → „Run workflow“ starten.

Lokal: `pip install curl_cffi && python3 scripts/shops.py [platz ...]`

## Alles neu erheben (BGG-Daten, Top 50)

1. Daten neu erheben: Top 50 aus der Geekliste, je Spiel BGG-Seite + `/versions`, Shopsuche
   (Spiele-Offensive `index.php?cmd=suchergebnis&suchwort=…`, Spielefürst `search/suggest.json?q=…`,
   Spieletastisch über Websuche `site:spieletastisch.de …`, da die Shopsuche nur per Formular geht).
2. `data/top50.json`, `data/rohdaten/*.json` und `data/meta.json` überschreiben.
3. `python3 scripts/build.py` und committen.
