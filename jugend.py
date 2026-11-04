"""
Jugend-Seite (jugend.html) und die Jugend-Karte auf der Mannschaften-Übersicht.

Alles, was sich pro Saison ändert, steht oben unter EINSTELLUNGEN.
Die Termine kommen automatisch aus der Spalte "Jugend" in termine/termine.typ,
Jugendberichte aus allen Berichten mit der Zeile  #kategorie[Jugend].
build_site.py ruft seite() und mannschaften_karte() auf.
"""

import html
import re

# ==========================================
# EINSTELLUNGEN
# ==========================================
SAISON = "2026/27"

TRAINING = {
    "tag": "Jeden Freitag",
    "zeit": "18:00 – 19:30 Uhr",
    "ort": "Gymnasium Kirchheim, Heimstettner Str. 20, 85551 Kirchheim",
}

ANSPRECHPARTNER = {
    "name": "Anton Mai",
    "rolle": "Ansprechpartner Jugend",
    "mail": "",                 # leer = Kontakt über das Kontaktformular
}

# Spalte in termine/termine.typ, aus der die Jugendtermine kommen
TERMINE_SPALTE = "Jugend"
TERMINE_ANZAHL = 8             # wie viele kommende Termine angezeigt werden

# Jugendmannschaften der Saison (Reihenfolge = Anzeige)
#   name:   Anzeigename auf der Karte
#   liga:   Wettbewerb / Spielklasse
#   ebene:  Kurzinfo darunter (z. B. Veranstalter)
#   termin: Regex auf den Text in der Jugend-Spalte -> "Nächster Termin" auf der Karte
#   url:    Tabelle/Ergebnisse (öffnet in neuem Tab); "" = ohne Link
#   aktiv:  False = Karte ausblenden (z. B. Team noch nicht gemeldet)
TEAMS = [
    {
        "name": "U20 I",
        "liga": "U20 Landesliga Süd",
        "ebene": "Bayerische Jugendligen",
        "termin": r"Landesliga Süd",
        "url": "https://ligamanager.schachbund-bayern.de/bsj/2026-2027/u20-landesliga-sued-2610/spielplan",
        "aktiv": True,
    },
    {
        "name": "U20 II",
        "liga": "1. Jugend-Bezirksliga",
        "ebene": "Münchner U20-Mannschaftsmeisterschaft",
        "termin": r"U20 MMM,\s*1\.\s*Liga",
        "url": "https://www.schachbezirk-muenchen.de/mm-u20.html",
        "aktiv": True,
    },
    {
        "name": "U20 III",
        "liga": "Jugend-Bezirksliga (ab 2. Liga)",
        "ebene": "Münchner U20-Mannschaftsmeisterschaft",
        "termin": r"U20 MMM,\s*Ab 2\.\s*Liga",
        "url": "https://www.schachbezirk-muenchen.de/mm-u20.html",
        "aktiv": False,        # auf True setzen, sobald gemeldet
    },
    {
        "name": "U16",
        "liga": "Münchner U16-Meisterschaft",
        "ebene": "Schachbezirk München",
        "termin": r"U16",
        "url": "https://www.schachbezirk-muenchen.de/mm-u16-u14.html",
        "aktiv": True,
    },
    {
        "name": "U14",
        "liga": "Münchner U14-Meisterschaft",
        "ebene": "Schachbezirk München",
        "termin": r"U14",
        "url": "https://www.schachbezirk-muenchen.de/mm-u16-u14.html",
        "aktiv": True,
    },
]

# Erfolge (neueste zuerst); leere Liste = Abschnitt ausblenden
ERFOLGE = [
    ("2024/25", "Platz 2 in der U20 Landesliga Süd"),
]

# Weiterführende Links
LINKS = [
    ("Münchner Schachjugend", "https://www.schachbezirk-muenchen.de/jugend.html"),
    ("Bayerische Schachjugend", "https://bayerische-schachjugend.de/"),
]


