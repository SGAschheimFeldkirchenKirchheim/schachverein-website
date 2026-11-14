"""
Laufende Vereinsturniere von chess-results.com auf der Website (Tabelle, Paarungen, Kreuztabelle).

Einrichten: in turniere/chessresults.json ein Turnier mit seiner chess-results-Nummer eintragen
(die Zahl hinter "tnr" in der Adresse, z. B. https://chess-results.com/tnr1171232.aspx -> 1171232).
build_site.py ruft bauen(render_page) auf; jede Seite steht danach unter "Turniere".

Abrufe werden in turniere/chessresults_cache/ zwischengespeichert:
  - laufendes Turnier: höchstens alle CACHE_MINUTEN neu laden
  - "abgeschlossen": true -> nur noch aus dem Cache (chess-results wird nicht mehr gefragt)
  - chess-results nicht erreichbar -> letzter Stand aus dem Cache, mit Hinweis auf der Seite
"""

import datetime
import html
import json
import os
import re
import time

import urllib.request

try:
    import requests
except ImportError:          # Fallback ohne requests (z. B. auf GitHub ohne pip install)
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:          # ohne beautifulsoup4 werden keine Turnierseiten gebaut (Website-Build läuft weiter)
    BeautifulSoup = None

# ==========================================
# EINSTELLUNGEN
# ==========================================
KONFIG = os.path.join("turniere", "chessresults.json")
CACHE_ORDNER = os.path.join("turniere", "chessresults_cache")
CACHE_MINUTEN = 60
URL = "https://chess-results.com/tnr{tnr}.aspx?lan=0&art={art}&turdet=YES&SNode=S0"
MAX_RUNDEN = 15                       # so weit wird gesucht, wenn die Rundenzahl unbekannt ist
PAUSE_SEKUNDEN = 1.0                  # zwischen zwei Abrufen (chess-results schonen)

# Reiter: (Schlüssel, Beschriftung, art-Parameter). Paarungen (art=2) kommen automatisch dazu.
ANSICHTEN = [
    ("tabelle", "Tabelle", 1),
    ("kreuz", "Kreuztabelle", 4),
    ("start", "Teilnehmer", 0),
]
PAARUNGEN_TEXT = "Paarungen"

# Eigene Spieler hervorheben: Muster für die Vereinsspalte (oder die ganze Zeile)
VEREIN_MUSTER = r"Aschheim|Feldkirchen|Kirchheim|\bAFK\b"
# Spalten, die nicht angezeigt werden (Überschrift wie bei chess-results, Groß-/Kleinschreibung egal)
WEG_SPALTEN = {"", "land", "fed", "typ", "gr", "sex", "k", "fide-id", "id"}

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
           "Accept-Language": "de-DE,de;q=0.9"}


# ==========================================
# ABRUF + CACHE
# ==========================================
def lade_konfig():
    try:
        with open(KONFIG, encoding="utf-8") as f:
            return json.load(f).get("turniere") or []
    except (OSError, ValueError) as e:
        if os.path.exists(KONFIG):
            print(f"WARNUNG: {KONFIG} nicht lesbar ({e}).")
        return []


def _cache_pfad(tnr, art, rd):
    return os.path.join(CACHE_ORDNER, f"{tnr}-art{art}" + (f"-rd{rd}" if rd else "") + ".html")


def _hole(url):
    if requests:
        r = requests.get(url, headers=HEADERS, timeout=(10, 25))
        r.raise_for_status()
        return r.text
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


