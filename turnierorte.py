"""
"AFK on Tour" – Turnierorte sammeln (wie Stadion-Sammeln beim Fußball).

Jede Stadt zählt pro Spieler einmal, egal wie oft man dort war. Gezählt werden klassische
Einzelturniere (keine Liga); Ausnahmen (z. B. Deutsche Hochschulmeisterschaft) kann der Webmaster zulassen.

Ablauf:
  1. Mitglied füllt auf turnierorte.html "Turnier einreichen" aus -> Apps Script legt
     turnierorte/antraege/<Datum>_<Name>.json im Repo an und schickt eine Mail.
  2. Webmaster: "Alles aktualisieren", dann  py turnierorte_pruefen.py  (prüft mit chess-results,
     sucht den Ort, fragt j/n) -> landet in turnierorte/besuche.json. Nochmal "Alles aktualisieren".
  Eigene alte Turniere direkt eintragen:  py turnierorte_pruefen.py --neu
  Fehler korrigieren (löschen, ausblenden, Link/Ort/Datum ändern):  py turnierorte_pruefen.py --verwalten

Dateien (alle in turnierorte/):
  spieler.json        Profile: {"KorbinianR": {"name": "Korbinian Ruff", "anzeige": "Korbinian R."}}
  besuche.json        bestätigte Turniere (eine Zeile pro Spieler und Turnier)
  einstellungen.json  Ortsgruppen (z. B. Tegernsee), Heimat, Texte
  antraege/           offene Anträge (werden vom Prüfskript abgearbeitet)
"""

import datetime
import html
import json
import math
import os
import re
import unicodedata

import abzeichen

ORDNER = "turnierorte"
SEITE = "turnierorte.html"
TITEL = "AFK on Tour"



def _lade(pfad, standard):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return standard


def _speichere(pfad, daten):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pfad)


def einstellungen():
    return _lade(os.path.join(ORDNER, "einstellungen.json"), {})


def spieler_laden():
    return _lade(os.path.join(ORDNER, "spieler.json"), {})


def besuche_laden():
    return _lade(os.path.join(ORDNER, "besuche.json"), [])


def spieler_id(name):
    """'Korbinian Ruff' -> 'KorbinianR' (wie in der Aufstellungs-Datenbank)."""
    teile = [t for t in re.split(r"\s+", name.strip()) if t]
    if not teile:
        return ""
    vor = re.sub(r"[^\wäöüÄÖÜß]", "", "".join(teile[:-1]) or teile[0])
    return vor + (teile[-1][0].upper() if len(teile) > 1 else "")


def seite_fuer_name(name):
    """Für die Spielerseiten: 'tour-<id>.html', wenn dieser Spieler ein AFK-on-Tour-Profil hat (sonst '')."""
    sid = spieler_id(name)
    profil = spieler_laden().get(sid)
    if not profil or profil.get("ausgeblendet"):
        return ""
    return spieler_seite(sid) if os.path.exists(spieler_seite(sid)) else ""


def anzeige_name(name):
    teile = name.split()
    return f"{' '.join(teile[:-1])} {teile[-1][0]}." if len(teile) > 1 else name


