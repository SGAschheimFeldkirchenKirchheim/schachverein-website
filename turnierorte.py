"""
"AFK on Tour" – Turnierorte sammeln (wie Stadion-Sammeln beim Fußball).

Jede Stadt zählt pro Spieler einmal, egal wie oft man dort war. Gezählt werden klassische
Einzelturniere (keine Liga); Ausnahmen (z. B. Deutsche Hochschulmeisterschaft) kann der Webmaster zulassen.

Ablauf:
  1. Mitglied füllt auf turnierorte.html "Ort beantragen" aus -> Apps Script legt
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

ORDNER = "turnierorte"
SEITE = "turnierorte.html"
TITEL = "AFK on Tour"

# Abzeichen: (Name, Beschreibung, Bedingung auf den Statistik-Werten)
ABZEICHEN = [
    ("Erste Reise", "Das erste Turnier auswärts", lambda s: s["orte"] >= 1),
    ("5 Orte", "In 5 verschiedenen Orten gespielt", lambda s: s["orte"] >= 5),
    ("10 Orte", "In 10 verschiedenen Orten gespielt", lambda s: s["orte"] >= 10),
    ("25 Orte", "In 25 verschiedenen Orten gespielt", lambda s: s["orte"] >= 25),
    ("Grenzgänger", "Turnier im Ausland gespielt", lambda s: s["ausland"] >= 1),
    ("Europäer", "In 5 Ländern gespielt", lambda s: s["laender"] >= 5),
    ("Stammgast", "3-mal oder öfter am selben Ort", lambda s: s["max_gleich"] >= 3),
    ("Weltenbummler", "Mehr als 1000 km von zu Hause", lambda s: s["weiteste"] >= 1000),
]


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
        abz = [(n, t) for n, t, bed in ABZEICHEN if bed(werte)]
        tabelle.append({"id": sid, "name": spieler[sid].get("anzeige") or anzeige_name(spieler[sid].get("name", sid)),
                        "werte": werte, "abzeichen": abz,
                        "liste": sorted(liste, key=lambda b: b.get("von", ""), reverse=True)})
    tabelle.sort(key=lambda t: (-t["werte"]["orte"], -t["werte"]["laender"], -t["werte"]["turniere"], t["name"]))
    return tabelle, orte


def _monat(datum):
    """'2017-06-12' oder '2017-06' -> 'Juni 2017'"""
    namen = ["Jan", "Feb", "März", "Apr", "Mai", "Juni", "Juli", "Aug", "Sep", "Okt", "Nov", "Dez"]
    m = re.match(r"(\d{4})-(\d{1,2})", datum or "")
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{namen[int(m.group(2)) - 1]} {m.group(1)}"
    return (datum or "")[:4]


def _abzeichen_html(liste):
    return "".join(f'<span class="tour-abz" title="{html.escape(b)}">{html.escape(n)}</span>' for n, b in liste)


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

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById("tour-daten").textContent);
  if (!window.L || !document.getElementById("tour-karte")) return;
  var karte = L.map("tour-karte", {scrollWheelZoom: false}).setView([48.2, 11.6], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(karte);
  var ebene = L.layerGroup().addTo(karte), sel = document.getElementById("tour-wer");
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function zeichne() {
    ebene.clearLayers();
    var wer = sel.value, punkte = [];
    D.orte.forEach(function (o) {
      var b = o.besuche.filter(function (x) { return !wer || x.id === wer; });
      if (!b.length || o.lat == null) return;
      var leute = {}; b.forEach(function (x) { leute[x.id] = 1; });
      var n = wer ? b.length : Object.keys(leute).length;
      var icon = L.divIcon({className: "tour-flagge", iconSize: [34, 40], iconAnchor: [3, 39], popupAnchor: [13, -36],
        html: D.flagge.replace("{farbe}", D.farbe).replace("{n}", n)});
      var html = "<h4>" + esc(o.ort) + (o.land ? " <small>(" + esc(o.land) + ")</small>" : "") + "</h4><ul>" +
        b.map(function (x) {
          var t = x.link ? '<a href="' + esc(x.link) + '" target="_blank" rel="noopener">' + esc(x.turnier || "Turnier") + "</a>" : esc(x.turnier || "");
          return "<li>" + esc(x.monat) + " · <b>" + esc(x.name) + "</b>" + (t ? " · " + t : "") + "</li>";
        }).join("") + "</ul>";
      L.marker([o.lat, o.lon], {icon: icon}).bindPopup(html).addTo(ebene);
      punkte.push([o.lat, o.lon]);
    });
    if (punkte.length > 1) karte.fitBounds(punkte, {padding: [30, 30], maxZoom: 9});
    else if (punkte.length === 1) karte.setView(punkte[0], 8);
  }
  sel.addEventListener("change", zeichne);
  zeichne();
})();
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
        m.className = "meldung ok"; m.textContent = "Danke! Dein Antrag ist angekommen und wird geprüft.";
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
      <summary><span><strong>Ort beantragen</strong><br><span class="klein">Du hast in einer neuen Stadt ein Turnier gespielt – auch früher? Trag es ein, wir prüfen und vergeben den Punkt.</span></span>
        <span class="btn">Beantragen</span></summary>
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


def bauen(render_page, skript_url=""):
    konf = einstellungen()
    spieler = spieler_laden()
    tabelle, orte = auswerten(spieler, besuche_laden(), konf)
    alle_orte = [o for o in orte.values() if any(b.get("spieler") in spieler for b in o["besuche"])]
    laender = {o["land"] for o in alle_orte if o.get("land")}
    turniere = {(b.get("turnier", ""), b.get("von", "")[:7], o["ort"]) for o in alle_orte for b in o["besuche"]}
    namen = {t["id"]: t["name"] for t in tabelle}
    daten = {
        "farbe": konf.get("flaggenfarbe", "#c0392b"), "flagge": FLAGGE,
        "orte": [{"ort": o["ort"], "land": o.get("land", ""), "lat": o.get("lat"), "lon": o.get("lon"),
                  "besuche": [{"id": b["spieler"], "name": namen.get(b["spieler"], b["spieler"]), "monat": _monat(b.get("von", "")),
                               "turnier": b.get("turnier", ""), "link": b.get("link", "")}
                              for b in sorted(o["besuche"], key=lambda b: b.get("von", ""), reverse=True)]}
                 for o in sorted(alle_orte, key=lambda o: o["ort"])],
    }
    zahlen = "".join(f'<div class="tour-zahl"><strong>{w}</strong><span>{t}</span></div>' for w, t in (
        (len(alle_orte), "Orte"), (len(laender), "Länder"), (len(turniere), "Turniere"), (len(tabelle), "Spieler auf Tour")))
    if tabelle:
        zeilen = "".join(
            f'<tr><td>{i}.</td><td><a href="#p-{html.escape(t["id"])}">{html.escape(t["name"])}</a></td>'
            f'<td class="z">{t["werte"]["orte"]}</td><td class="z">{t["werte"]["laender"]}</td><td class="z">{t["werte"]["turniere"]}</td>'
            f'<td class="z">{t["werte"]["weiteste"]} km</td>'
            f'<td>{_abzeichen_html(t["abzeichen"])}</td></tr>'
            for i, t in enumerate(tabelle, 1))
        rangliste = (f'<div style="overflow-x:auto"><table class="tour-tab"><thead><tr><th>#</th><th>Spieler</th><th>Orte</th><th>Länder</th>'
                     f'<th>Turniere</th><th>Weiteste Reise</th><th>Abzeichen</th></tr></thead><tbody>{zeilen}</tbody></table></div>')
        profile = "".join(
            f'<article class="tour-profil" id="p-{html.escape(t["id"])}"><h3>{html.escape(t["name"])}</h3>'
            f'<p class="k">{_anz(t["werte"]["orte"], "Ort", "Orte")} · {_anz(t["werte"]["laender"], "Land", "Länder")} · '
            f'{_anz(t["werte"]["turniere"], "Turnier", "Turniere")}</p>'
            f'{_abzeichen_html(t["abzeichen"])}'
            f'<ul>{_profil_orte(t["liste"])}</ul></article>'
            for t in tabelle)
        auswahl = "".join(f'<option value="{html.escape(t["id"])}">{html.escape(t["name"])}</option>' for t in tabelle)
    else:
        rangliste = '<p class="tour-leer">Noch niemand auf Tour. Sei der Erste und beantrage unten deinen ersten Ort!</p>'
        profile, auswahl = "", ""
    js_daten = json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")
    inhalt = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">{TITEL}</h1>
    <p>Wo hat die SG AFK schon überall Turniere gespielt? Jede Stadt zählt pro Spieler einmal – egal wie oft man dort war.
      Gezählt werden klassische Einzelturniere.</p>
    <div class="tour-zahlen">{zahlen}</div>
    <div class="tour-kartenkopf"><h2>Wo SG AFK schon war</h2>
      <label>Zeige <select id="tour-wer"><option value="">alle Spieler</option>{auswahl}</select></label></div>
    <div id="tour-karte" role="img" aria-label="Karte der Turnierorte"></div>
    <h2 style="margin-top:2rem;">Rangliste</h2>
    {rangliste}
    {('<h2 style="margin-top:2rem;">Profile</h2><div class="tour-profile">' + profile + '</div>') if profile else ''}
    {antrag_html(skript_url)}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script type="application/json" id="tour-daten">{js_daten}</script>
    <script>{JS}</script>
    """
    render_page(TITEL, inhalt, SEITE, extra_styles="<style>" + CSS + "</style>")
    return SEITE


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
