"""
Mannschaften-Seite und Ergebnis-Ticker aus mannschaften/*.json.

Die JSON-Dateien schreibt der Tabellenrechner (py main.py website). Darin steht SEINE
Wertung nach TO §15 – nicht die Tabelle vom Schachbezirk.
build_site.py ruft lade_teams(), mannschaften_seite() und ticker_html() auf.
"""

import glob
import html
import json
import os
from datetime import datetime

# ==========================================
# EINSTELLUNGEN
# ==========================================
DATEN_ORDNER = "mannschaften"

# Zusätzliche Karten ohne Liga-Daten (erscheinen in der Übersicht)
EXTRA_KARTEN = [
    {"name": "Jugendmannschaften", "kurz": "Jugend", "klasse": "Jugendrunden",
     "text": "Liga wird nachgetragen.", "url": None},
]

# Eigener (langer) Vereinsname in Tabellen -> kürzer, z. B. "SG AFK 2"; None = unverändert
EIGENER_NAME = "SG {kurz}"

TICKER_TITEL = "Letzte Ergebnisse"
ZEIGE_SPIELER = True          # Spielerstatistik auf der Seite anzeigen
ZEIGE_RECHNER = True          # Was-wäre-wenn-Rechner anzeigen

ERGEBNIS_TEXT = {"s": "Sieg", "u": "Unentschieden", "n": "Niederlage"}


def esc(x):
    return html.escape(str(x if x is not None else ""))


def zahl(x):
    """3.0 -> '3', 3.5 -> '3½'"""
    if x is None:
        return ""
    ganz = int(x)
    return f"{ganz}½" if x - ganz else str(ganz)