def _km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    x = math.sin(math.radians(c - a) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def ort_gruppe(stadt, gruppen):
    """'Bad Wiessee' -> 'Tegernsee', wenn so in den Ortsgruppen eingetragen."""
    s = stadt.strip().lower()
    for gruppe, orte in (gruppen or {}).items():
        if s == gruppe.lower() or s in (o.lower() for o in orte):
            return gruppe
    return stadt.strip()


# ------------------------------------------------------------
# Auswertung
# ------------------------------------------------------------
def auswerten(spieler, besuche, konf):
    gruppen = konf.get("ort_gruppen", {})
    heimat = konf.get("heimat") or {"lat": 48.1766, "lon": 11.7553}
    orte = {}                    # Ort -> {lat, lon, land, besuche: [...]}
    pro = {sid: [] for sid in spieler}
    for b in besuche:
        if b.get("spieler") not in spieler or b.get("ausgeblendet"):
            continue
        ort = ort_gruppe(b.get("stadt", ""), gruppen)
        if not ort:
            continue
        o = orte.setdefault(ort, {"ort": ort, "land": b.get("land", ""), "lat": b.get("lat"), "lon": b.get("lon"), "besuche": []})
        if o["lat"] is None and b.get("lat") is not None:
            o["lat"], o["lon"] = b["lat"], b["lon"]
        o["besuche"].append(b)
        pro[b["spieler"]].append(dict(b, ort=ort))
    tabelle = []
    for sid, liste in pro.items():
        if not liste:
            continue
        zaehl = {}
        for b in liste:
            zaehl[b["ort"]] = zaehl.get(b["ort"], 0) + 1
        laender = {b.get("land", "") for b in liste if b.get("land")}
        weit = max([_km(heimat["lat"], heimat["lon"], b["lat"], b["lon"]) for b in liste if b.get("lat") is not None] or [0])
        werte = {"orte": len(zaehl), "laender": len(laender), "turniere": len(liste),
                 "ausland": len([l for l in laender if l != "Deutschland"]), "max_gleich": max(zaehl.values()),
                 "weiteste": round(weit)}
        tabelle.append({"id": sid, "name": spieler[sid].get("anzeige") or anzeige_name(spieler[sid].get("name", sid)),
                        "werte": werte, "liste": sorted(liste, key=lambda b: b.get("von", ""), reverse=True)})
    tabelle.sort(key=lambda t: (-t["werte"]["orte"], -t["werte"]["laender"], -t["werte"]["turniere"], t["name"]))
    infos, pro_abz = abzeichen.auswerten({t["id"]: t["liste"] for t in tabelle},
                                         [b for t in tabelle for b in t["liste"]], heimat, konf)
    for t in tabelle:
        t.update(pro_abz[t["id"]])
    return tabelle, orte, infos


def _monat(datum):
    """'2017-06-12' oder '2017-06' -> 'Juni 2017'"""
    namen = ["Jan", "Feb", "März", "Apr", "Mai", "Juni", "Juli", "Aug", "Sep", "Okt", "Nov", "Dez"]
    m = re.match(r"(\d{4})-(\d{1,2})", datum or "")
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{namen[int(m.group(2)) - 1]} {m.group(1)}"
    return (datum or "")[:4]


def _stufen_html(t, infos):
    """Kleine Zähler je Stufe, z. B. Gold 2 · Silber 5 · Bronze 4."""
    n = {}
    for a in infos:
        if a["id"] in t["erreicht"]:
            n[a["stufe"]] = n.get(a["stufe"], 0) + 1
    return " ".join(f'<span class="st st-{k}" title="{abzeichen.STUFEN[k][0]}">{n[k]}</span>'
                    for k in ("legendaer", "gold", "silber", "bronze") if n.get(k))


def _seltenste_html(t, infos, anzahl=4):
    eigene = sorted((a for a in infos if a["id"] in t["erreicht"]), key=lambda a: (a["anteil"], -a["punkte"]))[:anzahl]
    return "".join(f'<span class="tour-abz st-{a["stufe"]}" title="{html.escape(a["text"])} – {a["anteil"]} % im Verein">'
                   f'{html.escape(a["name"])}</span>' for a in eigene)


# ------------------------------------------------------------
# Seite
# ------------------------------------------------------------
CSS = """
  .tour-zahlen { display: flex; flex-wrap: wrap; gap: 0.8rem; margin: 1rem 0 1.4rem; }
  .tour-zahl { flex: 1 1 8rem; padding: 0.8rem 1rem; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
  .tour-zahl strong { display: block; font-size: 1.8rem; line-height: 1.1; }
  .tour-zahl span { font-size: 0.85rem; color: var(--muted); }
  .tour-kartenkopf { display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; align-items: center; justify-content: space-between; margin: 1.6rem 0 0.6rem; }
  .tour-kartenkopf h2 { margin: 0; }
  .tour-kartenkopf select { font: inherit; padding: 0.35rem 0.5rem; border: 1px solid var(--line); border-radius: 6px; background: var(--soft); color: var(--text); }
  #tour-karte { height: 480px; border-radius: 10px; border: 1px solid var(--line); z-index: 0; }
  @media (max-width: 600px) { #tour-karte { height: 360px; } }
  .tour-flagge { background: none; border: 0; }
  .tour-flagge svg { overflow: visible; filter: drop-shadow(0 1px 2px rgba(0,0,0,.4)); }
  .leaflet-popup-content { font-size: 0.85rem; line-height: 1.35; }
  .leaflet-popup-content-wrapper, .leaflet-popup-tip { background: var(--surface, #fff); color: var(--text, #222);
    box-shadow: 0 4px 16px rgba(0,0,0,.35); }
  .leaflet-popup-content-wrapper { border: 1px solid var(--line, #ddd); border-radius: 10px; }
  .leaflet-popup-content a { color: var(--link-c, #2c5d99); }
  .leaflet-container a.leaflet-popup-close-button { color: var(--muted, #888); }
  .leaflet-container { font-family: inherit; }
  .leaflet-control-zoom a { background: var(--surface, #fff); color: var(--text, #222); border-color: var(--line, #ccc); }
  .leaflet-control-attribution { background: rgba(0,0,0,.35) !important; color: #ccc; }
  .leaflet-control-attribution a { color: #ddd; }
  .leaflet-popup-content h4 { margin: 0 0 0.3rem; font-size: 1rem; }
  .leaflet-popup-content ul { margin: 0; padding-left: 1rem; }
  .tour-tab { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
  .tour-tab th, .tour-tab td { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
  .tour-tab th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--muted); }
  .tour-tab td.z { text-align: right; font-variant-numeric: tabular-nums; }
  .tour-tab tr:first-child td:first-child { font-weight: 800; }
  .tour-abz { display: inline-block; font-size: 0.72rem; padding: 0.05rem 0.45rem; margin: 0.1rem 0.15rem 0.1rem 0; border-radius: 999px;
    background: var(--hell, #6f9fd8); color: #0e1524; white-space: nowrap; }
  .tour-profile { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: 0.8rem; margin-top: 1rem; }
  .tour-profil { padding: 0.9rem 1rem; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); scroll-margin-top: 90px; }
  .tour-profil h3 { margin: 0 0 0.2rem; }
  .tour-profil .k { font-size: 0.85rem; color: var(--muted); margin: 0 0 0.4rem; }
  .tour-profil ul { margin: 0.5rem 0 0; padding-left: 1.1rem; font-size: 0.88rem; }
  .tour-profil li small { color: var(--muted); }
  .tour-hinweis { font-size: 0.9rem; color: var(--muted); }
  .tour-abz.st-bronze, .st.st-bronze { background: #b87333; color: #fff; }
  .tour-abz.st-silber, .st.st-silber { background: #8e9aa6; color: #fff; }
  .tour-abz.st-gold, .st.st-gold { background: #d4a017; color: #1b1b1b; }
  .tour-abz.st-legendaer, .st.st-legendaer { background: linear-gradient(135deg, #7b4fbf, #c0392b); color: #fff; }
  .st { display: inline-block; min-width: 1.4rem; text-align: center; font-size: 0.75rem; font-weight: 700; padding: 0.05rem 0.35rem;
    border-radius: 999px; margin-right: 0.15rem; }
  .abz-kopf { display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; margin: 1.4rem 0 0.8rem; }
  .abz-kopf label { display: grid; gap: 0.2rem; font-size: 0.85rem; font-weight: 600; }
  .abz-kopf select { font: inherit; font-weight: normal; padding: 0.35rem 0.5rem; border: 1px solid var(--line); border-radius: 6px;
    background: var(--soft); color: var(--text); }
  .abz-kat { margin: 1.2rem 0 0.5rem; font-size: 1.05rem; }
  .abz-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr)); gap: 0.6rem; }
  .abz { position: relative; padding: 0.7rem 0.85rem 0.75rem; border: 1px solid var(--line); border-left: 5px solid var(--line);
    border-radius: 10px; background: var(--surface); }
  .abz.st-bronze { border-left-color: #b87333; } .abz.st-silber { border-left-color: #8e9aa6; }
  .abz.st-gold { border-left-color: #d4a017; } .abz.st-legendaer { border-left-color: #7b4fbf; }
  .abz h4 { margin: 0 0 0.15rem; font-size: 0.98rem; display: flex; justify-content: space-between; gap: 0.5rem; align-items: baseline; }
  .abz h4 small { font-weight: 600; font-size: 0.72rem; color: var(--muted); white-space: nowrap; }
  .abz p { margin: 0; font-size: 0.84rem; }
  .abz .wer { margin-top: 0.35rem; font-size: 0.78rem; color: var(--muted); }
  .abz.offen { opacity: 0.55; }
  .abz.erreicht { box-shadow: 0 0 0 1px var(--hell, #6f9fd8) inset; }
  .abz .balken { height: 6px; border-radius: 3px; background: var(--soft); margin-top: 0.4rem; overflow: hidden; }
  .abz .balken span { display: block; height: 100%; background: var(--hell, #6f9fd8); }
  .abz .selten { position: absolute; right: 0.6rem; bottom: 0.45rem; font-size: 0.7rem; font-weight: 700; color: #c0392b; }
  .rl-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0 0 0.6rem; }
  .rl-tabs button { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.75rem; border-radius: 999px; border: 1px solid var(--line);
    background: transparent; color: var(--text); cursor: pointer; }
  .rl-tabs button.an { background: var(--hell, #6f9fd8); color: #0e1524; border-color: transparent; font-weight: 700; }
  .tour-tab.rl th[data-nach] { cursor: pointer; }
  .tour-tab.rl th.z, .tour-tab.rl td.z { text-align: center; }
  .tour-tab.rl th.an, .tour-tab.rl td.an { color: var(--text); font-weight: 700; }
  .tour-tab.rl tr td.pl { font-weight: 800; width: 2.5rem; }
  .tour-tab.rl tr.platz1 td.pl { color: #d4a017; } .tour-tab.rl tr.platz2 td.pl { color: #9aa6b2; }
  .tour-tab.rl tr.platz3 td.pl { color: #b87333; }
  .tour-tab.rl tr.platz1 { box-shadow: inset 4px 0 0 #d4a017; } .tour-tab.rl tr.platz2 { box-shadow: inset 4px 0 0 #9aa6b2; }
  .tour-tab.rl tr.platz3 { box-shadow: inset 4px 0 0 #b87333; }
  .rl-mehr { text-align: center; margin: 0.8rem 0 0; }
  .rl-mehr button { font: inherit; font-weight: 600; padding: 0.45rem 1.1rem; border-radius: 8px; border: 1px solid var(--line);
    background: var(--surface); color: var(--text); cursor: pointer; }
  @media (max-width: 700px) {
    .tour-tab.rl thead { display: none; }
    .tour-tab.rl, .tour-tab.rl tbody { display: block; }
    .tour-tab.rl tr { display: grid; grid-template-columns: 2.2rem repeat(3, minmax(0, 1fr)); gap: 0.15rem 0.5rem; padding: 0.6rem 0.4rem;
      font-size: 0.85rem;
      border-bottom: 1px solid var(--line); }
    .tour-tab.rl td { border: 0; padding: 0; text-align: left !important; }
    .tour-tab.rl td.sp { grid-column: 2 / -1; font-weight: 700; }
    .tour-tab.rl td.pl { grid-row: span 3; }
    .tour-tab.rl td[data-l]::before { content: attr(data-l) ": "; color: var(--muted); font-size: 0.78rem; }
    .tour-tab.rl td.st-zelle { grid-column: 2 / -1; }
  }
  .tour-weiter { margin: 0.9rem 0 0; font-weight: 600; }
  .tour-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .tour-liste { padding-left: 1.1rem; }
  .tour-liste li { margin-bottom: 0.45rem; }
  .tour-liste li small { color: var(--muted); }
  .tour-leer { padding: 1.4rem; text-align: center; color: var(--muted); border: 1px dashed var(--line); border-radius: 10px; }
  .tour-antrag { margin-top: 2.5rem; }
  .tour-antrag > summary { cursor: pointer; list-style: none; padding: 0.9rem 1.2rem; display: flex; justify-content: space-between;
    align-items: center; gap: 1rem; flex-wrap: wrap; }
  .tour-antrag > summary::-webkit-details-marker { display: none; }
  .tour-antrag form { display: grid; gap: 0.8rem; padding: 0 1.2rem 1.2rem; }
  .tour-reihe { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 0.8rem; }
  .tour-antrag label { display: grid; gap: 0.25rem; font-weight: 600; font-size: 0.9rem; }
  .tour-antrag label.inline { display: flex; align-items: center; gap: 0.4rem; font-weight: normal; }
  .tour-antrag input, .tour-antrag select, .tour-antrag textarea { font: inherit; font-weight: normal; padding: 0.5rem 0.65rem;
    border: 1px solid var(--line); border-radius: 6px; background: var(--soft); color: var(--text); width: 100%; box-sizing: border-box; }
  .tour-antrag label.inline input { width: auto; }
  .tour-antrag .klein { font-size: 0.85rem; color: var(--muted); margin: 0; font-weight: normal; }
  .tour-antrag .falle { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
  .tour-antrag .meldung { margin: 0; font-weight: 600; }
  .tour-antrag .meldung.ok { color: #2e8b57; }
  .tour-antrag .meldung.fehler { color: #c0392b; }
"""

FLAGGE = ('<svg width="34" height="40" viewBox="0 0 34 40"><line x1="3" y1="2" x2="3" y2="39" stroke="#333" stroke-width="2.6"/>'
          '<path d="M4 3 H31 L26 11 L31 19 H4 Z" fill="{farbe}" stroke="#fff" stroke-width="1.2"/>'
          '<text x="15.5" y="15" font-size="11" font-weight="700" text-anchor="middle" fill="#fff" font-family="sans-serif">{n}</text></svg>')

LAENDER_ISO = {  # deutscher Ländername -> Nummer in den Ländergrenzen (ISO 3166 numerisch); Kosovo hat keine
    "Deutschland": "276", "Österreich": "040", "Schweiz": "756", "Italien": "380", "Frankreich": "250", "Spanien": "724",
    "Portugal": "620", "Niederlande": "528", "Belgien": "056", "Luxemburg": "442", "Dänemark": "208", "Polen": "616",
    "Tschechien": "203", "Slowakei": "703", "Ungarn": "348", "Slowenien": "705", "Kroatien": "191",
    "Bosnien und Herzegowina": "070", "Serbien": "688", "Montenegro": "499", "Nordmazedonien": "807", "Albanien": "008",
    "Griechenland": "300", "Bulgarien": "100", "Rumänien": "642", "Moldau": "498", "Republik Moldau": "498", "Ukraine": "804",
    "Belarus": "112", "Russland": "643", "Litauen": "440", "Lettland": "428", "Estland": "233", "Finnland": "246",
    "Schweden": "752", "Norwegen": "578", "Island": "352", "Irland": "372", "Vereinigtes Königreich": "826",
    "Großbritannien": "826", "Malta": "470", "Zypern": "196", "Türkei": "792", "Liechtenstein": "438", "Monaco": "492",
    "Andorra": "020", "San Marino": "674", "Georgien": "268", "Armenien": "051", "Aserbaidschan": "031", "Israel": "376",
    "Vereinigte Staaten": "840", "Kanada": "124", "China": "156", "Indien": "356", "Japan": "392", "Australien": "036",
    "Brasilien": "076", "Argentinien": "032", "Mexiko": "484", "Südafrika": "710", "Ägypten": "818", "Marokko": "504",
    "Tunesien": "788", "Vereinigte Arabische Emirate": "784", "Katar": "634", "Singapur": "702", "Thailand": "764",
}
KARTE_FARBEN = {
    "dunkel": {"meer": "#0e1524", "land": "#1d2b47", "besucht": "#2f5d9a", "rand": "#3c5070"},
    "hell": {"meer": "#dfe8f2", "land": "#f7f8fa", "besucht": "#b9d0ea", "rand": "#a8b6c7"},
}
GRENZEN_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"
LIBS = ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
        '<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>')

