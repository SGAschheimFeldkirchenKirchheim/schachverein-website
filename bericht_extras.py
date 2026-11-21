"""
Partien (PGN) und chess-results-Tabellen in Berichten.

In Bericht.typ (schreibt der Editor auf der Website, geht aber auch von Hand):
  #partie("partie1.pgn", ab: 19, sicht: "w")   PGN-Datei im selben Ordner
        ab    = Halbzug, bei dem das Brett startet (0 = Grundstellung, -1 = Schlussstellung)
        sicht = "w" oder "b" (diese Farbe steht unten)
        ergebnis: "ende" = Ergebnis erst nach dem letzten Zug zeigen (sonst oben neben den Namen)
  #partien("partie1.pgn", ergebnis: "ende")    mehrere Partien in einer PGN-Datei: eine Tabelle, ein Brett
        (z. B. Mannschaftskampf; mit [WhiteTeam]/[BlackTeam] in der PGN gibt es den Endstand dazu)
  #tabelle("https://chess-results.com/tnr1171232.aspx")   Endtabelle bzw. aktueller Stand

Im Browser: partie.js (Brett: lib/partien/chessground, Regeln: lib/partien/chess.js).
"""

import datetime
import html
import json
import os
import re
import time

import chessresults

# ==========================================
# EINSTELLUNGEN
# ==========================================
TABELLE_SICHTBAR = 10            # so viele Plätze sofort, der Rest klappt auf
AKTUALISIEREN_TAGE = 30          # so lange nach dem Berichtsdatum wird die Tabelle bei jedem Build neu geholt
CACHE_ORDNER = os.path.join("berichte", "_cache_chessresults")
CACHE_MINUTEN = 60

SAMMLUNG_RE = re.compile(r'^#partien\(\s*"([^"]+)"\s*((?:,\s*\w+\s*:\s*(?:"[^"]*"|-?\d+)\s*)*)\)\s*$')
PARTIE_RE = re.compile(r'^#partie\(\s*"([^"]+)"\s*((?:,\s*\w+\s*:\s*(?:"[^"]*"|-?\d+)\s*)*)\)\s*$')
TABELLE_RE = re.compile(r'^#tabelle\(\s*"([^"]+)"\s*\)\s*$')
TNR_RE = re.compile(r'^https?://(?:[\w-]+\.)?chess-results\.com/(?:\w+/)?tnr(\d+)\.aspx', re.I)

esc = lambda s: html.escape(str(s), quote=True)


def kopf_html():
    """Zusätzliche <head>-Zeilen für Seiten mit Partien (Pfad relativ zu berichte/)."""
    return ('<link rel="stylesheet" href="../lib/partien/chessground.base.css">'
            '<link rel="stylesheet" href="../lib/partien/chessground.cburnett.css">')


SKRIPT = '<script type="module" src="../partie.js"></script>'


# ==========================================
# PARTIE
# ==========================================
def partie_html(ordner, zeile, warnung):
    m = PARTIE_RE.match(zeile)
    if not m:
        return None
    name = m.group(1)
    if os.path.basename(name) != name or not name.lower().endswith(".pgn"):
        warnung(f"Partie '{name}' ungültig (nur .pgn-Datei aus demselben Ordner).")
        return ""
    pfad = os.path.join(ordner, name)
    try:
        with open(pfad, encoding="utf-8-sig") as f:
            pgn = f.read().strip()
    except OSError:
        warnung(f"Partie '{name}' nicht gefunden.")
        return ""
    args = dict(re.findall(r'(\w+)\s*:\s*"?(-?[\w]+)"?', m.group(2) or ""))
    try:
        ab = int(args.get("ab", 0))
    except ValueError:
        ab = 0
    daten = {"pgn": pgn, "ab": ab, "sicht": "b" if args.get("sicht") == "b" else "w"}
    if args.get("ergebnis") == "ende":
        daten["ergebnis"] = "ende"
    return f'<figure class="pz" data-partie="{esc(json.dumps(daten, ensure_ascii=False))}"><noscript>Zum Nachspielen der Partie bitte JavaScript einschalten.</noscript></figure>'


def sammlung_html(ordner, zeile, warnung):
    m = SAMMLUNG_RE.match(zeile)
    if not m:
        return None
    name = m.group(1)
    if os.path.basename(name) != name or not name.lower().endswith(".pgn"):
        warnung(f"Partien '{name}' ungültig (nur .pgn-Datei aus demselben Ordner).")
        return ""
    try:
        with open(os.path.join(ordner, name), encoding="utf-8-sig") as f:
            pgn = f.read().strip()
    except OSError:
        warnung(f"Partien '{name}' nicht gefunden.")
        return ""
    args = dict(re.findall(r'(\w+)\s*:\s*"?(-?[\w]+)"?', m.group(2) or ""))
    daten = {"pgn": pgn}
    if args.get("ergebnis") == "ende":
        daten["ergebnis"] = "ende"
    return f'<div class="ps" data-sammlung="{esc(json.dumps(daten, ensure_ascii=False))}"><noscript>Zum Nachspielen der Partien bitte JavaScript einschalten.</noscript></div>'


