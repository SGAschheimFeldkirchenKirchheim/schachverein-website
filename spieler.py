"""
Spielerseiten (spieler/<name>.html) für alle eigenen Spieler aus den Mannschafts-Daten
(mannschaften/*.json vom Tabellenrechner):
  - DWZ / ELO (aktuell von der DSB-Vereinsliste, sonst aus der Meldeliste)
  - gemeldet für: Mannschaft, Melde-Nr., Stamm (Meldeliste beim Bezirk)
  - alle gespielten Partien über alle Mannschaften und Saisons (aktuelle offen, ältere zugeklappt)
  - inoffizielle DWZ-Prognose mit der AKTUELLEN DWZ (Wertungsordnung des DSB)

FOTO UND GEBURTSTAG:
  - Foto: Für jeden Spieler legt der Build einen Platzhalter spieler/fotos/<name>.jpg an
    ("Hier Bild einfügen"), z. B. spieler/fotos/arthur-krumm.jpg. Einfach durch das echte Foto
    ersetzen (gleicher Name, auch .png/.webp geht). Platzhalter werden auf der Seite nicht gezeigt.
    Am besten quadratisch oder Hochformat.
  - Eigener Text: spieler/texte/<name>.txt (leere Datei liegt für jeden Spieler bereit).
    Einfach Text reinschreiben, Leerzeile = neuer Absatz, Links werden klickbar. Leer = kein Kasten.
  - Jahrgang: kommt automatisch aus der Geburtstagsliste. Tag und Monat werden NIE gezeigt (Datenschutz).
    Ausnahmen in spieler/profile.json, z. B.
        {
          "Max Muster":   {"geburtstag": false},
          "Gast Spieler": {"geburtstag": "1990"}
        }
    false = Jahrgang nicht zeigen, "1990" = selbst eingetragen (z. B. wenn nicht in der Liste).

build_site.py: erst sammeln(teams, dsb) -> liga.SPIELER_SEITEN, dann bauen(...).
Das Geburtsjahr von der DSB-Liste wird nur für den Entwicklungskoeffizienten benutzt,
nie angezeigt oder gespeichert.
"""

import datetime
import html
import json
import math
import os
import re
import unicodedata
from urllib.parse import quote
from statistics import NormalDist

# ==========================================
# EINSTELLUNGEN
# ==========================================
ORDNER = "spieler"                  # spieler/<slug>.html
PROGNOSE = True                     # DWZ-Prognose anzeigen
J_OHNE_ALTER = 15                   # Altersfaktor J, wenn kein Geburtsjahr bekannt (über 25 Jahre)
KEIN_SPIELER = {"", "n.n.", "nn", "-", "spielfrei"}
ERG_TEXT = {1.0: "1", 0.5: "½", 0.0: "0"}
VERLAUF = os.path.join(ORDNER, "dwz_verlauf.json")   # wird bei jedem Build mit der DSB-DWZ fortgeschrieben
VERLAUF_AN = True                   # DWZ-Verlauf zeigen (sobald mind. 2 verschiedene Werte aufgezeichnet sind)
BERICHTE_MAX = 12                   # so viele Berichte, in denen der Spieler vorkommt, höchstens anzeigen
TOUR_LINK = True                    # Link zum "AFK on Tour"-Profil, falls vorhanden
FOTO_ORDNER = os.path.join(ORDNER, "fotos")          # spieler/fotos/<slug>.jpg
KONTO_FOTOS = os.path.join(ORDNER, "fotos_konto")    # Fotos aus dem Mitgliederbereich (konten.py)
TEXT_ORDNER = os.path.join(ORDNER, "texte")          # spieler/texte/<slug>.txt – eigener Text, leer = nichts
TEXT_PLATZHALTER = True             # für jeden Spieler eine leere Textdatei anlegen
TEXT_UEBERSCHRIFT = ""              # z. B. "Über mich"; "" = ohne Überschrift
PROFILE = os.path.join(ORDNER, "profile.json")       # Ausnahmen (Geburtstag aus/selbst, Alter)
FOTO_PLATZHALTER = True             # für jeden Spieler einen Platzhalter "Hier Bild einfügen" anlegen
GEBURTSTAG_AUTO = True              # Jahrgang aus der Geburtstagsliste zeigen (False = nur über profile.json)
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
          "Oktober", "November", "Dezember"]


def esc(x):
    return html.escape(str(x if x is not None else ""))


def _norm(text):
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("ß", "ss")
    return re.sub(r"[^a-z0-9 ]+", " ", t).split()


def slug(name):
    return "-".join(_norm(name)) or "spieler"


def seite(name):
    """Pfad der Spielerseite relativ zur Website-Wurzel."""
    return f"{ORDNER}/{slug(name)}.html"


# ==========================================
# FOTO UND GEBURTSTAG
# ==========================================
_PLATZHALTER = None


