"""
Mannschaften: Übersicht (mannschaften.html), eine Seite pro Team (afk-1.html ...)
und die "Letzten Ergebnisse" auf der Startseite.

Die Daten (mannschaften/*.json) schreibt der Tabellenrechner (py main.py website).
Darin steht SEINE Wertung nach TO §15, nicht die Tabelle vom Schachbezirk.
build_site.py ruft lade_teams(), uebersicht_seite(), team_seite() und ticker_html() auf.
"""

import glob
from urllib.parse import quote

import partien  # Reiter "Partien" (Partie-Viewer)
import spieler as spielerseiten  # Spielerseiten (spieler/<name>.html)
import aufstellung as auf        # Meldelisten mit Ergebnissen + Einsatz-Prognose (Einstellungen dort)
import re
import html
import json
import os
from datetime import datetime

# ==========================================
# EINSTELLUNGEN
# ==========================================
DATEN_ORDNER = "mannschaften"
SEITE = "{slug}.html"           # Dateiname der Team-Seite; slug aus "AFK 1" -> "afk-1"
DEZIMAL = ","                   # "." -> 3.5   |   "," -> 3,5
BP_IMMER_NACHKOMMA = True       # Brettpunkte in Tabellen immer mit Nachkommastelle (6.0, 6.5)

# Bretter pro Spielklasse. Gilt, solange in einer Liga noch kein Ergebnis steht
# (danach wird die Zahl aus den Ergebnissen erkannt). Einmal pflegen, gilt für alle Ligen & Saisons.
BRETTER = {
    "Bezirksliga": 8,
    "A-Klasse": 8,
    "B-Klasse": 7,
    "C-Klasse": 6,
    "D-Klasse": 6,
    "E-Klasse": 4,
    "1. Jugend-Bezirksliga": 4,
    "U20 Landesliga Süd": 4,
}
BRETTER_STANDARD = 8            # falls die Klasse oben fehlt

# Eigener (langer) Vereinsname in Tabellen -> kürzer; None = unverändert
#   {nr}   Mannschaftsnummer aus dem Namen beim Bezirk ("SG Aschheim/... 1" -> "1"; ohne Nummer leer)
#   {kurz} Name der Mannschaft auf der Website ("AFK 1", "Senioren")
EIGENER_NAME = "SG AFK {nr}"

# Reiter auf der Team-Seite (Reihenfolge = Anzeige; Eintrag löschen = Reiter weg)
REITER = [
    ("tabelle", "Tabelle"),
    ("spieltage", "Spieltage"),
    ("spiele", "Unsere Spiele"),
    ("partien", "Partien"),          # nur wenn Partien hochgeladen sind (Ligamanager), siehe partien.py
    ("aufstellung", "Aufstellung"),  # Meldeliste mit Ergebnissen je Runde (ohne Meldeliste: Spielerstatistik)
    ("verlauf", "Verlauf"),
    ("saisons", "Saisons"),          # Platz/Klasse aller Saisons (nur wenn es ein Archiv gibt)
    ("rechner", "Tabellenrechner"),  # nicht in abgeschlossenen Saisons
]
NICHT_IM_ARCHIV = {"rechner"}        # Reiter, die es in alten Saisons nicht gibt

# Zusätzliche Karten ohne Liga-Daten (nur in der Übersicht)
EXTRA_KARTEN = [
    {"name": "Jugendmannschaften", "kurz": "Jugend", "klasse": "Jugendrunden",
     "text": "Liga wird nachgetragen.", "url": None},
]

# Bretter: DWZ hinter dem Namen anzeigen; Namen anklicken
DWZ_AN_BRETTERN = True          # False = keine DWZ an den Brettern
GEGNER_VERLINKEN = True         # Gegner -> Spielerseite beim Schachbezirk (neuer Tab)
SPIELER_SEITEN = set()          # setzt build_site.py (eigene Spieler mit Spielerseite)
WURZEL = ""                     # Weg zur Website-Wurzel; build_site.py setzt "../../" für Archivseiten
VEREIN_INDEX = {}               # build_site.py: Mannschaften der aktuellen Saison nach Verein (Prognose)

# Vorbereitung: Knopf neben jedem Gegner-Spieler (Aufstellungs-Fenster + voraussichtliche Aufstellung).
# {nach} / {vor} = Nachname / Vorname, klein, Leerzeichen -> "-". None = kein Knopf.
VORBEREITUNG_URL = "https://players.chessbase.com/en/player/{nach}_{vor}"
VORBEREITUNG_TEXT = "Partien bei ChessBase"
ARCHIV_HINWEIS = "Archiv – abgeschlossene Saison {saison}."

TICKER_TITEL = "Letzte Ergebnisse"
ERGEBNIS_TEXT = {"s": "Sieg", "u": "Unentschieden", "n": "Niederlage"}
KEIN_TEAM = "spielfrei"


# ==========================================
# HILFSFUNKTIONEN
# ==========================================
def esc(x):
    return html.escape(str(x if x is not None else ""))


def zahl(x, fest=False):
    """3.0 -> '3' (fest: '3.0'), 3.5 -> '3.5'"""
    if x is None:
        return ""
    text = f"{x:.1f}" if fest or x % 1 else str(int(x))
    return text.replace(".", DEZIMAL)


def bp(x):
    return zahl(x, BP_IMMER_NACHKOMMA)