class Abruf:
    """Merkt sich, ob Daten frisch oder aus dem Cache kommen."""

    def __init__(self, tnr, abgeschlossen):
        self.tnr, self.abgeschlossen = tnr, abgeschlossen
        self.aus_cache_wegen_fehler = False
        self.stand = None

    def seite(self, art, rd=None):
        pfad = _cache_pfad(self.tnr, art, rd)
        alter = (time.time() - os.path.getmtime(pfad)) / 60 if os.path.exists(pfad) else None
        if alter is not None and (self.abgeschlossen or alter < CACHE_MINUTEN):
            return self._lies(pfad)
        url = URL.format(tnr=self.tnr, art=art) + (f"&rd={rd}" if rd else "")
        try:
            time.sleep(PAUSE_SEKUNDEN)
            text = _hole(url)
        except Exception as e:
            if alter is not None:
                print(f"Hinweis: chess-results nicht erreichbar ({e}) – nehme Cache für {url}")
                self.aus_cache_wegen_fehler = True
                return self._lies(pfad)
            print(f"WARNUNG: chess-results nicht erreichbar ({e}) – {url}")
            return None
        os.makedirs(CACHE_ORDNER, exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(text)
        self._merke_stand(time.time())
        return text

    def _lies(self, pfad):
        self._merke_stand(os.path.getmtime(pfad))
        with open(pfad, encoding="utf-8") as f:
            return f.read()

    def _merke_stand(self, ts):
        self.stand = max(self.stand or 0, ts)


# ==========================================
# PARSEN (allgemein: Tabellen mit class="CRs1")
# ==========================================
def tabellen(text):
    """-> Liste von (Kopf, Zeilen) aller CRs1-Tabellen; Zellen als Text."""
    if not text:
        return []
    soup = BeautifulSoup(text, "html.parser")
    aus = []
    for t in soup.find_all("table", class_="CRs1"):
        rows = [[re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"])]
                for tr in t.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if len(rows) >= 2:
            aus.append((rows[0], [r for r in rows[1:] if len(r) >= len(rows[0]) - 1]))
    return aus


def turniername(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    h2 = soup.find("h2")
    return h2.get_text(" ", strip=True) if h2 else ""


def runden_aus_links(text):
    if not text:
        return 0
    nummern = [int(m) for m in re.findall(r"art=2[^\"'>]*?rd=(\d+)", text)]
    return max(nummern, default=0)


def spalten_filtern(kopf, zeilen):
    """Unnötige und komplett leere Spalten weg."""
    behalten = [i for i, k in enumerate(kopf)
                if k.strip().lower().rstrip(".") not in WEG_SPALTEN
                and any(i < len(z) and z[i].strip() for z in zeilen)]
    # Name immer behalten, auch wenn die Überschrift fehlt
    return [kopf[i] for i in behalten], [[z[i] if i < len(z) else "" for i in behalten] for z in zeilen]


def eigene_zeile(zeile):
    return bool(re.search(VEREIN_MUSTER, " ".join(zeile), re.I))


def ergebnis_da(zeilen):
    return any(re.search(r"\d\s*[-:]\s*\d|½|\+\s*[-:]\s*-|-\s*[-:]\s*\+", " ".join(z)) for z in zeilen)


# ==========================================
# HTML
# ==========================================
def esc(x):
    return html.escape(str(x), quote=True)


def eigene_namen(kopf, zeilen):
    """Namen unserer Spieler aus einer Tabelle mit Vereinsspalte (für die Paarungen ohne Verein)."""
    i = next((i for i, k in enumerate(kopf) if k.strip().lower() == "name"), None)
    return {z[i] for z in zeilen if i is not None and i < len(z) and eigene_zeile(z)}


def tabelle_html(kopf, zeilen, klasse="", namen=frozenset()):
    zahl = lambda s: bool(re.fullmatch(r"[\d,.½+\-– :]*", s.strip()))
    kopfzeile = "".join(f"<th>{esc(k)}</th>" for k in kopf)
    body = []

    def zelle(c):
        cls = "" if zahl(c) else "name"
        if c in namen:
            cls += " eigen-name"
        return f'<td class="{cls.strip()}">{esc(c)}</td>' if cls else f"<td>{esc(c)}</td>"

    for z in zeilen:
        cls = ' class="eigen"' if eigene_zeile(z) else ""
        body.append(f"<tr{cls}>" + "".join(zelle(c) for c in z) + "</tr>")
    return (f'<div class="tab-wrap"><table class="liga-tab cr-tab {klasse}"><thead><tr>{kopfzeile}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def turnier_seite(t, render_page):
    tnr = t.get("tnr")
    abruf = Abruf(tnr, bool(t.get("abgeschlossen")))
    reiter, inhalte = [], []
    erste, namen = None, set()
    for key, titel, art in ANSICHTEN:
        if key in (t.get("ohne") or []):
            continue
        text = abruf.seite(art)
        erste = erste or text
        tabs = tabellen(text)
        if not tabs:
            continue
        namen |= eigene_namen(*tabs[0])
        kopf, zeilen = spalten_filtern(*tabs[0])
        reiter.append((key, titel))
        inhalte.append((key, tabelle_html(kopf, zeilen, f"cr-{key}")))

    runden = t.get("runden") or runden_aus_links(erste)
    paarungen, letzte_mit_paarung = [], 0
    for rd in range(1, (runden or MAX_RUNDEN) + 1):
        tabs = tabellen(abruf.seite(2, rd))
        if not tabs:
            if not runden:
                break               # Rundenzahl unbekannt: erste leere Runde = Ende
            continue
        kopf, zeilen = spalten_filtern(*tabs[0])
        paarungen.append((rd, tabelle_html(kopf, zeilen, "cr-paar", namen), ergebnis_da(zeilen)))
        letzte_mit_paarung = rd
    if paarungen:
        offen = next((rd for rd, _, erg in reversed(paarungen) if erg), letzte_mit_paarung)
        offen = max(offen, letzte_mit_paarung) if not t.get("abgeschlossen") else offen
        bloecke = "".join(f'<details class="cr-runde"{" open" if rd == offen else ""}>'
                          f'<summary>Runde {rd}{"" if erg else " <span class=klein>(noch keine Ergebnisse)</span>"}'
                          f'</summary>{h}</details>' for rd, h, erg in reversed(paarungen))
        reiter.insert(1, ("paar", PAARUNGEN_TEXT))
        inhalte.insert(1, ("paar", bloecke))

    name = t.get("name") or turniername(erste) or "Turnier"
    if not reiter:
        print(f"WARNUNG: {name} (tnr {tnr}): keine Daten von chess-results – Seite wird nicht gebaut.")
        return False

    stand = datetime.datetime.fromtimestamp(abruf.stand).strftime("%d.%m.%Y %H:%M") if abruf.stand else "–"
    warnung = ('<p class="cr-warnung">chess-results war beim letzten Aktualisieren nicht erreichbar – '
               'hier steht der letzte gespeicherte Stand.</p>' if abruf.aus_cache_wegen_fehler else "")
    knoepfe = "".join(f'<button type="button" class="cr-knopf{" aktiv" if i == 0 else ""}" data-ziel="{k}">{esc(ti)}</button>'
                      for i, (k, ti) in enumerate(reiter))
    teile = "".join(f'<section class="cr-teil" data-teil="{k}"{"" if i == 0 else " hidden"}>{h}</section>'
                    for i, (k, h) in enumerate(inhalte))
    link = URL.format(tnr=tnr, art=1)
    content = f"""
      <a href="turniere.html" style="text-decoration:none;">← Turniere</a>
      <h1>{esc(name)}</h1>
      {f'<p class="lead">{esc(t["text"])}</p>' if t.get("text") else ""}
      {warnung}
      <div class="cr-reiter" role="tablist">{knoepfe}</div>
      {teile}
      <p class="klein">Stand: {stand} · Quelle: <a href="{esc(link)}" target="_blank" rel="noopener">chess-results.com</a>
        · Unsere Spieler sind hervorgehoben.</p>
      <script>
      document.querySelectorAll(".cr-knopf").forEach(function (b) {{
        b.addEventListener("click", function () {{
          document.querySelectorAll(".cr-knopf").forEach(function (x) {{ x.classList.toggle("aktiv", x === b); }});
          document.querySelectorAll(".cr-teil").forEach(function (s) {{ s.hidden = s.dataset.teil !== b.dataset.ziel; }});
        }});
      }});
      </script>"""
    render_page(name, content, t["seite"], extra_styles="<style>" + CSS + "</style>",
                description=f"{name}: Tabelle, Paarungen und Ergebnisse.")
    t["_name"] = name
    return True


def bauen(render_page):
    """Baut alle eingetragenen Turniere. -> Liste (Seite, Name, Text) der gebauten Seiten."""
    gebaut = []
    turniere = [t for t in lade_konfig() if t.get("tnr") and t.get("seite") and not t.get("aus")]
    if turniere and BeautifulSoup is None:
        print("WARNUNG: beautifulsoup4 fehlt (pip install beautifulsoup4) – keine Turnierseiten von chess-results.")
        return gebaut
    for t in lade_konfig():
        if not t.get("tnr") or not t.get("seite") or t.get("aus"):
            continue
        try:
            if turnier_seite(t, render_page):
                gebaut.append((t["seite"], t["_name"], t.get("text") or "Tabelle, Paarungen und Ergebnisse."))
        except Exception as e:          # ein kaputtes Turnier soll den Website-Build nicht stoppen
            print(f"WARNUNG: Turnier {t.get('name')} (tnr {t.get('tnr')}) nicht gebaut: {e}")
    # alte Cache-Dateien von Turnieren, die nicht mehr eingetragen sind, löschen
    aktiv = {str(t.get("tnr")) for t in lade_konfig() if t.get("tnr")}
    if os.path.isdir(CACHE_ORDNER):
        for f in os.listdir(CACHE_ORDNER):
            if f.split("-")[0] not in aktiv:
                os.remove(os.path.join(CACHE_ORDNER, f))
    return gebaut


CSS = """
      .cr-reiter { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 1rem 0 0.8rem; }
      .cr-knopf { font: inherit; cursor: pointer; border: 1px solid var(--border); background: var(--soft); color: inherit;
                  border-radius: 999px; padding: 0.35rem 0.9rem; }
      .cr-knopf.aktiv { background: var(--navy); border-color: var(--navy); color: #fff; }
      .cr-tab { border-collapse: collapse; width: 100%; }
      .cr-tab th, .cr-tab td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--border); white-space: nowrap; text-align: center; }
      .cr-tab td.name { text-align: left; }
      .cr-tab tr.eigen td { background: rgba(230, 160, 20, 0.16); font-weight: 600; }
      .cr-tab td.eigen-name { background: rgba(230, 160, 20, 0.16); font-weight: 600; }
      .cr-runde { margin: 0.4rem 0; }
      .cr-runde > summary { cursor: pointer; font-weight: bold; padding: 0.4rem 0; }
      .cr-warnung { padding: 0.5rem 0.8rem; border-left: 4px solid #b9770e; background: #fdf2e0; color: #6e4a07; border-radius: 4px; }
      .tab-wrap { overflow-x: auto; }
"""