def _platzhalter_bytes():
    """Graues Bild mit 'Hier Bild einfügen' (wird einmal erzeugt)."""
    global _PLATZHALTER
    if _PLATZHALTER is None:
        from PIL import Image, ImageDraw
        import io
        im = Image.new("RGB", (400, 500), (200, 204, 212))
        d = ImageDraw.Draw(im)
        d.ellipse((130, 90, 270, 230), fill=(160, 166, 178))
        d.ellipse((70, 260, 330, 560), fill=(160, 166, 178))
        d.text((200, 470), "Hier Bild einfuegen", fill=(60, 64, 72), anchor="mm")
        b = io.BytesIO()
        im.save(b, "JPEG", quality=80)
        _PLATZHALTER = b.getvalue()
    return _PLATZHALTER


def _ist_platzhalter(pfad):
    try:
        if os.path.getsize(pfad) != len(_platzhalter_bytes()):
            return False
        with open(pfad, "rb") as f:
            return f.read() == _platzhalter_bytes()
    except Exception:
        return False


def platzhalter_anlegen(name):
    """Legt spieler/fotos/<name>.jpg als Platzhalter an, wenn noch gar kein Foto da ist."""
    if not FOTO_PLATZHALTER:
        return
    if any(os.path.exists(os.path.join(FOTO_ORDNER, slug(name) + e)) for e in (".jpg", ".jpeg", ".png", ".webp")):
        return
    try:
        os.makedirs(FOTO_ORDNER, exist_ok=True)
        with open(os.path.join(FOTO_ORDNER, slug(name) + ".jpg"), "wb") as f:
            f.write(_platzhalter_bytes())
    except Exception as e:
        print(f"Hinweis: Platzhalter für {name} nicht angelegt ({e}).")


def text_html(name):
    """Inhalt von spieler/texte/<name>.txt als HTML (Leerzeile = neuer Absatz, Links werden klickbar)."""
    pfad = os.path.join(TEXT_ORDNER, slug(name) + ".txt")
    if not os.path.exists(pfad):
        if TEXT_PLATZHALTER:
            try:
                os.makedirs(TEXT_ORDNER, exist_ok=True)
                open(pfad, "w", encoding="utf-8").close()
            except Exception:
                pass
        return ""
    with open(pfad, encoding="utf-8-sig") as f:
        return absaetze_html(f.read())


def absaetze_html(roh):
    """Text -> <p>-Absätze (Leerzeile = neuer Absatz, Links klickbar). Gleiche Regeln wie konto.js."""
    roh = (roh or "").strip()
    if not roh:
        return ""
    absaetze = []
    for teil in re.split(r"\n\s*\n", roh):
        t = esc(teil.strip())
        t = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
        absaetze.append("<p>" + t.replace("\n", "<br>") + "</p>")
    kopf = f"<strong>{esc(TEXT_UEBERSCHRIFT)}</strong>" if TEXT_UEBERSCHRIFT else ""
    return kopf + "".join(absaetze)


def konto_text_html(k):
    """Text und Lichess/Chess.com-Links aus dem eigenen Profil (Mitgliederbereich)."""
    links = []
    if k.get("lichess"):
        links.append(f'Lichess: <a href="https://lichess.org/@/{quote(k["lichess"])}" target="_blank" rel="noopener">{esc(k["lichess"])}</a>')
    if k.get("chesscom"):
        links.append(f'Chess.com: <a href="https://www.chess.com/member/{quote(k["chesscom"])}" target="_blank" rel="noopener">{esc(k["chesscom"])}</a>')
    return absaetze_html(k.get("text", "")) + (f'<p class="sp-links-profil">{" · ".join(links)}</p>' if links else "")


def konto_geburtstag(k):
    """(Beschriftung, Wert) nach der Wahl im Profil: nur Jahrgang / Geburtstag öffentlich / nichts."""
    if k.get("gb") == "nichts":
        return "Jahrgang", ""
    if k.get("gb") == "oeffentlich" and k.get("geburtstag"):
        j, m, t = k["geburtstag"].split("-")
        return "Geburtstag", f"{int(t)}. {MONATE[int(m) - 1]} {j}"
    return "Jahrgang", k.get("jahr", "")


def foto(name):
    """Pfad des Fotos relativ zur Website-Wurzel oder '' (Platzhalter zählen nicht)."""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        pfad = os.path.join(FOTO_ORDNER, slug(name) + ext)
        if os.path.exists(pfad) and not _ist_platzhalter(pfad):
            return pfad.replace(os.sep, "/")
    return ""


def profile_laden():
    try:
        with open(PROFILE, encoding="utf-8") as f:
            daten = json.load(f)
        return {slug(k): v for k, v in daten.items() if isinstance(v, dict)}
    except FileNotFoundError:
        return {}
    except ValueError as e:
        print(f"Hinweis: {PROFILE} ist kein gültiges JSON ({e}) – keine Geburtstage auf Spielerseiten.")
        return {}


def geburtstag_text(name, profil, geburtstage, heute=None):
    """Nur der Jahrgang ('1983') – Tag und Monat werden aus Datenschutzgründen nie gezeigt.
    Quelle: Geburtstagsliste, Ausnahmen in profile.json."""
    profil = profil or {}
    wert = profil.get("geburtstag", GEBURTSTAG_AUTO)
    if not wert:
        return ""
    if isinstance(wert, (str, int)) and not isinstance(wert, bool):   # selbst eingetragen: "1983" oder "14.03.1983"
        m = re.search(r"(\d{4})", str(wert))
        return m.group(1) if m else ""
    for g in geburtstage or ():                    # aus der Geburtstagsliste (gleicher Name)
        if slug(f"{g.get('vorname', '')} {g.get('nachname', '')}") == slug(name):
            m = re.search(r"(\d{4})", str(g.get("geburtstag", "")))
            return m.group(1) if m else ""
    if "geburtstag" in profil:
        print(f"Hinweis: Jahrgang für {name} freigegeben, aber nicht in der Geburtstagsliste gefunden.")
    return ""