JS_KARTE = r"""
(function () {
  var D = JSON.parse(document.getElementById("tour-daten").textContent), el = document.getElementById("tour-karte");
  if (!el || !window.L) return;
  var F = D.karte, sel = document.getElementById("tour-wer");
  function thema() { return document.documentElement.getAttribute("data-theme") === "dark" ? "dunkel" : "hell"; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  var karte = L.map(el, {scrollWheelZoom: false, zoomSnap: 0.25}).setView([48.5, 11], 5);
  karte.attributionControl.addAttribution('Grenzen &copy; <a href="https://www.naturalearthdata.com/">Natural Earth</a>');
  var grenzen = null, marker = L.layerGroup().addTo(karte), besucht = {};
  function stil() {
    var f = F[thema()];
    el.style.background = f.meer;
    if (grenzen) grenzen.setStyle(function (ft) {
      var b = besucht[ft.id] || besucht["name:" + ft.properties.name];
      return {color: f.rand, weight: 0.8, fillColor: b ? f.besucht : f.land, fillOpacity: 1};
    });
  }
  function zeichne() {
    var wer = sel ? sel.value : D.fest, punkte = [];
    marker.clearLayers(); besucht = {};
    D.orte.forEach(function (o) {
      var b = o.besuche.filter(function (x) { return !wer || x.id === wer; });
      if (!b.length || o.lat == null) return;
      if (o.iso) besucht[o.iso] = 1;
      var leute = {}; b.forEach(function (x) { leute[x.id] = 1; });
      var n = wer ? b.length : Object.keys(leute).length;
      var icon = L.divIcon({className: "tour-flagge", iconSize: [34, 40], iconAnchor: [3, 39], popupAnchor: [13, -36],
        html: D.flagge.replace("{farbe}", D.farbe).replace("{n}", n)});
      var html = "<h4>" + esc(o.ort) + (o.land ? " <small>(" + esc(o.land) + ")</small>" : "") + "</h4><ul>" +
        b.map(function (x) {
          var t = x.link ? '<a href="' + esc(x.link) + '" target="_blank" rel="noopener">' + esc(x.turnier || "Turnier") + "</a>" : esc(x.turnier || "");
          return "<li>" + esc(x.monat) + (wer ? "" : " · <b>" + esc(x.name) + "</b>") + (t ? " · " + t : "") + "</li>";
        }).join("") + "</ul>";
      L.marker([o.lat, o.lon], {icon: icon}).bindPopup(html).addTo(marker);
      punkte.push([o.lat, o.lon]);
    });
    stil();
    if (punkte.length > 1) karte.fitBounds(punkte, {padding: [40, 40], maxZoom: 7});
    else if (punkte.length === 1) karte.setView(punkte[0], 6);
  }
  fetch(D.grenzen).then(function (r) { return r.json(); }).then(function (topo) {
    grenzen = L.geoJSON(topojson.feature(topo, topo.objects.countries), {interactive: false}).addTo(karte);
    grenzen.bringToBack(); stil();
  }).catch(function () {});
  new MutationObserver(stil).observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme"]});
  if (sel) sel.addEventListener("change", zeichne);
  zeichne();
})();
"""