def stand_text(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y, %H:%M Uhr")
    except (TypeError, ValueError):
        return ""


# ==========================================
# DATEN
# ==========================================
def lade_teams(ordner=DATEN_ORDNER):
    teams = []
    for pfad in sorted(glob.glob(os.path.join(ordner, "*.json"))):
        try:
            with open(pfad, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            print(f"Hinweis: {pfad} nicht lesbar ({e})")
            continue
        if d.get("version") == 1 and d.get("tabelle") is not None:
            if EIGENER_NAME and d.get("eigen") is not None:
                d["teams"][str(d["eigen"])] = EIGENER_NAME.format(kurz=d["kurz"])
            teams.append(d)
    teams.sort(key=lambda d: (len(d["key"]), d["key"]))
    return teams


def name_von(d, tlnr):
    return d["teams"].get(str(tlnr), "spielfrei") if tlnr is not None else "spielfrei"


def sicht(d, m):
    """Ergebnis aus Sicht der eigenen Mannschaft:
    (heim?, gegner, eigene BP, gegner BP, 's'/'u'/'n' oder None)"""
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
    gespielt = [m for m in eigene_spiele(d) if m["gesp"]]
    return gespielt[-1] if gespielt else None


def naechstes_spiel(d):
    return next((m for m in eigene_spiele(d) if not m["gesp"]), None)


def eigene_zeile(d):
    return next((r for r in d["tabelle"] if r["tlnr"] == d["eigen"]), None)


# ==========================================
# HTML-BAUSTEINE
# ==========================================
def ergebnis_badge(art, mein, sein):
    if art is None:
        return '<span class="erg erg-offen">offen</span>'
    return (f'<span class="erg erg-{art}" title="{ERGEBNIS_TEXT[art]}">'
            f'{zahl(mein)} : {zahl(sein)}</span>')


def spiel_text(d, m):
    if m.get("sf"):
        return "spielfrei"
    heim, gegner, *_ = sicht(d, m)
    return f'{"vs." if heim else "bei"} {esc(gegner)}'


def tabelle_html(d):
    n = len(d["tabelle"])
    zeilen = []
    for i, r in enumerate(d["tabelle"]):
        klassen = []
        if r["tlnr"] == d["eigen"]:
            klassen.append("eigen")
        if d.get("auf") and i < d["auf"]:
            klassen.append("auf")
        if d.get("ab") and i >= n - d["ab"]:
            klassen.append("ab")
        if d.get("auf") and i == d["auf"] or d.get("ab") and i == n - d["ab"]:
            klassen.append("trenn")
        cls = f' class="{" ".join(klassen)}"' if klassen else ""
        zeilen.append(
            f'<tr{cls}><td>{r["platz"]}</td><td class="name">{esc(name_von(d, r["tlnr"]))}</td>'
            f'<td>{r["sp"]}</td><td><strong>{r["mp"]}</strong></td><td>{zahl(r["bp"])}</td>'
            f'<td class="neben">{r["siege"]}</td><td class="neben">{r["gp"]}</td></tr>')
    return f"""
      <div class="tab-wrap"><table class="liga-tab">
        <thead><tr><th>Rg</th><th class="name">Mannschaft</th><th title="Spiele">Sp</th>
          <th title="Mannschaftspunkte">MP</th><th title="Brettpunkte">BP</th>
          <th class="neben" title="Mannschaftssiege">Siege</th><th class="neben" title="Gewinnpartien">GewP</th></tr></thead>
        <tbody>{"".join(zeilen)}</tbody>
      </table></div>"""


def bretter_html(d, m):
    if not m.get("bretter"):
        return ""
    heim = m["h"] == d["eigen"]
    zeilen = []
    for brett, sp_h, sp_g, art, h, g in m["bretter"]:
        if art == "score":
            erg = f"{zahl(h)} – {zahl(g)}"
        else:
            erg = {"forfeit_heim": "+ / –", "forfeit_gast": "– / +", "annulliert": "– / –"}.get(art, "")
        eigen, gegner = (sp_h, sp_g) if heim else (sp_g, sp_h)
        if art == "score":
            mein = h if heim else g
            cls = "s" if mein == 1 else "n" if mein == 0 else "u"
        else:
            cls = "s" if (art == "forfeit_heim") == heim and art != "annulliert" else "n"
        zeilen.append(f'<tr><td>{brett}</td><td class="name">{esc(eigen)}</td>'
                      f'<td><span class="erg erg-{cls} klein">{erg if heim else " ".join(reversed(erg.split(" ")))}</span></td>'
                      f'<td class="name">{esc(gegner)}</td></tr>')
    return f'<table class="bretter"><tbody>{"".join(zeilen)}</tbody></table>'


def spiele_html(d):
    teile = []
    for m in eigene_spiele(d):
        heim, gegner, mein, sein, art = sicht(d, m)
        if m.get("sf"):
            kopf = f'<span class="rd">R{m["r"]}</span><span class="geg">spielfrei</span>'
            teile.append(f'<div class="spiel">{kopf}</div>')
            continue
        dwz = m.get("dg" if heim else "dh")
        info = f'<span class="dwz">Ø {dwz}</span>' if dwz else ""
        kopf = (f'<span class="rd">R{m["r"]}</span><span class="ha">{"H" if heim else "A"}</span>'
                f'<span class="geg">{esc(gegner)}{info}</span>{ergebnis_badge(art, mein, sein)}')
        details = bretter_html(d, m)
        if details:
            teile.append(f'<details class="spiel"><summary>{kopf}</summary>{details}</details>')
        else:
            teile.append(f'<div class="spiel">{kopf}</div>')
    return "".join(teile)


def spieler_html(d):
    if not d.get("spieler"):
        return ""
    zeilen = []
    for s in d["spieler"]:
        proz = f'{round(100 * s["pkt"] / s["sp"])} %' if s["sp"] else "–"
        kl = " ".join(f'{n}× kampfl. {z}' for n, z in ((s["kl_plus"], "+"), (s["kl_minus"], "–")) if n)
        bretter = ", ".join(map(str, s["bretter"])) or "–"
        zeilen.append(f'<tr><td class="name">{esc(s["name"])}</td><td>{s["sp"]}</td>'
                      f'<td>{zahl(s["pkt"])}</td><td>{proz}</td><td class="neben">{bretter}</td>'
                      f'<td class="neben klein">{kl}</td></tr>')
    return f"""
      <details class="block"><summary>Spielerstatistik</summary>
        <div class="tab-wrap"><table class="liga-tab spieler">
          <thead><tr><th class="name">Spieler</th><th title="gespielte Partien">Sp</th><th>Pkt</th><th>%</th>
            <th class="neben">Brett</th><th class="neben"></th></tr></thead>
          <tbody>{"".join(zeilen)}</tbody>
        </table></div>
        <p class="klein">Nur gespielte Partien; kampflose Bretter stehen extra.</p>
      </details>"""


def json_fuer_script(d):
    daten = {k: d[k] for k in ("key", "kurz", "bretter", "eigen", "teams", "tabelle", "auf", "ab")}
    daten["matches"] = [{k: v for k, v in m.items() if k != "bretter"} for m in d["matches"]]
    return json.dumps(daten, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def team_section(d):
    zeile = eigene_zeile(d)
    platz = f'Platz {zeile["platz"]} von {len(d["tabelle"])}' if zeile else ""
    runde = d.get("aktuelle_runde") or 0
    nach = f"nach Runde {runde} von {d['runden']}" if runde else "noch kein Spieltag gespielt"
    links = [f'<a href="{esc(d["url_liga"])}" target="_blank" rel="noopener">Liga beim Schachbezirk ↗</a>']
    rechner = ""
    offen = sum(1 for m in d["matches"] if not m["gesp"] and not m.get("sf"))
    if ZEIGE_RECHNER and offen:
        rechner = f"""
      <details class="block rechner-block"><summary>Tabellenrechner: Was wäre, wenn …?</summary>
        <div class="rechner" data-key="{esc(d["key"])}"><noscript>Der Rechner braucht JavaScript.</noscript></div>
        <script type="application/json" id="liga-{esc(d["key"])}">{json_fuer_script(d)}</script>
      </details>"""
    return f"""
    <section class="team" id="{esc(d["key"])}">
      <div class="team-kopf">
        <h2>{esc(d["kurz"])} <span class="team-klasse">{esc(d.get("klasse", ""))}</span></h2>
        <span class="team-platz">{platz}</span>
      </div>
      <p class="klein">Tabelle {nach}</p>
      {tabelle_html(d)}
      <details class="block" open><summary>Unsere Spiele</summary>{spiele_html(d)}</details>
      {spieler_html(d) if ZEIGE_SPIELER else ""}
      {rechner}
      <p class="klein quelle">{" · ".join(links)}</p>
    </section>"""


def karte_html(d):
    zeile = eigene_zeile(d)
    letztes, naechstes = letztes_spiel(d), naechstes_spiel(d)
    zeilen = []
    if zeile and d.get("aktuelle_runde"):
        zeilen.append(f'<p class="k-platz"><strong>Platz {zeile["platz"]}</strong> von {len(d["tabelle"])}'
                      f' · {zeile["mp"]} MP · {zahl(zeile["bp"])} BP</p>')
    if letztes:
        _, _, mein, sein, art = sicht(d, letztes)
        zeilen.append(f'<p>Zuletzt: {spiel_text(d, letztes)} {ergebnis_badge(art, mein, sein) if not letztes.get("sf") else ""}</p>')
    if naechstes:
        zeilen.append(f'<p>Nächstes Spiel (R{naechstes["r"]}): {spiel_text(d, naechstes)}</p>')
    return f"""
      <a class="card team-karte" href="#{esc(d["key"])}">
        <h3>{esc(d["kurz"])} <span class="team-klasse">{esc(d.get("klasse", ""))}</span></h3>
        {"".join(zeilen)}
      </a>"""


def extra_karte_html(k):
    inhalt = f'<p>{esc(k["text"])}</p>'
    if k.get("url"):
        inhalt += f'<a class="btn" href="{esc(k["url"])}" target="_blank" rel="noopener">Ergebnisse öffnen</a>'
    return f"""
      <div class="card team-karte">
        <h3>{esc(k["name"])} <span class="team-klasse">{esc(k.get("klasse", ""))}</span></h3>
        {inhalt}
      </div>"""


# ==========================================
# SEITEN
# ==========================================
def mannschaften_seite(teams):
    """Rückgabe: (content, styles) für render_page."""
    saison = teams[0].get("saison") if teams else ""
    stand = max((d.get("stand", "") for d in teams), default="")
    karten = "".join(karte_html(d) for d in teams) + "".join(extra_karte_html(k) for k in EXTRA_KARTEN)
    content = f"""
    <h1>Unsere Mannschaften</h1>
    <p>Aktuelle Tabellen, Ergebnisse und Statistiken unserer Teams. Wann wir spielen, steht im
      <a href="termine.html">Spielplan</a>.</p>
    <div class="grid-3 team-grid">{karten}</div>
    {"".join(team_section(d) for d in teams)}
    <p class="klein quelle">Wertung nach Turnierordnung §15 selbst berechnet (MP, BP, Mannschaftssiege,
      Gewinnpartien; Gleichstand = geteilter Platz). Daten: Schachbezirk München, Saison-ID {esc(saison)}.
      {f"Letzte Änderung: {stand_text(stand)}." if stand else ""}</p>
    {RECHNER_JS if ZEIGE_RECHNER else ""}
    """
    return content, STYLES


def ticker_html(teams):
    """Startseite: letztes Ergebnis je Mannschaft (leer, wenn noch nichts gespielt)."""
    karten = []
    for d in teams:
        m = letztes_spiel(d)
        if not m or m.get("sf"):
            continue
        heim, gegner, mein, sein, art = sicht(d, m)
        zeile = eigene_zeile(d)
        platz = f' · Platz {zeile["platz"]}' if zeile else ""
        karten.append(f"""
        <a class="tick tick-{art}" href="mannschaften.html#{esc(d["key"])}">
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
        <a href="mannschaften.html">Alle Tabellen →</a>
      </div>
      <div class="ticker">{"".join(karten)}</div>
    </section>"""


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
      .team-grid .team-karte { display: block; color: inherit; text-decoration: none; }
      a.team-karte:hover { border-color: var(--link); }
      .team-karte h3 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 0.6rem; margin-bottom: 0.4rem; }
      .team-karte p { margin: 0.3rem 0; }
      .team-klasse { font-size: 0.8rem; font-weight: bold; background: #dcebf7; color: #1b4f7a; border-radius: 999px; padding: 0.05rem 0.65rem; }

      .team { margin-top: 2.5rem; scroll-margin-top: 5rem; }
      .team-kopf { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 0.5rem 1rem; border-bottom: 3px solid var(--navy); }
      .team-kopf h2 { margin: 0; color: var(--navy); display: flex; align-items: baseline; gap: 0.6rem; }
      .team-platz { font-weight: bold; color: var(--navy); }

      .tab-wrap { overflow-x: auto; }
      .liga-tab { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
      .liga-tab th, .liga-tab td { padding: 0.4rem 0.5rem; text-align: center; border-bottom: 1px solid var(--border); }
      .liga-tab th { background: var(--navy); color: #fff; }
      .liga-tab .name { text-align: left; }
      .liga-tab tr.eigen td { background: #dcebf7; font-weight: bold; }
      .liga-tab tr.auf td:first-child { box-shadow: inset 4px 0 #1e8449; }
      .liga-tab tr.ab td:first-child { box-shadow: inset 4px 0 #c0392b; }
      .liga-tab tr.trenn td { border-top: 2px dashed #888; }
      .liga-tab .delta { font-size: 0.8rem; font-weight: bold; }
      .delta.hoch { color: #1e8449; } .delta.runter { color: #c0392b; }
      @media (max-width: 600px) {
        .neben { display: none; }
        .liga-tab { font-size: 0.85rem; }
        .liga-tab th, .liga-tab td { padding: 0.35rem 0.3rem; }
      }

      details.block { margin-top: 1rem; border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 1rem; background: #fff; }
      details.block > summary { cursor: pointer; font-weight: bold; color: var(--navy); }
      details.block[open] > summary { margin-bottom: 0.6rem; }

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

      .erg { display: inline-block; min-width: 3.6rem; text-align: center; border-radius: 999px; padding: 0.05rem 0.6rem; font-weight: bold; font-size: 0.9rem; background: #e3e6ea; color: #333; }
      .erg.klein { min-width: 3rem; font-size: 0.8rem; }
      .erg-s { background: #d4efdf; color: #145a32; }
      .erg-u { background: #fdebd0; color: #7e5109; }
      .erg-n { background: #fadbd8; color: #922b21; }
      .erg-offen { background: transparent; color: #888; font-weight: normal; }

      .bretter { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 0.4rem 0 0.6rem; }
      .bretter td { padding: 0.2rem 0.4rem; text-align: center; }
      .bretter td.name { text-align: left; }
      .bretter td:first-child { width: 2rem; color: #777; }

      .quelle { margin-top: 0.8rem; }

      .rechner p { margin: 0.4rem 0; }
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


# Gleiche Rechnung wie chess_league.py (_tabellen_zeilen / _plaetze), nur im Browser.
RECHNER_JS = r"""<script>
(function () {
  function zahl(x) { var g = Math.floor(x); return (x - g) ? (g ? g + "½" : "½") : String(g); }
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
    ["Rg", "", "Mannschaft", "Sp", "MP", "BP"].forEach(function (h, i) {
      var th = el("th", i === 2 ? "name" : "", h); kopf.appendChild(th);
    });
    var thead = el("thead"); thead.appendChild(kopf); t.appendChild(thead);
    var tb = el("tbody"), n = rows.length;
    rows.forEach(function (r, i) {
      var tr = el("tr");
      if (r.tlnr === d.eigen) tr.className = "eigen";
      if (d.auf && i < d.auf) tr.classList.add("auf");
      if (d.ab && i >= n - d.ab) tr.classList.add("ab");
      var diff = (alt[r.tlnr] || r.platz) - r.platz;
      var dz = el("span", "delta " + (diff > 0 ? "hoch" : diff < 0 ? "runter" : ""), diff > 0 ? "▲" + diff : diff < 0 ? "▼" + (-diff) : "");
      var cells = [String(r.platz), dz, d.teams[r.tlnr] || ("Team " + r.tlnr), r.sp, r.mp, zahl(r.bp)];
      cells.forEach(function (c, j) {
        var td = el("td", j === 2 ? "name" : "");
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
    var B = d.bretter || 8, hoch = Math.floor(B / 2) + 1;
    box.textContent = "";
    box.appendChild(el("p", "klein", "Trag Ergebnisse für offene Spiele ein – die Tabelle unten rechnet sofort neu (▲▼ = Veränderung zum echten Stand). Nichts wird gespeichert."));

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