# ==========================================
# HILFSFUNKTIONEN
# ==========================================
def esc(x):
    return html.escape(str(x if x is not None else ""))


def plain(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def aktive_teams():
    return [t for t in TEAMS if t.get("aktiv", True)]


def naechster_termin(team, termine):
    if not team.get("termin"):
        return None
    rx = re.compile(team["termin"], re.I)
    return next((t for t in termine if rx.search(plain(t["title"]))), None)


# ==========================================
# BAUSTEINE
# ==========================================
def team_karte(t, termine):
    nt = naechster_termin(t, termine)
    nt_text = f'Nächster Termin: <strong>{nt["when"]}</strong>' if nt else "Termine folgen"
    inner = f"""
        <h3>{esc(t["name"])} <span class="team-klasse">{esc(t["liga"])}</span></h3>
        <p>{esc(t.get("ebene", ""))}</p>
        <p>{nt_text}</p>
        <p>{esc(plain(nt["title"])) if nt else ""}</p>"""
    if t.get("url"):
        return f"""
      <a class="card team-karte team-jugend" href="{esc(t["url"])}" target="_blank" rel="noopener">{inner}
        <span class="k-mehr">Ergebnisse ↗</span>
      </a>"""
    return f"""
      <div class="card team-karte team-jugend">{inner}
        <span class="k-mehr"></span>
      </div>"""


def termin_zeile(ev):
    return f"""
        <a class="event-card" href="termine.html" data-date="{ev["date"].isoformat()}">
          <div class="ev-date">{ev["when"]}</div>
          <div class="ev-title">{ev["title"]}</div>
          <div class="ev-teams"></div>
        </a>"""


def bericht_karte(r):
    return f"""
        <div class="card news-card">
          <h3>{r["title"]}</h3>
          <p class="news-meta">{r["meta"]}</p>
          <p class="news-snippet">{r["snippet"]}</p>
          <a href="berichte/{r["filename"]}">Weiterlesen →</a>
        </div>"""


def kontakt_html():
    a = ANSPRECHPARTNER
    weg = (f'<a href="mailto:{esc(a["mail"])}">{esc(a["mail"])}</a>' if a.get("mail")
           else '<a href="kontakt.html">über das Kontaktformular</a>')
    return f'<p><strong>{esc(a["name"])}</strong><br>{esc(a["rolle"])}</p><p>Erreichbar {weg}.</p>'


# ==========================================
# SEITEN
# ==========================================
def seite(termine, berichte):
    """jugend.html. termine: kommende Termine der Jugend-Spalte, berichte: Jugendberichte.
    Rückgabe (content, styles)."""
    teams = aktive_teams()
    karten = "".join(team_karte(t, termine) for t in teams)

    termine_html = (f'<div class="events-grid jugend-termine">{"".join(termin_zeile(e) for e in termine[:TERMINE_ANZAHL])}</div>'
                    '<p class="klein"><a href="termine.html">Ganzer Spielplan →</a> · '
                    '<a href="kalender/jugend.ics">Jugendtermine als Kalender abonnieren</a></p>'
                    if termine else "<p>Aktuell stehen keine Jugendtermine an.</p>")

    berichte_html = ""
    if berichte:
        berichte_html = f"""
    <section>
      <div class="section-head"><h2>Berichte aus der Jugend</h2><a href="berichte.html">Alle Berichte →</a></div>
      <div class="grid jugend-berichte">{"".join(bericht_karte(r) for r in berichte[:3])}</div>
    </section>"""

    erfolge_html = ""
    if ERFOLGE:
        zeilen = "".join(f"<li><strong>{esc(s)}:</strong> {esc(t)}</li>" for s, t in ERFOLGE)
        erfolge_html = f"""
      <div class="card jugend-box">
        <h3>Erfolge</h3>
        <ul>{zeilen}</ul>
      </div>"""

    links_html = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(n)} ↗</a></li>'
                         for n, u in LINKS)

    content = f"""
    <h1>Jugend</h1>
    <p class="jugend-intro">Schach für Kinder und Jugendliche: Bei uns lernen Einsteiger die Regeln,
      und Fortgeschrittene spielen in unseren Jugendmannschaften um Punkte.
      Schnuppern ist kostenlos, eine Anmeldung ist nicht nötig.</p>

    <div class="jugend-boxen">
      <div class="card jugend-box jugend-training">
        <h3>Jugendtraining</h3>
        <p><strong>{esc(TRAINING["tag"])}, {esc(TRAINING["zeit"])}</strong></p>
        <p>{esc(TRAINING["ort"])}</p>
        <p><a class="btn" href="neu-hier.html">Zum Schnuppern vorbeikommen →</a></p>
      </div>
      <div class="card jugend-box">
        <h3>Ansprechpartner</h3>
        {kontakt_html()}
      </div>
      {erfolge_html}
    </div>

    <section>
      <div class="section-head"><h2>Jugendmannschaften {esc(SAISON)}</h2></div>
      <div class="grid-3 team-grid">{karten}</div>
    </section>

    <section>
      <div class="section-head"><h2>Nächste Jugendtermine</h2></div>
      {termine_html}
    </section>
    {berichte_html}

    <section>
      <div class="section-head"><h2>Weitere Infos</h2></div>
      <ul class="jugend-links">{links_html}</ul>
    </section>
    """
    return content, STYLES