JS_RANGLISTE = r"""
(function () {
  var D = JSON.parse(document.getElementById("tour-daten").textContent), out = document.getElementById("rangliste");
  if (!out || !D.rangliste) return;
  var SP = [["orte", "Orte"], ["laender", "Länder"], ["turniere", "Turniere"], ["km", "Weiteste Reise"], ["punkte", "Punkte"]];
  var KURZ = {orte: "Orte", laender: "Länder", turniere: "Turniere", km: "Weiteste", punkte: "Punkte"};
  var nach = "orte", alle = false, TOP = 10;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function zeichne() {
    var reihen = D.rangliste.slice().sort(function (a, b) {
      return b[nach] - a[nach] || b.orte - a.orte || b.punkte - a.punkte || a.name.localeCompare(b.name, "de");
    });
    // Gleicher Platz nur bei echtem Gleichstand (Sortierwert, Orte und Punkte gleich)
    var platz = 0, vorher = null;
    reihen.forEach(function (r, i) {
      var k = [r[nach], r.orte, r.punkte].join("|");
      if (k !== vorher) platz = i + 1; r._platz = platz; vorher = k;
    });
    var zeigen = alle ? reihen : reihen.slice(0, TOP);
    var kopf = '<div class="rl-tabs">' + SP.map(function (s) {
      return '<button type="button" data-nach="' + s[0] + '"' + (s[0] === nach ? ' class="an"' : "") + ">" + s[1] + "</button>"; }).join("") + "</div>";
    var tab = '<table class="tour-tab rl"><thead><tr><th>#</th><th>Spieler</th>' + SP.map(function (s) {
      return '<th class="z' + (s[0] === nach ? " an" : "") + '" data-nach="' + s[0] + '">' + s[1] + "</th>"; }).join("") +
      "<th>Abzeichen</th></tr></thead><tbody>" + zeigen.map(function (r) {
        var m = r._platz <= 3 ? ' class="platz' + r._platz + '"' : "";
        return "<tr" + m + '><td class="pl">' + r._platz + '.</td><td class="sp"><a href="' + esc(r.seite) + '">' + esc(r.name) + "</a></td>" +
          SP.map(function (s) { return '<td class="z' + (s[0] === nach ? " an" : "") + '" data-l="' + KURZ[s[0]] + '">' +
            (s[0] === "km" ? r.km + " km" : r[s[0]]) + "</td>"; }).join("") +
          '<td class="st-zelle" data-l="Abzeichen">' + r.stufen + "</td></tr>";
      }).join("") + "</tbody></table>";
    var mehr = reihen.length > TOP ? '<p class="rl-mehr"><button type="button">' + (alle ? "Nur Top " + TOP : "Alle anzeigen (" + reihen.length + ")") + "</button></p>" : "";
    out.innerHTML = kopf + tab + mehr;
  }
  out.addEventListener("click", function (ev) {
    var n = ev.target.closest("[data-nach]");
    if (n) { nach = n.getAttribute("data-nach"); zeichne(); return; }
    if (ev.target.closest(".rl-mehr button")) { alle = !alle; zeichne(); }
  });
  zeichne();
})();
"""