def stand_text(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y, %H:%M Uhr")
    except (TypeError, ValueError):
        return ""


def seite_datei(d):
    return SEITE.format(slug=d["kurz"].lower().replace(" ", "-"))


# ==========================================
# DATEN
# ==========================================
def bretter_aus_ergebnissen(d):
    """Höchste Summe der Brettpunkte eines gespielten Kampfes (None, wenn noch nichts gespielt)."""
    summen = [m["bh"] + m["bg"] for m in d.get("matches", []) if m.get("gesp") and not m.get("sf")]
    return int(max(summen)) if summen and max(summen) > 0 else None


def bretter_bestimmen(d):
    """Ergebnisse > Tabelle BRETTER (nach Klasse) > Angabe vom Tabellenrechner > BRETTER_STANDARD."""
    return (bretter_aus_ergebnissen(d) or BRETTER.get(d.get("klasse", "").strip())
            or d.get("bretter") or BRETTER_STANDARD)


def lade_teams(ordner=DATEN_ORDNER):
    teams = []
    for pfad in sorted(glob.glob(os.path.join(ordner, "*.json"))):
        try:
            with open(pfad, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            print(f"Hinweis: {pfad} nicht lesbar ({e})")
            continue
        if d.get("version") != 1 or d.get("tabelle") is None:
            continue
        if EIGENER_NAME and d.get("eigen") is not None:
            original = d["teams"].get(str(d["eigen"]), "")
            nr = re.search(r"(\d+)\s*$", original)
            d["teams"][str(d["eigen"])] = EIGENER_NAME.format(kurz=d["kurz"], nr=nr.group(1) if nr else "").strip()
        d.setdefault("runden_tabellen", {})
        d["bretter"] = bretter_bestimmen(d)
        teams.append(d)
    teams.sort(key=lambda d: (len(d["key"]), d["key"]))
    return teams


def name_von(d, tlnr):
    return d["teams"].get(str(tlnr), f"Team {tlnr}") if tlnr is not None else KEIN_TEAM


def sicht(d, m):
    """Aus Sicht der eigenen Mannschaft: (heim?, gegner, eigene BP, gegner BP, 's'/'u'/'n'/None)"""
    heim = m["h"] == d["eigen"]
    gegner = name_von(d, m["g"] if heim else m["h"])
    if not m["gesp"]:
        return heim, gegner, None, None, None
    mein, sein = (m["bh"], m["bg"]) if heim else (m["bg"], m["bh"])
    haelfte = (d["bretter"] or (mein + sein)) / 2
    art = "s" if mein > haelfte else "u" if mein == haelfte else "n"
    return heim, gegner, mein, sein, art


def eigene_spiele(d):
    return [m for m in d["matches"] if d["eigen"] in (m["h"], m["g"])]


def letztes_spiel(d):
    gespielt = [m for m in eigene_spiele(d) if m["gesp"] and not m.get("sf")]
    return gespielt[-1] if gespielt else None


def naechstes_spiel(d):
    return next((m for m in eigene_spiele(d) if not m["gesp"]), None)


def eigene_zeile(d, tabelle=None):
    return next((r for r in (tabelle or d["tabelle"]) if r["tlnr"] == d["eigen"]), None)


# ==========================================
# BAUSTEINE
# ==========================================
def ergebnis_badge(art, mein, sein):
    if art is None:
        return '<span class="erg erg-offen">offen</span>'
    return f'<span class="erg erg-{art}" title="{ERGEBNIS_TEXT[art]}">{zahl(mein)} : {zahl(sein)}</span>'


def spiel_text(d, m):
    if m.get("sf"):
        return KEIN_TEAM
    heim, gegner, *_ = sicht(d, m)
    return f'{"vs." if heim else "bei"} {esc(gegner)}'


def tabelle_html(d, tabelle, mit_delta=None):
    """mit_delta: {tlnr: Platz vorher} -> ▲▼ anzeigen"""
    n = len(tabelle)
    zeilen = []
    for i, r in enumerate(tabelle):
        klassen = []
        if r["tlnr"] == d["eigen"]:
            klassen.append("eigen")
        if d.get("auf") and i < d["auf"]:
            klassen.append("auf")
        if d.get("ab") and i >= n - d["ab"]:
            klassen.append("ab")
        auf, ab = d.get("auf") or 0, d.get("ab") or 0
        if d.get("auf_evtl") and auf <= i < auf + d["auf_evtl"]:
            klassen.append("auf-evtl")
        if d.get("ab_evtl") and n - ab - d["ab_evtl"] <= i < n - ab:
            klassen.append("ab-evtl")
        if (d.get("auf") and i == d["auf"]) or (d.get("ab") and i == n - d["ab"]):
            klassen.append("trenn")
        cls = f' class="{" ".join(klassen)}"' if klassen else ""
        delta = ""
        if mit_delta is not None:
            v = mit_delta.get(r["tlnr"], r["platz"]) - r["platz"]
            delta = (f'<span class="delta hoch">▲{v}</span>' if v > 0 else
                     f'<span class="delta runter">▼{-v}</span>' if v < 0 else "")
            delta = f"<td>{delta}</td>"
        zeilen.append(
            f'<tr{cls}><td>{r["platz"]}</td>{delta}<td class="name">{team_knopf(d, r["tlnr"])}</td>'
            f'<td>{r["sp"]}</td><td><strong>{r["mp"]}</strong></td><td>{bp(r["bp"])}</td>'
            f'<td class="neben">{r["siege"]}</td><td class="neben">{r["gp"]}</td></tr>')
    delta_kopf = "<th></th>" if mit_delta is not None else ""
    return f"""
      <div class="tab-wrap"><table class="liga-tab">
        <thead><tr><th>Rg</th>{delta_kopf}<th class="name">Mannschaft</th><th title="Spiele">Sp</th>
          <th title="Mannschaftspunkte">MP</th><th title="Brettpunkte">BP</th>
          <th class="neben" title="Mannschaftssiege">Siege</th><th class="neben" title="Gewinnpartien">GewP</th></tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>{auf_ab_legende(d)}"""


def kader_von(d, tlnr):
    return (d.get("kader_alle") or {}).get(str(tlnr)) or (d.get("kader") if tlnr == d.get("eigen") else None) or []


def team_knopf(d, tlnr):
    """Mannschaftsname; mit Meldeliste als Knopf, der das Aufstellungs-Fenster öffnet."""
    if not kader_von(d, tlnr):
        return esc(name_von(d, tlnr))
    return (f'<button type="button" class="team-knopf" data-tlnr="{tlnr}" '
            f'title="Aufstellung anzeigen">{esc(name_von(d, tlnr))}</button>')


def team_url(d, tlnr):
    url = d.get("url_team") or ""
    return re.sub(r"tlnr=\d+", f"tlnr={tlnr}", url) if "tlnr=" in url else None


def _prognose(d, tlnr):
    """-> ({Name: p}, {neue Spieler}) fürs nächste Spiel (Spielort automatisch)."""
    verein = auf.andere_teams(VEREIN_INDEX, d, tlnr) if VEREIN_INDEX else None
    return auf.prognose(d, tlnr, d.get("historie_ereignisse") or [], d.get("bretter") or 0,
                        kader=kader_von(d, tlnr), verein=verein)


def vorbereitung_html(k):
    """Kleiner Link zu den Partien des Spielers (Profil bei ChessBase)."""
    if not VORBEREITUNG_URL:
        return ""
    roh = k.get("roh") or ""
    if "," in roh:
        nach, _, vor = roh.partition(",")
    else:                                   # ältere Daten ohne "roh": letztes Wort = Nachname
        vor, _, nach = k["name"].strip().rpartition(" ")
    teil = lambda x: quote(re.sub(r"\s+", "-", x.strip().lower()))
    if not nach.strip():
        return ""
    url = VORBEREITUNG_URL.format(nach=teil(nach), vor=teil(vor.split()[0] if vor.split() else ""))
    return (f' <a class="vorb" href="{esc(url)}" target="_blank" rel="noopener" '
            f'title="{esc(VORBEREITUNG_TEXT)}" aria-label="{esc(VORBEREITUNG_TEXT)}">♞</a>')


def chance_html(p, neu=False):
    if neu:
        return '<span class="chance neu" title="noch keine Einsätze bekannt">neu</span>'
    pr = round(100 * p)
    return f'<span class="chance" style="--p:{pr}%">{pr} %</span>'


def aufstellung_tabelle(d, tlnr):
    """Meldeliste wie beim Bezirk: Nr, Stamm, Name, DWZ, Ergebnis je Runde, Pkt, Spl +
    eigene Mannschaft: Einsätze (gespielt / Runden) | Gegner: Prognose fürs nächste Spiel."""
    eigen = tlnr == d.get("eigen")
    kader = list(kader_von(d, tlnr))
    runden, res = auf.ergebnisse(d, tlnr)
    namen = {k["name"] for k in kader}
    kader += [{"name": n, "nr": None, "ersatz": True} for n in res if n not in namen]
    p, neu = ({}, set()) if eigen or d.get("archiv") else _prognose(d, tlnr)
    alle_runden = range(1, (d.get("runden") or max(runden, default=0)) + 1)
    zeilen = []
    for k in kader:
        rs = res.get(k["name"], {})
        pkt = sum(x["p"] for x in rs.values() if x["p"] is not None)
        spl = sum(1 for x in rs.values() if x["p"] is not None)
        zellen = "".join(f'<td class="neben rd-erg{" kl" if rs.get(r, {}).get("t") in ("+", "–") else ""}">'
                         f'{rs.get(r, {}).get("t", "")}</td>' for r in alle_runden)
        if eigen:
            name = spieler_html(k["name"], None, None, True)
            letzte = f'<td>{sum(1 for x in rs.values() if x["e"])}/{len(runden)}</td>' if runden else "<td>–</td>"
        else:
            name = (f'<a class="sp-link" href="{esc(k["url"])}" target="_blank" rel="noopener">{esc(k["name"])}</a>'
                    if k.get("url") else esc(k["name"])) + vorbereitung_html(k)
            letzte = f'<td>{chance_html(p[k["name"]], k["name"] in neu)}</td>' if k["name"] in p else "<td></td>"
        titel = f'<span class="titel">{esc(k["titel"])}</span> ' if k.get("titel") else ""
        cls = ' class="ersatz"' if k.get("ersatz") else ""
        zeilen.append(f'<tr{cls}><td>{k.get("nr") or "–"}</td><td class="neben">{"x" if k.get("stamm") else ""}</td>'
                      f'<td class="name">{titel}{name}</td><td>{k.get("dwz") or ""}</td>{zellen}'
                      f'<td>{zahl(pkt) if spl else ""}</td><td>{spl or ""}</td>{letzte}</tr>')
    rkopf = "".join(f'<th class="neben">{r}</th>' for r in alle_runden)
    letzte_kopf = ('<th title="gespielte Runden von bisher gespielten Runden">Einsätze</th>' if eigen else
                   "" if not p else '<th title="geschätzte Wahrscheinlichkeit für einen Einsatz im nächsten Spiel">Prognose</th>')
    return f"""
      <div class="tab-wrap"><table class="liga-tab aufst">
        <thead><tr><th>Nr</th><th class="neben" title="Stammspieler">St</th><th class="name">Name</th><th>DWZ</th>
          {rkopf}<th title="Punkte">Pkt</th><th title="gespielte Partien">Spl</th>{letzte_kopf}</tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>"""


LEGENDE_EIGEN = ("<strong>Einsätze</strong> = gespielte Runden von bisher gespielten Runden "
                 "(kein Prozent, keine Prognose).")
LEGENDE_GEGNER = ("<strong>Prognose</strong> = geschätzte Wahrscheinlichkeit, dass der Spieler im nächsten "
                  "Spiel dabei ist – aus seinen Einsätzen (letzte Runden zählen mehr als frühere, frühere Saisons "
                  "weniger, Heim/Auswärts berücksichtigt). <strong>neu</strong> = noch keine Einsätze bekannt. "
                  "Nur eine Statistik.")


VARIANTEN = 3                   # so viele wahrscheinlichste Aufstellungen beim nächsten Gegner


def vorschau_html(d, tlnr):
    """Die wahrscheinlichsten Aufstellungen einer Mannschaft im nächsten Spiel (Brettfolge = Meldereihenfolge)."""
    kader, n = kader_von(d, tlnr), d.get("bretter") or 0
    if not kader or not n or d.get("archiv"):
        return ""
    p, neu = _prognose(d, tlnr)
    varianten = auf.top_aufstellungen(kader, p, n, VARIANTEN)
    if not varianten:
        return ""
    erste = {k["name"] for k in varianten[0][1]}
    spalten = []
    for i, (wk, liste) in enumerate(varianten, 1):
        dwz = [k["dwz"] for k in liste if k.get("dwz")]
        schnitt = f"Ø {round(sum(dwz) / len(dwz))}" if dwz else ""
        zeilen = []
        for b, k in enumerate(liste, 1):
            titel = f'<span class="titel">{esc(k["titel"])}</span> ' if k.get("titel") else ""
            anders = i > 1 and k["name"] not in erste
            chance = chance_html(p.get(k["name"], 0), k["name"] in neu) if i == 1 else ""
            cls = ' class="anders"' if anders else ""
            zeilen.append(f'<tr{cls}><td>{b}</td>'
                          f'<td class="name">{titel}{esc(k["name"])}{vorbereitung_html(k)}</td><td>{k.get("dwz") or ""}</td>'
                          f'<td>{chance}</td></tr>')
        spalten.append(f"""
          <div class="variante">
            <p class="v-kopf"><strong>{"Wahrscheinlichste" if i == 1 else f"Variante {i}"}</strong>
              <span class="klein">{round(100 * wk)} % · {schnitt}</span></p>
            <table class="bretter"><tbody>{"".join(zeilen)}</tbody></table>
          </div>""")
    return f"""
      <div class="vorschau">
        <p><strong>Voraussichtliche Aufstellung {esc(name_von(d, tlnr))}</strong></p>
        <div class="varianten">{"".join(spalten)}</div>
        <p class="klein">Prozente oben = Wahrscheinlichkeit der ganzen Aufstellung (es gibt sehr viele mögliche,
          deshalb sind die Werte klein); hervorgehoben = anders als in der wahrscheinlichsten.
          {LEGENDE_GEGNER}</p>
      </div>"""


def reiter_aufstellung(d):
    if not d.get("kader"):
        return reiter_spieler(d)          # Archiv / ohne Meldeliste: Spielerstatistik wie bisher
    return (aufstellung_tabelle(d, d["eigen"]) +
            f'<p class="klein">{LEGENDE_EIGEN} Ergebnisse je Runde: 1 / ½ / 0, + / – kampflos. '
            f'Andere Mannschaften: in der Tabelle auf den Namen tippen.</p>')


def aufstellungen_dialog(d):
    """Ein Fenster für alle Mannschaften der Liga; die Tabellen-Namen öffnen den passenden Teil."""
    if not d.get("kader_alle"):
        return ""
    bloecke = []
    for t in sorted(d["teams"], key=int):
        tlnr = int(t)
        if not kader_von(d, tlnr):
            continue
        eigen = tlnr == d.get("eigen")
        url = team_url(d, tlnr)
        link = (f'<a href="{esc(url)}" target="_blank" rel="noopener">Beim Schachbezirk ansehen ↗</a>'
                if url else "")
        legende = LEGENDE_EIGEN if eigen else LEGENDE_GEGNER
        bloecke.append(f"""
        <div class="auf-block" data-tlnr="{tlnr}" hidden>
          <h2>{esc(name_von(d, tlnr))}</h2>
          {aufstellung_tabelle(d, tlnr)}
          <p class="klein">{legende if (eigen or not d.get("archiv")) else ""} {link}</p>
        </div>""")
    return f"""
    <dialog class="auf-dialog" aria-label="Mannschaftsaufstellung">
      <form method="dialog"><button class="auf-zu" aria-label="Schließen">✕</button></form>
      {"".join(bloecke)}
    </dialog>
    <script>
    (function () {{
      var dlg = document.querySelector(".auf-dialog");
      if (!dlg || !dlg.showModal) return;
      document.querySelectorAll(".team-knopf").forEach(function (b) {{
        b.addEventListener("click", function () {{
          dlg.querySelectorAll(".auf-block").forEach(function (x) {{ x.hidden = x.dataset.tlnr !== b.dataset.tlnr; }});
          dlg.showModal();
          dlg.scrollTop = 0;
        }});
      }});
      dlg.addEventListener("click", function (e) {{ if (e.target === dlg) dlg.close(); }});
    }})();
    </script>"""


def auf_ab_legende(d):
    """Kleine Erklärung der Platzfarben (nur die Stufen, die in dieser Liga vorkommen)."""
    teile = [(d.get("auf"), "l-auf", "Aufstieg"), (d.get("auf_evtl"), "l-auf-evtl", "evtl. Aufstieg"),
             (d.get("ab_evtl"), "l-ab-evtl", "evtl. Abstieg"), (d.get("ab"), "l-ab", "Abstieg")]
    spans = "".join(f'<span class="{k}">{t}</span>' for n, k, t in teile if n)
    return f'<p class="auf-ab-legende">{spans}</p>' if spans else ""


def brett_felder(b):
    """[Brett, Heim, Gast, Art, h, g, (DWZ H, DWZ G, Link H, Link G)] -> immer 10 Felder."""
    return (list(b) + [None] * 10)[:10]


def spieler_html(name, dwz, url, eigen, fett=False):
    """Name (verlinkt: eigene -> Spielerseite, Gegner -> Bezirk) + DWZ klein dahinter."""
    text = f"<strong>{esc(name)}</strong>" if fett else esc(name)
    seite = spielerseiten.seite(name) if eigen else None
    if seite in SPIELER_SEITEN:
        text = f'<a class="sp-link" href="{esc(WURZEL + seite)}">{text}</a>'
    elif url and GEGNER_VERLINKEN and name.strip().lower() not in spielerseiten.KEIN_SPIELER:
        text = f'<a class="sp-link" href="{esc(url)}" target="_blank" rel="noopener">{text}</a>'
    if DWZ_AN_BRETTERN and dwz:
        text += f' <span class="dwz">{dwz}</span>'
    return text


def bretter_html(d, m):
    if not m.get("bretter"):
        return ""
    heim = m["h"] == d["eigen"]
    zeilen = []
    for b in m["bretter"]:
        brett, sp_h, sp_g, art, h, g, dh, dg, uh, ug = brett_felder(b)
        eigen, gegner = (sp_h, sp_g) if heim else (sp_g, sp_h)
        d_eigen, d_gegner, u_eigen, u_gegner = (dh, dg, uh, ug) if heim else (dg, dh, ug, uh)
        if art == "score":
            mein, sein = (h, g) if heim else (g, h)
            erg, cls = f"{zahl(mein)} – {zahl(sein)}", "s" if mein == 1 else "n" if mein == 0 else "u"
        elif art == "annulliert":
            erg, cls = "– / –", "n"
        else:
            gewonnen = (art == "forfeit_heim") == heim
            erg, cls = ("+ / –", "s") if gewonnen else ("– / +", "n")
        pid = partien.partie_id(d, m, brett)
        abspielen = (f' <a class="partie-link" href="#partien/{pid}" title="Partie nachspielen" '
                     f'aria-label="Partie nachspielen">▶</a>' if pid else "")
        zeilen.append(f'<tr><td>{brett}</td><td class="name">{spieler_html(eigen, d_eigen, u_eigen, True)}</td>'
                      f'<td><span class="erg erg-{cls} klein">{erg}</span>{abspielen}</td>'
                      f'<td class="name">{spieler_html(gegner, d_gegner, u_gegner, False)}</td></tr>')
    return f'<table class="bretter"><tbody>{"".join(zeilen)}</tbody></table>'


def bretter_neutral_html(d, m):
    """Einzelergebnisse aus Heim-Sicht (für die Spieltags-Ansicht). Sieger fett."""
    if not m.get("bretter"):
        return ""
    zeilen = []
    for b in m["bretter"]:
        brett, sp_h, sp_g, art, h, g, dh, dg, uh, ug = brett_felder(b)
        if art == "score":
            erg = f"{zahl(h)} – {zahl(g)}"
            sieger = "h" if h > g else "g" if g > h else ""
        else:
            erg = {"forfeit_heim": "+ / –", "forfeit_gast": "– / +", "annulliert": "– / –"}.get(art, "")
            sieger = {"forfeit_heim": "h", "forfeit_gast": "g"}.get(art, "")
        links = spieler_html(sp_h, dh, uh, m["h"] == d["eigen"], sieger == "h")
        rechts = spieler_html(sp_g, dg, ug, m["g"] == d["eigen"], sieger == "g")
        zeilen.append(f'<tr><td>{brett}</td><td class="name">{links}</td>'
                      f'<td><span class="erg klein">{erg}</span></td>'
                      f'<td class="name rechts">{rechts}</td></tr>')
    return f'<table class="bretter"><tbody>{"".join(zeilen)}</tbody></table>'


def paarungen_html(d, runde):
    """Paarungen einer Runde; gespielte Wettkämpfe lassen sich aufklappen (Bretter mit Namen)."""
    teile = []
    for m in (m for m in d["matches"] if m["r"] == runde):
        cls = "paar eigen" if d["eigen"] in (m["h"], m["g"]) else "paar"
        if m.get("sf"):
            erg = "–"
        elif m["gesp"]:
            erg = f'{zahl(m["bh"])} : {zahl(m["bg"])}'
        else:
            erg = '<span class="klein">offen</span>'
        zeile = (f'<span class="p-h">{esc(name_von(d, m["h"]))}</span><span class="p-e">{erg}</span>'
                 f'<span class="p-g">{esc(name_von(d, m["g"]))}</span>')
        bretter = bretter_neutral_html(d, m) if m["gesp"] else ""
        teile.append(f'<details class="{cls}"><summary>{zeile}</summary>{bretter}</details>' if bretter
                     else f'<div class="{cls}"><div class="p-zeile">{zeile}</div></div>')
    hinweis = ('<p class="klein">Auf einen Wettkampf tippen, um die Einzelergebnisse zu sehen.</p>'
               if any(m.get("bretter") and m["gesp"] for m in d["matches"] if m["r"] == runde) else "")
    return f'{hinweis}<div class="paarungen">{"".join(teile)}</div>'


# ==========================================
# REITER
# ==========================================
def reiter_tabelle(d):
    runde = d.get("aktuelle_runde") or 0
    nach = f"nach Runde {runde} von {d['runden']}" if runde else "noch kein Spieltag gespielt"
    vorher = d["runden_tabellen"].get(str(runde - 1)) if runde > 1 else None
    delta = {r["tlnr"]: r["platz"] for r in vorher} if vorher else None
    hinweis = " · ▲▼ = Veränderung zum Spieltag davor" if delta else ""
    return f'<p class="klein">Tabelle {nach}{hinweis}</p>{tabelle_html(d, d["tabelle"], delta)}'


def reiter_spieltage(d):
    runden = d["runden"] or max((m["r"] for m in d["matches"]), default=0)
    if not runden:
        return ""
    start = d.get("aktuelle_runde") or 1
    teile = []
    for r in range(1, runden + 1):
        tab = d["runden_tabellen"].get(str(r))
        vorher = d["runden_tabellen"].get(str(r - 1))
        delta = {x["tlnr"]: x["platz"] for x in vorher} if vorher else None
        tabelle = (f'<h3>Tabelle nach Runde {r}</h3>{tabelle_html(d, tab, delta)}' if tab
                   else '<p class="klein">Noch nicht gespielt.</p>')
        teile.append(f"""
        <div class="runde" data-runde="{r}"{"" if r == start else " data-zu"}>
          <h3>Runde {r}</h3>{paarungen_html(d, r)}{tabelle}
        </div>""")
    knoepfe = "".join(f'<button type="button" data-runde="{r}">{r}</button>' for r in range(1, runden + 1))
    return f"""
      <div class="runden-wahl" hidden><span class="klein">Runde:</span>{knoepfe}</div>
      {"".join(teile)}"""


def reiter_spiele(d):
    teile = []
    for m in eigene_spiele(d):
        if m.get("sf"):
            teile.append(f'<div class="spiel"><span class="rd">R{m["r"]}</span><span class="geg">{KEIN_TEAM}</span></div>')
            continue
        heim, gegner, mein, sein, art = sicht(d, m)
        dwz = m.get("dg" if heim else "dh")
        info = f'<span class="dwz">Ø {dwz}</span>' if dwz else ""
        kopf = (f'<span class="rd">R{m["r"]}</span><span class="ha">{"H" if heim else "A"}</span>'
                f'<span class="geg">{esc(gegner)}{info}</span>{ergebnis_badge(art, mein, sein)}')
        details = bretter_html(d, m)
        if not m["gesp"] and m is naechstes_spiel(d):
            details = vorschau_html(d, m["g"] if heim else m["h"])
        teile.append(f'<details class="spiel"><summary>{kopf}</summary>{details}</details>' if details
                     else f'<div class="spiel">{kopf}</div>')
    return ('<p class="klein">Auf ein gespieltes Spiel tippen, um die Bretter zu sehen – beim nächsten Spiel '
            'die voraussichtliche Aufstellung des Gegners.</p>' + "".join(teile))


def reiter_spieler(d):
    if not d.get("spieler"):
        return ""
    zeilen = []
    for s in d["spieler"]:
        proz = f'{round(100 * s["pkt"] / s["sp"])} %' if s["sp"] else "–"
        kl = " ".join(f'{n}× kampfl. {z}' for n, z in ((s["kl_plus"], "+"), (s["kl_minus"], "–")) if n)
        bretter = ", ".join(map(str, s["bretter"])) or "–"
        zeilen.append(f'<tr><td class="name">{spieler_html(s["name"], None, None, True)}</td><td>{s["sp"]}</td>'
                      f'<td>{zahl(s["pkt"])}</td><td>{proz}</td><td class="neben">{bretter}</td>'
                      f'<td class="neben klein">{kl}</td></tr>')
    return f"""
      <div class="tab-wrap"><table class="liga-tab spieler">
        <thead><tr><th class="name">Spieler</th><th title="gespielte Partien">Sp</th><th>Pkt</th><th>%</th>
          <th class="neben">Brett</th><th class="neben"></th></tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>
      <p class="klein">Nur gespielte Partien; kampflose Bretter stehen extra.</p>"""


def verlauf_svg(punkte, n_teams, n_runden):
    """punkte: [(runde, platz)] -> Liniendiagramm, Platz 1 oben."""
    B, H, L, R, O, U = 640, 240, 34, 14, 14, 30
    x = lambda r: L + (r - 1) * (B - L - R) / max(n_runden - 1, 1)
    y = lambda p: O + (p - 1) * (H - O - U) / max(n_teams - 1, 1)
    gitter = "".join(
        f'<line x1="{L}" x2="{B - R}" y1="{y(p):.1f}" y2="{y(p):.1f}" class="g"/>'
        f'<text x="{L - 8}" y="{y(p) + 4:.1f}" text-anchor="end">{p}</text>'
        for p in range(1, n_teams + 1))
    achse = "".join(f'<text x="{x(r):.1f}" y="{H - 8}" text-anchor="middle">R{r}</text>'
                    for r in range(1, n_runden + 1))
    linie = " ".join(f"{x(r):.1f},{y(p):.1f}" for r, p in punkte)
    kreise = "".join(f'<circle cx="{x(r):.1f}" cy="{y(p):.1f}" r="5"><title>Runde {r}: Platz {p}</title></circle>'
                     for r, p in punkte)
    return (f'<svg class="verlauf" viewBox="0 0 {B} {H}" role="img" aria-label="Platzierung nach jeder Runde">'
            f'{gitter}{achse}<polyline points="{linie}"/>{kreise}</svg>')


def reiter_verlauf(d):
    zeilen, punkte = [], []
    for r in range(1, (d.get("aktuelle_runde") or 0) + 1):
        tab = d["runden_tabellen"].get(str(r))
        zeile = eigene_zeile(d, tab) if tab else None
        if not zeile:
            continue
        punkte.append((r, zeile["platz"]))
        m = next((m for m in eigene_spiele(d) if m["r"] == r), None)
        if m and m.get("sf"):
            spiel = KEIN_TEAM
        elif m:
            _, _, mein, sein, art = sicht(d, m)
            spiel = f'{spiel_text(d, m)} {ergebnis_badge(art, mein, sein)}'
        else:
            spiel = "–"
        zeilen.append(f'<tr><td>{r}</td><td class="name">{spiel}</td><td>{zeile["mp"]}</td>'
                      f'<td>{bp(zeile["bp"])}</td><td><strong>{zeile["platz"]}</strong></td></tr>')
    if not punkte:
        return '<p class="klein">Noch kein Spieltag gespielt.</p>'
    return f"""
      {verlauf_svg(punkte, len(d["tabelle"]), d["runden"] or punkte[-1][0])}
      <div class="tab-wrap"><table class="liga-tab">
        <thead><tr><th>R</th><th class="name">Spiel</th><th title="Mannschaftspunkte gesamt">MP</th>
          <th title="Brettpunkte gesamt">BP</th><th>Platz</th></tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>"""


def json_fuer_script(d):
    daten = {k: d.get(k) for k in ("key", "kurz", "bretter", "eigen", "teams", "tabelle", "auf", "ab", "auf_evtl", "ab_evtl")}
    daten["matches"] = [{k: v for k, v in m.items() if k != "bretter"} for m in d["matches"]]
    daten["dezimal"] = DEZIMAL
    return json.dumps(daten, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def reiter_rechner(d):
    if not any(not m["gesp"] and not m.get("sf") for m in d["matches"]):
        return ""
    return f"""
      <div class="rechner" data-key="{esc(d["key"])}"><noscript>Der Rechner braucht JavaScript.</noscript></div>
      <script type="application/json" id="liga-{esc(d["key"])}">{json_fuer_script(d)}</script>"""


def platz_status(d, platz):
    """Endstatus nach Platz: ('auf'|'auf-evtl'|'ab'|'ab-evtl'|'', Text)."""
    n = len(d.get("tabelle") or [])
    auf, ab = d.get("auf") or 0, d.get("ab") or 0
    auf_e, ab_e = d.get("auf_evtl") or 0, d.get("ab_evtl") or 0
    if not platz or not n:
        return "", ""
    if platz <= auf:
        return "auf", "Aufstieg ↑"
    if platz <= auf + auf_e:
        return "auf-evtl", "evtl. Aufstieg"
    if platz > n - ab:
        return "ab", "Abstieg ↓"
    if platz > n - ab - ab_e:
        return "ab-evtl", "evtl. Abstieg"
    return "", ""


def saison_leiste(saisons):
    """[(Text, href, aktiv)] -> Knöpfe zum Wechseln der Saison (leer bei nur einer Saison)."""
    if not saisons or len(saisons) < 2:
        return ""
    aktiv = ' aria-current="page"'
    knoepfe = "".join(f'<a href="{esc(h)}"{aktiv if a else ""}>{esc(t)}</a>' for t, h, a in saisons)
    return f'<nav class="saisons" aria-label="Saison"><span class="klein">Saison</span>{knoepfe}</nav>'


def archiv_banner(d):
    if not d.get("archiv"):
        return ""
    aktuell = d.get("aktuell_url")
    link = f' <a href="{esc(aktuell)}">Zur aktuellen Saison →</a>' if aktuell else ""
    return f'<p class="archiv-hinweis">{esc(ARCHIV_HINWEIS.format(saison=d.get("saison_text", "")))}{link}</p>'


def reiter_saisons(d):
    """d["historie"] = [{saison, klasse, href, tabelle-d}] (setzt build_site.py), neueste zuerst."""
    zeilen = []
    for h in d.get("historie") or []:
        x = h["d"]
        z = eigene_zeile(x)
        laufend = not x.get("archiv")
        platz = f'{z["platz"]}. von {len(x["tabelle"])}' if z and x.get("aktuelle_runde") else "–"
        cls, text = ("", "läuft") if laufend else platz_status(x, z["platz"] if z else None)
        status = f'<span class="status s-{cls}">{text}</span>' if text else ""
        zeilen.append(f'<tr><td><a href="{esc(h["href"])}">{esc(h["saison"])}</a></td>'
                      f'<td class="name">{esc(x.get("klasse", ""))}</td><td>{platz}</td><td>{status}</td></tr>')
    if len(zeilen) < 2:
        return ""
    return f"""
      <div class="tab-wrap"><table class="liga-tab">
        <thead><tr><th>Saison</th><th class="name">Klasse</th><th>Platz</th><th></th></tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>"""


REITER_FUNKTIONEN = {
    "tabelle": reiter_tabelle, "spieltage": reiter_spieltage, "spiele": reiter_spiele,
    "spieler": reiter_spieler, "verlauf": reiter_verlauf, "rechner": reiter_rechner,
    "saisons": reiter_saisons, "aufstellung": reiter_aufstellung,
    "partien": partien.reiter_partien,
}


# ==========================================
# SEITEN
# ==========================================
def team_seite(d):
    """Rückgabe: (Titel, Dateiname, content, styles, Beschreibung)"""
    zeile = eigene_zeile(d)
    platz = f'Platz {zeile["platz"]} von {len(d["tabelle"])}' if zeile and d.get("aktuelle_runde") else ""
    reiter = [(key, titel, REITER_FUNKTIONEN[key](d)) for key, titel in REITER if key in REITER_FUNKTIONEN
              and not (d.get("archiv") and key in NICHT_IM_ARCHIV)]
    reiter = [r for r in reiter if r[2]]
    knoepfe = "".join(f'<a href="#p-{k}" data-reiter="{k}">{esc(t)}</a>' for k, t, _ in reiter)
    panels = "".join(f'<section class="panel" id="p-{k}" data-reiter="{k}"><h2 class="panel-titel">{esc(t)}</h2>{inhalt}</section>'
                     for k, t, inhalt in reiter)
    links = [f'<a href="{esc(d["url_liga"])}" target="_blank" rel="noopener">Liga beim {esc(d.get("quelle", "Schachbezirk"))} ↗</a>']
    content = f"""
    <p class="zurueck"><a href="{esc(d.get("zurueck_url", "mannschaften.html"))}">← {esc(d.get("zurueck_text", "Alle Mannschaften"))}</a></p>
    <div class="team-kopf">
      <h1>{esc(d["kurz"])} <span class="team-klasse">{esc(d.get("klasse", ""))}</span></h1>
      <span class="team-platz">{platz}</span>
    </div>
    {archiv_banner(d)}
    {saison_leiste(d.get("saisons"))}
    <nav class="reiter" aria-label="Bereiche">{knoepfe}</nav>
    {panels}
    <p class="klein quelle">Wertung nach Turnierordnung §15 selbst berechnet (MP, BP, Mannschaftssiege,
      Gewinnpartien; Gleichstand = geteilter Platz). {" · ".join(links)}
      {f"<br>Letzte Änderung: {stand_text(d.get('stand'))}" if d.get("stand") else ""}</p>
    {aufstellungen_dialog(d)}
    {TEAM_JS}{RECHNER_JS if "rechner" in [k for k, _, _ in reiter] else ""}
    """
    beschreibung = f"{d['kurz']} ({d.get('klasse', '')}): Tabelle, Spieltage, Ergebnisse und Statistik."
    titel = f"{d['kurz']} {d['saison_text']}" if d.get("archiv") else d["kurz"]
    return titel, seite_datei(d), content, STYLES, beschreibung


def karte_html(d):
    zeile = eigene_zeile(d)
    letztes, naechstes = letztes_spiel(d), naechstes_spiel(d)
    zeilen = []
    if zeile and d.get("aktuelle_runde"):
        cls, text = platz_status(d, zeile["platz"]) if d.get("archiv") else ("", "")
        status = f' <span class="status s-{cls}">{text}</span>' if text else ""
        zeilen.append(f'<p class="k-platz"><strong>Platz {zeile["platz"]}</strong> von {len(d["tabelle"])}'
                      f' · {zeile["mp"]} MP · {bp(zeile["bp"])} BP{status}</p>')
    if letztes:
        _, _, mein, sein, art = sicht(d, letztes)
        zeilen.append(f'<p>Zuletzt: {spiel_text(d, letztes)} {ergebnis_badge(art, mein, sein)}</p>')
    if naechstes:
        zeilen.append(f'<p>Nächstes Spiel (R{naechstes["r"]}): {spiel_text(d, naechstes)}</p>')
    return f"""
      <a class="card team-karte team-{seite_datei(d)[:-5]}" href="{seite_datei(d)}">
        <h3>{esc(d["kurz"])} <span class="team-klasse">{esc(d.get("klasse", ""))}</span></h3>
        {"".join(zeilen)}
        <span class="k-mehr">{"Tabelle, Spieltage →" if d.get("archiv") else "Tabelle, Spieltage, Rechner →"}</span>
      </a>"""


def extra_karte_html(k):
    if isinstance(k, str):          # fertiges HTML (z. B. Jugend-Karte aus jugend.py)
        return k
    inhalt = f'<p>{esc(k["text"])}</p>'
    if k.get("url"):
        inhalt += f'<a class="btn" href="{esc(k["url"])}" target="_blank" rel="noopener">Ergebnisse öffnen</a>'
    return f"""
      <div class="card team-karte">
        <h3>{esc(k["name"])} <span class="team-klasse">{esc(k.get("klasse", ""))}</span></h3>
        {inhalt}
      </div>"""


def uebersicht_seite(teams, saisons=None, archiv=None):
    """mannschaften.html (archiv = {'saison_text', 'aktuell_url'} für alte Saisons): Rückgabe (content, styles)"""
    stand = max((d.get("stand", "") for d in teams), default="")
    extra = "" if archiv else "".join(extra_karte_html(k) for k in EXTRA_KARTEN)
    karten = "".join(karte_html(d) for d in teams) + extra
    text = ("Endstand dieser Saison. Klick auf eine Mannschaft für Tabelle, Spieltage, Ergebnisse und Spieler."
            if archiv else
            f'Klick auf eine Mannschaft für Tabelle, Spieltage, Ergebnisse, Spielerstatistik und den '
            f'Tabellenrechner. Wann wir spielen, steht im <a href="termine.html">Spielplan</a>.')
    content = f"""
    <div class="team-kopf"><h1>Unsere Mannschaften{f" {esc(archiv['saison_text'])}" if archiv else ""}</h1></div>
    {archiv_banner({**archiv, "archiv": True}) if archiv else ""}
    {saison_leiste(saisons)}
    <p>{text}</p>
    <div class="grid-3 team-grid">{karten}</div>
    <p class="klein quelle">Wertung nach Turnierordnung §15 selbst berechnet.
      {f"Letzte Änderung: {stand_text(stand)}." if stand else ""}</p>
    """
    return content, STYLES


def ticker_html(teams):
    """Startseite: letztes Ergebnis je Mannschaft (leer, wenn noch nichts gespielt)."""
    karten = []
    for d in teams:
        m = letztes_spiel(d)
        if not m:
            continue
        heim, gegner, mein, sein, art = sicht(d, m)
        zeile = eigene_zeile(d)
        platz = f' · Platz {zeile["platz"]}' if zeile else ""
        karten.append(f"""
        <a class="tick tick-{art} team-{seite_datei(d)[:-5]}" href="{seite_datei(d)}">
          <span class="tick-team">{esc(d["kurz"])}</span>
          <span class="tick-erg">{zahl(mein)} : {zahl(sein)}</span>
          <span class="tick-geg">{"vs." if heim else "bei"} {esc(gegner)}</span>
          <span class="tick-info">Runde {m["r"]}{platz}</span>
        </a>""")
    if not karten:
        return ""
    return f"""
    <section>
      <div class="section-head">
        <h2>{TICKER_TITEL}</h2>
        <a href="mannschaften.html">Alle Mannschaften →</a>
      </div>
      <div class="ticker">{"".join(karten)}</div>
    </section>"""


# ==========================================
# CSS / JS
# ==========================================
TICKER_CSS = """
      .ticker { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 0.8rem; }
      .tick { display: grid; grid-template-columns: 1fr auto; gap: 0.1rem 0.6rem; padding: 0.7rem 0.9rem; border-radius: 6px; background: var(--soft); border-left: 4px solid #95a5a6; color: inherit; text-decoration: none; }
      .tick:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.12); }
      .tick-s { border-left-color: #1e8449; } .tick-u { border-left-color: #b9770e; } .tick-n { border-left-color: #c0392b; }
      .tick-team { font-weight: bold; color: var(--navy); }
      .tick-erg { font-weight: bold; font-size: 1.1rem; text-align: right; }
      .tick-geg, .tick-info { grid-column: 1 / -1; font-size: 0.9rem; color: #555; }
      .tick-info { font-size: 0.8rem; }
"""

STYLES = """<style>
      .klein { font-size: 0.85rem; color: #555; }
      .team-grid .team-karte { display: flex; flex-direction: column; color: inherit; text-decoration: none; }
      a.team-karte:hover { border-color: var(--link); box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
      .team-karte h3 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 0.6rem; margin-bottom: 0.4rem; }
      .team-karte p { margin: 0.3rem 0; }
      .k-mehr { margin-top: auto; padding-top: 0.6rem; font-weight: bold; color: var(--link); font-size: 0.9rem; }
      .team-klasse { font-size: 0.8rem; font-weight: bold; background: #dcebf7; color: #1b4f7a; border-radius: 999px; padding: 0.05rem 0.65rem; vertical-align: middle; }

      .partie-link { margin-left: .35rem; text-decoration: none; font-size: .8rem; color: var(--accent); }
      .zurueck { margin: 0 0 0.5rem; } .zurueck a { text-decoration: none; font-weight: bold; }
      .team-kopf { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 0.5rem 1rem; }
      .team-kopf h1 { margin: 0; color: var(--navy); display: flex; align-items: center; gap: 0.6rem; }
      .team-platz { font-weight: bold; color: var(--navy); font-size: 1.1rem; }

      .reiter { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 1rem 0 1.2rem; border-bottom: 3px solid var(--navy); }
      .reiter a { padding: 0.5rem 0.9rem; border-radius: 6px 6px 0 0; text-decoration: none; font-weight: bold; color: var(--navy); background: var(--soft); }
      .reiter a:hover { background: #dcebf7; }
      .reiter a[aria-current="true"] { background: var(--navy); color: #fff; }
      .js .panel-titel { display: none; }
      .panel { scroll-margin-top: 5rem; }
      .panel-titel { color: var(--navy); margin-top: 2rem; }
      .panel h3 { color: var(--navy); margin: 1.2rem 0 0.5rem; font-size: 1.1rem; }

      .tab-wrap { overflow-x: auto; }
      .liga-tab { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
      .liga-tab th, .liga-tab td { padding: 0.4rem 0.5rem; text-align: center; border-bottom: 1px solid var(--border); }
      .liga-tab th { background: var(--navy); color: #fff; }
      .liga-tab .name { text-align: left; }
      .liga-tab .rechts { text-align: right; }
      .liga-tab tr.eigen td { background: #dcebf7; font-weight: bold; }
      .liga-tab tr.auf td:first-child { box-shadow: inset 4px 0 #1e8449; }
      .liga-tab tr.ab td:first-child { box-shadow: inset 4px 0 #c0392b; }
      .liga-tab tr.trenn td { border-top: 2px dashed #888; }
      .paarungen { border-top: 1px solid var(--border); }
      .paar { border-bottom: 1px solid var(--border); }
      .paar > summary { list-style: none; cursor: pointer; }
      .paar > summary::-webkit-details-marker { display: none; }
      .paar > summary, .p-zeile { display: grid; grid-template-columns: 1fr 6.5rem 1fr 1rem; align-items: center; gap: 0.5rem; padding: 0.45rem 0.5rem; }
      .p-zeile::after { content: ""; }
      .paar > summary::after { content: "▸"; color: #888; text-align: right; }
      .paar[open] > summary::after { content: "▾"; }
      .paar > summary:hover { background: var(--soft); }
      .paar.eigen > summary, .paar.eigen .p-zeile { background: #dcebf7; font-weight: bold; }
      .p-e { text-align: center; font-weight: bold; white-space: nowrap; }
      .p-g { text-align: right; }
      .paar .bretter { margin: 0.2rem 0 0.6rem; }
      .bretter td.rechts { text-align: right; }
      @media (max-width: 600px) { .paar > summary, .p-zeile { grid-template-columns: 1fr 5rem 1fr 0.8rem; gap: 0.3rem; font-size: 0.9rem; } }
      .delta { font-size: 0.8rem; font-weight: bold; }
      .delta.hoch { color: #1e8449; } .delta.runter { color: #c0392b; }
      @media (max-width: 600px) {
        .neben { display: none; }
        .liga-tab { font-size: 0.85rem; }
        .liga-tab th, .liga-tab td { padding: 0.35rem 0.3rem; }
        .reiter a { padding: 0.4rem 0.6rem; font-size: 0.9rem; }
      }

      .runden-wahl { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; margin-bottom: 0.5rem; }
      .runden-wahl button { font: inherit; min-width: 2.4rem; cursor: pointer; border: 1px solid var(--border); background: var(--soft); border-radius: 6px; padding: 0.25rem 0.5rem; }
      .runden-wahl button[aria-pressed="true"] { background: var(--navy); color: #fff; border-color: var(--navy); }
      .js .runde[data-zu] { display: none; }

      .spiel { border-top: 1px solid var(--border); padding: 0.35rem 0; }
      .spiel > summary { cursor: pointer; list-style: none; }
      .spiel > summary::-webkit-details-marker { display: none; }
      .spiel > summary, div.spiel { display: flex; align-items: center; gap: 0.6rem; }
      details.spiel > summary::after { content: "▸"; color: #888; margin-left: 0.2rem; }
      details.spiel[open] > summary::after { content: "▾"; }
      .rd { width: 2.2rem; font-weight: bold; color: #555; }
      .ha { width: 1.4rem; font-size: 0.8rem; font-weight: bold; color: #777; }
      .geg { flex: 1; }
      .dwz { margin-left: 0.5rem; font-size: 0.8rem; color: #777; }
      .bretter .dwz { margin-left: 0.25rem; font-size: 0.75rem; font-weight: normal; white-space: nowrap; }
      a.sp-link { color: inherit; text-decoration: none; border-bottom: 1px dotted #999; }
      a.sp-link:hover { color: var(--link); border-bottom-color: var(--link); }

      .erg { display: inline-block; min-width: 3.6rem; text-align: center; border-radius: 999px; padding: 0.05rem 0.6rem; font-weight: bold; font-size: 0.9rem; background: #e3e6ea; color: #333; white-space: nowrap; }
      .erg.klein { min-width: 3rem; font-size: 0.8rem; }
      .erg-s { background: #d4efdf; color: #145a32; }
      .erg-u { background: #fdebd0; color: #7e5109; }
      .erg-n { background: #fadbd8; color: #922b21; }
      .erg-offen { background: transparent; color: #888; font-weight: normal; }

      .bretter { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 0.4rem 0 0.6rem; }
      .bretter td { padding: 0.2rem 0.4rem; text-align: center; }
      .bretter td.name { text-align: left; }
      .bretter td:first-child { width: 2rem; color: #777; }

      .verlauf { width: 100%; max-width: 720px; height: auto; display: block; margin: 0 0 1rem; font-size: 12px; }
      .verlauf .g { stroke: #e3e6ea; }
      .verlauf text { fill: #666; }
      .verlauf polyline { fill: none; stroke: var(--link); stroke-width: 3; }
      .verlauf circle { fill: #fff; stroke: var(--link); stroke-width: 3; }

      .quelle { margin-top: 2rem; }

      .team-knopf { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: left; border-bottom: 1px dotted #999; }
      .team-knopf:hover { color: var(--link); border-bottom-color: var(--link); }
      .auf-dialog { width: min(980px, 96vw); max-height: 88vh; padding: 1rem 1.2rem 1.2rem; border: 1px solid var(--border); border-radius: 12px; background: var(--surface, #fff); color: inherit; box-shadow: 0 10px 40px rgba(0,0,0,0.35); }
      .auf-dialog::backdrop { background: rgba(10, 18, 35, 0.6); }
      .auf-dialog h2 { margin: 0 2rem 0.6rem 0; color: var(--navy); font-size: 1.3rem; }
      .auf-dialog form { position: sticky; top: 0; float: right; z-index: 1; }
      .auf-zu { font: inherit; font-size: 1.1rem; cursor: pointer; border: 1px solid var(--border); background: var(--soft); border-radius: 999px; width: 2.2rem; height: 2.2rem; }
      .aufst td, .aufst th { white-space: nowrap; }
      .aufst .rd-erg { min-width: 1.6rem; color: var(--navy); }
      .aufst .rd-erg.kl { color: #888; }
      .aufst tr.ersatz td { color: #777; font-style: italic; }
      .titel { font-size: 0.7rem; font-weight: bold; color: #b9770e; }
      .chance { display: inline-block; min-width: 3.4rem; padding: 0 0.4rem; border-radius: 999px; font-size: 0.8rem; font-weight: bold;
                background: linear-gradient(90deg, rgba(46,125,79,0.35) var(--p), rgba(127,127,127,0.15) var(--p)); }
      a.vorb { text-decoration: none; font-size: 0.85rem; margin-left: 0.25rem; opacity: 0.6; }
      a.vorb:hover { opacity: 1; }
      .chance.neu { background: rgba(127,127,127,0.15); font-weight: normal; font-style: italic; }
      .vorschau { padding: 0.3rem 0 0.6rem; }
      .varianten { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 0.4rem 1.2rem; }
      .variante .v-kopf { display: flex; justify-content: space-between; gap: 0.5rem; margin: 0.4rem 0 0; border-bottom: 2px solid var(--border); }
      .variante tr.anders td { background: rgba(185, 119, 14, 0.15); font-weight: bold; }
      @media (max-width: 600px) { .auf-dialog { padding: 0.8rem 0.5rem; width: 98vw; } .chance { min-width: 2.8rem; padding: 0 0.25rem; } }
      .vorschau p { margin: 0.3rem 0; }

      .saisons { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; margin: 0.6rem 0 0.2rem; }
      .saisons span { margin-right: 0.3rem; }
      .saisons a { padding: 0.15rem 0.6rem; border-radius: 999px; border: 1px solid var(--border); text-decoration: none; font-size: 0.85rem; color: var(--navy); background: var(--soft); }
      .saisons a:hover { border-color: var(--link); }
      .saisons a[aria-current="page"] { background: var(--navy); color: #fff; border-color: var(--navy); font-weight: bold; }
      .archiv-hinweis { margin: 0.6rem 0; padding: 0.5rem 0.8rem; border-left: 4px solid #b9770e; background: #fdf2e0; color: #6e4a07; border-radius: 4px; font-size: 0.9rem; }
      .archiv-hinweis a { font-weight: bold; }
      .status { display: inline-block; font-size: 0.75rem; font-weight: bold; border-radius: 999px; padding: 0 0.5rem; margin-left: 0.3rem; background: #e3e6ea; color: #444; }
      .status.s-auf, .status.s-auf-evtl { background: #d4efdf; color: #145a32; }
      .status.s-ab, .status.s-ab-evtl { background: #fadbd8; color: #922b21; }

      .rechner .r-runde { margin: 0.5rem 0 0.2rem; font-weight: bold; cursor: pointer; }
      .rechner .r-runde-box { border-top: 1px solid var(--border); }
      .rechner .r-spiel { display: grid; grid-template-columns: 1fr auto 1fr; gap: 0.5rem; align-items: center; padding: 0.25rem 0; border-top: 1px solid var(--border); }
      .rechner .r-spiel.eigen { background: #eef5fb; }
      .rechner .r-spiel span:last-child { text-align: right; }
      .rechner select { font: inherit; padding: 0.15rem 0.3rem; }
      .rechner .r-knoepfe { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
      .rechner button { font: inherit; cursor: pointer; border: 1px solid var(--border); background: var(--soft); border-radius: 6px; padding: 0.3rem 0.8rem; }
      .rechner button:hover { border-color: var(--link); }
      .rechner .r-tabelle { margin: 0.5rem 0 1rem; }
      @media (max-width: 600px) { .rechner .r-spiel { grid-template-columns: 1fr; } .rechner .r-spiel span:last-child { text-align: left; } }
</style>"""


# Reiter + Spieltag-Auswahl (ohne JavaScript ist einfach alles untereinander sichtbar)
TEAM_JS = r"""<script>
(function () {
  document.documentElement.classList.add("js");
  var links = document.querySelectorAll(".reiter a[data-reiter]");
  var panels = document.querySelectorAll(".panel");
  // Adresse "#spieler" (ohne passendes Element -> der Browser springt nicht nach unten)
  function zeige(id) {
    id = (id || "").replace(/^p-/, "").split("/")[0];   // "#partien/123" -> Reiter "partien"
    var gibts = false;
    panels.forEach(function (p) { if (p.dataset.reiter === id) gibts = true; });
    if (!gibts && panels.length) id = panels[0].dataset.reiter;
    panels.forEach(function (p) { p.hidden = p.dataset.reiter !== id; });
    links.forEach(function (a) { a.setAttribute("aria-current", a.dataset.reiter === id ? "true" : "false"); });
  }
  links.forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      history.replaceState(null, "", "#" + a.dataset.reiter);
      zeige(a.dataset.reiter);
    });
  });
  zeige(location.hash.slice(1));
  window.addEventListener("hashchange", function () { zeige(location.hash.slice(1)); });

  var wahl = document.querySelector(".runden-wahl");
  if (wahl) {
    wahl.hidden = false;
    var runden = document.querySelectorAll(".runde[data-runde]");
    function runde(r) {
      runden.forEach(function (x) { if (x.dataset.runde === r) x.removeAttribute("data-zu"); else x.setAttribute("data-zu", ""); });
      wahl.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.runde === r ? "true" : "false"); });
    }
    wahl.querySelectorAll("button").forEach(function (b) { b.addEventListener("click", function () { runde(b.dataset.runde); }); });
    var offen = document.querySelector(".runde:not([data-zu])");
    runde(offen ? offen.dataset.runde : "1");
  }
})();
</script>"""


# Gleiche Rechnung wie chess_league.py (_tabellen_zeilen / _plaetze), nur im Browser.
RECHNER_JS = r"""<script>
(function () {
  var DEZ = ".";
  function zahl(x, fest) { var t = (fest || x % 1) ? x.toFixed(1) : String(x); return t.replace(".", DEZ); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  // §15: 2 MP bei mehr als der Hälfte der ERZIELBAREN Brettpunkte (= Bretterzahl), 1 MP bei genau der Hälfte
  function tabelle(d, sim) {
    var stats = {}, reihe = {};
    d.tabelle.forEach(function (r, i) { reihe[r.tlnr] = i; });
    d.matches.forEach(function (m) {
      [m.h, m.g].forEach(function (t) {
        if (t != null && !stats[t]) stats[t] = { tlnr: t, sp: 0, mp: 0, bp: 0, siege: 0, gp: 0 };
      });
    });
    d.matches.forEach(function (m, i) {
      var e = m.gesp ? m : sim[i];
      if (!e) return;
      var erzielbar = d.bretter || (e.bh + e.bg), half = erzielbar / 2;
      [[m.h, e.bh, e.wh], [m.g, e.bg, e.wg]].forEach(function (s) {
        if (s[0] == null) return;
        var r = stats[s[0]];
        r.sp++; r.bp += s[1]; r.gp += s[2];
        if (erzielbar > 0) {
          if (s[1] > half) { r.mp += 2; r.siege++; }
          else if (s[1] === half) r.mp += 1;
        }
      });
    });
    var rows = Object.keys(stats).map(function (k) { return stats[k]; });
    rows.sort(function (a, b) {
      return (b.mp - a.mp) || (b.bp - a.bp) || (b.siege - a.siege) || (b.gp - a.gp)
        || ((reihe[a.tlnr] == null ? 999 : reihe[a.tlnr]) - (reihe[b.tlnr] == null ? 999 : reihe[b.tlnr]));
    });
    var platz = [];
    rows.forEach(function (r, i) {
      var p = rows[i - 1];
      platz.push(i && r.mp === p.mp && r.bp === p.bp && r.siege === p.siege && r.gp === p.gp ? platz[i - 1] : i + 1);
    });
    rows.forEach(function (r, i) { r.platz = platz[i]; });
    return rows;
  }

  // Ergebnis -> Gewinnpartien wie im Python-Rechner: maximal viele Siege, Rest Remis
  function ergebnis(bh, bg) {
    var wh = Math.floor(bh), remis = Math.round(2 * (bh - wh));
    return { bh: bh, bg: bg, wh: wh, wg: Math.round(bg - remis / 2) };
  }

  function zeichneTabelle(d, ziel, rows) {
    var alt = {};
    d.tabelle.forEach(function (r) { alt[r.tlnr] = r.platz; });
    ziel.textContent = "";
    var wrap = el("div", "tab-wrap"), t = el("table", "liga-tab"), kopf = el("tr");
    var spalten = [["Rg", ""], ["", ""], ["Mannschaft", "name"], ["Sp", ""], ["MP", ""], ["BP", ""], ["Siege", "neben"], ["GewP", "neben"]];
    spalten.forEach(function (h) { kopf.appendChild(el("th", h[1], h[0])); });
    var thead = el("thead"); thead.appendChild(kopf); t.appendChild(thead);
    var tb = el("tbody"), n = rows.length;
    rows.forEach(function (r, i) {
      var tr = el("tr");
      if (r.tlnr === d.eigen) tr.className = "eigen";
      if (d.auf && i < d.auf) tr.classList.add("auf");
      if (d.ab && i >= n - d.ab) tr.classList.add("ab");
      var au = d.auf || 0, ab = d.ab || 0;
      if (d.auf_evtl && i >= au && i < au + d.auf_evtl) tr.classList.add("auf-evtl");
      if (d.ab_evtl && i >= n - ab - d.ab_evtl && i < n - ab) tr.classList.add("ab-evtl");
      var diff = (alt[r.tlnr] || r.platz) - r.platz;
      var dz = el("span", "delta " + (diff > 0 ? "hoch" : diff < 0 ? "runter" : ""), diff > 0 ? "▲" + diff : diff < 0 ? "▼" + (-diff) : "");
      var cells = [String(r.platz), dz, d.teams[r.tlnr] || ("Team " + r.tlnr), r.sp, r.mp, zahl(r.bp, true), r.siege, r.gp];
      cells.forEach(function (c, j) {
        var td = el("td", spalten[j][1]);
        if (c instanceof Node) td.appendChild(c); else td.textContent = c;
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t); ziel.appendChild(wrap);
  }

  document.querySelectorAll(".rechner[data-key]").forEach(function (box) {
    var quelle = document.getElementById("liga-" + box.dataset.key);
    if (!quelle) return;
    var d = JSON.parse(quelle.textContent), sim = {}, selects = [];
    DEZ = d.dezimal || ".";
    var B = d.bretter || 8, hoch = Math.floor(B / 2) + 1;
    box.textContent = "";
    box.appendChild(el("p", "klein", "Trag Ergebnisse für offene Spiele ein – die Tabelle rechnet sofort neu (▲▼ = Veränderung zum echten Stand). Nichts wird gespeichert."));

    var knoepfe = el("div", "r-knoepfe");
    function knopf(text, fn) { var b = el("button", "", text); b.type = "button"; b.onclick = fn; knoepfe.appendChild(b); }
    box.appendChild(knoepfe);

    var liste = el("div"), ausgabe = el("div", "r-tabelle");
    var runden = {};
    d.matches.forEach(function (m, i) { if (!m.gesp && !m.sf) (runden[m.r] = runden[m.r] || []).push(i); });

    var optionen = [["", "–"]];
    for (var x = B; x >= 0; x -= 0.5) optionen.push([String(x), zahl(x) + " : " + zahl(B - x)]);

    Object.keys(runden).sort(function (a, b) { return a - b; }).forEach(function (r, nr) {
      var det = el("details", "r-runde-box"), sum = el("summary", "r-runde", "Runde " + r);
      det.appendChild(sum);
      if (nr === 0) det.open = true;        // nächste offene Runde aufgeklappt
      liste.appendChild(det);
      runden[r].forEach(function (i) {
        var m = d.matches[i], z = el("div", "r-spiel" + ((m.h === d.eigen || m.g === d.eigen) ? " eigen" : ""));
        z.appendChild(el("span", "", d.teams[m.h]));
        var s = el("select");
        s.setAttribute("aria-label", "Ergebnis " + d.teams[m.h] + " gegen " + d.teams[m.g]);
        optionen.forEach(function (o) { var op = el("option", "", o[1]); op.value = o[0]; s.appendChild(op); });
        s.onchange = function () {
          if (s.value === "") delete sim[i]; else { var bh = parseFloat(s.value); sim[i] = ergebnis(bh, B - bh); }
          neu();
        };
        selects.push([s, i]);
        z.appendChild(s);
        z.appendChild(el("span", "", d.teams[m.g]));
        det.appendChild(z);
      });
    });

    function setze(i, bh) {
      selects.forEach(function (p) { if (p[1] === i) p[0].value = bh == null ? "" : String(bh); });
      if (bh == null) delete sim[i]; else sim[i] = ergebnis(bh, B - bh);
    }
    knopf(d.kurz + " gewinnt alles knapp", function () {
      d.matches.forEach(function (m, i) {
        if (m.gesp || m.sf) return;
        if (m.h === d.eigen) setze(i, hoch); else if (m.g === d.eigen) setze(i, B - hoch);
      });
      neu();
    });
    knopf("Alle offenen Remis", function () {
      selects.forEach(function (p) { setze(p[1], B / 2); }); neu();
    });
    knopf("Zurücksetzen", function () { selects.forEach(function (p) { setze(p[1], null); }); neu(); });

    box.appendChild(ausgabe);
    box.appendChild(liste);
    function neu() {
      var n = Object.keys(sim).length;
      zeichneTabelle(d, ausgabe, tabelle(d, sim));
      var info = el("p", "klein", n ? n + " Ergebnis(se) eingetragen." : "Noch nichts eingetragen – das ist der echte Stand.");
      ausgabe.insertBefore(info, ausgabe.firstChild);
    }
    neu();
  });

  // fürs Testen (node): window.__ligaTabelle(d, sim)
  window.__ligaTabelle = tabelle;
})();
</script>"""