def mannschaften_karte(termine):
    """Karte für mannschaften.html, die auf die Jugendseite verweist (HTML-String)."""
    teams = aktive_teams()
    ligen = " · ".join(t["liga"] for t in teams[:2])
    rest = " · ".join(t["name"] for t in teams[2:])
    nt = termine[0] if termine else None
    return f"""
      <a class="card team-karte team-jugend" href="jugend.html">
        <h3>Jugend <span class="team-klasse">{len(teams)} Teams</span></h3>
        <p>{esc(ligen)}</p>
        <p>{esc(rest)}</p>
        <p>{f'Nächster Termin: {nt["when"]}' if nt else ""}</p>
        <span class="k-mehr">Zur Jugendseite →</span>
      </a>"""


STYLES = """<style>
      .klein { font-size: 0.85rem; color: var(--muted); }
      .jugend-intro { max-width: 50rem; font-size: 1.05rem; }
      .jugend-boxen { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1.5rem 0 2rem; }
      .jugend-box { padding: 1.1rem 1.3rem; border-top: 4px solid var(--jugend); }
      .jugend-box h3 { margin-top: 0; }
      .jugend-box p { margin: 0.35rem 0; }
      .jugend-box ul { padding-left: 1.2rem; margin: 0.3rem 0 0; }
      .jugend-training .btn { display: inline-block; margin-top: 0.5rem; text-decoration: none; padding: 0.5rem 1rem; }
      section { margin-top: 2rem; }
      .section-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
      .team-grid .team-karte { color: inherit; text-decoration: none; }
      .k-mehr { font-weight: bold; color: var(--link); font-size: 0.9rem; }
      .team-klasse { font-size: 0.8rem; font-weight: bold; border-radius: 999px; padding: 0.05rem 0.65rem; vertical-align: middle; }
      a.team-karte:hover { border-color: var(--link); }
      .jugend-termine > .event-card:first-child { border-top-width: 1px; border-radius: var(--radius) var(--radius) 0 0; }
      .jugend-termine > .event-card:last-child { border-radius: 0 0 var(--radius) var(--radius); }
      .jugend-termine > .event-card:only-child { border-radius: var(--radius); }
      .jugend-termine > .event-card { border-left-color: var(--jugend); color: inherit; text-decoration: none; }
      .jugend-berichte { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
      .jugend-links { padding-left: 1.2rem; }
    </style>"""