JS_ABZEICHEN = r"""
(function () {
  var D = JSON.parse(document.getElementById("tour-daten").textContent), out = document.getElementById("abz-liste");
  if (!out) return;
  var wer = document.getElementById("abz-wer"), zeige = document.getElementById("abz-zeige"),
      sort = document.getElementById("abz-sort"), stufe = document.getElementById("abz-stufe");
  var vorgabe = new URLSearchParams(location.search).get("wer");
  if (vorgabe && D.spieler[vorgabe]) wer.value = vorgabe;
  var RANG = {legendaer: 0, gold: 1, silber: 2, bronze: 3};
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function karte(a, sp) {
    var hat = sp && sp.erreicht.indexOf(a.id) >= 0, fs = sp && sp.fortschritt[a.id];
    var klasse = "abz st-" + a.stufe + (sp ? (hat ? " erreicht" : " offen") : "");
    var namen = a.wer.slice(0, 5).join(", ") + (a.wer.length > 5 ? " + " + (a.wer.length - 5) + " weitere" : "");
    var w = a.wer.length ? a.wer.length + " von " + D.anzahl_spieler + " (" + a.anteil + " %): " + namen : "noch niemand";
    return '<div class="' + klasse + '"><h4>' + esc(a.name) + "<small>" + a.stufe_name + " · " + a.punkte + "</small></h4>" +
      "<p>" + esc(a.text) + "</p>" +
      (fs ? '<div class="balken" title="' + fs[0] + " von " + fs[1] + '"><span style="width:' + Math.round(100 * fs[0] / fs[1]) + '%"></span></div>' +
            '<p class="wer">' + fs[0] + " / " + fs[1] + "</p>" : "") +
      '<p class="wer">' + esc(w) + "</p>" +
      (a.wer.length && a.anteil <= 15 ? '<span class="selten">selten</span>' : "") + "</div>";
  }
  function zeichne() {
    var sp = D.spieler[wer.value], z = zeige.value;
    zeige.disabled = !sp; if (!sp) z = "alle";
    var liste = D.abzeichen.filter(function (a) {
      if (stufe.value && a.stufe !== stufe.value) return false;
      if (z === "erreicht") return sp.erreicht.indexOf(a.id) >= 0;
      if (z === "offen") return sp.erreicht.indexOf(a.id) < 0;
      return true;
    });
    if (!liste.length) { out.innerHTML = '<p class="tour-leer">Keine Abzeichen für diese Auswahl.</p>'; return; }
    if (sort.value === "kat") {
      var kats = [], html = "";
      liste.forEach(function (a) { if (kats.indexOf(a.kat) < 0) kats.push(a.kat); });
      kats.forEach(function (k) {
        var teil = liste.filter(function (a) { return a.kat === k; });
        var n = sp ? teil.filter(function (a) { return sp.erreicht.indexOf(a.id) >= 0; }).length : 0;
        html += '<h3 class="abz-kat">' + esc(k) + (sp ? " <small>(" + n + "/" + teil.length + ")</small>" : "") + '</h3><div class="abz-grid">' +
          teil.map(function (a) { return karte(a, sp); }).join("") + "</div>";
      });
      out.innerHTML = html;
    } else {
      liste = liste.slice().sort(sort.value === "selten"
        ? function (a, b) { return (a.wer.length ? a.anteil : 101) - (b.wer.length ? b.anteil : 101) || RANG[a.stufe] - RANG[b.stufe]; }
        : function (a, b) { return RANG[a.stufe] - RANG[b.stufe] || a.anteil - b.anteil; });
      out.innerHTML = '<div class="abz-grid">' + liste.map(function (a) { return karte(a, sp); }).join("") + "</div>";
    }
  }
  [wer, zeige, sort, stufe].forEach(function (e) { e.addEventListener("change", zeichne); });
  zeichne();
})();
"""