# ==========================================
# DWZ (Wertungsordnung DSB)
# ==========================================
def erwartung(eigen, gegner):
    """Gewinnerwartung über die Normalverteilung (wie die DSB-Tabelle)."""
    return 0.5 * (1 + math.erf((eigen - gegner) / 400))


def leistung(niveau, w, n):
    if not n or w <= 0 or w >= n:
        return None
    return round(niveau + 200 * math.sqrt(2) * NormalDist().inv_cdf(w / n))


def prognose(r_alt, gegner_dwz, punkte, alter=None, index=None):
    """-> dict mit W, We, E, Niveau, Leistung, DWZ neu. gegner_dwz/punkte: gleiche Länge."""
    n = len(gegner_dwz)
    if not n or not r_alt:
        return None
    w = sum(punkte)
    we = sum(erwartung(r_alt, g) for g in gegner_dwz)
    j = J_OHNE_ALTER if alter is None else 5 if alter <= 20 else 10 if alter <= 25 else 15
    e0 = (r_alt / 1000) ** 4 + j
    fb = min(1.0, max(0.5, r_alt / 2000)) if alter is not None and alter <= 20 and w > we else 1.0
    sbr = math.exp((1300 - r_alt) / 150) - 1 if r_alt < 1300 and w < we else 0.0
    e = e0 * fb + sbr
    obergrenze = 150 if sbr else 30
    if index:
        obergrenze = min(obergrenze, 5 * index)
    e = round(min(max(e, 5), max(obergrenze, 5)))
    niveau = sum(gegner_dwz) / n
    return {"n": n, "w": w, "we": we, "e": e, "niveau": round(niveau),
            "leistung": leistung(niveau, w, n), "neu": round(r_alt + 800 * (w - we) / (e + n))}


# ==========================================
# DATEN
# ==========================================
def dsb_index(liste):
    """DSB-Vereinsliste -> {Namens-Schlüssel: Eintrag}."""
    idx = {}
    for p in liste or []:
        vor = re.sub(r"\b(dr|prof)\.?\s*", "", p.get("vorname") or "", flags=re.I)
        nach = re.sub(r"\b(dr|prof)\.?\s*", "", p.get("nachname") or "", flags=re.I)
        idx[tuple(sorted(_norm(f"{vor} {nach}")))] = p
    return idx


def dsb_finden(name, idx):
    """Exakt gleiche Namensteile, sonst eindeutige Teilmenge (zweiter Vorname fehlt o. ä.)."""
    teile = set(_norm(name))
    exakt = idx.get(tuple(sorted(teile)))
    if exakt:
        return exakt
    treffer = [p for k, p in idx.items() if teile <= set(k) or set(k) <= teile]
    return treffer[0] if len(treffer) == 1 else None


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def sammeln(teams, seite_datei, name_von):
    """Alle eigenen Spieler aus Brettern und Meldelisten (aktuelle Saison + Archiv) -> {slug: {...}}.
    seite_datei(d) = Pfad der Teamseite ab Website-Wurzel; name_von(d, tlnr) aus liga.py."""
    spieler = {}

    def hole(name):
        s = slug(name)
        return spieler.setdefault(s, {"name": name, "partien": [], "meldungen": [], "url": None,
                                      "dwz_board": None, "dwz_board_jahr": 0})

    for d in teams:
        eigen = d.get("eigen")
        if eigen is None:
            continue
        jahr = d.get("saison_jahr") or 0
        saison = d.get("saison_text") or (f"{jahr}/{(jahr + 1) % 100:02d}" if jahr else "")
        for k in ([] if d.get("archiv") else d.get("kader", [])):   # "gemeldet für" nur aktuelle Saison
            if k["name"].strip().lower() in KEIN_SPIELER:
                continue
            p = hole(k["name"])
            p["meldungen"].append({"team": d["kurz"], "klasse": d.get("klasse", ""), "datei": seite_datei(d),
                                   "nr": k.get("nr"), "stamm": k.get("stamm"), "rang": d["key"]})
            p["url"] = p["url"] or k.get("url")
            p["dwz_kader"] = p.get("dwz_kader") or k.get("dwz")
        for m in d.get("matches", []):
            if eigen not in (m["h"], m["g"]) or not m.get("bretter"):
                continue
            heim = m["h"] == eigen
            for b in m["bretter"]:
                brett, sp_h, sp_g, art, h, g, *rest = b
                dh, dg, uh, ug = (rest + [None] * 4)[:4]
                name, geg = (sp_h, sp_g) if heim else (sp_g, sp_h)
                if name.strip().lower() in KEIN_SPIELER:
                    continue
                mein_dwz, geg_dwz, mein_url, geg_url = (dh, dg, uh, ug) if heim else (dg, dh, ug, uh)
                if art == "score":
                    erg = h if heim else g
                elif art == "annulliert":
                    erg = None
                else:
                    erg = "+" if (art == "forfeit_heim") == heim else "-"
                p = hole(name)
                p["url"] = p["url"] or mein_url
                if mein_dwz and jahr >= p["dwz_board_jahr"]:
                    p["dwz_board"], p["dwz_board_jahr"] = mein_dwz, jahr
                p["partien"].append({
                    "team": d["kurz"], "klasse": d.get("klasse", ""), "datei": seite_datei(d), "rang": d["key"],
                    "r": m["r"], "heim": heim, "brett": brett, "gegner": geg, "gdwz": geg_dwz,
                    "gurl": geg_url, "gteam": name_von(d, m["g"] if heim else m["h"]),
                    "erg": erg, "art": art, "jahr": jahr, "saison": saison,
                })
    for p in spieler.values():
        p["partien"].sort(key=lambda x: (-x["jahr"], len(x["rang"]), x["rang"], x["r"]))
        p["meldungen"].sort(key=lambda x: (len(x["rang"]), x["rang"]))
    return spieler


