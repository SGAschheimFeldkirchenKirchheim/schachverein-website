"""
Senioren-Seite (senioren.html) und die Senioren-Karte auf der Mannschaften-Übersicht.

Alles, was sich pro Saison ändert, steht oben unter EINSTELLUNGEN.
Die Termine kommen automatisch aus der Spalte "Senioren" in termine/termine.typ,
Seniorenberichte aus allen Berichten mit der Zeile  #kategorie[Senioren].
build_site.py ruft seite() und mannschaften_karte() auf.
"""

import html
import re

# ==========================================
# EINSTELLUNGEN
# ==========================================
SAISON = "2026/27"

# Wettbewerb der Seniorenmannschaft
LIGA = "Münchner Senioren-Mannschaftsmeisterschaft (MSMM)"
LIGA_KURZ = "MSMM"
LIGA_URL = ""                  # Link zu Tabelle/Ergebnissen; "" = ohne Link

# Kurzer Text oben auf der Seite (HTML erlaubt). "" = Standardtext
INTRO = ""

# Wer darf mitspielen? z. B. "Spieler ab 50 Jahren"; "" = Zeile ausblenden
ALTERSGRENZE = ""

ANSPRECHPARTNER = {
    "name": "",                 # leer = Box zeigt nur das Kontaktformular
    "rolle": "Mannschaftsführer Senioren",
    "mail": "",                 # leer = Kontakt über das Kontaktformular
}

# Spalte in termine/termine.typ, aus der die Seniorentermine kommen
TERMINE_SPALTE = "Senioren"
TERMINE_ANZAHL = 8

# Erfolge (neueste zuerst); leere Liste = Abschnitt ausblenden
ERFOLGE = [
    # ("2025/26", "Platz 2 in der MSMM"),
]


# ==========================================
# HILFSFUNKTIONEN
# ==========================================
def esc(x):
    return html.escape(str(x if x is not None else ""))


def plain(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


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
    wer = f'<p><strong>{esc(a["name"])}</strong><br>{esc(a["rolle"])}</p>' if a.get("name") else ""
    return f'{wer}<p>Erreichbar {weg}.</p>'


# ==========================================
# SEITE
# ==========================================
def seite(termine, berichte, spielort=""):
    """senioren.html. termine: kommende Termine der Senioren-Spalte. Rückgabe (content, styles)."""
    intro = INTRO or ("Unsere Seniorenmannschaft spielt in der " + esc(LIGA) + ". "
                      "Die Spieltermine stehen unten und im Spielplan.")

    liga_link = (f'<p><a class="btn" href="{esc(LIGA_URL)}" target="_blank" rel="noopener">Tabelle &amp; Ergebnisse ↗</a></p>'
                 if LIGA_URL else "")
    alter = f"<p>{esc(ALTERSGRENZE)}</p>" if ALTERSGRENZE else ""

    erfolge_html = ""
    if ERFOLGE:
        zeilen = "".join(f"<li><strong>{esc(s)}:</strong> {esc(t)}</li>" for s, t in ERFOLGE)
        erfolge_html = f'<div class="card sen-box"><h3>Erfolge</h3><ul>{zeilen}</ul></div>'

    termine_html = (f'<div class="events-grid sen-termine">{"".join(termin_zeile(e) for e in termine[:TERMINE_ANZAHL])}</div>'
                    '<p class="klein"><a href="termine.html">Ganzer Spielplan →</a> · '
                    '<a href="kalender/senioren.ics">Seniorentermine als Kalender abonnieren</a></p>'
                    if termine else "<p>Aktuell stehen keine Seniorentermine an.</p>")

    berichte_html = ""
    if berichte:
        berichte_html = f"""
    <section>
      <div class="section-head"><h2>Berichte</h2><a href="berichte.html">Alle Berichte →</a></div>
      <div class="grid sen-berichte">{"".join(bericht_karte(r) for r in berichte[:3])}</div>
    </section>"""

    content = f"""
    <a href="mannschaften.html" style="text-decoration:none;">← Alle Mannschaften</a>
    <h1>Senioren</h1>
    <p class="sen-intro">{intro}</p>

    <div class="sen-boxen">
      <div class="card sen-box">
        <h3>Mannschaft {esc(SAISON)}</h3>
        <p><strong>{esc(LIGA)}</strong></p>
        {alter}
        {f"<p>Heimspiele: {esc(spielort)}</p>" if spielort else ""}
        {liga_link}
      </div>
      <div class="card sen-box">
        <h3>Mitspielen?</h3>
        {kontakt_html()}
      </div>
      {erfolge_html}
    </div>

    <section>
      <div class="section-head"><h2>Nächste Termine</h2></div>
      {termine_html}
    </section>
    {berichte_html}
    """
    return content, STYLES


def mannschaften_karte(termine):
    """Karte für mannschaften.html, die auf die Seniorenseite verweist (HTML-String)."""
    nt = termine[0] if termine else None
    return f"""
      <a class="card team-karte team-senioren" href="senioren.html">
        <h3>Senioren <span class="team-klasse">{esc(LIGA_KURZ)}</span></h3>
        <p>{esc(LIGA)}</p>
        <p>{f'Nächster Termin: <strong>{nt["when"]}</strong>' if nt else "Termine folgen"}</p>
        <p>{esc(plain(nt["title"])) if nt else ""}</p>
        <span class="k-mehr">Zur Seniorenseite →</span>
      </a>"""


STYLES = """<style>
      .klein { font-size: 0.85rem; color: var(--muted); }
      .sen-intro { max-width: 50rem; font-size: 1.05rem; }
      .sen-boxen { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1.5rem 0 2rem; }
      .sen-box { padding: 1.1rem 1.3rem; border-top: 4px solid var(--senioren); }
      .sen-box h3 { margin-top: 0; }
      .sen-box p { margin: 0.35rem 0; }
      .sen-box ul { padding-left: 1.2rem; margin: 0.3rem 0 0; }
      .sen-box .btn { display: inline-block; margin-top: 0.5rem; text-decoration: none; padding: 0.5rem 1rem; }
      section { margin-top: 2rem; }
      .section-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
      .sen-termine > .event-card:first-child { border-top-width: 1px; border-radius: var(--radius) var(--radius) 0 0; }
      .sen-termine > .event-card:last-child { border-radius: 0 0 var(--radius) var(--radius); }
      .sen-termine > .event-card:only-child { border-radius: var(--radius); }
      .sen-termine > .event-card { border-left-color: var(--senioren); color: inherit; text-decoration: none; }
      .sen-berichte { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
    </style>"""
