"""
Mannschaftshistorie (mannschaftshistorie.html): in welcher Klasse welche Mannschaft wann gespielt hat,
Auf- und Abstiege, Steckbriefe und Meilensteine.

Daten:
  - ab dem Archiv (mannschaften/archiv/<Jahr>/) und die laufende Saison: automatisch
  - ältere Saisons, Gründungen, Korrekturen, Meilensteine: mannschaften_historie.json (von Hand)
build_site.py ruft seite(aktuell, teams, archiv, seiten_pfad) auf.
"""

import html
import json
import os
import re

import liga

# ==========================================
# EINSTELLUNGEN
# ==========================================
DATEI = "mannschaften_historie.json"
SEITE = "mannschaftshistorie.html"
TITEL = "Mannschaftshistorie"

# Ligastufen von oben nach unten: (Muster im Klassennamen, Beschriftung). Erste passende gewinnt.
STUFEN = [
    (r"bezirksliga", "Bezirksliga"),
    (r"^a-klasse", "A-Klasse"),
    (r"^b-klasse", "B-Klasse"),
    (r"^c-klasse", "C-Klasse"),
    (r"^d-klasse", "D-Klasse"),
    (r"^e-klasse", "E-Klasse"),
]
SENIOREN_STUFEN = [
    (r"^1\.\s*senioren", "1. Seniorenliga"),
    (r"^2\.\s*senioren", "2. Seniorenliga"),
]
# Welche Teams (Kurzname) erscheinen? Muster; Jugendteams (U20 ...) bleiben draußen.
TEAM_MUSTER = r"^(AFK \d+|Senioren)$"
SENIOREN = "Senioren"

# Linienfarben je Mannschaft (Reihenfolge AFK 1, 2, ...); Senioren eigene Farbe
FARBEN = ["#1c4e9c", "#c0392b", "#1e8449", "#b9770e", "#7d3c98", "#16a085", "#5d6d7e", "#d35400"]
SENIOREN_FARBE = "#7d3c98"

STATUS_TEXT = {"auf": "Aufstieg ↑", "ab": "Abstieg ↓", "läuft": "läuft"}

INTRO = ("In welcher Klasse hat welche Mannschaft wann gespielt? Ab 2022/23 stammen die Daten aus den "
         "Tabellen des Schachbezirks, ältere Saisons aus unserer Vereinschronik – dort gibt es noch Lücken. "
         "Wer alte Tabellen oder Unterlagen hat: gern beim Vorstand melden!")
HINWEIS_NUMMERN = ("Die Nummern werden jede Saison nach Spielstärke neu vergeben – „AFK 3“ von 2017/18 ist "
                   "also nicht unbedingt dieselbe Mannschaft wie „AFK 3“ heute.")


# ==========================================
# DATEN
# ==========================================
def esc(x):
    return html.escape(str(x), quote=True)


def saison_text(j):
    return f"{j}/{(j + 1) % 100:02d}"


def saison_jahr(text):
    m = re.match(r"\s*(\d{4})", str(text))
    return int(m.group(1)) if m else None


def stufe(klasse, senioren=False):
    """-> (Index 0 = oben, Beschriftung) oder (None, None)"""
    for i, (muster, name) in enumerate(SENIOREN_STUFEN if senioren else STUFEN):
        if re.search(muster, (klasse or "").strip(), re.I):
            return i, name
    return None, None