# ==========================================
# SEITE
# ==========================================
def _erg_html(erg):
    if erg is None:
        return '<span class="erg klein">– / –</span>'
    if erg in ("+", "-"):
        cls = "s" if erg == "+" else "n"
        return f'<span class="erg erg-{cls} klein" title="kampflos">{"+" if erg == "+" else "–"}</span>'
    cls = "s" if erg == 1 else "n" if erg == 0 else "u"
    return f'<span class="erg erg-{cls} klein">{ERG_TEXT.get(float(erg), erg)}</span>'


def _zahl(x, stellen=2):
    return f"{x:.{stellen}f}".replace(".", ",")


def _punkte(x):
    return (str(int(x)) if float(x).is_integer() else str(x).replace(".5", "½").replace("0½", "½"))


def bilanz(partien):
    """-> (Punkte, gewertete Partien) ohne kampflose/annullierte."""
    gewertet = [x for x in partien if x["art"] == "score" and isinstance(x["erg"], (int, float))]
    return sum(x["erg"] for x in gewertet), len(gewertet)


def _team_tabelle(team, klasse, datei, liste):
    zeilen = []
    for x in liste:
        gname = esc(x["gegner"])
        if x.get("gurl"):
            gname = f'<a href="{esc(x["gurl"])}" target="_blank" rel="noopener">{gname}</a>'
        zeilen.append(
            f'<tr><td>{x["r"]}</td><td class="neben">{"Heim" if x["heim"] else "Gast"}</td><td>{x["brett"]}</td>'
            f'<td class="name">{gname}</td><td>{x["gdwz"] or "–"}</td>'
            f'<td class="name neben">{esc(x["gteam"])}</td><td>{_erg_html(x["erg"])}</td></tr>')
    pkt, n = bilanz(liste)
    return f"""
        <h4><a href="../{esc(datei)}">{esc(team)}</a> <span class="team-klasse">{esc(klasse)}</span></h4>
        <div class="tab-wrap"><table class="liga-tab">
          <thead><tr><th title="Runde">Rd</th><th class="neben">Ort</th><th title="Brett">Brt</th>
            <th class="name">Gegner</th><th>DWZ</th><th class="name neben">Mannschaft</th><th>Erg.</th></tr></thead>
          <tbody>{"".join(zeilen)}</tbody>
          <tfoot><tr><td colspan="7" class="rechts"><strong>Summe {_punkte(pkt)} / {n}</strong></td></tr></tfoot>
        </table></div>"""


def partien_html(p, aktuell):
    if not p["partien"]:
        return '<p class="klein">Noch keine gespielten Partien.</p>'
    saisons = {}
    for x in p["partien"]:
        saisons.setdefault((x["jahr"], x["saison"]), {}).setdefault((x["team"], x["klasse"], x["datei"]), []).append(x)
    teile = []
    for (jahr, saison), teams in saisons.items():
        alle = [x for liste in teams.values() for x in liste]
        pkt, n = bilanz(alle)
        kopf = f'Saison {esc(saison)} <span class="klein">{_punkte(pkt)} / {n}</span>'
        inhalt = "".join(_team_tabelle(*k, liste) for k, liste in teams.items())
        offen = " open" if jahr == aktuell else ""
        teile.append(f'<details class="sp-saison"{offen}><summary><h3>{kopf}</h3></summary>{inhalt}</details>')
    if not any(jahr == aktuell for jahr, _ in saisons):
        teile.insert(0, '<p class="klein">In dieser Saison noch keine gespielten Partien.</p>')
    return "".join(teile)


