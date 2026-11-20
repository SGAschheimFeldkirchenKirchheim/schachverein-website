"""
Geschichte (geschichte.html, früher mannschaftshistorie.html): Vereinsgeschichte + wie der Verein an Mannschaften gewachsen ist,
in welcher Liga welche Mannschaft wann gespielt hat (Erwachsene, Senioren, Jugend), Steckbriefe, Meilensteine.

Daten:
  - Erwachsene + Senioren ab dem Archiv (mannschaften/archiv/<Jahr>/) und die laufende Saison: automatisch
  - alles andere (ältere Saisons, Jugend, Schätzungen, Korrekturen, Meilensteine): mannschaften_historie.json
build_site.py ruft seite(aktuell, teams, archiv, seiten_pfad) und karte() auf.
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
SEITE = "geschichte.html"          # gemeinsame Seite: Vereinsgeschichte + Mannschaftshistorie
ALTE_SEITE = "mannschaftshistorie.html"   # leitet auf SEITE weiter (alte Links)
TITEL = "Geschichte"

# Bereiche: je eine Liga-Grafik. muster = Mannschaftsname; stufen = (Muster im Klassennamen, Beschriftung),
# von oben nach unten. lueckenlos_ab = ab dieser Saison sind alle Saisons bekannt ("erstmals ..." nur ab da).
BEREICHE = [
    {"key": "erw", "titel": "Erwachsene", "untertitel": "Münchner Mannschaftsmeisterschaft (MMM)",
     "muster": r"^AFK \d+$", "lueckenlos_ab": 2013, "farbe": "#1c4e9c",
     "stufen": [(r"bezirksliga", "Bezirksliga"), (r"^a-klasse", "A-Klasse"), (r"^b-klasse", "B-Klasse"),
                (r"^c-klasse", "C-Klasse"), (r"^d-klasse", "D-Klasse"), (r"^e-klasse", "E-Klasse")]},
    {"key": "sen", "titel": "Senioren", "untertitel": "Münchner Senioren-Mannschaftsmeisterschaft",
     "muster": r"^Senioren", "lueckenlos_ab": 2014, "farbe": "#7d3c98",
     "stufen": [(r"^1\.\s*senioren", "1. Seniorenliga"), (r"^2\.\s*senioren", "2. Seniorenliga")]},
    {"key": "u20", "titel": "Jugend U20", "untertitel": "Bayerische Jugendligen und Bezirksligen",
     "muster": r"^U20", "lueckenlos_ab": 2011, "farbe": "#1e8449",
     "stufen": [(r"bayernliga", "Bayernliga"), (r"landesliga", "Landesliga Süd"),
                (r"^1\.\s*jugend", "1. Jugend-Bezirksliga"), (r"^2\.\s*jugend", "2. Jugend-Bezirksliga"),
                (r"^3\.\s*jugend", "3. Jugend-Bezirksliga")]},
    {"key": "u16", "titel": "Jugend U16", "untertitel": "bis 2022/23 eine gemeinsame Liga",
     "muster": r"^U16", "lueckenlos_ab": 2011, "farbe": "#b9770e",
     "stufen": [(r"1\.\s*liga|^mm u16", "1. Liga"), (r"2\.\s*liga", "2. Liga")]},
    {"key": "u14", "titel": "Jugend U14", "untertitel": "",
     "muster": r"^U14", "lueckenlos_ab": 2011, "farbe": "#16a085",
     "stufen": [(r"1\.\s*liga|^mm u14", "1. Liga"), (r"2\.\s*liga", "2. Liga"), (r"3\.\s*liga", "3. Liga")]},
]
# Bereiche in der Wachstums-Grafik (Balken übereinander): (Beschriftung, Bereich-Keys, Farbe)
WACHSTUM = [("Erwachsene", ["erw"], "#1c4e9c"), ("Senioren", ["sen"], "#7d3c98"),
            ("Jugend", ["u20", "u16", "u14"], "#1e8449")]
# Linienfarben je Mannschaft innerhalb eines Bereichs
FARBEN = ["#1c4e9c", "#c0392b", "#1e8449", "#b9770e", "#7d3c98", "#16a085", "#5d6d7e", "#d35400"]

# Kurztext oben ("6 Erwachsenen-, 1 Senioren- und 4 Jugend" + "mannschaften")
KURZ_TEXT = {"Erwachsene": "Erwachsenen-", "Senioren": "Senioren-", "Jugend": "Jugend-"}
# Text, wenn eine Gruppe zum ersten Mal Mannschaften hat ({n} = Anzahl)
ERSTE_TEXT = {"Erwachsene": "Erste Mannschaft in der MMM",
              "Senioren": "Erste bekannte Saison unserer Seniorenmannschaft",
              "Jugend": "Die ersten Jugendmannschaften ({n})"}

STATUS_TEXT = {"auf": "Aufstieg ↑", "ab": "Abstieg ↓", "läuft": "läuft"}

INTRO = ("Wie ist die SG AFK an Mannschaften gewachsen, und wer spielte wann in welcher Liga? "
         "Ab 2013/14 stammen die Daten aus den Tabellen des Schachbezirks und des Bayerischen Schachbunds, "
         "ältere Saisons aus unserer Vereinschronik – dort gibt es noch Lücken. "
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


def bereich_von(team):
    return next((b for b in BEREICHE if re.search(b["muster"], team)), None)


def stufe(klasse, bereich):
    """-> (Index 0 = oben, Beschriftung) oder (None, None)"""
    for i, (muster, name) in enumerate(bereich["stufen"]):
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


def sammeln(aktuell, teams, archiv, seiten_pfad):
    """-> ({Jahr: {Team: Eintrag}}, Rohdaten der JSON)"""
    roh = lade_json()
    daten = {}
    for s_text, mannschaften in (roh.get("saisons") or {}).items():
        j = saison_jahr(s_text)
        for team, e in mannschaften.items():
            daten.setdefault(j, {})[team] = {
                "klasse": e.get("klasse", ""), "platz": e.get("platz"), "n": e.get("n"),
                "status": "läuft" if j == aktuell else e.get("status", ""), "notiz": e.get("notiz", ""),
                "titel": e.get("titel", ""), "href": None, "quelle": "Hand"}
    for jahr, ts in [*archiv.items(), (aktuell, teams)]:
        for d in ts:
            if not bereich_von(d.get("kurz", "")):
                continue
            z = liga.eigene_zeile(d)
            platz = z["platz"] if z and d.get("aktuelle_runde") else None
            alt = daten.get(jahr, {}).get(d["kurz"], {})
            art, _ = liga.platz_status(d, platz)
            daten.setdefault(jahr, {})[d["kurz"]] = {
                "klasse": d.get("klasse", ""), "platz": platz, "n": len(d.get("tabelle") or []) or None,
                "status": "läuft" if jahr == aktuell else (art if art in ("auf", "ab") else ""),
                "notiz": alt.get("notiz", ""), "titel": alt.get("titel", ""),
                "href": seiten_pfad(d, aktuell), "quelle": "Schachbezirk"}
    for s_text, mannschaften in (roh.get("korrekturen") or {}).items():
        j = saison_jahr(s_text)
        for team, felder in mannschaften.items():
            if j in daten and team in daten[j]:
                daten[j][team].update(felder)
            else:
                print(f"Hinweis: Korrektur {s_text} {team} – keine Daten zum Korrigieren.")
    return daten, roh


def teams_im_bereich(daten, bereich):
    namen = {t for s in daten.values() for t in s if bereich_von(t) is bereich}

    def nr(t):
        m = re.search(r"(\d+|I{1,3}V?|IV)$", t)
        if not m:
            return 0
        x = m.group(1)
        return int(x) if x.isdigit() else {"I": 1, "II": 2, "III": 3, "IV": 4}.get(x, 9)
    return sorted(namen, key=lambda t: (nr(t), t))


def farbe(team, bereich, daten):
    ts = teams_im_bereich(daten, bereich)
    return FARBEN[ts.index(team) % len(FARBEN)] if team in ts else "#888"


def anzahl_je_saison(daten, roh, aktuell):
    """-> {Jahr: {Wachstums-Gruppe: (Anzahl, vermutet?)}} inkl. geschätzter Saisons aus der JSON."""
    aus = {}
    for j, s in daten.items():
        for label, keys, _ in WACHSTUM:
            n = sum(1 for t in s if (bereich_von(t) or {}).get("key") in keys)
            aus.setdefault(j, {})[label] = (n, False)
    for sch in roh.get("anzahl") or []:
        von, bis = saison_jahr(sch.get("von")), saison_jahr(sch.get("bis") or sch.get("von"))
        for j in range(von, bis + 1):
            for label, _, _ in WACHSTUM:
                if label in sch:
                    bekannt = aus.get(j, {}).get(label, (0, False))[0]
                    if sch[label] >= bekannt:
                        aus.setdefault(j, {})[label] = (sch[label], bool(sch.get("vermutet")))
    ausgefallen = {saison_jahr(s) for s in (roh.get("ausgefallen") or {})}
    for j in ausgefallen:
        aus.setdefault(j, {})
    return {j: aus[j] for j in sorted(aus) if j <= aktuell}


# ==========================================
# WACHSTUM
# ==========================================
def wachstum_grafik(anzahl, roh):
    """Gestapelte Balken je Saison; gleiche geschätzte Saisons am Stück werden zu einem Balken."""
    ausgefallen = {saison_jahr(s): t for s, t in (roh.get("ausgefallen") or {}).items()}
    # Saisons in einem Schätz-Zeitraum ("anzahl" in der JSON) werden zu einem breiten Balken
    bereiche = [(saison_jahr(x.get("von")), saison_jahr(x.get("bis") or x.get("von")))
                for x in roh.get("anzahl") or [] if x.get("vermutet")]
    gruppen = []
    for j, werte in anzahl.items():
        zr = next(((v, b) for v, b in bereiche if v <= j <= b), None)
        if zr and gruppen and gruppen[-1].get("zr") == zr:
            gruppen[-1]["bis"] = j
            continue
        gruppen.append({"von": j, "bis": j, "zr": zr,
                        "werte": {k: (n, True) for k, (n, _) in werte.items()} if zr else werte})
    if not gruppen:
        return ""
    maxi = max(sum(v[0] for v in g["werte"].values()) for g in gruppen) or 1
    bw, gap, links, oben, unten, eh = 22, 8, 34, 14, 58, 26
    breiten = [bw * (2.4 if g["von"] != g["bis"] else 1) for g in gruppen]
    breite = links + sum(breiten) + gap * len(gruppen) + 10
    hoehe = oben + eh * maxi + unten
    teile = [f'<svg class="hist-svg" viewBox="0 0 {breite:.0f} {hoehe}" width="{breite:.0f}" height="{hoehe}" '
             f'role="img" aria-label="Anzahl der Mannschaften je Saison">',
             '<defs><pattern id="schraffur" width="6" height="6" patternUnits="userSpaceOnUse" '
             'patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff" opacity="0.0"/>'
             '<line x1="0" y1="0" x2="0" y2="6" stroke="#fff" stroke-width="2.5" opacity="0.55"/></pattern></defs>']
    for k in range(0, maxi + 1):
        y = oben + eh * (maxi - k)
        teile.append(f'<line class="hl" x1="{links - 4}" x2="{breite - 6}" y1="{y}" y2="{y}"/>'
                     f'<text class="hy" x="{links - 8}" y="{y + 4}" text-anchor="end">{k}</text>')
    x = links + gap / 2
    for g, w in zip(gruppen, breiten):
        y = oben + eh * maxi
        label = saison_text(g["von"]) if g["von"] == g["bis"] else f'{g["von"]}–{g["bis"] + 1}'
        tip = [label]
        for name, _, f in WACHSTUM:
            n, verm = g["werte"].get(name, (0, False))
            if not n:
                continue
            h = eh * n
            y -= h
            teile.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h - 1.5}" rx="2" fill="{f}"/>')
            if verm:
                teile.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h - 1.5}" rx="2" fill="url(#schraffur)"/>')
            tip.append(f"{name}: {n}{' (vermutet)' if verm else ''}")
        if g["von"] in ausgefallen:
            tip.append(ausgefallen[g["von"]])
            teile.append(f'<text class="hp" x="{x + w / 2:.1f}" y="{oben + eh * maxi - 6}" text-anchor="middle" '
                         f'fill="#999">✕</text>')
        gesamt = sum(v[0] for v in g["werte"].values())
        if gesamt:
            teile.append(f'<text class="hz" x="{x + w / 2:.1f}" y="{y - 4}" text-anchor="middle">{gesamt}</text>')
        teile.append(f'<rect x="{x:.1f}" y="{oben}" width="{w:.1f}" height="{eh * maxi}" fill="transparent">'
                     f'<title>{esc(" · ".join(tip))}</title></rect>')
        lx = x + w / 2
        teile.append(f'<text class="hx" x="{lx:.1f}" y="{oben + eh * maxi + 14}" text-anchor="end" '
                     f'transform="rotate(-45 {lx:.1f} {oben + eh * maxi + 14})">{label}</text>')
        x += w + gap
    teile.append("</svg>")
    legende = "".join(f'<span><i style="background:{f}"></i>{n}</span>' for n, _, f in WACHSTUM)
    legende += '<span><i class="schraffiert"></i>vermutet</span><span>✕ ausgefallen (Corona)</span>'
    return f'<div class="hist-legende">{legende}</div><div class="hist-scroll">{"".join(teile)}</div>'


def erstmals(daten, anzahl, roh):
    """Zeitleiste 'erstmals ...': -> [(Jahr, Rang, HTML)]"""
    liste = []
    # Zahl der Mannschaften: neues Maximum je Wachstums-Gruppe
    for name, keys, _ in WACHSTUM:
        hoch = 0
        for j, werte in anzahl.items():
            n, verm = werte.get(name, (0, False))
            if n > hoch:
                if not verm:
                    if hoch == 0:
                        text = ERSTE_TEXT.get(name, f"Erste Mannschaft: {name}")
                        text = text.replace("{n}", str(n))
                    elif name == "Erwachsene":
                        text = f"Erstmals <strong>{n} Mannschaften</strong> in der MMM"
                    else:
                        text = f"Erstmals <strong>{n} {name}-Mannschaften</strong>"
                    liste.append((j, 0, text + "."))
                hoch = n
    # höchste Liga je Bereich (nur ab lueckenlos_ab, außer die Chronik sagt "erstmals")
    for b in BEREICHE:
        eintr = sorted((j, t, e) for j in daten for t, e in daten[j].items() if bereich_von(t) is b)
        stufen = [(j, t, e, stufe(e["klasse"], b)) for j, t, e in eintr]
        stufen = [(j, t, e, k, name) for j, t, e, (k, name) in stufen if k is not None]
        # was die (lückenhafte) Zeit vor lueckenlos_ab schon erreicht hat, inkl. Aufstiege
        vorher = [k - 1 if e["status"] == "auf" and k > 0 else k
                  for j, t, e, k, _ in stufen if j < b["lueckenlos_ab"]]
        grenze = min(vorher) if vorher else None
        beste = None
        for j, t, e, k, name in stufen:
            if (beste is not None and k < beste and j >= b["lueckenlos_ab"]
                    and (grenze is None or k < grenze)):
                liste.append((j, 1, f"{esc(b['titel'])}: erstmals in der <strong>{esc(name)}</strong> ({esc(t)})."))
            beste = k if beste is None else min(beste, k)
    # Titel und Chronik-"erstmals"
    for j, s in daten.items():
        for t, e in s.items():
            if e.get("titel"):
                liste.append((j, 2, f"<strong>{esc(t)}: {esc(e['titel'])}</strong>"))
            elif e.get("platz") == 1 and e["status"] != "läuft" and stufe(e["klasse"], bereich_von(t))[0] is not None:
                liste.append((j, 2, f"{esc(t)}: Platz 1 in der {esc(e['klasse'])}."))
            if e.get("quelle") == "Hand" and re.search(r"erstmals|erstes", e.get("notiz", ""), re.I):
                liste.append((j, 1, f"{esc(t)}: {esc(e['notiz'])}."))
    for m in roh.get("meilensteine") or []:
        j = saison_jahr(m.get("saison"))
        if j is not None and m.get("text"):
            liste.append((j, -1, esc(m["text"])))
    for s_text, grund in (roh.get("ausgefallen") or {}).items():
        liste.append((saison_jahr(s_text), 3, esc(grund)))
    return liste


def zeitleiste(liste):
    jahre = sorted({m[0] for m in liste if m[0] is not None}, reverse=True)
    gruppen = []
    for j in jahre:
        punkte = "".join(f"<li>{text}</li>" for jj, _, text in sorted(liste, key=lambda m: m[1]) if jj == j)
        gruppen.append(f'<li><span class="hist-jahr">{saison_text(j)}</span><ul>{punkte}</ul></li>')
    return f'<ol class="hist-meilensteine">{"".join(gruppen)}</ol>'


# ==========================================
# LIGA-GRAFIKEN + TABELLEN
# ==========================================
def liga_grafik(daten, bereich):
    """SVG: x = Saisons mit Daten, y = Ligastufe, eine Linie je Mannschaft."""
    st = bereich["stufen"]
    teams = teams_im_bereich(daten, bereich)
    jahre = sorted(j for j, s in daten.items()
                   if any(t in s and stufe(s[t]["klasse"], bereich)[0] is not None for t in teams))
    if not jahre:
        return ""
    sp, zh, links, oben, unten = 46, 34, 150, 18, 46
    breite, hoehe = links + sp * len(jahre) + 20, oben + zh * len(st) + unten
    x = {j: links + sp * i + sp / 2 for i, j in enumerate(jahre)}
    y = lambda k: oben + zh * k + zh / 2
    teile = [f'<svg class="hist-svg" viewBox="0 0 {breite} {hoehe}" width="{breite}" height="{hoehe}" '
             f'role="img" aria-label="Ligen {esc(bereich["titel"])} je Saison">']
    for k, (_, name) in enumerate(st):
        teile.append(f'<line class="hl" x1="{links - 6}" x2="{breite - 10}" y1="{y(k)}" y2="{y(k)}"/>'
                     f'<text class="hy" x="{links - 12}" y="{y(k) + 4}" text-anchor="end">{esc(name)}</text>')
    for j in jahre:
        teile.append(f'<text class="hx" x="{x[j]}" y="{hoehe - unten + 16}" text-anchor="end" '
                     f'transform="rotate(-45 {x[j]} {hoehe - unten + 16})">{saison_text(j)}</text>')
    for t in teams:
        f = farbe(t, bereich, daten)
        punkte = [(j, stufe(daten[j][t]["klasse"], bereich)[0], daten[j][t]) for j in jahre if t in daten[j]]
        punkte = [p for p in punkte if p[1] is not None]
        for (j1, k1, _), (j2, k2, _) in zip(punkte, punkte[1:]):
            strich = ' stroke-dasharray="4 4" opacity="0.6"' if j2 - j1 > 1 else ""
            teile.append(f'<line x1="{x[j1]}" y1="{y(k1)}" x2="{x[j2]}" y2="{y(k2)}" stroke="{f}" '
                         f'stroke-width="2.5"{strich}/>')
        for j, k, e in punkte:
            pfeil = {"auf": "▲", "ab": "▼"}.get(e["status"], "")
            stern = "★" if e.get("titel") or (e.get("platz") == 1 and e["status"] != "läuft") else ""
            tip = (f'{t} {saison_text(j)}: {e["klasse"]}' + (f', Platz {e["platz"]}' if e["platz"] else "")
                   + (f' – {STATUS_TEXT[e["status"]]}' if e["status"] in STATUS_TEXT else "")
                   + (f' – {e["titel"]}' if e.get("titel") else ""))
            zeichen = ""
            if pfeil:
                zeichen += (f'<text class="hp" x="{x[j]}" y="{y(k) + (-10 if pfeil == "▲" else 17)}" '
                            f'text-anchor="middle" fill="{f}">{pfeil}</text>')
            if stern:
                zeichen += f'<text class="hs" x="{x[j] + 9}" y="{y(k) - 5}" fill="#d4a017">{stern}</text>'
            teile.append(f'<g><title>{esc(tip)}</title><circle cx="{x[j]}" cy="{y(k)}" r="5.5" fill="{f}" '
                         f'stroke="var(--surface, #fff)" stroke-width="1.5"/>{zeichen}</g>')
    teile.append("</svg>")
    legende = "".join(f'<span><i style="background:{farbe(t, bereich, daten)}"></i>{esc(t)}</span>' for t in teams)
    # Handy: Ligabeschriftung bleibt beim Wischen links stehen (zweites, schmales SVG über der Grafik)
    achse = [f'<svg class="hist-achse" width="{links}" height="{hoehe}" viewBox="0 0 {links} {hoehe}" aria-hidden="true">'
             f'<rect width="{links}" height="{hoehe - unten + 4}" fill="var(--bg, #fff)"/>']
    for k, (_, name) in enumerate(st):
        achse.append(f'<text class="hy" x="{links - 12}" y="{y(k) + 4}" text-anchor="end">{esc(name)}</text>')
    achse.append("</svg>")
    return (f'<div class="hist-legende">{legende}</div>'
            f'<div class="hist-wrap"><div class="hist-scroll">{"".join(teile)}</div>{"".join(achse)}</div>'
            '<p class="hist-wischen">← seitlich wischen für ältere Saisons</p>')


def steckbrief(team, eintraege, roh, bereich):
    stufen = [(stufe(e["klasse"], bereich)[0], j, e) for j, e in eintraege
              if stufe(e["klasse"], bereich)[0] is not None]
    hoechste_text = ""
    if stufen:
        k_best = min(s[0] for s in stufen)
        jahre_dort = [saison_text(j) for k, j, _ in stufen if k == k_best]
        hoechste_text = f'{esc(bereich["stufen"][k_best][1])} ({", ".join(jahre_dort)})'
    auf = sum(1 for _, e in eintraege if e["status"] == "auf")
    ab = sum(1 for _, e in eintraege if e["status"] == "ab")
    erfolge = [f'{saison_text(j)}: {esc(e["titel"])}' for j, e in eintraege if e.get("titel")]
    erfolge += [f'{saison_text(j)}: Platz 1' for j, e in eintraege
                if not e.get("titel") and e.get("platz") == 1 and e["status"] != "läuft"]
    seit = (roh.get("gruendung") or {}).get(team) or f"erste bekannte Saison: {saison_text(eintraege[0][0])}"
    zeilen = [("Seit", esc(seit)), ("Höchste Liga", hoechste_text),
              ("Aufstiege / Abstiege", f"{auf} / {ab}"), ("Saisons erfasst", str(len(eintraege)))]
    if erfolge:
        zeilen.append(("Erfolge", "<br>".join(sorted(erfolge))))
    return '<dl class="hist-steckbrief">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in zeilen if v) + "</dl>"


def tabelle(eintraege):
    zeilen = []
    for j, e in sorted(eintraege, reverse=True):
        saison = f'<a href="{esc(e["href"])}">{saison_text(j)}</a>' if e.get("href") else saison_text(j)
        platz = (f'{e["platz"]}.' + (f' von {e["n"]}' if e.get("n") else "")) if e.get("platz") else "–"
        st = e["status"]
        status = f'<span class="status s-{st}">{STATUS_TEXT[st]}</span>' if st in STATUS_TEXT else ""
        extra = " · ".join(x for x in (e.get("titel"), e.get("notiz")) if x and x != "läuft")
        notiz = f'<span class="hist-notiz">{esc(extra)}</span>' if extra else ""
        zeilen.append(f'<tr><td>{saison}</td><td class="name">{esc(e["klasse"])}{notiz}</td>'
                      f'<td>{platz}</td><td>{status}</td></tr>')
    return (f'<div class="tab-wrap"><table class="liga-tab hist-tab"><thead><tr><th>Saison</th>'
            f'<th class="name">Liga</th><th>Platz</th><th></th></tr></thead>'
            f'<tbody>{"".join(zeilen)}</tbody></table></div>')


def mini_linie(eintraege, bereich, farbe_):
    """Kleine Verlaufslinie (letzte 12 Saisons) für die Mannschaftskarte."""
    pkt = [(j, stufe(e["klasse"], bereich)[0]) for j, e in eintraege]
    pkt = [p for p in pkt if p[1] is not None][-12:]
    if not pkt:
        return ""
    n = len(bereich["stufen"]) - 1 or 1
    w, h = 240, 56
    xs = [(i * w / max(1, len(pkt) - 1)) if len(pkt) > 1 else w / 2 for i in range(len(pkt))]
    ys = [6 + k * (h - 12) / n for _, k in pkt]
    linie = (f'<polyline fill="none" stroke="{farbe_}" stroke-width="3" stroke-linejoin="round" '
             f'points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in zip(xs, ys))}"/>' if len(pkt) > 1 else "")
    punkt = f'<circle cx="{xs[-1]:.0f}" cy="{ys[-1]:.0f}" r="4.5" fill="{farbe_}"/>'
    return f'<svg class="gs-mini" viewBox="-6 0 {w + 12} {h}" preserveAspectRatio="none" aria-hidden="true">{linie}{punkt}</svg>'


def bereich_block(daten, roh, bereich, aktuell):
    teams = teams_im_bereich(daten, bereich)
    if not teams:
        return ""
    karten, heute = [], []
    for t in teams:
        eintraege = sorted((j, s[t]) for j, s in daten.items() if t in s)
        f = farbe(t, bereich, daten)
        letzte_j, letzte = eintraege[-1]
        jetzt = letzte_j == aktuell
        if jetzt:
            platz = f' · Platz {letzte["platz"]}' if letzte.get("platz") else ""
            heute.append(f'<span><b style="color:{f}">{esc(t)}</b> {esc(letzte["klasse"])}{platz}</span>')
        stufen = [stufe(e["klasse"], bereich) for _, e in eintraege]
        beste = min((k for k, _ in stufen if k is not None), default=None)
        beste_name = bereich["stufen"][beste][1] if beste is not None else "–"
        auf = sum(1 for _, e in eintraege if e["status"] == "auf")
        titel = sum(1 for _, e in eintraege if e.get("titel") or (e.get("platz") == 1 and e["status"] != "läuft"))
        karten.append(f"""
        <details class="card hist-team gs-team" style="--team:{f}">
          <summary>
            <span class="gs-kopf"><h4>{esc(t)}</h4><span class="klein">{"heute" if jetzt else "zuletzt " + saison_text(letzte_j)}: {esc(letzte["klasse"])}</span></span>
            {mini_linie(eintraege, bereich, f)}
            <span class="gs-zahlen"><span><b>{len(eintraege)}</b>Saisons</span><span><b>{auf}</b>Aufstiege</span>
              <span><b>{titel}</b>Titel</span></span>
            <span class="klein gs-beste">Beste Liga: <strong>{esc(beste_name)}</strong></span>
            <span class="gs-auf">Alle Saisons ▾</span>
          </summary>
          {steckbrief(t, eintraege, roh, bereich)}
          {tabelle(eintraege)}
        </details>""")
    unter = f'<p class="klein">{esc(bereich["untertitel"])}</p>' if bereich.get("untertitel") else ""
    heute_box = (f'<div class="gs-heute"><span class="gs-label">Saison {saison_text(aktuell)}</span>'
                 f'{"".join(heute)}</div>') if heute else ""
    return f"""
      <section class="hist-bereich gs-bereich" id="{bereich['key']}" data-b="{bereich['key']}">
        <h3>{esc(bereich['titel'])}</h3>{unter}
        {heute_box}
        <div class="card gs-grafik">{liga_grafik(daten, bereich)}</div>
        <div class="gs-teams">{"".join(karten)}</div>
      </section>"""


# ==========================================
# SEITE
# ==========================================
def jahr_schluessel(ueberschrift):
    """'1994/95' -> 1995, '2026' -> 2026 (Kalenderjahr, in dem die Saison endet)."""
    m = re.match(r"(\d{4})(?:/(\d{2}))?", ueberschrift)
    if not m:
        return 0
    return int(m.group(1)) + (1 if m.group(2) else 0)


def jahrzehnt(jahr):
    return "1952–1989" if jahr < 1990 else f"{jahr // 10 * 10}er"


def chronik_html(chronik, meilensteine, pdf):
    """Chronik nach Jahrzehnten, Meilensteine stehen beim passenden Jahr (alt -> neu)."""
    jahre = {}                                     # Schlüsseljahr -> {"titel", "text", "marken"}
    for titel, text in chronik:
        k = jahr_schluessel(titel)
        e = jahre.setdefault(k, {"titel": titel, "text": "", "marken": []})
        e["text"] += text
    for j, rang, html in sorted(meilensteine, key=lambda m: m[1]):
        if j is None:
            continue
        k = j + 1                                  # Saison 2025/26 steht in der Chronik bei 2026
        jahre.setdefault(k, {"titel": str(k), "text": "", "marken": []})["marken"].append(html.rstrip("."))
    dek = {}
    for k in sorted(jahre):                       # alt -> neu (oben -> unten)
        dek.setdefault(jahrzehnt(k), []).append(k)
    namen = sorted(dek, key=lambda d: int(d[:4]), reverse=True)
    pillen = "".join(f'<button type="button" data-dek="{d}"{" class=an" if d == namen[0] else ""}>{d}</button>'
                     for d in reversed(namen))                   # alt -> neu, das neueste Jahrzehnt ist offen
    bloecke = []
    for d in namen:
        z = []
        for k in dek[d]:
            e = jahre[k]
            marken = "".join(f'<span class="gs-marke">{m}</span>' for m in e["marken"])
            anker = esc(e["titel"].replace("/", "-"))
            z.append(f'<div class="gs-jahr" id="j{anker}"><b class="gs-j">{esc(e["titel"])}</b><div>'
                     f'{f"<div class=gs-marken>{marken}</div>" if marken else ""}{e["text"]}</div></div>')
        bloecke.append(f'<div class="gs-dek" data-dek="{d}">{"".join(z)}</div>')
    pdf_link = f'<a class="gs-pdf" href="{pdf}">Chronik als PDF</a>' if pdf else ""
    return (f'<div class="gs-pillen" role="tablist">{pillen}{pdf_link}</div>'
            f'<p class="klein gs-legende"><span class="gs-marke">Erfolg</span> = Meilenstein der Saison.</p>'
            + "".join(bloecke))


def seite(aktuell, teams, archiv, seiten_pfad, chronik=(), pdf=""):
    """-> (content, styles). chronik = [(Jahr-Überschrift, HTML-Absätze)] aus dokumente/historie.typ."""
    daten, roh = sammeln(aktuell, teams, archiv, seiten_pfad)
    anzahl = anzahl_je_saison(daten, roh, aktuell)
    jetzt = anzahl.get(aktuell, {})
    teile = [f"{jetzt[n][0]} {KURZ_TEXT.get(n, n)}" for n, _, _ in WACHSTUM if jetzt.get(n, (0,))[0]]
    if teile:
        teile[-1] = teile[-1].rstrip("-") + "mannschaften"
    kurz = ", ".join(teile[:-1]) + " und " + teile[-1] if len(teile) > 1 else "".join(teile)
    bereiche = [b for b in BEREICHE if teams_im_bereich(daten, b)]
    b_pillen = "".join(f'<button type="button" data-b="{b["key"]}"{" class=an" if i == 0 else ""}>{esc(b["titel"])}</button>'
                       for i, b in enumerate(bereiche))
    content = f"""
      <h1>Unsere Geschichte</h1>
      <p class="lead">Seit 1952 wird in Feldkirchen, Aschheim und Kirchheim Schach gespielt. Hier steht, was der Verein
        erlebt hat – und welche Mannschaft wann in welcher Liga spielte.</p>
      <div class="gs-reiter" role="tablist">
        <a href="#chronik" data-r="chronik" class="an">Vereinsgeschichte</a>
        <a href="#mannschaften" data-r="mannschaften">Mannschaften</a>
      </div>

      <section class="gs-teil" data-r="chronik" id="chronik">
        <span id="meilensteine"></span>
        {chronik_html(chronik, erstmals(daten, anzahl, roh), pdf)}
      </section>

      <section class="gs-teil" data-r="mannschaften" id="mannschaften">
        <h2 id="wachstum">So sind wir gewachsen</h2>
        {f'<p>In der Saison {saison_text(aktuell)} spielen wir mit <strong>{kurz}</strong>.</p>' if kurz else ''}
        <div class="card gs-grafik">{wachstum_grafik(anzahl, roh)}</div>
        <p class="klein">Balken antippen oder darüberfahren für die Zahlen.</p>

        <h2 id="ligen">Wer spielte wo?</h2>
        <p class="klein">Punkt antippen für Liga und Platz. ▲ Aufstieg, ▼ Abstieg, ★ Meister/Titel,
          gestrichelt = Saisons dazwischen fehlen. Karte antippen für alle Saisons. {HINWEIS_NUMMERN}</p>
        <div class="gs-pillen gs-b-pillen" role="tablist">{b_pillen}</div>
        {"".join(bereich_block(daten, roh, b, aktuell) for b in BEREICHE)}
      </section>
      <script>
      (function () {{
        var teile = document.querySelectorAll(".gs-teil"), reiter = document.querySelectorAll(".gs-reiter a");
        function zeige(r) {{
          teile.forEach(function (t) {{ t.hidden = t.getAttribute("data-r") !== r; }});
          reiter.forEach(function (a) {{ a.classList.toggle("an", a.getAttribute("data-r") === r); }});
          document.querySelectorAll(".gs-teil:not([hidden]) .hist-scroll").forEach(function (el) {{ el.scrollLeft = el.scrollWidth; }});
        }}
        function gruppe(sel, attr, wert) {{
          document.querySelectorAll(sel + " button").forEach(function (b) {{ b.classList.toggle("an", b.getAttribute(attr) === wert); }});
        }}
        function dek(d) {{ gruppe(".gs-pillen:not(.gs-b-pillen)", "data-dek", d);
          document.querySelectorAll(".gs-dek").forEach(function (x) {{ x.hidden = x.getAttribute("data-dek") !== d; }}); }}
        function ber(b) {{ gruppe(".gs-b-pillen", "data-b", b);
          document.querySelectorAll(".gs-bereich").forEach(function (x) {{ x.hidden = x.getAttribute("data-b") !== b; }});
          var s = document.querySelector('.gs-bereich[data-b="' + b + '"] .hist-scroll'); if (s) s.scrollLeft = s.scrollWidth; }}
        document.querySelectorAll("[data-dek]").forEach(function (b) {{ if (b.tagName === "BUTTON") b.onclick = function () {{ dek(b.getAttribute("data-dek")); }}; }});
        document.querySelectorAll(".gs-b-pillen button").forEach(function (b) {{ b.onclick = function () {{ ber(b.getAttribute("data-b")); }}; }});
        reiter.forEach(function (a) {{ a.onclick = function (ev) {{ ev.preventDefault(); history.replaceState(null, "", a.getAttribute("href")); zeige(a.getAttribute("data-r")); }}; }});
        var erste = document.querySelector(".gs-pillen:not(.gs-b-pillen) button.an"); if (erste) dek(erste.getAttribute("data-dek"));
        var eb = document.querySelector(".gs-b-pillen button"); if (eb) ber(eb.getAttribute("data-b"));
        // Sprungziele aus alten Links: #wachstum, #ligen, #erw ... -> Mannschaften; #j2026 -> passendes Jahrzehnt
        var h = decodeURIComponent(location.hash.slice(1)), ziel = h && document.getElementById(h);
        var inM = ziel && ziel.closest('.gs-teil[data-r="mannschaften"]');
        zeige(inM || h === "mannschaften" ? "mannschaften" : "chronik");
        if (ziel && ziel.classList.contains("gs-bereich")) ber(h);
        var d = ziel && ziel.closest(".gs-dek"); if (d) dek(d.getAttribute("data-dek"));
        if (ziel && h !== "chronik" && h !== "mannschaften") setTimeout(function () {{ ziel.scrollIntoView(); }}, 50);
      }})();
      </script>
    """
    return content, liga.STYLES + "<style>" + CSS + "</style>"


def erfolge(aktuell, teams, archiv, seiten_pfad, keys):
    """Erfolge der Bereiche keys (z. B. Jugend) für andere Seiten: [(Saison, Text, Titel?)], neueste zuerst."""
    daten, roh = sammeln(aktuell, teams, archiv, seiten_pfad)
    anzahl = anzahl_je_saison(daten, roh, aktuell)
    bereiche = [b for b in BEREICHE if b["key"] in keys]
    def passt(t):
        team = t.split(":")[0].strip()
        if any(team == b["titel"] for b in bereiche) or bereich_von(team) in bereiche:
            return True
        return "Jugend" in t and any("Jugend" in b["titel"] for b in bereiche)
    aus, gesehen = [], set()
    for j, rang, text in sorted(erstmals(daten, anzahl, roh), key=lambda m: (-(m[0] or 0), m[1])):
        t = re.sub(r"<[^>]+>", "", text).rstrip(".").strip()
        if j is None or j > aktuell or rang == 3 or not passt(t) or (j, t) in gesehen:
            continue
        gesehen.add((j, t))
        aus.append((saison_text(j), t, rang == 2))
    return aus


def karte():
    """Karte für die Mannschaften-Übersicht."""
    return f"""
      <style>
        /* Breite Ansicht (eine Zeile pro Team): der lange Titel bekommt die ersten beiden Spalten, der Text die Mitte */
        @media (min-width: 901px) {{
          .team-grid > .team-historie h3 {{ grid-column: 1 / 3; }}
          .team-grid > .team-historie p {{ grid-column: 3 / -2; }}
        }}
      </style>
      <a class="card team-karte team-historie" href="{SEITE}#mannschaften">
        <h3>Mannschaftshistorie</h3>
        <p>Wie der Verein an Mannschaften gewachsen ist und wer wann in welcher Liga spielte – Erwachsene, Senioren und Jugend.</p>
        <span class="k-mehr">Zur Geschichte →</span>
      </a>"""


CSS = """
      .hist-sprung { font-size: 0.95rem; }
      .hist-sprung a { font-weight: 600; }
      .lead { max-width: 52rem; }
      .hist-scroll { overflow-x: auto; margin: 0.4rem 0; }
      .hist-svg { display: block; max-width: none; font-family: inherit; }
      /* PC/Tablet: Grafik passt sich der Breite an (nur verkleinern). Handy: Originalgröße, seitlich wischen */
      @media (min-width: 701px) { .hist-svg { max-width: 100%; height: auto; } }
      .hist-wischen { display: none; font-size: 0.8rem; color: var(--muted, #888); margin: 0.2rem 0 0; }
      @media (max-width: 700px) { .hist-wischen { display: block; } }
      .hist-wrap { position: relative; }
      .hist-achse { display: none; position: absolute; left: 0; top: 0; pointer-events: none; font-family: inherit; }
      .hist-achse .hy { font-size: 12px; fill: currentColor; font-weight: 600; }
      @media (max-width: 700px) { .hist-achse { display: block; } }
      .hist-svg .hl { stroke: var(--border, #e3e6ea); stroke-width: 1; }
      .hist-svg .hy { font-size: 12px; fill: currentColor; font-weight: 600; }
      .hist-svg .hx { font-size: 11px; fill: #888; }
      .hist-svg .hz { font-size: 11px; fill: currentColor; font-weight: bold; }
      .hist-svg .hp { font-size: 10px; font-weight: bold; }
      .hist-svg .hs { font-size: 12px; }
      .hist-legende { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.9rem; margin-top: 0.6rem; }
      .hist-legende i { display: inline-block; width: 1.1rem; height: 0.7rem; border-radius: 2px; vertical-align: middle; margin-right: 0.35rem; }
      .hist-legende i.schraffiert { background: repeating-linear-gradient(45deg, #888, #888 2px, #ccc 2px, #ccc 5px); }
      .hist-bereich { margin: 1.6rem 0 2.2rem; }
      .hist-bereich h3 { margin-bottom: 0; }
      .hist-teams { display: grid; gap: 0.6rem; margin-top: 0.6rem; }
      .hist-team { border-left: 5px solid var(--team); padding: 0.5rem 1rem; }
      .hist-team > summary { cursor: pointer; display: flex; align-items: baseline; gap: 0.8rem; list-style: none; }
      .hist-team > summary::-webkit-details-marker { display: none; }
      .hist-team > summary::after { content: "▾"; margin-left: auto; color: #888; }
      .hist-team[open] > summary::after { content: "▴"; }
      .hist-team h4 { margin: 0; color: var(--team); font-size: 1.05rem; }
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
      /* Neue Gliederung: Reiter, Jahrzehnte, Mannschaftskarten */
      .gs-reiter { display: flex; gap: .3rem; margin: 1.2rem 0 1.8rem; border-bottom: 1px solid var(--line, var(--border, #e3e6ea)); }
      .gs-reiter a { padding: .7rem 1.1rem; font-weight: 700; color: var(--muted, #777); text-decoration: none; border-bottom: 3px solid transparent; margin-bottom: -1px; }
      .gs-reiter a.an { color: var(--head, var(--navy)); border-color: var(--link-c, var(--link, #1c4e9c)); }
      .gs-teil[hidden], .gs-dek[hidden], .gs-bereich[hidden] { display: none; }
      .gs-pillen { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; margin: 0 0 1rem; }
      .gs-pillen button { font: inherit; font-weight: 600; padding: .45rem 1rem; border-radius: 20px; cursor: pointer;
        border: 1px solid var(--line, var(--border, #ddd)); background: var(--surface, #fff); color: var(--muted, #666); }
      .gs-pillen button.an { background: var(--link-c, #1c4e9c); border-color: var(--link-c, #1c4e9c); color: #0e1524; }
      :root:not([data-theme="dark"]) .gs-pillen button.an { background: #1c2d52; border-color: #1c2d52; color: #fff; }
      .gs-pdf { margin-left: auto; font-weight: 600; }
      .gs-legende { margin: 0 0 .5rem; }
      .gs-jahr { display: grid; grid-template-columns: 7rem 1fr; gap: 1.2rem; padding: 1.2rem 0; border-bottom: 1px solid var(--line, var(--border, #e3e6ea)); }
      .gs-j { font-family: var(--font-display, Georgia, serif); font-size: 1.45rem; color: var(--head, var(--navy)); font-variant-numeric: tabular-nums; }
      .gs-jahr p { margin: 0 0 .6rem; }
      .gs-marken { margin-bottom: .5rem; }
      .gs-marke { display: inline-block; background: #e0a84f22; color: #9a6510; border: 1px solid #e0a84f66; border-radius: 20px;
        padding: .12rem .65rem; font-size: .85rem; font-weight: 600; margin: 0 .35rem .35rem 0; }
      .gs-marke strong { font-weight: 700; }
      :root[data-theme="dark"] .gs-marke { color: #f2c37a; }
      .gs-grafik { padding: .8rem 1rem; overflow: hidden; }
      .gs-heute { display: flex; flex-wrap: wrap; gap: .4rem .6rem; align-items: center; margin: .6rem 0 .8rem; font-size: .92rem; }
      .gs-heute > span:not(.gs-label) { background: var(--surface, #fff); border: 1px solid var(--line, var(--border, #e3e6ea)); border-radius: 20px; padding: .25rem .75rem; }
      .gs-label { font-size: .82rem; font-weight: 700; color: var(--link-c, var(--link)); margin-right: .2rem; }
      .gs-teams { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .9rem; margin-top: 1rem; }
      .gs-team { border-left: 0; border-top: 4px solid var(--team); padding: 1rem 1.1rem; }
      .gs-team[open] { grid-column: 1 / -1; }
      .gs-team > summary { display: block; }
      .gs-team > summary::after, .gs-team[open] > summary::after { content: none; }
      .gs-kopf { display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap; }
      .gs-kopf h4 { font-size: 1.2rem; }
      .gs-mini { display: block; width: 100%; height: 56px; margin: .6rem 0 .4rem; }
      .gs-beste { display: block; margin-top: .5rem; text-align: center; }
      .gs-zahlen { display: grid; grid-template-columns: repeat(3, 1fr); gap: .3rem; text-align: center; font-size: .78rem; color: var(--muted, #777); }
      .gs-zahlen b { display: block; font-size: 1.1rem; color: var(--head, var(--navy)); }
      .gs-zahlen b.gs-liga { font-size: .85rem; line-height: 1.35rem; }
      .gs-auf { display: block; margin-top: .6rem; font-size: .85rem; font-weight: 600; color: var(--link-c, var(--link)); }
      .gs-team[open] .gs-auf { display: none; }
      .gs-team[open] .gs-mini { max-width: 420px; }
      @media (max-width: 800px) { .gs-jahr { grid-template-columns: 1fr; gap: .2rem; } }
"""