def lade_json():
    try:
        with open(DATEI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        if os.path.exists(DATEI):
            print(f"WARNUNG: {DATEI} nicht lesbar ({e}).")
        return {}


def _status_aus_tabelle(d, platz):
    art, _ = liga.platz_status(d, platz)
    return art if art in ("auf", "ab") else ""


def sammeln(aktuell, teams, archiv, seiten_pfad):
    """-> {Jahr: {Team: Eintrag}}, Daten aus JSON (alt) + Archiv + laufende Saison."""
    roh = lade_json()
    daten = {}
    for s_text, mannschaften in (roh.get("saisons") or {}).items():
        j = saison_jahr(s_text)
        for team, e in mannschaften.items():
            daten.setdefault(j, {})[team] = {"klasse": e.get("klasse", ""), "platz": e.get("platz"),
                                             "n": e.get("n"), "status": e.get("status", ""),
                                             "notiz": e.get("notiz", ""), "href": None, "quelle": "Chronik"}
    for jahr, ts in [*archiv.items(), (aktuell, teams)]:
        for d in ts:
            if not re.match(TEAM_MUSTER, d.get("kurz", "")):
                continue
            z = liga.eigene_zeile(d)
            platz = z["platz"] if z and d.get("aktuelle_runde") else None
            laufend = jahr == aktuell
            daten.setdefault(jahr, {})[d["kurz"]] = {
                "klasse": d.get("klasse", ""), "platz": platz, "n": len(d.get("tabelle") or []) or None,
                "status": "läuft" if laufend else _status_aus_tabelle(d, platz),
                "notiz": "", "href": seiten_pfad(d, aktuell), "quelle": "Schachbezirk"}
    for s_text, mannschaften in (roh.get("korrekturen") or {}).items():
        j = saison_jahr(s_text)
        for team, felder in mannschaften.items():
            if j in daten and team in daten[j]:
                daten[j][team].update(felder)
            else:
                print(f"Hinweis: Korrektur {s_text} {team} – keine Daten zum Korrigieren.")
    return daten, roh


def team_reihenfolge(daten):
    namen = {t for s in daten.values() for t in s}
    return sorted(namen, key=lambda t: (t == SENIOREN, int(re.sub(r"\D", "", t) or 0), t))


def farbe(team, reihenfolge):
    if team == SENIOREN:
        return SENIOREN_FARBE
    afk = [t for t in reihenfolge if t != SENIOREN]
    return FARBEN[afk.index(team) % len(FARBEN)] if team in afk else "#888"


# ==========================================
# BAUSTEINE
# ==========================================
def grafik(daten, reihenfolge, senioren=False):
    """SVG: x = Saisons mit Daten, y = Ligastufe, eine Linie je Mannschaft."""
    st = SENIOREN_STUFEN if senioren else STUFEN
    teams = [t for t in reihenfolge if (t == SENIOREN) == senioren]
    jahre = sorted(j for j, s in daten.items() if any(t in s and stufe(s[t]["klasse"], senioren)[0] is not None
                                                       for t in teams))
    if not jahre or not teams:
        return ""
    sp, zh, links, oben, unten = 46, 34, 104, 16, 44
    breite, hoehe = links + sp * len(jahre) + 20, oben + zh * len(st) + unten
    x = {j: links + sp * i + sp / 2 for i, j in enumerate(jahre)}
    y = lambda k: oben + zh * k + zh / 2
    teile = [f'<svg class="hist-svg" viewBox="0 0 {breite} {hoehe}" width="{breite}" height="{hoehe}" '
             f'role="img" aria-label="Ligastufen der Mannschaften je Saison">']
    for k, (_, name) in enumerate(st):
        teile.append(f'<line class="hl" x1="{links - 6}" x2="{breite - 10}" y1="{y(k)}" y2="{y(k)}"/>'
                     f'<text class="hy" x="{links - 12}" y="{y(k) + 4}" text-anchor="end">{esc(name)}</text>')
    for j in jahre:
        teile.append(f'<text class="hx" x="{x[j]}" y="{hoehe - unten + 16}" text-anchor="end" '
                     f'transform="rotate(-45 {x[j]} {hoehe - unten + 16})">{saison_text(j)}</text>')
    for t in teams:
        f = farbe(t, reihenfolge)
        punkte = [(j, stufe(daten[j][t]["klasse"], senioren)[0], daten[j][t]) for j in jahre if t in daten[j]]
        punkte = [p for p in punkte if p[1] is not None]
        for (j1, k1, _), (j2, k2, _) in zip(punkte, punkte[1:]):
            luecke = jahre.index(j2) - jahre.index(j1) > 1 or j2 - j1 > 1
            strich = ' stroke-dasharray="4 4" opacity="0.6"' if luecke else ""
            teile.append(f'<line x1="{x[j1]}" y1="{y(k1)}" x2="{x[j2]}" y2="{y(k2)}" stroke="{f}" '
                         f'stroke-width="2.5"{strich}/>')
        for j, k, e in punkte:
            pfeil = {"auf": "▲", "ab": "▼"}.get(e["status"], "")
            tip = f'{t} {saison_text(j)}: {e["klasse"]}' + (f', Platz {e["platz"]}' if e["platz"] else "") + \
                  (f' – {STATUS_TEXT[e["status"]]}' if e["status"] in STATUS_TEXT else "")
            teile.append(f'<g><title>{esc(tip)}</title><circle cx="{x[j]}" cy="{y(k)}" r="5.5" fill="{f}" '
                         f'stroke="var(--surface, #fff)" stroke-width="1.5"/>'
                         + (f'<text class="hp" x="{x[j]}" y="{y(k) + (-10 if pfeil == "▲" else 17)}" text-anchor="middle" '
                            f'fill="{f}">{pfeil}</text>' if pfeil else "")
                         + "</g>")
    teile.append("</svg>")
    legende = "".join(f'<span><i style="background:{farbe(t, reihenfolge)}"></i>{esc(t)}</span>' for t in teams)
    return (f'<div class="hist-legende">{legende}</div>'
            f'<div class="hist-scroll">{"".join(teile)}</div>')


def steckbrief(team, eintraege, roh):
    """eintraege = [(Jahr, Eintrag)] aufsteigend."""
    senioren = team == SENIOREN
    stufen = [(stufe(e["klasse"], senioren)[0], j, e) for j, e in eintraege if stufe(e["klasse"], senioren)[0] is not None]
    hoechste = min(stufen, key=lambda s: (s[0], s[1])) if stufen else None
    hoechste_text = ""
    if hoechste:
        jahre_dort = [saison_text(j) for k, j, _ in stufen if k == hoechste[0]]
        hoechste_text = f'{esc(stufe(hoechste[2]["klasse"], senioren)[1])} ({", ".join(jahre_dort)})'
    auf = sum(1 for _, e in eintraege if e["status"] == "auf")
    ab = sum(1 for _, e in eintraege if e["status"] == "ab")
    meister = [saison_text(j) for j, e in eintraege if e.get("platz") == 1 and e["status"] != "läuft"]
    gruendung = (roh.get("gruendung") or {}).get(team) or f"erste bekannte Saison: {saison_text(eintraege[0][0])}"
    zeilen = [("Seit", esc(gruendung)), ("Höchste Klasse", hoechste_text),
              ("Aufstiege / Abstiege", f"{auf} / {ab}"), ("Saisons erfasst", str(len(eintraege)))]
    if meister:
        zeilen.append(("Meister", ", ".join(meister)))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in zeilen if v)
    return f'<dl class="hist-steckbrief">{dl}</dl>'