def prognose_html(p, r_alt, quelle, alter, index, aktuell):
    gewertet = [x for x in p["partien"] if x["jahr"] == aktuell and x["art"] == "score" and x["gdwz"]
                and isinstance(x["erg"], (int, float))]
    pr = prognose(r_alt, [x["gdwz"] for x in gewertet], [x["erg"] for x in gewertet], alter, index)
    if not pr:
        return ""
    diff = pr["neu"] - r_alt
    diff_txt = f'<span class="delta {"hoch" if diff > 0 else "runter" if diff < 0 else ""}">{diff:+d}</span>'
    return f"""
      <h3>Inoffizielle DWZ-Prognose (aktuelle Saison)</h3>
      <div class="tab-wrap"><table class="liga-tab">
        <thead><tr><th>DWZ jetzt</th><th title="Punkte">W</th><th title="Gewinnerwartung">W<sub>e</sub></th>
          <th class="neben" title="Entwicklungskoeffizient">E</th><th class="neben">Niveau</th>
          <th class="neben">Leistung</th><th>DWZ neu</th><th>±</th></tr></thead>
        <tbody><tr><td>{r_alt}</td><td>{_punkte(pr["w"])} / {pr["n"]}</td><td>{_zahl(pr["we"])}</td>
          <td class="neben">{pr["e"]}</td><td class="neben">{pr["niveau"]}</td>
          <td class="neben">{pr["leistung"] or "–"}</td><td><strong>{pr["neu"]}</strong></td><td>{diff_txt}</td></tr></tbody>
      </table></div>
      <p class="klein">Gerechnet mit der {quelle} DWZ, nur gespielte Partien gegen Gegner mit DWZ.
        Offiziell ausgewertet wird die Saison erst am Ende.</p>"""


# ==========================================
# DWZ-VERLAUF (eigene Aufzeichnung)
# ==========================================
def verlauf_laden():
    try:
        with open(VERLAUF, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def verlauf_eintragen(verlauf, sl, dwz, heute):
    """Neuen Wert anhängen, wenn er sich geändert hat. Ein Eintrag = [Datum, DWZ]."""
    if not dwz:
        return
    liste = verlauf.setdefault(sl, [])
    if not liste or liste[-1][1] != dwz:
        liste.append([heute.isoformat(), dwz])


def verlauf_html(punkte):
    """Kleines Liniendiagramm (SVG) aus [[Datum, DWZ], ...]."""
    if not VERLAUF_AN or len(punkte) < 2:
        return ""
    # Stufenverlauf bis heute verlängern
    pkt = [(datetime.date.fromisoformat(d), w) for d, w in punkte]
    pkt.append((max(datetime.date.today(), pkt[-1][0]), pkt[-1][1]))
    t0, t1 = pkt[0][0].toordinal(), pkt[-1][0].toordinal()
    lo, hi = min(w for _, w in pkt), max(w for _, w in pkt)
    lo, hi = lo - max(10, (hi - lo) * 0.15), hi + max(10, (hi - lo) * 0.15)
    B, H, L, R, O, U = 640, 200, 44, 12, 12, 26
    def x(d): return L + (d.toordinal() - t0) / max(1, t1 - t0) * (B - L - R)
    def y(w): return O + (hi - w) / (hi - lo) * (H - O - U)
    linie = []
    for i, (d, w) in enumerate(pkt):
        if i:
            linie.append(f"{x(d):.1f},{y(pkt[i - 1][1]):.1f}")
        linie.append(f"{x(d):.1f},{y(w):.1f}")
    raster = ""
    schritt = max(10, round((hi - lo) / 4 / 10) * 10)
    w = math.ceil(lo / schritt) * schritt
    while w <= hi:
        raster += (f'<line x1="{L}" x2="{B - R}" y1="{y(w):.1f}" y2="{y(w):.1f}" class="dv-raster"/>'
                   f'<text x="{L - 6}" y="{y(w) + 4:.1f}" text-anchor="end">{w}</text>')
        w += schritt
    marken = "".join(f'<circle cx="{x(d):.1f}" cy="{y(w):.1f}" r="3.5"><title>{d.strftime("%d.%m.%Y")}: {w}</title></circle>'
                     for d, w in pkt[:-1])
    jahre = ""
    for j in range(pkt[0][0].year + 1, pkt[-1][0].year + 1):
        d = datetime.date(j, 1, 1)
        jahre += f'<text x="{x(d):.1f}" y="{H - 6}" text-anchor="middle">{j}</text>'
    erster, letzter = pkt[0][1], pkt[-1][1]
    diff = letzter - erster
    return f"""
    <h2 class="panel-titel sp-titel">DWZ-Verlauf</h2>
    <p class="klein">Seit {pkt[0][0].strftime("%m/%Y")}: {erster} → {letzter}
      ({"+" if diff > 0 else ""}{diff}). Aufgezeichnet von der Website, sobald sich die DWZ beim DSB ändert.</p>
    <svg class="dwz-verlauf" viewBox="0 0 {B} {H}" role="img" aria-label="DWZ-Verlauf">
      {raster}{jahre}<polyline points="{" ".join(linie)}"/>{marken}</svg>"""


def _plain(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x or "")))


def berichte_finden(name, berichte):
    """Berichte, in denen der Spieler mit Vor- und Nachname (oder 'Nachname, Vorname') vorkommt."""
    teile = name.split()
    if len(teile) < 2:
        return []
    vor, nach = " ".join(teile[:-1]), teile[-1]
    muster = re.compile(rf"\b{re.escape(vor)}\s+{re.escape(nach)}\b|\b{re.escape(nach)},\s*{re.escape(vor)}\b", re.I)
    return [r for r in berichte if muster.search(_plain(r.get("title", "")) + " " + _plain(r.get("body", "")))]


