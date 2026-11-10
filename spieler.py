"""
Spielerseiten (spieler/<name>.html) für alle eigenen Spieler aus den Mannschafts-Daten
(mannschaften/*.json vom Tabellenrechner):
  - DWZ / ELO (aktuell von der DSB-Vereinsliste, sonst aus der Meldeliste)
  - gemeldet für: Mannschaft, Melde-Nr., Stamm (Meldeliste beim Bezirk)
  - alle gespielten Partien über alle Mannschaften und Saisons (aktuelle offen, ältere zugeklappt)
  - inoffizielle DWZ-Prognose mit der AKTUELLEN DWZ (Wertungsordnung des DSB)

build_site.py: erst sammeln(teams, dsb) -> liga.SPIELER_SEITEN, dann bauen(...).
Das Geburtsjahr von der DSB-Liste wird nur für den Entwicklungskoeffizienten benutzt,
nie angezeigt oder gespeichert.
"""

import html
import math
import re
import unicodedata
from statistics import NormalDist

# ==========================================
# EINSTELLUNGEN
# ==========================================
ORDNER = "spieler"                  # spieler/<slug>.html
PROGNOSE = True                     # DWZ-Prognose anzeigen
J_OHNE_ALTER = 15                   # Altersfaktor J, wenn kein Geburtsjahr bekannt (über 25 Jahre)
KEIN_SPIELER = {"", "n.n.", "nn", "-", "spielfrei"}
ERG_TEXT = {1.0: "1", 0.5: "½", 0.0: "0"}


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


def seite_html(p, dsb, saison_jahr):
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
    zurueck = p["meldungen"][0]["datei"] if p["meldungen"] else (p["partien"][0]["datei"] if p["partien"] else "mannschaften.html")
    zurueck_text = p["meldungen"][0]["team"] if p["meldungen"] else (p["partien"][0]["team"] if p["partien"] else "Mannschaften")
    return f"""
    <p class="zurueck"><a href="../{esc(zurueck)}">← {esc(zurueck_text)}</a></p>
    <h1 class="sp-name">{esc(p["name"])}</h1>
    <div class="sp-kopf">
      <dl>
        <dt>DWZ</dt><dd>{r_alt or "–"}</dd>
        {f"<dt>ELO</dt><dd>{elo}</dd>" if elo else ""}
        {gesamt}
        {ha}
      </dl>
      <div><strong>Gemeldet für</strong><ul class="sp-meldungen">{meldungen}</ul></div>
    </div>
    {bezirk}
    <h2 class="panel-titel sp-titel">Gespielte Partien</h2>
    {partien_html(p, saison_jahr)}
    {prognose_html(p, r_alt, quelle, alter, index, saison_jahr) if PROGNOSE and r_alt else ""}
    """


STYLES = """<style>
      .sp-name { color: var(--navy); margin: 0.2rem 0 0.8rem; }
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
</style>"""


def bauen(spieler, dsb_liste, render_page, liga_styles, saison_jahr):
    """Schreibt alle Spielerseiten. render_page/liga_styles kommen aus build_site/liga."""
    idx = dsb_index(dsb_liste)
    for p in spieler.values():
        content = seite_html(p, dsb_finden(p["name"], idx), saison_jahr)
        render_page(p["name"], content, seite(p["name"]), css_path="../", nav_path="../",
                    extra_styles=liga_styles.replace("</style>", "") + STYLES.replace("<style>", ""),
                    description=f"{p['name']} – Partien und DWZ in der Mannschaftssaison.")
    return len(spieler)