def tabelle(team, eintraege):
    zeilen = []
    for j, e in sorted(eintraege, reverse=True):
        saison = (f'<a href="{esc(e["href"])}">{saison_text(j)}</a>' if e.get("href") else saison_text(j))
        platz = (f'{e["platz"]}.' + (f' von {e["n"]}' if e.get("n") else "")) if e.get("platz") else "–"
        st = e["status"]
        status = f'<span class="status s-{st}">{STATUS_TEXT[st]}</span>' if st in STATUS_TEXT else ""
        notiz = f'<span class="hist-notiz">{esc(e["notiz"])}</span>' if e.get("notiz") else ""
        zeilen.append(f'<tr><td>{saison}</td><td class="name">{esc(e["klasse"])}{notiz}</td>'
                      f'<td>{platz}</td><td>{status}</td></tr>')
    return (f'<div class="tab-wrap"><table class="liga-tab hist-tab"><thead><tr><th>Saison</th>'
            f'<th class="name">Klasse</th><th>Platz</th><th></th></tr></thead>'
            f'<tbody>{"".join(zeilen)}</tbody></table></div>')


def meilensteine(daten, reihenfolge, roh):
    """Automatisch: Auf-/Abstiege, erstmals in einer Klasse, neue Mannschaft; dazu die aus der JSON."""
    liste = []
    for s in roh.get("meilensteine") or []:
        j = saison_jahr(s.get("saison"))
        if j is not None and s.get("text"):
            liste.append((j, 0, esc(s["text"])))
    for s_text, grund in (roh.get("ausgefallen") or {}).items():
        liste.append((saison_jahr(s_text), 0, esc(grund)))
    for t in reihenfolge:
        sen = t == SENIOREN
        eintraege = sorted((j, s[t]) for j, s in daten.items() if t in s)
        for i, (j, e) in enumerate(eintraege):
            k, _ = stufe(e["klasse"], sen)
            # "neu dabei" nur, wenn die Vorsaison bekannt ist (sonst ist es nur die erste bekannte Saison)
            # (und vollständig, also aus den Tabellen des Schachbezirks – die Chronik nennt nicht jede Mannschaft)
            vorher_bekannt = bool(daten.get(j - 1)) and all(x.get("quelle") == "Schachbezirk"
                                                             for x in daten[j - 1].values())
            if vorher_bekannt and t not in daten[j - 1]:
                wort = "ist neu dabei" if i == 0 else "ist wieder dabei"
                liste.append((j, 1, f"{esc(t)} {wort} – in der {esc(e['klasse'])}."))
            if e["status"] == "auf":
                ziel = (SENIOREN_STUFEN if sen else STUFEN)[k - 1][1] if k else "nächsthöhere Klasse"
                liste.append((j, 2, f"{esc(t)} steigt aus der {esc(e['klasse'])} in die {esc(ziel)} auf."))
            elif e["status"] == "ab":
                liste.append((j, 2, f"{esc(t)} steigt aus der {esc(e['klasse'])} ab."))
            if e.get("notiz") and e.get("quelle") == "Chronik" and re.search(r"erstmals|erste", e["notiz"], re.I):
                liste.append((j, 3, f"<strong>{esc(t)}: {esc(e['notiz'])}</strong>"))
    liste = [m for m in liste if m[0] is not None]
    liste.sort(key=lambda m: (-m[0], m[1]))
    gruppen = []
    for j in sorted({m[0] for m in liste}, reverse=True):
        punkte = "".join(f"<li>{text}</li>" for jj, _, text in liste if jj == j)
        gruppen.append(f'<li><span class="hist-jahr">{saison_text(j)}</span><ul>{punkte}</ul></li>')
    return f'<ol class="hist-meilensteine">{"".join(gruppen)}</ol>'