def berichte_html(liste, eigene=()):
    """eigene = Berichte, die dieser Spieler geschrieben hat (stehen oben, mit Zähler)."""
    eigene = list(eigene)
    geschrieben = ""
    if eigene:
        li = "".join(f'<li><a href="../berichte/{esc(r["filename"])}">{esc(_plain(r["title"]))}</a>'
                     + (f' <span class="klein">{r["when"].strftime("%d.%m.%Y")}</span>' if r.get("when") and r["when"].year > 1 else "")
                     + "</li>" for r in eigene[:BERICHTE_MAX])
        rest_e = "".join(f'<li><a href="../berichte/{esc(r["filename"])}">{esc(_plain(r["title"]))}</a></li>' for r in eigene[BERICHTE_MAX:])
        geschrieben = (f'<h2 class="panel-titel sp-titel">Geschriebene Berichte <span class="sp-anzahl">{len(eigene)}</span></h2>'
                       f'<ul class="sp-berichte">{li}</ul>'
                       + (f'<details class="sp-mehr"><summary>… und {len(eigene) - BERICHTE_MAX} weitere anzeigen</summary>'
                          f'<ul class="sp-berichte">{rest_e}</ul></details>' if rest_e else ""))
    namen = {r["filename"] for r in eigene}
    liste = [r for r in liste if r["filename"] not in namen]
    if not liste:
        return geschrieben
    zeilen = "".join(
        f'<li><a href="../berichte/{esc(r["filename"])}">{esc(_plain(r["title"]))}</a>'
        + (f' <span class="klein">{r["when"].strftime("%d.%m.%Y")}</span>' if r.get("when") and r["when"].year > 1 else "")
        + "</li>" for r in liste[:BERICHTE_MAX])
    rest = "".join(
        f'<li><a href="../berichte/{esc(r["filename"])}">{esc(_plain(r["title"]))}</a>'
        + (f' <span class="klein">{r["when"].strftime("%d.%m.%Y")}</span>' if r.get("when") and r["when"].year > 1 else "")
        + "</li>" for r in liste[BERICHTE_MAX:])
    mehr = (f'<details class="sp-mehr"><summary>… und {len(liste) - BERICHTE_MAX} weitere anzeigen</summary>'
            f'<ul class="sp-berichte">{rest}</ul></details>') if rest else ""
    return geschrieben + f"""
    <h2 class="panel-titel sp-titel">In den Berichten</h2>
    <ul class="sp-berichte">{zeilen}</ul>{mehr}"""


def seite_html(p, dsb, saison_jahr, verlauf=(), berichte=(), tour="", bild="", geburtstag="", text="",
               gb_label="Jahrgang", konto=None, eigene=(), tour_box=""):
    """saison_jahr = Startjahr der aktuellen Saison (für Alter und Prognose)."""
    r_dsb = _int(dsb.get("dwz")) if dsb else None
    elo = _int(dsb.get("elo")) if dsb else None
    r_alt = r_dsb or p.get("dwz_kader") or p.get("dwz_board")
    quelle = "aktuellen" if r_dsb else "gemeldeten"
    jahr = _int(dsb.get("geburtsjahr")) if dsb else None
    alter = saison_jahr - jahr if jahr else None
    index = _int(dsb.get("dwz_index") or dsb.get("index")) if dsb else None

    def meldung(m):
        info = [m["klasse"]] + ([f"Nr. {m['nr']}"] if m.get("nr") else []) + (["Stamm"] if m.get("stamm") else [])
        return (f'<li><a href="../{esc(m["datei"])}">{esc(m["team"])}</a> '
                f'<span class="klein">{esc(" · ".join(x for x in info if x))}</span></li>')
    meldungen = "".join(meldung(m) for m in p["meldungen"]) or "<li>–</li>"
    bezirk = (f'<p class="klein"><a href="{esc(p["url"])}" target="_blank" rel="noopener">'
              f'Beim Schachbezirk ansehen ↗</a></p>' if p.get("url") else "")
    heim = sum(1 for x in p["partien"] if x["heim"] and x["art"] != "annulliert")
    ausw = sum(1 for x in p["partien"] if not x["heim"] and x["art"] != "annulliert")
    ha = f"<dt>Partien</dt><dd>Heim {heim} · Auswärts {ausw}</dd>" if heim + ausw else ""
    pkt, n = bilanz(p["partien"])
    gesamt = (f"<dt>Bilanz</dt><dd>{_punkte(pkt)} / {n} ({round(100 * pkt / n)} %)"
              f"{' seit ' + esc(p['partien'][-1]['saison']) if len({x['jahr'] for x in p['partien']}) > 1 else ''}</dd>"
              if n else "")
    nur_profil = not p["meldungen"] and not p["partien"]          # Mitglied ohne Mannschaftseinsätze
    daten = (f' data-profil-slug="{esc(slug(p["name"]))}"' + (f' data-benutzer="{esc(konto["benutzer"])}"' if konto else ""))
    zurueck = p["meldungen"][0]["datei"] if p["meldungen"] else (p["partien"][0]["datei"] if p["partien"] else "ueber-uns.html")
    zurueck_text = p["meldungen"][0]["team"] if p["meldungen"] else (p["partien"][0]["team"] if p["partien"] else "Über uns")
    return f"""
    <p class="zurueck"><a href="../{esc(zurueck)}">← {esc(zurueck_text)}</a></p>
    <div class="sp-oben"{daten}>
    <div class="sp-links">
    <h1 class="sp-name">{esc(p["name"])}{'<span class="kt-verifiziert" title="Registriertes Mitglied">verifiziert</span>' if konto else ""}</h1>
    <div class="sp-kopf">
      <dl>
        {f'<dt>DWZ</dt><dd>{r_alt or "–"}</dd>' if r_alt or not nur_profil else ""}
        {f"<dt>ELO</dt><dd>{elo}</dd>" if elo else ""}
        {gesamt}
        {ha}
        {f'<dt>Berichte</dt><dd>{len(eigene)} geschrieben</dd>' if eigene else ""}
        <div class="sp-gb" data-gb-zeile{"" if geburtstag else " hidden"}><dt>{esc(gb_label)}</dt><dd>{esc(geburtstag)}</dd></div>
      </dl>
      {"" if nur_profil else f'<div><strong>Gemeldet für</strong><ul class="sp-meldungen">{meldungen}</ul></div>'}
    </div>
    <div class="sp-text" data-kt-text{"" if text else " hidden"}>{text}</div>
    {bezirk}
    {f'<p class="klein"><a href="../{esc(tour)}">Turnierreisen bei AFK on Tour ansehen →</a></p>' if tour and not tour_box else ""}
    </div>
    {f'<img class="sp-foto" src="../{esc(bild)}" alt="{esc(p["name"])}">' if bild else ""}
    </div>
    {tour_box}
    {verlauf_html(list(verlauf))}
    {"" if nur_profil else '<h2 class="panel-titel sp-titel">Gespielte Partien</h2>' + partien_html(p, saison_jahr)}
    {prognose_html(p, r_alt, quelle, alter, index, saison_jahr) if PROGNOSE and r_alt and not nur_profil else ""}
    {berichte_html(list(berichte), eigene)}
    """