JS_ANTRAG = r"""
(function () {
  var f = document.getElementById("tour-form"); if (!f) return;
  if (location.hash === "#beantragen") document.getElementById("beantragen").open = true;
  f.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var knopf = f.querySelector("button"), m = f.querySelector(".meldung"), d = {typ: "turnierort"};
    ["name", "link", "turnier", "stadt", "land", "monat", "bedenkzeit", "begruendung", "website"].forEach(function (n) { d[n] = (f.elements[n].value || "").trim(); });
    d.ausnahme = f.elements.ausnahme.checked;
    if (!d.link && !(d.stadt && d.monat)) { m.className = "meldung fehler"; m.textContent = "Bitte chess-results-Link angeben oder Stadt und Monat ausfüllen."; return; }
    knopf.disabled = true; m.className = "meldung"; m.textContent = "Wird gesendet …";
    fetch(f.getAttribute("data-url"), {method: "POST", body: JSON.stringify(d)})
      .then(function (r) { return r.json(); })
      .then(function (a) {
        if (!a.ok) throw new Error(a.fehler || "Unbekannter Fehler");
        m.className = "meldung ok"; m.textContent = "Danke! Dein Turnier ist angekommen und wird geprüft.";
        var name = f.elements.name.value; f.reset(); f.elements.name.value = name;
      })
      .catch(function (e) { m.className = "meldung fehler"; m.textContent = "Das hat nicht geklappt (" + e.message + "). Bitte später nochmal versuchen."; })
      .finally(function () { knopf.disabled = false; });
  });
})();
"""


def antrag_html(skript_url):
    if not skript_url:
        return ""
    return f"""
    <details class="card tour-antrag" id="beantragen">
      <summary><span><strong>Turnier einreichen</strong><br><span class="klein">Du hast ein Turnier gespielt – auch früher? Reich es ein, wir prüfen es und tragen es bei dir ein.</span></span>
        <span class="btn">Einreichen</span></summary>
      <form id="tour-form" data-url="{html.escape(skript_url)}">
        <div class="tour-reihe">
          <label>Dein Name <input name="name" required maxlength="80" autocomplete="name" placeholder="Vor- und Nachname"></label>
          <label>chess-results-Link <input name="link" type="url" maxlength="300" placeholder="https://chess-results.com/tnr…"></label>
        </div>
        <p class="klein">Mit chess-results-Link geht die Prüfung am schnellsten. Ohne Link bitte die Felder darunter ausfüllen.</p>
        <div class="tour-reihe">
          <label>Turnier <input name="turnier" maxlength="150" placeholder="z. B. Grenke Open"></label>
          <label>Stadt <input name="stadt" maxlength="80" placeholder="z. B. Karlsruhe"></label>
          <label>Land <input name="land" maxlength="60" value="Deutschland"></label>
          <label>Monat <input name="monat" type="month"></label>
          <label>Bedenkzeit <select name="bedenkzeit"><option value="klassisch">Klassisch</option><option value="schnell">Schnellschach</option><option value="blitz">Blitz</option></select></label>
        </div>
        <label class="inline"><input type="checkbox" name="ausnahme"> Besonderes Turnier (Ausnahme, z. B. Meisterschaft mit anderer Bedenkzeit)</label>
        <label>Begründung (nur bei Ausnahme) <input name="begruendung" maxlength="300"></label>
        <label class="falle" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
        <p class="klein">Es zählen klassische Einzelturniere, keine Ligaspiele. Jede Stadt zählt einmal.</p>
        <div><button class="btn" type="submit">Absenden</button></div>
        <p class="meldung" role="status"></p>
      </form>
    </details>"""


SEITE_ABZEICHEN = "turnierorte-abzeichen.html"


def spieler_seite(sid):
    """Dateiname der Spielerseite, z. B. tour-KorbinianR.html"""
    t = unicodedata.normalize("NFKD", sid).encode("ascii", "ignore").decode()
    return "tour-" + (re.sub(r"[^A-Za-z0-9_-]", "", t) or "spieler") + ".html"


def _orte_daten(orte, namen, nur=None):
    """Orte für die Karte (optional nur ein Spieler)."""
    out = []
    for o in sorted(orte.values(), key=lambda o: o["ort"]):
        bs = [b for b in o["besuche"] if b.get("spieler") in namen and (nur is None or b["spieler"] == nur)]
        if not bs:
            continue
        land = o.get("land", "")
        out.append({"ort": o["ort"], "land": land, "lat": o.get("lat"), "lon": o.get("lon"),
                    "iso": LAENDER_ISO.get(land) or ("name:" + land if land == "Kosovo" else ""),
                    "besuche": [{"id": b["spieler"], "name": namen[b["spieler"]], "monat": _monat(b.get("von", "")),
                                 "turnier": b.get("turnier", ""), "link": b.get("link", "")}
                                for b in sorted(bs, key=lambda b: b.get("von", ""), reverse=True)]})
    return out