# ==========================================
# SEITE
# ==========================================
def seite(aktuell, teams, archiv, seiten_pfad):
    """-> (content, styles)"""
    daten, roh = sammeln(aktuell, teams, archiv, seiten_pfad)
    reihenfolge = team_reihenfolge(daten)
    karten = []
    for t in reihenfolge:
        eintraege = sorted((j, s[t]) for j, s in daten.items() if t in s)
        if not eintraege:
            continue
        karten.append(f"""
        <details class="card hist-team" style="--team:{farbe(t, reihenfolge)}">
          <summary><h3>{esc(t)}</h3><span class="klein">{esc(eintraege[-1][1]['klasse'])}</span></summary>
          {steckbrief(t, eintraege, roh)}
          {tabelle(t, eintraege)}
        </details>""")
    senioren_grafik = grafik(daten, reihenfolge, senioren=True)
    content = f"""
      <a href="mannschaften.html" style="text-decoration:none;">← Mannschaften</a>
      <h1>{TITEL}</h1>
      <p class="lead">{INTRO}</p>
      <h2>Wer spielte wo?</h2>
      {grafik(daten, reihenfolge)}
      <p class="klein">Punkt antippen oder darüberfahren für Klasse und Platz. ▲ Aufstieg, ▼ Abstieg,
        gestrichelt = Saisons dazwischen fehlen. {HINWEIS_NUMMERN}</p>
      {f'<h3>Senioren</h3>{senioren_grafik}' if senioren_grafik else ''}
      <h2>Die Mannschaften</h2>
      <div class="hist-teams">{"".join(karten)}</div>
      <h2>Meilensteine</h2>
      {meilensteine(daten, reihenfolge, roh)}
    """
    return content, liga.STYLES + "<style>" + CSS + "</style>"


def karte():
    """Karte für die Mannschaften-Übersicht."""
    return f"""
      <a class="card team-karte" href="{SEITE}">
        <h3>{TITEL}</h3>
        <p>Welche Mannschaft spielte wann in welcher Klasse? Auf- und Abstiege seit den Anfängen.</p>
        <span class="k-mehr">Zur Historie →</span>
      </a>"""


CSS = """
      .hist-scroll { overflow-x: auto; margin: 0.4rem 0; }
      .hist-svg { display: block; max-width: none; font-family: inherit; }
      .hist-svg .hl { stroke: var(--border, #e3e6ea); stroke-width: 1; }
      .hist-svg .hy { font-size: 12px; fill: currentColor; font-weight: 600; }
      .hist-svg .hx { font-size: 11px; fill: #888; }
      .hist-svg .hp { font-size: 10px; font-weight: bold; }
      .hist-legende { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.9rem; margin-top: 0.6rem; }
      .hist-legende i { display: inline-block; width: 1.1rem; height: 4px; border-radius: 2px; vertical-align: middle; margin-right: 0.35rem; }
      .hist-teams { display: grid; gap: 0.8rem; }
      .hist-team { border-left: 5px solid var(--team); padding: 0.6rem 1rem; }
      .hist-team > summary { cursor: pointer; display: flex; align-items: baseline; gap: 0.8rem; list-style: none; }
      .hist-team > summary::-webkit-details-marker { display: none; }
      .hist-team > summary::after { content: "▾"; margin-left: auto; color: #888; }
      .hist-team[open] > summary::after { content: "▴"; }
      .hist-team h3 { margin: 0; color: var(--team); }
      .hist-steckbrief { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0.8rem 0; }
      .hist-steckbrief dt { color: #777; }
      .hist-steckbrief dd { margin: 0; font-weight: 600; }
      .hist-notiz { display: block; font-size: 0.8rem; color: #777; font-weight: normal; }
      .hist-tab td { vertical-align: top; }
      .status.s-läuft { background: rgba(127,127,127,0.15); }
      .hist-meilensteine { list-style: none; padding: 0; margin: 0.6rem 0; border-left: 3px solid var(--border, #e3e6ea); }
      .hist-meilensteine > li { position: relative; padding: 0 0 0.9rem 1.2rem; }
      .hist-meilensteine > li::before { content: ""; position: absolute; left: -7px; top: 0.35rem; width: 11px; height: 11px;
                                        border-radius: 50%; background: var(--link, #1c4e9c); }
      .hist-jahr { font-weight: bold; color: var(--navy); }
      .hist-meilensteine ul { margin: 0.2rem 0 0; padding-left: 1.1rem; }
"""