STYLES = """<style>
      .sp-name { color: var(--navy); margin: 0.2rem 0 0.8rem; }
      .sp-oben { display: flex; gap: 2.5rem; align-items: flex-start; justify-content: space-between; margin-bottom: 1rem; }
      .sp-links { flex: 1 1 auto; min-width: 0; }
      .sp-text { max-width: 640px; margin: 1.2rem 0 .8rem; padding: .9rem 1.1rem; border-left: 3px solid var(--link-c, var(--link));
        background: var(--soft, rgba(127,127,127,.08)); border-radius: 0 10px 10px 0; }
      .sp-text p { margin: 0 0 .6rem; } .sp-text p:last-child { margin-bottom: 0; }
      .sp-text strong { display: block; margin-bottom: .3rem; }
      .sp-text[hidden], .sp-gb[hidden] { display: none; }
      .sp-gb { display: contents; }
      .sp-links-profil { font-size: .95rem; }
      .sp-foto { width: clamp(240px, 26vw, 380px); height: auto; max-height: 480px; object-fit: contain; border-radius: 12px;
        flex: 0 0 auto; box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3); }
      @media (max-width: 800px) { .sp-oben { flex-direction: column-reverse; gap: 1.2rem; } .sp-foto { width: min(100%, 320px); } }
      .sp-kopf { display: flex; flex-wrap: wrap; gap: 0.8rem 3rem; align-items: flex-start; margin-bottom: 0.5rem; }
      .sp-kopf dl { display: grid; grid-template-columns: auto auto; gap: 0.2rem 1rem; margin: 0; }
      .sp-kopf dt { font-weight: bold; color: var(--navy); }
      .sp-kopf dd { margin: 0; }
      .sp-meldungen { margin: 0.2rem 0 0; padding-left: 1.1rem; }
      .sp-titel { display: block !important; }
      .liga-tab tfoot td { border-top: 2px solid var(--navy); }
      .sp-saison { border-top: 1px solid var(--border); }
      .sp-saison > summary { cursor: pointer; list-style: none; }
      .sp-saison > summary::-webkit-details-marker { display: none; }
      .sp-saison > summary h3 { display: inline-flex; gap: 0.8rem; align-items: baseline; margin: 0.8rem 0; color: var(--navy); }
      .sp-saison > summary h3::after { content: "▸"; color: #888; font-size: 0.9rem; }
      .sp-saison[open] > summary h3::after { content: "▾"; }
      .sp-saison h4 { margin: 0.6rem 0 0.4rem; }
      .dwz-verlauf { width: 100%; max-width: 680px; height: auto; display: block; margin: 0.3rem 0 1rem; font-size: 11px; }
      .dwz-verlauf text { fill: var(--muted, #777); }
      .dwz-verlauf .dv-raster { stroke: var(--border, #e3e7ee); stroke-width: 1; }
      .dwz-verlauf polyline { fill: none; stroke: var(--hell, #2c5d99); stroke-width: 2.5; stroke-linejoin: round; }
      .dwz-verlauf circle { fill: var(--hell, #2c5d99); }
      .sp-berichte { margin: 0.3rem 0 1rem; padding-left: 1.1rem; display: grid; gap: 0.25rem; }
      .sp-mehr summary { cursor: pointer; color: var(--link-c, var(--link)); font-weight: 600; font-size: .95rem; margin-bottom: .4rem; }
      .sp-mehr summary:hover { text-decoration: underline; }
      .sp-anzahl { font-size: .8rem; font-weight: 700; background: var(--soft, rgba(127,127,127,.12)); border-radius: 999px; padding: .1rem .55rem; vertical-align: middle; }
      .sp-tour { margin: 1.2rem 0 1.6rem; padding: 1.1rem 1.3rem; max-width: 760px; }
      .sp-tour-kopf { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: .3rem 1rem; }
      .sp-tour-kopf h2 { margin: 0; font-size: 1.15rem; color: var(--navy); }
      .sp-tour-zahlen { display: grid; grid-template-columns: repeat(4, 1fr); gap: .5rem; margin: .8rem 0; }
      .sp-tour-zahlen div { text-align: center; padding: .5rem .2rem; border-radius: 8px; background: var(--soft, rgba(127,127,127,.08)); }
      .sp-tour-zahlen b { display: block; font-size: 1.3rem; color: var(--navy); }
      .sp-tour-zahlen span { font-size: .78rem; color: var(--muted); }
      @media (max-width: 520px) { .sp-tour-zahlen { grid-template-columns: repeat(2, 1fr); } }
      .tour-chips { display: flex; flex-wrap: wrap; gap: .25rem; align-items: center; }
      .tour-abz { display: inline-block; font-size: 0.78rem; padding: 0.1rem 0.55rem; border-radius: 999px; background: var(--hell, #6f9fd8); color: #0e1524; white-space: nowrap; }
      .tour-abz.st-bronze { background: #b87333; color: #fff; }
      .tour-abz.st-silber { background: #8e9aa6; color: #fff; }
      .tour-abz.st-gold { background: #d4a017; color: #1b1b1b; }
      .tour-abz.st-legendaer { background: linear-gradient(135deg, #7b4fbf, #c0392b); color: #fff; }
</style>"""