def _abz_karte(a, fs=None):
    """Statische Abzeichen-Karte (für Vorschau und Spielerseite)."""
    balken = (f'<div class="balken"><span style="width:{round(100 * fs[0] / fs[1])}%"></span></div>'
              f'<p class="wer">{fs[0]} / {fs[1]}</p>') if fs else ""
    wer = f'{len(a["wer"])} im Verein ({a["anteil"]} %)' if a["wer"] else "noch niemand"
    selten = '<span class="selten">selten</span>' if a["wer"] and a["anteil"] <= 15 else ""
    return (f'<div class="abz st-{a["stufe"]}"><h4>{html.escape(a["name"])}<small>{a["stufe_name"]} · {a["punkte"]}</small></h4>'
            f'<p>{html.escape(a["text"])}</p>{balken}<p class="wer">{wer}</p>{selten}</div>')


def _seite(render_page, aktiv, titel, inhalt, seite, daten, js):
    if aktiv is not None:
        aktiv[seite] = "turniere.html"
    js_daten = json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")
    render_page(titel, inhalt + f'<script type="application/json" id="tour-daten">{js_daten}</script><script>{js}</script>',
                seite, extra_styles="<style>" + CSS + "</style>")


def bauen(render_page, skript_url="", aktiv=None):
    """Baut turnierorte.html, die Abzeichen-Seite und eine Seite pro Spieler.
    aktiv = ACTIVE_PARENT aus build_site.py (damit im Menü "Turniere" markiert ist)."""
    konf = einstellungen()
    spieler = spieler_laden()
    tabelle, orte, infos = auswerten(spieler, besuche_laden(), konf)
    namen = {t["id"]: t["name"] for t in tabelle}
    laender = {o["land"] for o in orte.values() if o.get("land") and any(b["spieler"] in namen for b in o["besuche"])}
    turniere = {(b.get("turnier", ""), b.get("von", "")[:7], o["ort"]) for o in orte.values() for b in o["besuche"] if b["spieler"] in namen}
    orte_mit = [o for o in orte.values() if any(b["spieler"] in namen for b in o["besuche"])]
    basis = {"farbe": konf.get("flaggenfarbe", "#c0392b"), "flagge": FLAGGE, "karte": KARTE_FARBEN, "grenzen": GRENZEN_URL}
    abz_daten = [dict(a, wer=[namen.get(w, w) for w in a["wer"]]) for a in infos]
    auswahl = "".join(f'<option value="{html.escape(t["id"])}">{html.escape(t["name"])}</option>' for t in tabelle)
    zurueck = '<a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>'

    # ---------- Hauptseite ----------
    zahlen = _zahlen([(len(orte_mit), "Orte"), (len(laender), "Länder"), (len(turniere), "Turniere"), (len(tabelle), "Spieler auf Tour")])
    if tabelle:
        rangliste = '<div id="rangliste"></div>'
        selten = sorted((a for a in abz_daten if a["wer"]), key=lambda a: (a["anteil"], -a["punkte"]))[:4]
        vorschau = (f'<h2 style="margin-top:2rem;">Abzeichen</h2><p class="tour-hinweis">Die seltensten Abzeichen, die schon jemand geholt hat:</p>'
                    f'<div class="abz-grid">{"".join(_abz_karte(a) for a in selten)}</div>'
                    f'<p class="tour-weiter"><a href="{SEITE_ABZEICHEN}">Alle {len(infos)} Abzeichen ansehen →</a></p>')
    else:
        rangliste = '<p class="tour-leer">Noch niemand auf Tour. Sei der Erste und reich unten dein erstes Turnier ein!</p>'
        vorschau = f'<p class="tour-weiter"><a href="{SEITE_ABZEICHEN}">Alle {len(infos)} Abzeichen ansehen →</a></p>'
    daten = dict(basis, orte=_orte_daten(orte, namen),
                 rangliste=[{"id": t["id"], "name": t["name"], "seite": spieler_seite(t["id"]), "orte": t["werte"]["orte"],
                             "laender": t["werte"]["laender"], "turniere": t["werte"]["turniere"], "km": t["werte"]["weiteste"],
                             "punkte": t["punkte"], "stufen": _stufen_html(t, infos) or "–"} for t in tabelle])
    inhalt = f"""
    {zurueck}
    <h1 style="margin-top:1rem;">{TITEL}</h1>
    <p>Wo hat die SG AFK schon überall Turniere gespielt? Jede Stadt zählt pro Spieler einmal – egal wie oft man dort war.
      Gezählt werden klassische Einzelturniere.</p>
    {zahlen}
    <div class="tour-kartenkopf"><h2>Wo SG AFK schon war</h2>
      <label>Zeige <select id="tour-wer"><option value="">alle Spieler</option>{auswahl}</select></label></div>
    <div id="tour-karte" role="img" aria-label="Karte der Turnierorte"></div>
    <h2 style="margin-top:2rem;">Rangliste</h2>
    {rangliste}
    {vorschau}
    {antrag_html(skript_url)}
    {LIBS}"""
    _seite(render_page, aktiv, TITEL, inhalt, SEITE, daten, JS_KARTE + JS_RANGLISTE + JS_ANTRAG)

    # ---------- Abzeichen-Seite ----------
    daten = dict(basis, abzeichen=abz_daten, anzahl_spieler=len(tabelle),
                 spieler={t["id"]: {"name": t["name"], "erreicht": t["erreicht"], "fortschritt": t["fortschritt"]} for t in tabelle})
    inhalt = f"""
    <a href="{SEITE}" style="text-decoration:none;">← Zurück zu {TITEL}</a>
    <h1 style="margin-top:1rem;">Abzeichen</h1>
    <p class="tour-hinweis">{len(infos)} Abzeichen in vier Stufen:
      <span class="tour-abz st-bronze">Bronze 10</span> <span class="tour-abz st-silber">Silber 25</span>
      <span class="tour-abz st-gold">Gold 50</span> <span class="tour-abz st-legendaer">Legendär 100</span> Punkte.
      Wähle einen Spieler, um seine erreichten und offenen Abzeichen zu sehen.</p>
    <div class="abz-kopf">
      <label>Spieler <select id="abz-wer"><option value="">alle</option>{auswahl}</select></label>
      <label>Zeige <select id="abz-zeige"><option value="alle">alle Abzeichen</option><option value="erreicht">nur erreichte</option>
        <option value="offen">nur offene</option></select></label>
      <label>Sortierung <select id="abz-sort"><option value="kat">nach Kategorie</option><option value="selten">seltenste zuerst</option>
        <option value="stufe">nach Stufe</option></select></label>
      <label>Stufe <select id="abz-stufe"><option value="">alle</option><option value="bronze">Bronze</option><option value="silber">Silber</option>
        <option value="gold">Gold</option><option value="legendaer">Legendär</option></select></label>
    </div>
    <div id="abz-liste"></div>"""
    _seite(render_page, aktiv, "Abzeichen – " + TITEL, inhalt, SEITE_ABZEICHEN, daten, JS_ABZEICHEN)

    # ---------- Spielerseiten ----------
    for platz, t in enumerate(tabelle, 1):
        erreicht = sorted((a for a in abz_daten if a["id"] in t["erreicht"]), key=lambda a: (a["anteil"], -a["punkte"]))
        naechste = sorted(((a, t["fortschritt"][a["id"]]) for a in abz_daten if a["id"] in t["fortschritt"]),
                          key=lambda x: (-x[1][0] / x[1][1], x[0]["punkte"]))[:4]
        zahlen = _zahlen([(t["werte"]["orte"], "Orte"), (t["werte"]["laender"], "Länder"), (t["werte"]["turniere"], "Turniere"),
                          (f'{t["werte"]["weiteste"]} km', "weiteste Reise"), (t["punkte"], "Punkte")])
        inhalt = f"""
    <a href="{SEITE}" style="text-decoration:none;">← Zurück zu {TITEL}</a>
    <h1 style="margin-top:1rem;">{html.escape(t["name"])}</h1>
    <p class="tour-hinweis">Platz {platz} von {len(tabelle)} nach Orten · {_anz(len(t["erreicht"]), "Abzeichen", "Abzeichen")} {_stufen_html(t, infos)}</p>
    {zahlen}
    <div id="tour-karte" role="img" aria-label="Karte der Turnierorte von {html.escape(t["name"])}"></div>
    <h2 style="margin-top:2rem;">Abzeichen</h2>
    <div class="tour-chips">{"".join(f'<span class="tour-abz st-{a["stufe"]}" title="{html.escape(a["text"])} – {a["anteil"]} % im Verein">{html.escape(a["name"])}</span>' for a in erreicht) or '<span class="tour-hinweis">noch keine</span>'}</div>
    {('<h3 style="margin-top:1.4rem;">Als Nächstes erreichbar</h3><div class="abz-grid">' + "".join(_abz_karte(a, fs) for a, fs in naechste) + '</div>') if naechste else ''}
    <p class="tour-weiter"><a href="{SEITE_ABZEICHEN}?wer={html.escape(t["id"])}">Alle Abzeichen von {html.escape(t["name"])} →</a></p>
    <h2 style="margin-top:2rem;">Turniere</h2>
    <ul class="tour-liste">{_profil_orte(t["liste"])}</ul>
    {LIBS}"""
        daten = dict(basis, orte=_orte_daten(orte, namen, nur=t["id"]), fest=t["id"])
        _seite(render_page, aktiv, f'{t["name"]} – {TITEL}', inhalt, spieler_seite(t["id"]), daten, JS_KARTE)
    return SEITE