# ==========================================
# CHESS-RESULTS-TABELLE
# ==========================================
def _cache_pfad(tnr):
    return os.path.join(CACHE_ORDNER, f"{tnr}.html")


def _seite(tnr, berichtsdatum):
    """HTML der Endrangliste (art=1). Neu geholt, solange der Bericht frisch ist; danach nur Cache."""
    pfad = _cache_pfad(tnr)
    alter = (time.time() - os.path.getmtime(pfad)) / 60 if os.path.exists(pfad) else None
    heute = datetime.date.today()
    frisch = berichtsdatum is None or (heute - berichtsdatum).days <= AKTUALISIEREN_TAGE
    if alter is not None and (not frisch or alter < CACHE_MINUTEN):
        return open(pfad, encoding="utf-8").read(), os.path.getmtime(pfad), False
    url = chessresults.URL.format(tnr=tnr, art=1)
    try:
        time.sleep(chessresults.PAUSE_SEKUNDEN)
        text = chessresults._hole(url)
    except Exception as e:
        if alter is not None:
            print(f"Hinweis: chess-results nicht erreichbar ({e}) – nehme Cache für tnr {tnr}")
            return open(pfad, encoding="utf-8").read(), os.path.getmtime(pfad), True
        print(f"WARNUNG: chess-results nicht erreichbar ({e}) – Tabelle tnr {tnr} fehlt im Bericht")
        return None, None, False
    os.makedirs(CACHE_ORDNER, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(text)
    return text, time.time(), False


def tabelle_html(zeile, berichtsdatum, warnung):
    m = TABELLE_RE.match(zeile)
    if not m:
        return None
    url = m.group(1)
    t = TNR_RE.match(url)
    if not t:
        warnung(f"Tabelle: '{url}' ist kein chess-results-Link.")
        return ""
    if chessresults.BeautifulSoup is None:
        warnung("beautifulsoup4 fehlt (pip install beautifulsoup4) – chess-results-Tabelle übersprungen.")
        return ""
    tnr = t.group(1)
    text, stand, fehler = _seite(tnr, berichtsdatum)
    tabs = chessresults.tabellen(text)
    link = chessresults.URL.format(tnr=tnr, art=1)
    if not tabs:
        return (f'<p class="cr-box-leer">Tabelle: <a href="{esc(link)}" target="_blank" rel="noopener">'
                f'auf chess-results.com ansehen ↗</a></p>')
    kopf, zeilen = chessresults.spalten_filtern(*tabs[0])
    name = chessresults.turniername(text) or "Tabelle"
    zahl = lambda s: bool(re.fullmatch(r"[\d,.½+\-– :]*", s.strip()))

    def zeile_html(z):
        cls = ' class="eigen"' if chessresults.eigene_zeile(z) else ""
        return f"<tr{cls}>" + "".join(f'<td{"" if zahl(c) else " class=name"}>{esc(c)}</td>' for c in z) + "</tr>"

    sofort = "".join(zeile_html(z) for z in zeilen[:TABELLE_SICHTBAR])
    rest = "".join(zeile_html(z) for z in zeilen[TABELLE_SICHTBAR:])
    kopfzeile = "".join(f'<th{"" if i == 0 or not any(not zahl(z[i]) for z in zeilen if i < len(z)) else " class=name"}>{esc(k)}</th>'
                        for i, k in enumerate(kopf))
    stand_txt = datetime.datetime.fromtimestamp(stand).strftime("%d.%m.%Y") if stand else ""
    return f"""<figure class="cr-box">
  <figcaption><b>{esc(name)}</b><span class="klein">{len(zeilen)} Spieler{f" · Stand {stand_txt}" if stand_txt else ""} · <a href="{esc(link)}" target="_blank" rel="noopener">chess-results.com ↗</a></span></figcaption>
  {'<p class="cr-warnung">chess-results war nicht erreichbar – letzter gespeicherter Stand.</p>' if fehler else ""}
  <div class="tab-wrap"><table class="cr-tab"><thead><tr>{kopfzeile}</tr></thead><tbody>{sofort}</tbody>{f'<tbody class="cr-rest" hidden>{rest}</tbody>' if rest else ""}</table></div>
  {f'<button type="button" class="cr-mehr" onclick="this.parentNode.querySelector(&quot;.cr-rest&quot;).hidden=false;this.remove()">Ganze Tabelle anzeigen ({len(zeilen)} Spieler)</button>' if rest else ""}
</figure>"""


def handler(ordner, berichtsdatum, warnung):
    """Für build_site.report_blocks: Zeile -> HTML (oder None, wenn die Zeile nichts von uns ist).
    handler.partien zählt mit, ob die Seite partie.js braucht."""
    def h(zeile):
        if zeile.startswith("#partien("):
            out = sammlung_html(ordner, zeile, warnung)
            if out:
                h.partien += 1
            return out
        if zeile.startswith("#partie("):
            out = partie_html(ordner, zeile, warnung)
            if out:
                h.partien += 1
            return out
        if zeile.startswith("#tabelle("):
            return tabelle_html(zeile, berichtsdatum, warnung)
        return None
    h.partien = 0
    return h