def bauen(spieler, dsb_liste, render_page, liga_styles, saison_jahr, berichte=(), tour_seiten=None, geburtstage=(), konten=None,
          tour_box=None):
    """Schreibt alle Spielerseiten. render_page/liga_styles kommen aus build_site/liga.
    berichte = build_site.ALLE_BERICHTE; tour_seiten(name) -> 'tour-….html' oder '';
    geburtstage = Geburtstagsliste (nur für Spieler, die in profile.json freigegeben sind)."""
    idx = dsb_index(dsb_liste)
    verlauf = verlauf_laden()
    heute = datetime.date.today()
    profile = profile_laden()
    konten = konten or {}
    alle = dict(spieler)
    for sl_k, k in konten.items():          # registrierte Mitglieder ohne Mannschaftseinsätze bekommen auch eine Seite
        if not any(slug(p["name"]) == sl_k for p in alle.values()):
            alle["konto:" + sl_k] = {"name": k["name"], "meldungen": [], "partien": [], "url": ""}
    for p in alle.values():
        dsb = dsb_finden(p["name"], idx)
        sl = slug(p["name"])
        if dsb:
            verlauf_eintragen(verlauf, sl, _int(dsb.get("dwz")), heute)
        tour = (tour_seiten(p["name"]) if tour_seiten and TOUR_LINK else "") or ""
        k = konten.get(sl)
        if k:                                # eigenes Profil aus dem Mitgliederbereich
            kfoto = os.path.join(KONTO_FOTOS, sl + ".jpg")
            bild = kfoto.replace(os.sep, "/") if k.get("foto") and os.path.exists(kfoto) else foto(p["name"])
            text = konto_text_html(k) or text_html(p["name"])
            gb_label, gb = konto_geburtstag(k)
        else:
            platzhalter_anlegen(p["name"])
            bild, text, gb_label = foto(p["name"]), text_html(p["name"]), "Jahrgang"
            gb = geburtstag_text(p["name"], profile.get(sl), geburtstage, heute)
        # Tour-Box nur, wenn das Mitglied es in "Mein Profil" eingeschaltet hat
        box = tour_box(p["name"]) if tour_box and k and k.get("tour") else ""
        eigene = [r for r in berichte if r.get("autor_slug") == sl]
        content = seite_html(p, dsb, saison_jahr, verlauf.get(sl, []), berichte_finden(p["name"], berichte), tour,
                             bild=bild, text=text, geburtstag=gb, gb_label=gb_label, konto=k, eigene=eigene, tour_box=box or "")
        render_page(p["name"], content, seite(p["name"]), css_path="../", nav_path="../",
                    extra_styles=liga_styles.replace("</style>", "") + STYLES.replace("<style>", ""),
                    description=f"{p['name']} – Partien und DWZ in der Mannschaftssaison.")
    if dsb_liste:            # nur mit echten DSB-Daten fortschreiben
        os.makedirs(ORDNER, exist_ok=True)
        with open(VERLAUF, "w", encoding="utf-8") as f:     # eine Zeile pro Spieler
            f.write("{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(verlauf.items())) + "\n}\n")
    return len(spieler)