def _zahlen(paare):
    return '<div class="tour-zahlen">' + "".join(f'<div class="tour-zahl"><strong>{w}</strong><span>{t}</span></div>' for w, t in paare) + "</div>"


def _anz(n, eins, mehr):
    return f"{n} {eins if n == 1 else mehr}"


def _profil_orte(liste):
    """Ein Listenpunkt pro Ort (neuester Besuch zuerst), darunter die einzelnen Turniere."""
    orte = {}
    for b in liste:                       # liste ist schon nach Datum absteigend sortiert
        orte.setdefault(b["ort"], []).append(b)
    zeilen = []
    for ort, bs in orte.items():
        teile = []
        for b in bs:
            t = html.escape(b.get("turnier") or "Turnier")
            if b.get("link"):
                t = f'<a href="{html.escape(b["link"])}" target="_blank" rel="noopener">{t}</a>'
            extra = f' (Ausnahme: {html.escape(b["ausnahme"])})' if b.get("ausnahme") and b["ausnahme"] != "ja" else (" (Ausnahme)" if b.get("ausnahme") else "")
            teile.append(f'{t} <small>{_monat(b.get("von", ""))}{extra}</small>')
        land = bs[0].get("land", "")
        mal = f" <small>{len(bs)}×</small>" if len(bs) > 1 else ""
        zeilen.append(f'<li><b>{html.escape(ort)}</b>{" <small>(" + html.escape(land) + ")</small>" if land and land != "Deutschland" else ""}{mal}'
                      f'<br>{"; ".join(teile)}</li>')
    return "".join(zeilen)
