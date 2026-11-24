import os
import re
import glob
import json
import datetime
import subprocess
import urllib.parse
import urllib.request
import html as htmllib
import shutil
from urllib.parse import quote
from itertools import groupby

import liga   # Mannschaften-Seite + Ergebnis-Ticker (Daten vom Tabellenrechner)
import jugend  # Jugend-Seite (Einstellungen in jugend.py)
import senioren  # Senioren-Seite (Einstellungen in senioren.py)
import faq     # FAQ-Seite (Fragen in faq.py)
import chessresults  # Vereinsturniere von chess-results.com (turniere/chessresults.json)
import turnierkalender  # externe Turniere: FIDE + chess-results (turniere/turnierkalender.json)
import turnierorte  # "AFK on Tour": Turnierorte sammeln (Daten in turnierorte/)
import konten   # Mitgliederbereich: Login, eigenes Profil, Verwaltung (Backend: Apps Script)
import bericht_extras  # Partien (PGN) und chess-results-Tabellen in Berichten
import historie  # Mannschaftshistorie (Daten: mannschaften_historie.json + Archiv)
import einreichen  # "Bericht einreichen"-Formular auf berichte.html (Einstellungen in einreichen.py)
import spieler  # Spielerseiten spieler/<name>.html (Einstellungen in spieler.py)
import startseite  # Startseite: Aufbau, Texte, Bilder-Ordner (startseite/)
import suche  # seitenweite Suche: suche.html + suche.json (Einstellungen in suche.py)
import benachrichtigung  # Mail-Benachrichtigungen: Neuigkeiten erkennen und ans Apps Script melden

try:
    from zoneinfo import ZoneInfo
except ImportError:  # sehr alte Python-Versionen
    ZoneInfo = None

# ==========================================
# KONFIGURATION
# ==========================================
# True  -> Termine-Seite zeigt die von Typst erzeugte SVG (falls vorhanden)
# False -> Termine-Seite wird immer als HTML-Tabelle gerendert
#          (Farben, klickbare Links, volle Breite, am Handy besser lesbar)
USE_SVG_FOR_TERMINE = False

# Wie viele kommende Termine beim Build in die Startseite geschrieben werden (Reserve:
# vergangene Karten blendet der Browser aus, auch wenn die Seite länger nicht neu gebaut wurde)
NEXT_EVENTS_COUNT = 12

# Wie viele Termin-Karten gleichzeitig sichtbar sind
HOME_EVENTS_VISIBLE = 8

# Öffentliche Adresse der Seite (für Kalender-Links)
SITE_URL = "https://sgaschheimfeldkirchenkirchheim.github.io/schachverein-website/"

# Kalender-Export
CAL_TZ = "Europe/Berlin"
EVENT_DURATION_HOURS = 3          # Standarddauer für Termine mit Uhrzeit
SPIELORT = "Gymnasium Kirchheim, Heimstettner Str. 20, 85551 Kirchheim"
# Satz unter dem Spielort (Startseite, "Neu hier?", Footer). "" = ausblenden
SPIELORT_HINWEIS = "Das Gymnasium Kirchheim (GyKi) ist Schachschule und unser Spielort."
SPIELORT_HINWEIS_KURZ = "Schachschule GyKi"   # kurze Fassung für die Startseiten-Box; "" = ausblenden

# VORÜBERGEHEND: alle Adressen @sg-afk.de (info@, jugend@, spielleiter@ ...) auf allen Seiten durch diese
# eine Adresse ersetzen (Text und mailto-Link). "" = normale Adressen, dann ist alles wieder wie vorher.
MAIL_UMLEITUNG = "sgafk1952@gmail.com"

# Datum in deutscher Zeit (GitHub rechnet in UTC; der nächtliche Lauf kurz nach Mitternacht soll schon den neuen Tag sehen)
def _heute_deutsch():
    try:
        return datetime.datetime.now(ZoneInfo("Europe/Berlin")).date()
    except Exception:  # Windows ohne Paket "tzdata": PC-Uhr ist dort ohnehin deutsche Zeit
        return datetime.date.today()


TODAY = _heute_deutsch()

# Kürzel -> Erklärung. Erscheint als kleine Legende unter den Termin-Karten,
# aber nur für Kürzel, die gerade wirklich angezeigt werden.
# ACHTUNG: Die Langnamen sind ein Vorschlag - bitte prüfen und anpassen!
ABBREVIATIONS = {
    "MMM": "Münchner Mannschaftsmeisterschaft",
    "MSMM": "Münchner Senioren-Mannschaftsmeisterschaft",
}

# Meta-Beschreibung (Google, WhatsApp-Vorschau). Standard für alle Seiten ohne eigenen Eintrag.
DEFAULT_DESCRIPTION = "Schachverein in Aschheim, Feldkirchen &amp; Kirchheim – Spielabend jeden Freitag."

# Eigene Beschreibung pro Seite (Schlüssel = Dateiname). Fehlt eine Seite, gilt der Standard.
PAGE_DESCRIPTIONS = {
    "termine.html": "Spielplan und Termine der SG Aschheim/Feldkirchen/Kirchheim: Mannschaftskämpfe, Turniere und Vereinsabende, mit Kalender-Abo fürs Handy.",
    "mannschaften.html": "Tabellen, Ergebnisse und Spielerstatistiken unserer Mannschaften – mit Tabellenrechner zum Ausprobieren.",
    "berichte.html": "Aktuelle Berichte und News aus dem Vereinsleben der SG AFK: Turniere, Mannschaftskämpfe und mehr.",
    "turniere.html": "Turniere der SG AFK: Oberlandquartett, Blitzjahreswertung, Hall of Fame und Ausschreibungen.",
    "senioren.html": "Seniorenmannschaft der SG AFK in der Münchner Senioren-Mannschaftsmeisterschaft: Termine, Ansprechpartner und Berichte.",
    "faq.html": "Häufige Fragen zur SG AFK: Schnuppern, Mitgliedschaft, Beiträge, Mannschaften, DWZ und Jugendtraining.",
    "jugend.html": "Schach für Kinder und Jugendliche bei der SG AFK: Jugendtraining jeden Freitag, Jugendmannschaften, Termine und Ansprechpartner.",
    "kontakt.html": "Kontakt und Anfahrt zur SG Aschheim/Feldkirchen/Kirchheim im Gymnasium Kirchheim.",
    "ausschreibungen.html": "Ausschreibungen der SG AFK als PDF und der Turnierkalender mit Opens in Bayern, Deutschland und Europa.",
    turnierorte.SEITE: "AFK on Tour: In welchen Städten und Ländern Spieler der SG AFK schon Turniere gespielt haben – mit Karte und Rangliste.",
    turnierkalender.SEITE: "Turnierkalender: Opens in Bayern, Deutschland und Europa mit Filtern nach Zeitraum, Entfernung und Bedenkzeit.",
    "oberlandquartett.html": "Ergebnisse und Pokalstand des Oberlandquartetts.",
    "blitzjahreswertung.html": "Gesamtwertung der Blitzjahreswertung der SG AFK.",
    "vereinsintern.html": "Vereinsmeister und Sieger der vereinsinternen Turniere: die Hall of Fame der SG AFK.",
    "mannschaftshistorie.html": "Welche Mannschaft der SG AFK spielte wann in welcher Klasse? Auf- und Abstiege und Meilensteine.",
    "geschichte.html": "Die Geschichte der SG Aschheim/Feldkirchen/Kirchheim von 1952 bis heute.",
}

# Favicon, solange es kein logo.png im Hauptverzeichnis gibt (Emoji als SVG)
FAVICON_EMOJI = '''<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E♟️%3C/text%3E%3C/svg%3E">'''

# Gelbes Hinweisbanner (Text kommt aus hinweis.txt)
HINWEIS_CSS = """
      .hinweis-banner { background: #fff3cd; border: 1px solid #ffe08a; color: #664d03; padding: 0.8rem 1.2rem; border-radius: 6px; margin-bottom: 1.2rem; font-weight: bold; }
"""

# Lässt einen Block die volle Fensterbreite nutzen, auch wenn der Seiten-Container schmal ist
FULL_BLEED_CSS = """
      .full-bleed { width: min(96vw, 1900px); position: relative; left: 50%; transform: translateX(-50%); }
"""

# Menü: hier einmal pflegen (Reihenfolge = Reihenfolge im Menü)
NAV = [
    ("index.html", "Start"),
    ("ueber-uns.html", "Über uns"),
    ("mannschaften.html", "Mannschaften"),
    ("jugend.html", "Jugend"),
    ("termine.html", "Termine"),
    ("berichte.html", "Berichte"),
    ("turniere.html", "Turniere"),
    ("faq.html", "FAQ"),
    ("kontakt.html", "Kontakt"),
    # ("senioren.html", "Senioren"),   # einkommentieren = eigener Reiter (sonst über Mannschaften erreichbar)
    # "Neu hier?" ist über die Startseite und den Footer erreichbar
]

# Untermenüs: klappen am PC beim Darüberfahren auf, am Handy stehen sie eingerückt unter dem Reiter.
# Reiter -> Liste (Seite, Text). Reiter ohne Eintrag haben kein Untermenü.
# "mannschaften.html" wird beim Build automatisch mit den aktuellen Teams gefüllt (siehe MAIN).
SUBNAV = {
    "berichte.html": [
        (einreichen.SEITE, "Bericht schreiben"),
    ],
    "ueber-uns.html": [
        ("geschichte.html", "Geschichte"),
        ("dokumente/satzung.pdf", "Satzung (PDF)"),
    ],
    "turniere.html": [
        ("oberlandquartett.html", "Oberlandquartett"),
        ("blitzjahreswertung.html", "Blitzjahreswertung"),
        ("vereinsintern.html", "Hall of Fame"),
        ("ausschreibungen.html", "Ausschreibungen"),
        (turnierkalender.SEITE, "Turnierkalender"),
        (turnierorte.SEITE, turnierorte.TITEL),
    ],
}

# Unterseiten, bei denen im Menü der übergeordnete Reiter markiert wird
ACTIVE_PARENT = {
    einreichen.SEITE: "berichte.html",
    "ausschreibungen.html": "turniere.html",
    turnierkalender.SEITE: "turniere.html",
    turnierorte.SEITE: "turniere.html",
    "oberlandquartett.html": "turniere.html",
    "blitzjahreswertung.html": "turniere.html",
    "vereinsintern.html": "turniere.html",
    "senioren.html": "mannschaften.html",
    "geschichte.html": "ueber-uns.html",
    "mannschaftshistorie.html": "mannschaften.html",
}

# Handgeschriebene Seiten: Inhalt liegt in seiten/<name>.html
STATIC_PAGES = [
    ("mannschaften", "Mannschaften"),
    ("kontakt", "Kontakt &amp; Anfahrt"),
    ("impressum", "Impressum &amp; Datenschutz"),
]

# Seitenweite Kleinigkeiten (Skip-Link, Untermenü-Skript). Header-Design: design.css
GLOBAL_CSS = """<style>
      /* Skip-Link: erst sichtbar, wenn er per Tastatur (Tab) angesprungen wird */
      .skip-link { position: absolute; left: -999px; top: 0; background: #fff; color: var(--navy); padding: 0.5rem 1rem; z-index: 200; font-weight: bold; }
      .skip-link:focus { left: 0; }

      /* Header (Kopf, Menü, Untermenüs, Handy-Menü): steht komplett in design.css */

      .footer-link { color: #aaa; }
    </style>
    <script>
      // Handy-Menü: Pfeil neben "Über uns" / "Mannschaften" klappt die Unterpunkte auf und zu
      document.addEventListener("click", function (e) {
        var k = e.target.closest && e.target.closest(".nav-auf");
        if (!k) return;
        var g = k.parentNode, offen = g.classList.toggle("offen");
        k.setAttribute("aria-expanded", offen ? "true" : "false");
      });
    </script>"""


# ==========================================
# 1. HELPER: RENDER PAGE MIT TEMPLATE
# ==========================================
def build_nav(nav_path, active, seite=None):
    """active = markierter Reiter, seite = aktuelle Datei (markiert den Eintrag im Untermenü)."""
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ''
        haupt = f'<a href="{nav_path}{href}"{cur}>{label}</a>'
        unter = SUBNAV.get(href)
        if not unter:
            links.append(haupt)
            continue
        eintraege = ""
        for u_href, u_label in unter:
            u_cur = ' aria-current="page"' if u_href == seite else ''
            eintraege += f'<a href="{nav_path}{u_href}"{u_cur}>{u_label}</a>'
        # Handy: Unterpunkte zugeklappt, Pfeil-Knopf klappt auf; der Bereich, in dem man gerade ist, ist offen
        offen = href == active or any(u == seite for u, _ in unter)
        knopf = (f'<button type="button" class="nav-auf" aria-expanded="{"true" if offen else "false"}" '
                 f'aria-label="{label} aufklappen"></button>')
        links.append(f'<div class="nav-gruppe{" offen" if offen else ""}">{haupt}{knopf}<div class="nav-unter">{eintraege}</div></div>')
    return "\n      ".join(links)


_DATEI_VERSION = {}


def _cache_brecher(html):
    """Hängt an eigene .css/.js-Dateien ?v=<Prüfsumme> an. Ändert sich eine Datei, lädt der Browser sie
    sofort neu (sonst zeigt er bis zu 10 Minuten die alte Fassung aus dem Zwischenspeicher)."""
    import hashlib

    def ersetze(m):
        name = m.group(2)
        if name not in _DATEI_VERSION:
            try:
                with open(name, "rb") as f:
                    _DATEI_VERSION[name] = hashlib.sha1(f.read()).hexdigest()[:8]
            except OSError:
                _DATEI_VERSION[name] = ""
        v = _DATEI_VERSION[name]
        return f'{m.group(1)}{name}{"?v=" + v if v else ""}"'
    return re.sub(r'((?:src|href)="(?:\.\./)*)([\w-]+\.(?:css|js))"', ersetze, html)


def render_page(title, content, filename, css_path="", nav_path="", extra_styles="", description=None):
    template_path = os.path.join("templates", "base.html")
    if not os.path.exists(template_path):
        print(f"Fehler: Template {template_path} nicht gefunden!")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    name = os.path.basename(filename)
    if os.path.dirname(filename).replace(os.sep, "/") == "berichte":
        name = "berichte.html"          # Einzelberichte -> Reiter "Berichte"
    active = ACTIVE_PARENT.get(name, name)

    # Beschreibung: explizit übergeben > Eintrag in PAGE_DESCRIPTIONS > Standard
    desc_src = description or PAGE_DESCRIPTIONS.get(name) or DEFAULT_DESCRIPTION
    desc = htmllib.escape(plain_text(desc_src), quote=True)

    # Logo und Favicon: nehmen logo.png (Groß-/Kleinschreibung egal), falls vorhanden
    logo_file = next((f for f in os.listdir(".") if f.lower() == "logo.png"), None)
    if logo_file:
        logo = f'<img src="{css_path}{logo_file}" alt="" class="brand-logo">'
        head_icon = f'<link rel="icon" href="{css_path}{logo_file}">'
        # Für die Vorschau in WhatsApp & Co. muss die Bild-Adresse absolut sein
        og_image_tag = (
            f'<meta property="og:image" content="{SITE_URL}{quote(logo_file)}">\n'
            '  <meta property="og:image:alt" content="Wappen der SG Aschheim / Feldkirchen / Kirchheim">'
        )
    else:
        logo = ""
        head_icon = FAVICON_EMOJI
        og_image_tag = ""

    full_html = template.format(
        title=title,
        content=content,
        css_path=css_path,
        nav_path=nav_path,
        nav=build_nav(nav_path, active, name),
        extra_styles=GLOBAL_CSS + suche.KNOPF_CSS + extra_styles,
        logo=logo,
        head_icon=head_icon,
        description=desc,
        og_image_tag=og_image_tag,
        jahr=TODAY.year,
        spielort_hinweis=(f'<p class="spielort-hinweis">{SPIELORT_HINWEIS}</p>' if SPIELORT_HINWEIS else ""),
        stand=letzte_aenderung(),
        konto_js=konten.script_tag(css_path, nav_path),
    )

    if MAIL_UMLEITUNG:
        full_html = re.sub(r"[\w.+-]+@sg-afk\.de", MAIL_UMLEITUNG, full_html)
    full_html = suche.knopf_einbauen(full_html, nav_path)
    full_html = _cache_brecher(full_html)
    suche.merken(title, content, filename, description or PAGE_DESCRIPTIONS.get(name, ""))

    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_html)


_STAND = None
def letzte_aenderung():
    """Datum der letzten echten Änderung (letzter Commit, der nicht vom automatischen Build stammt)."""
    global _STAND
    if _STAND is None:
        try:
            out = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=format:%d.%m.%Y",
                                  "--invert-grep", "--grep=Auto-generate"],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            out = ""
        _STAND = out or TODAY.strftime("%d.%m.%Y")
    return _STAND


# ==========================================
# 2. TERMINE: TYPST-TABELLE PARSEN
# ==========================================
def _find_closing(s, start):
    """Index der schließenden Klammer zur öffnenden '(' oder '[' an Position start."""
    open_ch = s[start]
    close_ch = ')' if open_ch == '(' else ']'
    depth = 0
    in_str = False
    for i in range(start, len(s)):
        c = s[i]
        if c == '"' and (i == 0 or s[i - 1] != '\\'):
            in_str = not in_str
        elif not in_str:
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return i
    return -1


def _top_level_brackets(s):
    """Inhalte aller [...] auf oberster Ebene."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '[':
            k = _find_closing(s, i)
            if k == -1:
                break
            result.append(s[i + 1:k])
            i = k + 1
        else:
            i += 1
    return result


def typst_inline_to_html(txt):
    """Wandelt den Inhalt einer Typst-Zelle in HTML um (Links, #strong, #align, #underline)."""
    txt = txt.strip()

    link_m = re.match(r'#link\(\s*"([^"]*)"\s*\)\[(.*)\]\s*$', txt, re.DOTALL)
    if link_m:
        label = typst_inline_to_html(link_m.group(2))
        url = htmllib.escape(link_m.group(1), quote=True)
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'

    # Terminkalender: #abw[...] = Abweichung (orange), #strong[...] = Spielabend (fett)
    txt = re.sub(r'#abw\[([^\]]*)\]', '\x01\\1\x02', txt)
    txt = re.sub(r'^#strong\[(.*)\]$', '\x03\\1\x04', txt, flags=re.DOTALL)
    txt = re.sub(r'#strong\s*\(\s*"(.*?)"\s*\)', r'\1', txt, flags=re.DOTALL)
    txt = re.sub(r'#align\s*\([^)]*\)\[(.*)\]', r'\1', txt, flags=re.DOTALL)
    txt = re.sub(r'#(?:strong|underline|emph)\[(.*)\]', r'\1', txt, flags=re.DOTALL)
    txt = txt.replace('*', '').strip()
    return (htmllib.escape(txt, quote=False).replace('\x01', '<b class="abw">').replace('\x02', '</b>')
            .replace('\x03', '<strong>').replace('\x04', '</strong>'))


def parse_typst_table(typst_content):
    """
    Liest die erste table(...) aus Typst-Code.
    Rückgabe: dict mit header (Liste), rows (Liste) und ncols - oder None.
    rows-Einträge: {'kind': 'month', 'text', 'colspan'} oder {'kind': 'row', 'cells': [...]}
    """
    code = re.sub(r'(?m)^\s*//.*$', '', typst_content)
    m = re.search(r'(?<![\w.])table\(', code)
    if not m:
        return None
    start = m.end() - 1
    end = _find_closing(code, start)
    if end == -1:
        return None
    body = code[start + 1:end]

    header = []
    items = []
    i, n = 0, len(body)

    while i < n:
        c = body[i]
        if c in ' \t\r\n,':
            i += 1
            continue

        if body.startswith('table.header(', i):
            p = i + len('table.header')
            q = _find_closing(body, p)
            if q == -1:
                break
            header = [typst_inline_to_html(t) for t in _top_level_brackets(body[p + 1:q])]
            i = q + 1

        elif body.startswith('table.cell(', i):
            p = i + len('table.cell')
            q = _find_closing(body, p)
            if q == -1:
                break
            args = body[p + 1:q]
            j = q + 1
            while j < n and body[j] in ' \t\r\n':
                j += 1
            text = ''
            if j < n and body[j] == '[':
                k = _find_closing(body, j)
                if k == -1:
                    break
                text = body[j + 1:k]
                i = k + 1
            else:
                i = j
            fill_m = re.search(r'fill:\s*(\w+)', args)
            span_m = re.search(r'colspan:\s*(\d+)', args)
            items.append({
                'text': typst_inline_to_html(text),
                'fill': fill_m.group(1) if fill_m else '',
                'colspan': int(span_m.group(1)) if span_m else 1,
            })

        elif c == '[':
            k = _find_closing(body, i)
            if k == -1:
                break
            items.append({'text': typst_inline_to_html(body[i + 1:k]), 'fill': '', 'colspan': 1})
            i = k + 1

        else:
            # Benannte Argumente wie "columns: 10," oder "stroke: 1pt + black," überspringen
            depth = 0
            while i < n:
                ch = body[i]
                if ch in '([':
                    depth += 1
                elif ch in ')]':
                    depth -= 1
                elif ch == ',' and depth == 0:
                    break
                i += 1

    ncols = len(header)
    if not ncols:
        cm = re.search(r'columns:\s*(\d+)', body)
        ncols = int(cm.group(1)) if cm else 10

    rows, current, filled = [], [], 0
    for it in items:
        if it['colspan'] >= ncols:
            if current:
                rows.append({'kind': 'row', 'cells': current})
                current, filled = [], 0
            rows.append({'kind': 'month', 'text': it['text'], 'colspan': it['colspan']})
        else:
            current.append(it)
            filled += it['colspan']
            if filled >= ncols:
                rows.append({'kind': 'row', 'cells': current})
                current, filled = [], 0
    if current:
        rows.append({'kind': 'row', 'cells': current})

    return {'header': header, 'rows': rows, 'ncols': ncols}


DATE_RE = re.compile(r'^\s*(\d{1,2})\.(\d{1,2})\.')


def assign_dates(rows, today=TODAY):
    """
    Setzt für jede Zeile mit Datum ('02.10. Fr, 18:00 Uhr') ein echtes date-Objekt.
    Das Jahr wird aus der Reihenfolge abgeleitet: Rutscht der Monat zurück (Dez -> Jan),
    beginnt ein neues Jahr. Die Saison startet im Herbst (ab Juli = laufendes Jahr).
    """
    year = today.year if today.month >= 7 else today.year - 1
    prev_month = None
    for r in rows:
        if r['kind'] == 'month':                  # "November 2027": Jahr steht dabei (Termine über ein Jahr hinaus)
            jm = re.search(r'\b(20\d\d)\b', r.get('text', ''))
            if jm:
                year, prev_month = int(jm.group(1)), None
            continue
        if r['kind'] != 'row':
            continue
        r['date'] = None
        plain = re.sub(r'<[^>]+>', '', r['cells'][0]['text'])
        dm = DATE_RE.match(plain)
        if not dm:
            continue
        day, month = int(dm.group(1)), int(dm.group(2))
        if prev_month is not None and month < prev_month:
            year += 1
        prev_month = month
        try:
            r['date'] = datetime.date(year, month, day)
        except ValueError:
            pass


TEAM_SPALTEN = r"AFK \d+|Senioren|Jugend"   # Spaltenköpfe, die eine Mannschaftsfarbe bekommen


def monats_schluessel(rows):
    """Monat (JJJJ-MM) je Tabellenzeile für den Monatsfilter: Monatsüberschrift = Monat des nächsten Termins darunter,
    Zeilen ohne erkennbares Datum gehören zum Monat davor."""
    monate, letzter = [], ""
    for i, r in enumerate(rows):
        if r['kind'] == 'month':
            naechster = next((x['date'] for x in rows[i + 1:] if x['kind'] != 'month' and x.get('date')), None)
            letzter = naechster.strftime("%Y-%m") if naechster else letzter
        elif r.get('date'):
            letzter = r['date'].strftime("%Y-%m")
        monate.append(letzter)
    return monate


TERMINE_AUSWAHL = "termine/auswahl"   # vorgebaute PDFs je Zeitraum Von–Bis (gleicher Typst-Stil wie termine.pdf)
MONAT_ZEILE = re.compile(r'table\.cell\(\s*colspan:.*strong\("')


def termine_auswahl_pdfs(rows):
    """Baut für jeden Zeitraum Von–Bis eine eigene PDF aus termine/termine.typ (nur die Monate dazwischen).
    Wird nur neu gebaut, wenn sich termine.typ oder template.typ geändert hat. -> {"JJJJ-MM|JJJJ-MM": Pfad}"""
    import hashlib
    quelle, vorlage = os.path.join("termine", "termine.typ"), os.path.join("termine", "template.typ")
    if not os.path.exists(quelle):
        return {}
    text = open(quelle, encoding="utf-8").read()
    zeilen = text.split("\n")
    kopf_ende = next((i for i, z in enumerate(zeilen) if MONAT_ZEILE.search(z)), None)
    ende = max((i for i, z in enumerate(zeilen) if z.strip() == ")"), default=None)
    if kopf_ende is None or ende is None or ende < kopf_ende:
        return {}
    bloecke, aktuell = [], None
    for z in zeilen[kopf_ende:ende]:
        if MONAT_ZEILE.search(z):
            aktuell = [z]
            bloecke.append(aktuell)
        elif aktuell is not None:
            aktuell.append(z)
    schluessel = [m for r, m in zip(rows, monats_schluessel(rows)) if r['kind'] == 'month']
    if len(schluessel) != len(bloecke) or not all(schluessel) or len(set(schluessel)) != len(schluessel):
        print(f"Hinweis: Auswahl-PDFs übersprungen ({len(bloecke)} Monate in termine.typ, {len(schluessel)} erkannt)")
        return {}
    n = len(bloecke)
    dateien = {f"{schluessel[i]}|{schluessel[j]}": f"{TERMINE_AUSWAHL}/{schluessel[i]}_{schluessel[j]}.pdf"
               for i in range(n) for j in range(i, n)}
    stand = hashlib.sha1((text + (open(vorlage, encoding="utf-8").read() if os.path.exists(vorlage) else "")).encode()).hexdigest()
    stand_datei = os.path.join(TERMINE_AUSWAHL, "stand.txt")
    alt = open(stand_datei, encoding="utf-8").read().strip() if os.path.exists(stand_datei) else ""
    if alt == stand and all(os.path.exists(d) for d in dateien.values()):
        return dateien
    os.makedirs(TERMINE_AUSWAHL, exist_ok=True)
    for f in os.listdir(TERMINE_AUSWAHL):
        if f.endswith(".pdf"):
            os.remove(os.path.join(TERMINE_AUSWAHL, f))
    tmp_tab, tmp_main = os.path.join("termine", "_auswahl_termine.typ"), os.path.join("termine", "_auswahl.typ")
    with open(tmp_main, "w", encoding="utf-8") as f:
        f.write('#import "template.typ": *\n#show: template\n\n#include "_auswahl_termine.typ"\n')
    fertig = {}
    try:
        for i in range(n):
            for j in range(i, n):
                teil = zeilen[:kopf_ende] + [z for b in bloecke[i:j + 1] for z in b] + zeilen[ende:]
                with open(tmp_tab, "w", encoding="utf-8") as f:
                    f.write("\n".join(teil))
                ziel = dateien[f"{schluessel[i]}|{schluessel[j]}"]
                try:
                    subprocess.run(["typst", "compile", tmp_main, ziel], check=True, capture_output=True)
                    fertig[f"{schluessel[i]}|{schluessel[j]}"] = ziel
                except Exception as e:
                    print(f"Hinweis: Auswahl-PDF {ziel} nicht gebaut ({e})")
    finally:
        for t in (tmp_tab, tmp_main):
            if os.path.exists(t):
                os.remove(t)
    if len(fertig) == len(dateien):
        with open(stand_datei, "w", encoding="utf-8") as f:
            f.write(stand)
    print(f"Termine: {len(fertig)} Auswahl-PDFs gebaut")
    return fertig


def render_table_inner_html(parsed, today=TODAY):
    out = []
    # Spalten der Mannschaften (AFK 1 ..., Senioren, Jugend) bekommen ihre Mannschaftsfarbe (design.css)
    header = parsed['header'] or []
    spalten_klasse = [team_klasse(h) if re.fullmatch(TEAM_SPALTEN, plain_text(h).strip()) else "" for h in header]
    if header:
        out.append('<thead><tr>' + ''.join(
            f'<th class="{k}">{h}</th>' if k else f'<th>{h}</th>' for h, k in zip(header, spalten_klasse)) + '</tr></thead>')
    out.append('<tbody>')
    rows = parsed['rows']
    pausen = sorted(read_ausfall(), key=lambda a: a["start"]) if PAUSE_IM_KALENDER else []
    breite = sum(c['colspan'] for c in next((x['cells'] for x in rows if x['kind'] != 'month'), [])) or len(header) or 2

    def pause_zeile(a):
        s_ = datetime.date.fromisoformat(a["start"]); e_ = datetime.date.fromisoformat(a["end"])
        wann = (f"{s_.day}.{s_.month}." if s_ == e_ else f"{s_.day}.{s_.month}. – {e_.day}.{e_.month}.")
        name = htmllib.escape(a["reason"] or "Pause")
        return (f'<tr class="pause-zeile" data-monat="{s_:%Y-%m}"><td>{wann}</td>'
                f'<td colspan="{breite - 1}"><b>{name}</b> – kein Spielabend</td></tr>')

    def vor(schluessel):
        while pausen and pausen[0]["start"] <= schluessel:
            out.append(pause_zeile(pausen.pop(0)))

    for r, monat in zip(rows, monats_schluessel(rows)):
        dm = f' data-monat="{monat}"' if monat else ''
        if r['kind'] == 'month':
            if monat:
                vor(f"{monat}-00")
        elif r.get('date'):
            vor(r['date'].isoformat())
        if r['kind'] == 'month':
            out.append(f'<tr class="monat-row"{dm}><td colspan="{r["colspan"]}" class="monat-header">{r["text"]}</td></tr>')
            continue
        past = r.get('date') is not None and r['date'] < today
        tr_cls = (' class="past"' if past else '') + dm
        tds, spalte = [], 0
        for c in r['cells']:
            klassen = []
            if c['fill'] == 'VereinFarbe' and c['text'].strip():     # sonst keine Füllfarben (Variante A)
                klassen.append('verein-zelle')
            if c['colspan'] == 1 and spalte < len(spalten_klasse) and spalten_klasse[spalte] and c['text'].strip():
                klassen += ['team-zelle', spalten_klasse[spalte]]
            cls = f' class="{" ".join(klassen)}"' if klassen else ''
            span = f' colspan="{c["colspan"]}"' if c['colspan'] > 1 else ''
            tds.append(f'<td{cls}{span}>{c["text"]}</td>')
            spalte += c['colspan']
        out.append(f'<tr{tr_cls}>' + ''.join(tds) + '</tr>')
    vor("9999")
    out.append('</tbody>')
    return '\n'.join(out)


def parse_typst_table_to_html(typst_content):
    """Kompatibel zur alten Version: liefert den Inhalt für <table>...</table>."""
    parsed = parse_typst_table(typst_content)
    if not parsed or not parsed['rows']:
        return '<tbody><tr><td>Keine Tabelle gefunden.</td></tr></tbody>'
    assign_dates(parsed['rows'])
    return render_table_inner_html(parsed)


def extract_upcoming_events(parsed, today=TODAY, limit=NEXT_EVENTS_COUNT):
    """
    Nächste Termine ab heute. Zeilen mit Veranstaltung zeigen den Titel,
    Zeilen ohne Veranstaltung (Mannschaftskämpfe) zeigen z. B. 'MMM Runde 1' + betroffene Teams.
    """
    header = parsed['header']
    events = []
    for r in parsed['rows']:
        if r['kind'] != 'row' or not r.get('date') or r['date'] < today:
            continue
        cells = r['cells']
        if len(cells) < 2:
            continue

        when = cells[0]['text']
        event = cells[1]['text']
        who = ''

        if event:
            title = event
        else:
            groups = {}
            for idx in range(2, len(cells)):
                t = cells[idx]['text']
                if t and 'spielfrei' not in t.lower():
                    name = header[idx] if idx < len(header) else f'Team {idx - 1}'
                    groups.setdefault(t, []).append(name)
            if not groups:
                continue
            if len(groups) == 1:
                title = next(iter(groups))
                who = ', '.join(next(iter(groups.values())))
            else:
                title = '<br>'.join(f"{t} ({', '.join(names)})" for t, names in groups.items())

        when = re.sub(r'</?(?:b|strong)\b[^>]*>', '', when)          # Hervorhebungen nur im Kalender
        events.append({'date': r['date'], 'when': when, 'title': title, 'who': who})
        if len(events) >= limit:
            break
    return events


# ------------------------------------------
# Kalender-Export (.ics)
# ------------------------------------------
TIME_RE = re.compile(r'(\d{1,2}):(\d{2})')


def plain_text(html_str):
    return htmllib.unescape(re.sub(r'<[^>]+>', '', html_str)).strip()


def slugify(text):
    text = plain_text(text).lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        text = text.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-') or 'x'


def ics_escape(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def ics_fold(line):
    """Zeilen laut Standard auf 75 Bytes umbrechen (nie mitten in einem UTF-8-Zeichen)."""
    out = []
    b = line.encode('utf-8')
    while len(b) > 75:
        cut = 75
        while (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode('utf-8'))
        b = b' ' + b[cut:]
    out.append(b.decode('utf-8'))
    return '\r\n'.join(out)


def ics_datetime(d, hh, mm, add_hours=0):
    local = datetime.datetime(d.year, d.month, d.day, hh, mm) + datetime.timedelta(hours=add_hours)
    try:
        return local.replace(tzinfo=ZoneInfo(CAL_TZ)).astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    except Exception:
        return local.strftime('%Y%m%dT%H%M%S')   # Notlösung: lokale Zeit ohne Zeitzone


def collect_calendar_events(parsed):
    header = [plain_text(h) for h in parsed['header']]
    events = []
    for r in parsed['rows']:
        if r['kind'] != 'row' or not r.get('date'):
            continue
        cells = r['cells']
        if len(cells) < 2:
            continue
        tm = TIME_RE.search(plain_text(cells[0]['text']))
        hh, mm = (int(tm.group(1)), int(tm.group(2))) if tm else (None, None)

        title = plain_text(cells[1]['text'])
        if title:
            events.append({'date': r['date'], 'h': hh, 'm': mm, 'title': title, 'teams': []})

        groups = {}
        for idx in range(2, len(cells)):
            t = plain_text(cells[idx]['text'])
            if t and 'spielfrei' not in t.lower():
                name = header[idx] if idx < len(header) else f'Team {idx - 1}'
                groups.setdefault(t, []).append(name)
        for t, names in groups.items():
            events.append({'date': r['date'], 'h': hh, 'm': mm, 'title': t, 'teams': names})
    return events


def write_ics(path, cal_name, feed_slug, entries):
    """entries: Liste von (event, summary)."""
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//SG AFK//Termine//DE',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
        f'X-WR-CALNAME:{ics_escape(cal_name)}', f'X-WR-TIMEZONE:{CAL_TZ}',
        'REFRESH-INTERVAL;VALUE=DURATION:PT12H', 'X-PUBLISHED-TTL:PT12H',
    ]
    for ev, summary in entries:
        d = ev['date']
        uid = f"{d.isoformat()}-{ev['h'] if ev['h'] is not None else 'ganztag'}-{slugify(summary)}-{feed_slug}@sg-afk"
        lines += ['BEGIN:VEVENT', f'UID:{uid}', f"DTSTAMP:{d.strftime('%Y%m%d')}T000000Z"]
        if ev['h'] is not None:
            lines.append(f"DTSTART:{ics_datetime(d, ev['h'], ev['m'])}")
            lines.append(f"DTEND:{ics_datetime(d, ev['h'], ev['m'], EVENT_DURATION_HOURS)}")
        else:
            lines.append(f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{(d + datetime.timedelta(days=1)).strftime('%Y%m%d')}")
        lines.append(f'SUMMARY:{ics_escape(summary)}')
        if 'vereinsabend' in ev['title'].lower():
            lines.append(f'LOCATION:{ics_escape(SPIELORT)}')
        lines.append(f'URL:{SITE_URL}termine.html')
        lines.append('END:VEVENT')
    lines.append('END:VCALENDAR')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(ics_fold(l) for l in lines) + '\r\n')


def build_calendar_feeds(parsed):
    """Schreibt kalender/alle.ics und je eine Datei pro Spalte (AFK 1 ... Jugend). Rückgabe: [(Label, Dateiname)]"""
    os.makedirs('kalender', exist_ok=True)
    events = collect_calendar_events(parsed)
    feeds = []

    # Alle Termine
    entries = []
    for ev in events:
        summary = f"{ev['title']} ({', '.join(ev['teams'])})" if ev['teams'] else ev['title']
        entries.append((ev, summary))
    write_ics('kalender/alle.ics', 'SG AFK – Alle Termine', 'alle', entries)
    feeds.append(('Alle Termine', 'alle.ics'))

    # Pro Mannschaft: Vereinstermine + eigene Spiele
    for team in [plain_text(h) for h in parsed['header'][2:]]:
        slug = slugify(team)
        entries = []
        for ev in events:
            if not ev['teams']:
                entries.append((ev, ev['title']))
            elif team in ev['teams']:
                entries.append((ev, f"{team}: {ev['title']}"))
        write_ics(f'kalender/{slug}.ics', f'SG AFK – {team}', slug, entries)
        feeds.append((team, f'{slug}.ics'))
    return feeds


def calendar_box_html(feeds):
    if not feeds:
        return ""
    webcal_base = SITE_URL.replace('https://', 'webcal://')
    rows = []
    for label, fname in feeds:
        https_url = f'{SITE_URL}kalender/{fname}'
        rows.append(
            f'<li><strong>{label}</strong> '
            f'<a href="{webcal_base}kalender/{fname}">Abonnieren</a> '
            f'<a href="{https_url}" data-url="{https_url}" '
            f'onclick="navigator.clipboard.writeText(this.dataset.url);this.textContent=\'Link kopiert\';return false;">Link kopieren</a></li>'
        )
    return f"""
    <details class="kalender-box">
      <summary>Termine im Handy-Kalender abonnieren</summary>
      <p>Der Kalender aktualisiert sich automatisch, wenn sich der Spielplan ändert.
         <strong>iPhone / Mac / Outlook:</strong> „Abonnieren" antippen.
         <strong>Google Kalender:</strong> „Link kopieren" und in Google Kalender unter „Weitere Kalender → Per URL" einfügen.</p>
      <ul>{''.join(rows)}</ul>
    </details>
    """


def read_hinweis():
    """Liest hinweis.txt im Hauptverzeichnis. Leer oder nicht vorhanden = kein Banner."""
    path = "hinweis.txt"
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        lines = [htmllib.escape(l.strip()) for l in f.read().splitlines() if l.strip()]
    if not lines:
        return ""
    return '<div class="hinweis-banner">' + '<br>'.join(lines) + '</div>'


TURNIERE = [
    # (Titel, Beschreibung, Link, Button-Text)
    ("Oberlandquartett", "Ergebnisse, Platzierungen und Rundenübersichten des traditionellen Oberlandquartetts.",
     "oberlandquartett.html", "Zum Oberlandquartett"),
    ("Blitzjahreswertung", "Die aktuelle Gesamtwertung und Zwischenstände unserer monatlichen Blitzschach-Turnierserie.",
     "blitzjahreswertung.html", "Zur Blitzjahreswertung"),
    ("Vereinsintern &amp; Hall of Fame", "Die historischen Vereinsmeister, Blitzschach-Champions und Pokalsieger unseres Vereins auf einen Blick.",
     "vereinsintern.html", "Zur Hall of Fame"),
]


def build_chessresults():
    """Turnierseiten von chess-results; stehen unter "Turniere" (Übersicht + Untermenü)."""
    gebaut = chessresults.bauen(render_page)
    for seite, name, text in reversed(gebaut):
        TURNIERE.insert(0, (htmllib.escape(name), htmllib.escape(text), seite, "Tabelle &amp; Paarungen"))
        SUBNAV["turniere.html"].insert(0, (seite, htmllib.escape(name)))
        ACTIVE_PARENT[seite] = "turniere.html"


def build_turniere_overview():
    zeilen = "".join(f"""
      <div class="turnier-zeile">
        <h2>{titel}</h2>
        <p>{text}</p>
        <a href="{link}" class="btn">{knopf} →</a>
      </div>""" for titel, text, link, knopf in TURNIERE)
    content = f"""
    <h1>Turniere &amp; Ergebnisse</h1>
    <p>Übersichten zu unseren regionalen Wettkämpfen, die Gesamtwertung der Blitzschach-Serie und die Hall of Fame unserer Vereinsmeister.</p>
    <div class="turnier-liste">{zeilen}
    </div>

    <section class="ausschreibungen-block">
      <h2>Ausschreibungen</h2>
      <p>Unsere eigenen Turniere als PDF oder Opens in ganz Europa im Turnierkalender.</p>
      {ausschreibungen_wahl_html("ausschreibungen.html")}
    </section>
    """
    render_page("Turniere & Ergebnisse", content, "turniere.html")


BG_FARBEN = {
    "green":         ("#00CD00", ""),
    "yellow":        ("#ffff00", ""),
    "blue":          ("#0000ff", "white"),
    "red":           ("#ff0000", "white"),
    "chocolate":     ("#d2691e", ""),
    "orange":        ("#ffa500", ""),
    "purple":        ("#551a8b", "white"),
    "gray":          ("#bebebe", ""),
    "white":         ("#ffffff", ""),
    "black":         ("#000000", "white"),
    "gold":          ("#B8860B", ""),
    "tuerkis":       ("#8B8878", ""),
    "blueviolet":    ("#8A2BE2", "white"),
    "orangered":     ("#ff4500", ""),
    "deepskyblue":   ("#00bfff", ""),
    "darkslategray": ("#528b8b", "white"),
}


def farben_css():
    zeilen = []
    for name, (bg, fg) in BG_FARBEN.items():
        regel = f"background: {bg};" + (f" color: {fg};" if fg else "")
        zeilen.append(f"      .custom-tabelle td.bg-{name} {{ {regel} }}")
    return "\n".join(zeilen) + "\n"


TERMINE_PDF = "termine.pdf"   # PDF zum Herunterladen/Mailen (liegt im Website-Root)


# ---- Monatsfilter + "Auswahl als PDF" (Drucken) auf termine.html ----
TERMINE_FILTER_HTML = """
    <div class="termine-filter" id="termine-filter">
      <label>Von <select id="tf-von"></select></label>
      <label>Bis <select id="tf-bis"></select></label>
      <button type="button" id="tf-alle">Alle</button>
      <a id="tf-druck" class="tf-haupt tf-knopf" href="#" download>Auswahl als PDF</a>
    </div>"""

TERMINE_FILTER_CSS = """<style>
      .termine-filter { display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; align-items: end; margin: 1rem 0 0; }
      .termine-filter label { display: grid; gap: 0.2rem; font-size: 0.85rem; font-weight: 600; }
      .termine-filter select, .termine-filter button { font: inherit; font-size: 0.92rem; padding: 0.4rem 0.6rem; border-radius: 6px;
        border: 1px solid var(--line, #ccc); background: var(--surface, #fff); color: var(--text, #222); }
      .termine-filter button, .termine-filter .tf-knopf { cursor: pointer; }
      .termine-filter .tf-knopf { font: inherit; font-size: 0.92rem; padding: 0.4rem 0.6rem; border-radius: 6px; text-decoration: none;
        border: 1px solid var(--line, #ccc); background: var(--surface, #fff); color: var(--text, #222); }
      .termine-filter .tf-knopf.aus { opacity: 0.45; pointer-events: none; }
      .termine-filter .tf-haupt { font-weight: 700; }
      .termine-filter button[disabled] { opacity: 0.45; cursor: not-allowed; }
      .custom-tabelle tr.tf-aus { display: none; }
      .termine-leer { text-align: center; padding: 1.5rem; color: var(--muted, #777); }
      .druck-titel { display: none; }
      @media print {
        @page { size: A4 landscape; margin: 10mm; }
        body * { visibility: hidden !important; }
        #termine-druck, #termine-druck * { visibility: visible !important; }
        #termine-druck { position: absolute !important; left: 0 !important; top: 0; width: 100% !important; transform: none !important;
          margin: 0 !important; padding: 0 !important; }
        .custom-tabelle { width: 100% !important; }
        .druck-titel { display: block; font-size: 14pt; margin: 0 0 6pt; color: #000; }
        .table-responsive { overflow: visible !important; margin: 0 !important; }
        .custom-tabelle { font-size: 8pt; }
        .custom-tabelle th, .custom-tabelle td { padding: 3px 4px !important; }
        .custom-tabelle tr { break-inside: avoid; }
        .custom-tabelle .past td { opacity: 1; }
        * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      }
    </style>"""

TERMINE_FILTER_JS = """<script>
(function () {
  var tab = document.querySelector(".custom-tabelle"); if (!tab) return;
  var zeilen = [].slice.call(tab.querySelectorAll("tbody tr[data-monat]"));
  var MON = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"];
  var monate = []; zeilen.forEach(function (z) { var m = z.getAttribute("data-monat"); if (monate.indexOf(m) < 0) monate.push(m); });
  monate.sort();
  if (!monate.length) { document.getElementById("termine-filter").hidden = true; return; }
  var von = document.getElementById("tf-von"), bis = document.getElementById("tf-bis"), SPEICHER = "afk-termine-filter2";
  var PDFS = {}; try { PDFS = JSON.parse(document.getElementById("termine-pdfs").textContent); } catch (e) {}
  function name(m) { return MON[+m.slice(5, 7) - 1] + " " + m.slice(0, 4); }
  monate.forEach(function (m) { [von, bis].forEach(function (s) { var o = document.createElement("option"); o.value = m; o.textContent = name(m); s.appendChild(o); }); });
  // Standard: aktueller Monat (oder der nächste mit Terminen) bis Saisonende
  var h = new Date(), jetzt = h.getFullYear() + "-" + ("0" + (h.getMonth() + 1)).slice(-2);
  var start = monate.filter(function (m) { return m >= jetzt; })[0] || monate[0];
  var w = null; try { w = JSON.parse(localStorage.getItem(SPEICHER) || "null"); } catch (e) {}
  // Gemerkte Auswahl nur, wenn man sie selbst gewählt hat; "bis zum letzten Monat" bleibt "bis zum Ende",
  // auch wenn neue Monate dazukommen (z. B. ein Termin ein Jahr später). Vergangene Monate fallen weg.
  von.value = w && monate.indexOf(w.von) >= 0 && w.von >= start ? w.von : start;
  bis.value = w && !w.ende && monate.indexOf(w.bis) >= 0 && w.bis >= von.value ? w.bis : monate[monate.length - 1];
  function anwenden(geaendert) {
    // Bis vor Von: tauschen (z. B. "April bis März" -> "März bis April")
    if (bis.value < von.value) { var t = von.value; von.value = bis.value; bis.value = t; }
    var a = von.value, b = bis.value, sichtbar = 0;
    zeilen.forEach(function (z) {
      var m = z.getAttribute("data-monat"), an = m >= a && m <= b;
      z.classList.toggle("tf-aus", !an);
      if (an && !z.classList.contains("monat-row")) sichtbar++;
    });
    // Monatsüberschriften ohne sichtbare Termine darunter ausblenden
    zeilen.forEach(function (z, i) {
      if (!z.classList.contains("monat-row") || z.classList.contains("tf-aus")) return;
      var n = zeilen[i + 1];
      if (!n || n.classList.contains("monat-row") || n.classList.contains("tf-aus")) z.classList.add("tf-aus");
    });
    tab.style.display = sichtbar ? "" : "none";
    document.getElementById("termine-leer").hidden = !!sichtbar;
    // Fertige PDF für genau diesen Zeitraum (beim Build mit Typst erzeugt); ohne PDF: Drucken als Notlösung
    var pdf = PDFS[a + "|" + b], knopf = document.getElementById("tf-druck");
    knopf.classList.toggle("aus", !sichtbar);
    if (pdf) { knopf.href = pdf; knopf.setAttribute("download", "Termine_" + a + "_bis_" + b + ".pdf"); knopf.dataset.drucken = ""; }
    else { knopf.href = "#"; knopf.removeAttribute("download"); knopf.dataset.drucken = "1"; }
    document.getElementById("druck-zeitraum").textContent = a === b ? name(a) : name(a) + " – " + name(b);
    if (geaendert === true) try { localStorage.setItem(SPEICHER, JSON.stringify({von: a, bis: b, ende: b === monate[monate.length - 1]})); } catch (e) {}
  }
  von.addEventListener("change", function () { anwenden(true); }); bis.addEventListener("change", function () { anwenden(true); });
  document.getElementById("tf-alle").addEventListener("click", function () { von.value = monate[0]; bis.value = monate[monate.length - 1]; anwenden(true); });
  // Drucken/PDF immer im hellen Design
  var thema = null;
  window.addEventListener("beforeprint", function () { thema = document.documentElement.getAttribute("data-theme"); document.documentElement.setAttribute("data-theme", "light"); });
  window.addEventListener("afterprint", function () { if (thema) document.documentElement.setAttribute("data-theme", thema); });
  document.getElementById("tf-druck").addEventListener("click", function (ev) {
    if (this.dataset.drucken) { ev.preventDefault(); window.print(); }
  });
  anwenden();
})();
</script>"""


def build_termine():
    folder_path = "termine"
    main_typ = os.path.join(folder_path, "termine.typ")
    svg_path = os.path.join(folder_path, "output.svg")

    # 0. PDF (A3 quer, mit template.typ) aus termine/main.typ
    pdf_typ = os.path.join(folder_path, "main.typ")
    if os.path.exists(pdf_typ):
        try:
            subprocess.run(["typst", "compile", pdf_typ, TERMINE_PDF], check=True)
        except Exception as e:
            print(f"Typst Compiling Hinweis (Termine-PDF): {e}")

    # 1. Lokales Kompilieren versuchen (nur nötig, wenn die SVG verwendet wird)
    if USE_SVG_FOR_TERMINE and os.path.exists(main_typ):
        try:
            subprocess.run(["typst", "compile", main_typ, svg_path], check=True)
        except Exception:
            pass

    # 2. Typst-Tabelle lesen
    parsed = None
    if os.path.exists(main_typ):
        with open(main_typ, "r", encoding="utf-8") as f:
            parsed = parse_typst_table(f.read())

    upcoming_events = []
    calendar_html = ""
    if parsed:
        assign_dates(parsed['rows'])
        upcoming_events = extract_upcoming_events(parsed)
        calendar_html = calendar_box_html(build_calendar_feeds(parsed))

    # 3. Tabelle: SVG oder HTML
    if USE_SVG_FOR_TERMINE and os.path.exists(svg_path):
        with open(svg_path, "r", encoding="utf-8") as f:
            table_html = f'<div class="svg-container">{f.read()}</div>'
    elif parsed and parsed['rows']:
        table_html = f'<table class="custom-tabelle">{render_table_inner_html(parsed)}</table>'
    else:
        table_html = "<p>Keine Termine vorhanden.</p>"

    pdf_link = (f'<p><a href="{TERMINE_PDF}" download>Termine als PDF herunterladen</a></p>'
                if os.path.exists(TERMINE_PDF) else "")

    filter_html = TERMINE_FILTER_HTML if (parsed and parsed['rows'] and not USE_SVG_FOR_TERMINE) else ""
    if filter_html:
        auswahl = termine_auswahl_pdfs(parsed['rows'])
        filter_html += ('<script type="application/json" id="termine-pdfs">'
                        + json.dumps(auswahl).replace("</", "<\\/") + '</script>')
    content = f"""{read_hinweis()}
    <h1>Termine & Spielplan</h1>
    {pdf_link}
    {calendar_html}
    {filter_html}
    <div class="full-bleed" id="termine-druck">
      <h2 class="druck-titel">SG Aschheim / Feldkirchen / Kirchheim – Termine <span id="druck-zeitraum"></span></h2>
      <div class="table-responsive">
        {table_html}
      </div>
      <p class="termine-leer" id="termine-leer" hidden>Keine Termine in diesem Zeitraum.</p>
    </div>
    {TERMINE_FILTER_JS if filter_html else ""}"""

    styles = """<style>""" + FULL_BLEED_CSS + HINWEIS_CSS + """
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; text-align: center; }
      .svg-container svg { max-width: 100%; height: auto; background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
      .custom-tabelle { width: 100%; border-collapse: collapse; font-size: 0.9rem; background: white; border-radius: 8px; overflow: hidden; }
      .custom-tabelle th, .custom-tabelle td { padding: 7px 8px; border: 1px solid #dcdcdc; text-align: center; line-height: 1.3; }
      .custom-tabelle th { background-color: #1a252f; color: white; }
      .custom-tabelle td:first-child { white-space: nowrap; }
      .custom-tabelle td.monat-header { background: deepskyblue; font-weight: bold; font-size: 1.05rem; }
      .custom-tabelle .past td { opacity: 0.45; }
      .custom-tabelle td.bg-yellow { background: yellow; }
      .custom-tabelle td.bg-orange { background: orange; }
      .custom-tabelle td.bg-green { background: #5fd068; }
      .custom-tabelle td.bg-darkslategray { background: #2f4f4f; color: white; }
      .custom-tabelle td.bg-deepskyblue { background: deepskyblue; }
      .kalender-box { background: #f8f9fa; border-left: 5px solid #3498db; border-radius: 6px; padding: 0.8rem 1.2rem; margin-top: 1rem; font-size: 0.9rem; }
      .kalender-box summary { cursor: pointer; font-weight: bold; }
      .kalender-box ul { list-style: none; padding: 0; margin: 0.6rem 0 0 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0.4rem 1.5rem; }
      .kalender-box li a { margin-left: 0.6rem; color: #3498db; text-decoration: none; font-weight: bold; }
    </style>""" + TERMINE_FILTER_CSS

    styles = styles.replace("</style>", farben_css() + "</style>", 1)
    render_page("Termine & Spielplan", content, "termine.html", extra_styles=styles)
    return upcoming_events


# ==========================================
# 2b. AUSSCHREIBUNGEN-ARCHIV & "NEU HIER?"
# ==========================================
def git_last_date(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path],
                             capture_output=True, text=True, check=True).stdout.strip()
        return datetime.date.fromisoformat(out) if out else None
    except Exception:
        return None


def ausschreibungen_eintraege():
    """Alle PDFs aus Ausschreibungen/ (neueste zuerst). Anzeigenamen optional in Ausschreibungen/titel.txt."""
    folder = "Ausschreibungen"
    files = glob.glob(os.path.join(folder, "*.pdf")) if os.path.isdir(folder) else []

    # Optionale Anzeigenamen: Datei Ausschreibungen/titel.txt, je Zeile "datei.pdf = Anzeigename"
    titles = {}
    titles_path = os.path.join(folder, "titel.txt")
    if os.path.exists(titles_path):
        with open(titles_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    if key.strip() and value.strip():
                        titles[key.strip().lower()] = value.strip()

    entries = []
    for path in files:
        name = os.path.basename(path)
        stem = os.path.splitext(name)[0]
        label = (titles.get(name.lower()) or titles.get(stem.lower())
                 or re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', stem)).strip())
        entries.append({
            'label': htmllib.escape(label),
            'url': f"{quote(folder)}/{quote(name)}",
            'size': max(1, os.path.getsize(path) // 1024),
            'date': git_last_date(path),
            'name': name.lower(),
        })
    entries.sort(key=lambda e: e['name'])
    entries.sort(key=lambda e: e['date'] or datetime.date.min, reverse=True)
    return entries


def pdf_liste_html(entries):
    if not entries:
        return "<p>Aktuell sind keine Ausschreibungen vorhanden.</p>"
    items = ""
    for e in entries:
        stand = f" · Stand {e['date'].strftime('%d.%m.%Y')}" if e['date'] else ""
        items += f"""
            <a class="pdf-card" href="{e['url']}" target="_blank" rel="noopener">
              <span class="pdf-icon" aria-hidden="true">PDF</span>
              <span class="pdf-text"><strong>{e['label']}</strong><br><small>PDF · {e['size']} KB{stand}</small></span>
            </a>"""
    return f'<div class="pdf-grid">{items}</div>'


def ausschreibungen_wahl_html(intern_link):
    """Drei Karten: Intern (eigene PDFs) / Turnierkalender / AFK on Tour."""
    n = len(ausschreibungen_eintraege())
    m = turnierkalender.ANZAHL
    return f"""<div class="pdf-grid">
            <a class="pdf-card" href="{intern_link}">
              <span class="pdf-icon" aria-hidden="true" style="background:var(--hell);color:#0e1524">AFK</span>
              <span class="pdf-text"><strong>Intern</strong><br><small>Unsere Turniere · {n} {"Ausschreibung" if n == 1 else "Ausschreibungen"} als PDF</small></span>
            </a>
            <a class="pdf-card" href="{turnierkalender.SEITE}">
              <span class="pdf-icon" aria-hidden="true" style="background:var(--hell);color:#0e1524">EU</span>
              <span class="pdf-text"><strong>Turnierkalender</strong><br><small>Opens in Bayern, Deutschland und Europa{f" · {m} Turniere" if m else ""}</small></span>
            </a>
            <a class="pdf-card" href="{turnierorte.SEITE}">
              <span class="pdf-icon" aria-hidden="true" style="background:var(--hell);color:#0e1524">TOUR</span>
              <span class="pdf-text"><strong>AFK on Tour</strong><br><small>Wo wir schon überall Turniere gespielt haben – mit Karte und Abzeichen</small></span>
            </a>
          </div>"""


def build_ausschreibungen():
    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">Ausschreibungen</h1>
    {turnierkalender.AUSSCHREIBUNG_TABS.format(intern=' class="an" aria-current="page"', extern="", anzahl=turnierkalender.ANZAHL)}
    <p>Hier findest du die Ausschreibungen zu unseren kommenden Turnieren. Ein Klick öffnet die PDF direkt.</p>
    {pdf_liste_html(ausschreibungen_eintraege())}
    """
    render_page("Ausschreibungen", content, "ausschreibungen.html")


# Mitgliedsbeiträge pro Jahr (Über uns, Abschnitt "Neu hier?")
BEITRAEGE = [
    ("Kinder, Schüler &amp; Studenten", "24 €"),
    ("Erwachsene", "75 €"),
]


def neu_hier_html():
    """Abschnitt „Neu hier?" – steht auf der Über-uns-Seite (früher eigene Seite neu-hier.html)."""
    beitraege = "".join(f"<li><strong>{wer}:</strong> {preis} im Jahr</li>" for wer, preis in BEITRAEGE)
    content = f"""
    <h2 id="neu-hier">Neu hier? So kommst du vorbei</h2>
    <p>Egal ob Einsteiger, Jugendlicher oder Turnierspieler: Komm einfach an einem Freitag bei uns vorbei.</p>

    <div class="neu-grid">
      <div class="neu-card">
        <h3>Wann?</h3>
        <p><strong>Jeden Freitag.</strong> Das Gebäude ist ab 18:00 Uhr geöffnet.</p>
        <ul>
          <li><strong>Jugendtraining:</strong> 18:00 – 19:30 Uhr</li>
          <li><strong>Erwachsene &amp; Spielabend:</strong> ab 19:30 Uhr (Open End)</li>
        </ul>
        <p>Die Zeiten sind flexibel: Erwachsene dürfen schon ab 18:00 Uhr kommen, Jugendliche müssen um 19:30 Uhr nicht gehen.</p>
      </div>

      <div class="neu-card">
        <h3>Wo?</h3>
           <p><strong>Gymnasium Kirchheim</strong><br>Heimstettner Str. 20<br>85551 Kirchheim</p>
           {f'<p>{SPIELORT_HINWEIS}</p>' if SPIELORT_HINWEIS else ''}
        <a href="https://maps.app.goo.gl/L8YRrvs52HD5cpDCA" target="_blank" rel="noopener" class="btn btn-outline">Auf Google Maps öffnen</a>
      </div>

      <div class="neu-card">
        <h3>Wer kann kommen?</h3>
        <ul>
          <li><strong>Alle sind willkommen – egal wie alt.</strong> Die Regeln musst du noch nicht kennen.</li>
          <li><strong>Schnuppern ist kostenlos und unverbindlich</strong>, so oft du willst.</li>
          <li><strong>Anmelden?</strong> Nicht nötig, einfach vorbeischauen. Wer mag, <a href="kontakt.html">meldet sich vorher kurz</a>.</li>
        </ul>
      </div>

      <div class="neu-card">
        <h3>Was erwartet dich?</h3>
        <ul>
          <li><strong>Hobbyspieler &amp; Einsteiger:</strong> zwanglos freie Partien, ohne Turnierdruck</li>
          <li><strong>Kinder &amp; Jugendliche:</strong> strukturiertes Jugendtraining für alle Alters- und Spielklassen (<a href="jugend.html">mehr zur Jugend</a>)</li>
          <li><strong>Mannschaftsschach:</strong> Teams von der E-Klasse bis zur Bezirksliga, für jedes Spielniveau</li>
        </ul>
        <a href="mannschaften.html">Unsere Teams →</a>
      </div>

      <div class="neu-card">
        <h3>Was kostet es?</h3>
        <ul>{beitraege}</ul>
        <p>Schnuppern kostet nichts.</p>
      </div>

      <div class="neu-card">
        <h3>Mitglied werden</h3>
        <p>Gefällt es dir bei uns? <a href="#mitglied">Mitgliedsantrag weiter unten →</a></p>
        <p style="margin-top:0.8rem;">Fragen vorab? <a href="kontakt.html">Schreib uns über die Kontaktseite →</a></p>
      </div>
    </div>
    """
    styles = """<style>
      .neu-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.2rem; margin-top: 1.5rem; }
      .neu-card { background: #f8f9fa; border-top: 4px solid #27ae60; border-radius: 6px; padding: 1.2rem 1.4rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .neu-card h3 { margin-top: 0; }
      .neu-card ul { padding-left: 1.2rem; }
      .neu-card a { color: #3498db; font-weight: bold; text-decoration: none; }
    </style>"""
    return content, styles


def build_ueber_uns():
    """Über uns + Neu hier auf einer Seite. Text aus seiten/ueber-uns.html; an der Stelle <!-- NEU_HIER -->
    kommt der Abschnitt „Neu hier?". neu-hier.html leitet auf den Abschnitt weiter."""
    with open(os.path.join("seiten", "ueber-uns.html"), "r", encoding="utf-8") as f:
        raw = f.read()
    style_re = r'<style[^>]*>.*?</style>'
    styles = "".join(re.findall(style_re, raw, re.DOTALL))
    text = re.sub(style_re, '', raw, flags=re.DOTALL).strip()
    neu, neu_styles = neu_hier_html()
    text = text.replace("<!-- NEU_HIER -->", neu) if "<!-- NEU_HIER -->" in text else text + neu
    render_page("Über uns", text, "ueber-uns.html", extra_styles=styles + neu_styles,
                description="Über die SG Aschheim/Feldkirchen/Kirchheim: wer wir sind, wann und wo wir spielen, "
                            "wie du vorbeikommst und Mitglied wirst.")
    weiterleitung("neu-hier.html", "ueber-uns.html#neu-hier")


# ==========================================
# 3. OBERLANDQUARTETT PARSER
# ==========================================
OQ_NEUESTE_OBEN = True     # True = neuestes Turnier oben
OQ_VORSCHAU_JAHRE = 4      # so viele kommende Jahre mit Ausrichter anzeigen (0 = aus)
OQ_AUSRICHTER_FEST = {}    # Abweichungen von der Reihum-Folge, z.B. {2028: "Holzkirchen"}
# Diashow unter der Übersicht: alle Bilder aus diesem Ordner (alphabetisch).
# Bildunterschrift = Dateiname, z. B. "2015 Siegermannschaft.jpg" -> "2015 Siegermannschaft".
# Nummern zum Sortieren wie "01-" oder "01_" werden weggelassen. Jedes Bild wird ganz gezeigt (nichts abgeschnitten).
OQ_DIASHOW = os.path.join("turniere", "oberlandquartett", "diashow")
OQ_DIASHOW_SEKUNDEN = 6    # Wechsel alle x Sekunden (0 = nur mit Pfeilen)
OQ_POKAL_SERIE, OQ_POKAL_GESAMT = 3, 5   # Pokal: 3x hintereinander oder 5x insgesamt (seit dem letzten Pokal)


def compute_pokal_wins(teams_count, data_list, mit_stand=False):
    streak = [0] * teams_count
    total = [0] * teams_count
    wins = []

    for i, entry in enumerate(data_list):
        results = entry[2]
        for j, val in enumerate(results):
            if isinstance(val, int) and val == 1:
                streak[j] += 1
                total[j] += 1
            else:
                streak[j] = 0

        for j in range(teams_count):
            if streak[j] >= OQ_POKAL_SERIE or total[j] >= OQ_POKAL_GESAMT:
                wins.append((i, j))
                streak = [0] * teams_count
                total = [0] * teams_count

    return (wins, streak, total) if mit_stand else wins


def _oq_daten(code):
    """[(jahr, datum, ausrichter, [ergebnisse])] aus main.typ; das Jahr steht im Kommentar darüber (// 2019)."""
    block = re.search(r'#let\s+data\s*=\s*\((.*?)\n\s*\)', code, re.DOTALL)
    daten, jahr, notiz = [], None, ""
    for zeile in (block.group(1).splitlines() if block else []):
        k = re.match(r'\s*//\s*(\d{4})\s*(.*)', zeile)
        if k:
            jahr, notiz = int(k.group(1)), k.group(2).strip(" ()")
            continue
        m = re.match(r'\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*\((.*)\)\s*\)\s*,?\s*$', zeile)
        if not m:
            continue
        werte = []
        for teil in re.findall(r'"[^"]*"|[^,\s]+', m.group(3)):
            teil = teil.strip('"')
            werte.append(int(teil) if teil.isdigit() else teil)
        if jahr is None and re.search(r"\d{4}$", m.group(1)):
            jahr = int(m.group(1)[-4:])
        daten.append((jahr, m.group(1), m.group(2), werte, notiz))
        jahr, notiz = None, ""
    return daten


def _oq_vorschau(zeilen, anzahl):
    """[(jahr, ausrichter)] für die kommenden Jahre. Die Ausrichter wechseln reihum
    (Folge = die letzten verschiedenen Ausrichter); ausgefallene Jahre zählen nicht."""
    gespielt = [(j, a.strip()) for j, _, a, _, _ in zeilen if j and a.strip("-? ")]
    if not anzahl or not gespielt:
        return []
    folge = []
    for _, a in reversed(gespielt):
        if a in folge:
            break
        folge.insert(0, a)
    letztes_jahr = max(j for j, *_ in zeilen if j)
    k = len(folge) - 1   # Position des letzten Ausrichters in der Folge
    vorschau = []
    for jahr in range(letztes_jahr + 1, letztes_jahr + 1 + anzahl):
        k = (k + 1) % len(folge)
        vorschau.append((jahr, OQ_AUSRICHTER_FEST.get(jahr, folge[k])))
    return vorschau


def oq_diashow_html():
    if not os.path.isdir(OQ_DIASHOW):
        return ""
    namen = sorted(n for n in os.listdir(OQ_DIASHOW)
                   if os.path.splitext(n)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if not namen:
        return ""
    esc = htmllib.escape
    bilder = []
    for i, n in enumerate(namen):
        t = re.sub(r"^\d{1,2}[-_]+", "", os.path.splitext(n)[0]).replace("_", " ").strip()
        url = "/".join(quote(x) for x in OQ_DIASHOW.split(os.sep)) + "/" + quote(n)
        bilder.append(f'<figure{" class=an" if i == 0 else ""}><span class="oq-bg" style="background-image:url(\'{url}\')"></span>'
                      f'<img src="{url}" alt="{esc(t)}"{"" if i == 0 else " loading=lazy"}>'
                      f'<figcaption>{esc(t)}</figcaption></figure>')
    knoepfe = ('<div class="oq-show-steuer"><button type="button" class="oq-z" aria-label="Zurück">←</button>'
               f'<span class="oq-nr">1 / {len(namen)}</span>'
               '<button type="button" class="oq-v" aria-label="Weiter">→</button></div>') if len(namen) > 1 else ""
    # Fester Rahmen (Seitenverhältnis 3:2): jedes Foto steht vollständig darin, der Rand wird mit einer
    # unscharfen, abgedunkelten Kopie desselben Fotos gefüllt -> gleiche Höhe, nichts springt, nichts abgeschnitten.
    return f"""<div class="oq-show" data-ms="{OQ_DIASHOW_SEKUNDEN * 1000}"><div class="oq-show-bilder">{"".join(bilder)}</div>{knoepfe}</div>
<style>
  .oq-show {{ position: relative; margin: 1.5rem 0 2rem; max-width: 900px; aspect-ratio: 3 / 2; max-height: 520px;
    border-radius: 12px; overflow: hidden; background: #0a0f1a; }}
  .oq-show-bilder, .oq-show figure {{ position: absolute; inset: 0; margin: 0; }}
  .oq-show figure {{ opacity: 0; transition: opacity 1.2s ease; pointer-events: none; }}
  .oq-show figure.an {{ opacity: 1; pointer-events: auto; }}
  .oq-bg {{ position: absolute; inset: -30px; background: center / cover no-repeat; filter: blur(26px) brightness(.45) saturate(1.2); }}
  .oq-show img {{ position: relative; display: block; width: 100%; height: 100%; object-fit: contain; }}
  .oq-show figcaption {{ position: absolute; left: 0; right: 0; bottom: 0; padding: 2.2rem 1rem .75rem; font-size: .92rem; font-weight: 600;
    color: #fff; background: linear-gradient(transparent, rgba(0, 0, 0, .65)); }}
  .oq-show-steuer {{ position: absolute; right: .7rem; bottom: .6rem; display: flex; align-items: center; gap: .45rem; z-index: 2; }}
  .oq-show-steuer button {{ width: 2.2rem; height: 2.2rem; border-radius: 50%; border: 0; background: rgba(0, 0, 0, .45);
    color: #fff; cursor: pointer; font-size: 1rem; backdrop-filter: blur(4px); }}
  .oq-show-steuer button:hover {{ background: rgba(0, 0, 0, .7); }}
  .oq-nr {{ font-size: .85rem; color: #fff; font-variant-numeric: tabular-nums; text-shadow: 0 1px 3px #000; }}
  @media (max-width: 600px) {{ .oq-show {{ aspect-ratio: 4 / 3; border-radius: 10px; }} }}
  @media (prefers-reduced-motion: reduce) {{ .oq-show figure {{ transition: none; }} }}
</style>
<script>
(function () {{
  var s = document.querySelector(".oq-show"); if (!s) return;
  var f = s.querySelectorAll("figure"), i = 0, t = null, ms = +s.dataset.ms, nr = s.querySelector(".oq-nr");
  if (f.length < 2) return;
  function geh(n) {{ f[i].classList.remove("an"); i = (n + f.length) % f.length; f[i].classList.add("an"); nr.textContent = (i + 1) + " / " + f.length; }}
  function start() {{ stop(); if (ms && !matchMedia("(prefers-reduced-motion: reduce)").matches) t = setInterval(function () {{ geh(i + 1); }}, ms); }}
  function stop() {{ if (t) clearInterval(t); t = null; }}
  s.querySelector(".oq-v").onclick = function () {{ geh(i + 1); start(); }};
  s.querySelector(".oq-z").onclick = function () {{ geh(i - 1); start(); }};
  var x0 = null;                                            // Wischen am Handy
  s.addEventListener("touchstart", function (e) {{ x0 = e.touches[0].clientX; }}, {{ passive: true }});
  s.addEventListener("touchend", function (e) {{ if (x0 === null) return; var d = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(d) > 40) {{ geh(i + (d < 0 ? 1 : -1)); start(); }} }});
  s.addEventListener("mouseenter", stop); s.addEventListener("mouseleave", start); start();
}})();
</script>"""


def build_oberlandquartett():
    path = os.path.join("turniere", "oberlandquartett", "main.typ")
    if not os.path.exists(path):
        path = os.path.join("turniere", "oberlandquartett.typ")

    html = ['<a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>',
            '<h1 style="margin-top:1rem;">Oberlandquartett</h1>']
    if not os.path.exists(path):
        html.append("<p>Keine Daten für Oberlandquartett gefunden.</p>")
    else:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        teams_m = re.search(r'#let\s+teams\s*=\s*\((.*?)\)', code, re.DOTALL)
        teams = [t.strip().strip('"\'') for t in teams_m.group(1).split(',') if t.strip()] if teams_m else []
        zeilen = _oq_daten(code)
        n = len(teams)
        pokale, serie, gesamt = compute_pokal_wins(n, [(d, a, w) for _, d, a, w, _ in zeilen], mit_stand=True)
        pokal_set = set(pokale)
        esc = htmllib.escape

        # Übersicht je Mannschaft: Turniersiege, Pokale, Stand zum nächsten Pokal
        karten = []
        for j, t in enumerate(teams):
            siege = sum(1 for z in zeilen if j < len(z[3]) and z[3][j] == 1)
            anz_pokale = sum(1 for _, jj in pokale if jj == j)
            stand = []
            if serie[j]:
                stand.append(f"{serie[j]}× in Folge")
            if gesamt[j]:
                stand.append(f"{gesamt[j]}/{OQ_POKAL_GESAMT} Siege")
            karten.append(
                f'<li><span class="oq-team">{esc(t)}</span>'
                f'<span class="oq-zahlen"><b>{siege}</b> Turniersiege · <b>{anz_pokale}</b> {"Pokal" if anz_pokale == 1 else "Pokale"}</span>'
                f'<span class="oq-stand">{"Zum nächsten Pokal: " + ", ".join(stand) if stand else "Zum nächsten Pokal: noch kein Sieg"}</span></li>')
        html.append(f'<ul class="oq-karten">{"".join(karten)}</ul>')
        html.append(oq_diashow_html())

        kopf = "".join(f"<th>{esc(t)}</th>" for t in teams)
        reihen, kommend = [], []
        for jahr, ort in sorted(_oq_vorschau(zeilen, OQ_VORSCHAU_JAHRE), reverse=OQ_NEUESTE_OBEN):
            kommend.append(f'<tr class="oq-kommend"><td class="oq-jahr">{jahr}</td><td class="oq-ort">{esc(ort)}</td>'
                          f'<td class="oq-plan" colspan="{n}"><span class="oq-plan-ort">Ausrichter: {esc(ort)}</span></td></tr>')
        reihenfolge = list(enumerate(zeilen))
        if OQ_NEUESTE_OBEN:
            reihenfolge.reverse()
        for i, (jahr, datum, ausrichter, werte, notiz) in reihenfolge:
            ausgefallen = all(not isinstance(v, int) for v in werte)
            jahr_txt = esc(str(jahr)) if jahr else "?"
            datum_txt = datum if re.match(r"\d", datum) else ""
            zellen = [f'<td class="oq-jahr">{jahr_txt}<small>{esc(datum_txt[:6]) if datum_txt else ""}</small></td>',
                      f'<td class="oq-ort">{esc(ausrichter) if ausrichter.strip("-? ") else ""}</td>']
            if ausgefallen:
                text = notiz or "nicht ausgetragen"
                zellen.append(f'<td class="oq-aus" colspan="{n}">{esc(text)}</td>')
            else:
                for j, v in enumerate(werte):
                    if (i, j) in pokal_set:
                        zellen.append('<td><span class="oq-platz oq-p1 oq-pokal" title="Turniersieg und Pokalgewinn">🏆 1</span></td>')
                    elif v == 1:
                        zellen.append('<td><span class="oq-platz oq-p1" title="Turniersieg">1</span></td>')
                    elif isinstance(v, int):
                        zellen.append(f'<td><span class="oq-platz">{v}</span></td>')
                    elif str(v).strip("- "):
                        zellen.append(f'<td class="oq-ersatz" title="Ersatzmannschaft">{esc(str(v))}</td>')
                    else:
                        zellen.append('<td class="oq-leer">–</td>')
            reihen.append(f'<tr{" class=oq-ausfall" if ausgefallen else ""}>{"".join(zellen)}</tr>')
        reihen = kommend + reihen if OQ_NEUESTE_OBEN else reihen + kommend   # kommende Jahre vor/nach den Ergebnissen

        html.append(f'<div class="oq-scroll"><table class="oq-tab"><thead><tr><th class="oq-jahr">Jahr</th>'
                    f'<th class="oq-ort">Ausrichter</th>{kopf}</tr></thead><tbody>{"".join(reihen)}</tbody></table></div>')
        html.append('<p class="oq-legende2"><span class="oq-platz oq-p1">1</span> Turniersieg '
                    '<span class="oq-platz oq-p1 oq-pokal">🏆 1</span> Pokalgewinn</p>')
        html.append(f'<p class="klein">Den Pokal gewinnt die Mannschaft, die entweder {OQ_POKAL_SERIE}x hintereinander gewinnt '
                    f'oder insgesamt {OQ_POKAL_GESAMT}x.<br>Nach dem Pokalgewinn beginnt die Zählung von vorne! '
                    'Der Gewinner spendiert den neuen Pokal.</p>')

    styles = """<style>
      .klein { font-size: 0.85rem; color: var(--muted); font-style: italic; }
      .oq-karten { list-style: none; padding: 0; margin: 1.2rem 0 1.4rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(220px, 42vw), 1fr)); gap: 0.6rem; }
      .oq-karten li { display: flex; flex-direction: column; gap: 0.15rem; padding: 0.7rem 0.9rem; border-radius: 10px; background: var(--soft, #f3f5f9); border: 1px solid var(--border, #e3e7ee); }
      .oq-team { font-weight: 800; font-size: 1.05rem; }
      .oq-fotos { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.8rem; margin: 0 0 1.4rem; }
      .oq-fotos figure { margin: 0; }
      .oq-fotos img { width: 100%; max-width: 720px; height: auto; border-radius: 10px; display: block; }
      .oq-fotos figcaption { font-size: 0.85rem; margin-top: 0.35rem; color: color-mix(in srgb, var(--text, #000) 70%, transparent); }
      .oq-zahlen { font-size: 0.9rem; }
      .oq-stand { font-size: 0.8rem; color: color-mix(in srgb, var(--text, #000) 65%, transparent); }
      .oq-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 10px; border: 1px solid var(--border, #d6dbe4); }
      .oq-tab { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: var(--surface, #fff); color: var(--text, inherit); }
      .oq-tab th, .oq-tab td { padding: 0.5rem 0.65rem; text-align: center; border-bottom: 1px solid var(--border, #e3e7ee); white-space: nowrap; }
      .oq-tab thead th { background: var(--accent, #1c2d52); color: #fff; font-weight: 700; }
      .oq-tab .oq-jahr, .oq-tab .oq-ort { text-align: left; }
      .oq-tab td.oq-jahr { font-weight: 700; font-variant-numeric: tabular-nums; }
      .oq-tab td.oq-jahr small { display: inline-block; margin-left: 0.5rem; font-weight: normal; font-size: 0.78rem; color: color-mix(in srgb, var(--text, #000) 55%, transparent); }
      .oq-tab tbody tr:nth-child(even) > * { background-color: var(--soft, #f5f7fa); }
      .oq-tab tbody tr:hover > * { background-color: color-mix(in srgb, var(--text, #000) 9%, var(--surface, #fff)); }
      .oq-platz { display: inline-block; min-width: 2em; padding: 0.1rem 0.45rem; border-radius: 6px; font-variant-numeric: tabular-nums; color: color-mix(in srgb, var(--text, #000) 70%, transparent); }
      .oq-platz.oq-p1 { background: var(--oq-sieg, #ffd54a); color: #1b2a4a; font-weight: 800; }
      .oq-platz.oq-pokal { box-shadow: 0 0 0 2px var(--surface, #fff), 0 0 0 4px var(--oq-sieg, #ffd54a); }
      .oq-tab .oq-leer { color: color-mix(in srgb, var(--text, #000) 30%, transparent); }
      .oq-tab .oq-ersatz { font-size: 0.82rem; font-style: italic; color: color-mix(in srgb, var(--text, #000) 60%, transparent); }
      .oq-tab td.oq-aus { font-style: italic; color: color-mix(in srgb, var(--text, #000) 50%, transparent);
                          background-image: repeating-linear-gradient(135deg, transparent 0 6px, color-mix(in srgb, var(--text, #000) 6%, transparent) 6px 12px); }
      .oq-tab tr.oq-kommend > * { color: color-mix(in srgb, var(--text, #000) 55%, transparent); font-style: italic; }
      .oq-tab tr.oq-kommend td.oq-jahr { font-weight: 600; }
      .oq-tab tr.oq-kommend + tr:not(.oq-kommend) > *, .oq-tab tr:not(.oq-kommend) + tr.oq-kommend > * { border-top: 2px solid var(--line, #d6dbe4); }
      .oq-tab td.oq-plan { font-size: 0.85rem; }
      .oq-tab .oq-plan-ort { display: none; }
      .oq-legende2 { font-size: 0.85rem; margin-top: 0.8rem; display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
      .oq-legende2 .oq-platz.oq-pokal { margin-left: 1rem; }
      @media (max-width: 700px) {
        .oq-tab { font-size: 0.85rem; } .oq-tab th, .oq-tab td { padding: 0.4rem 0.4rem; }
        .oq-tab td.oq-jahr small, .oq-tab .oq-ort { display: none; }
        .oq-tab .oq-plan-ort { display: inline; }
      }
    </style>"""

    render_page("Oberlandquartett", "\n".join(html), "oberlandquartett.html", extra_styles=styles)


# ==========================================
# 4. BLITZJAHRESWERTUNG PARSER
# ==========================================
BLITZ_MAX_WIDTH = "1200px"   # maximale Breite der Wertungs-Tabellen (darf breiter sein als der Textbereich)


def _page_no(path):
    m = re.search(r'(\d+)\.svg$', path)
    return int(m.group(1)) if m else 0


def _uniq_svg_ids(svg, prefix):
    """Macht IDs in einer SVG eindeutig, damit mehrere SVGs auf einer Seite sich nicht stören."""
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', svg)
    svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}{m.group(1)}"', svg)
    svg = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{prefix}{m.group(1)})', svg)
    return svg


BLITZ_PDF = "blitzjahreswertung.pdf"   # PDF zum Herunterladen (liegt im Website-Root)


def _blitz_turnier_namen(code):
    """Namen der gespielten Turniere aus der Liste `#let turniere = (...)` in main.typ
    (Reihenfolge = Seitenreihenfolge; Kommentare und `gespielt: false` werden ignoriert)."""
    code = re.sub(r'(?m)^\s*//.*$', '', code)
    namen = []
    for zeile in re.findall(r'\(name:\s*"[^"]+"[^\n]*', code):
        if re.search(r'gespielt:\s*false', zeile):
            continue
        namen.append(re.search(r'name:\s*"([^"]+)"', zeile).group(1))
    return namen


BLITZ_ARCHIV = os.path.join("turniere", "blitzjahreswertung", "archiv")   # abgeschlossene Jahre: archiv/<Jahr>/


def _blitz_jahr(code):
    m = re.search(r"Blitzjahreswertung\s+(\d{4})", code or "")
    return int(m.group(1)) if m else None


def build_blitzjahreswertung():
    """Aktuelles Jahr -> blitzjahreswertung.html, abgeschlossene Jahre (archiv/<Jahr>/, angelegt vom
    Jahresabschluss im Programm BlitzJahresWertung) -> blitzjahreswertung-<Jahr>.html, mit Jahresleiste."""
    ordner = os.path.join("turniere", "blitzjahreswertung")
    aktuell = None
    if os.path.exists(os.path.join(ordner, "main.typ")):
        with open(os.path.join(ordner, "main.typ"), encoding="utf-8") as f:
            aktuell = _blitz_jahr(f.read())
    archiv = sorted((int(os.path.basename(p)) for p in glob.glob(os.path.join(BLITZ_ARCHIV, "*"))
                     if os.path.basename(p).isdigit() and os.path.exists(os.path.join(p, "main.typ"))), reverse=True)
    seiten = [(aktuell, ordner, "blitzjahreswertung.html", BLITZ_PDF)] + [
        (j, os.path.join(BLITZ_ARCHIV, str(j)), f"blitzjahreswertung-{j}.html", f"blitzjahreswertung-{j}.pdf")
        for j in archiv if j != aktuell]
    leiste = [(str(j or "aktuell"), datei) for j, _, datei, _ in seiten]
    for j, pfad, datei, pdf in seiten:
        ACTIVE_PARENT.setdefault(datei, "turniere.html")
        _blitz_seite(pfad, datei, pdf, j, leiste, archiviert=pfad != ordner)


# Blitzjahreswertung als echte HTML-Tabelle (passt sich hell/dunkel und dem Handy an).
# Die Wertung rechnet weiterhin Typst (Technik/wertung.typ); build_site.py holt sich nur das Ergebnis
# per "typst query" als JSON. Klappt das nicht (kein Typst, altes Archiv), bleibt es bei den SVG-Bildern.
BLITZ_HTML = True              # False = wie früher: Typst-Bilder (SVG) statt HTML-Tabelle
BLITZ_MEDAILLEN = True         # Plätze 1-3 farbig markieren

BLITZ_DATEN_TYP = """#import "main.typ": turniere
#import "database.typ": mitglieder
#import "Technik/wertung.typ": berechne-jahreswertung, turnier-rangliste, ist-gespielt
#import "Technik/links.typ": stand
#metadata((
  wertung: berechne-jahreswertung(turniere, mitglieder,
    beste: int(sys.inputs.at("beste", default: "3")), sieg-punkte: int(sys.inputs.at("sieg", default: "20"))),
  turniere: turniere.map(t => (name: t.name, url: t.at("url", default: none), gespielt: ist-gespielt(t),
    rangliste: if ist-gespielt(t) { turnier-rangliste(t.daten, mitglieder) } else { () })),
  stand: stand,
)) <bjw-daten>
"""


def _blitz_daten(folder_path, code):
    """Fertig berechnete Wertung aus Typst (dict) oder None."""
    if not BLITZ_HTML or not code:
        return None
    beste = re.search(r"\bbeste:\s*(\d+)", code)
    sieg = re.search(r"\bsieg-punkte:\s*(\d+)", code)
    beste, sieg = (beste.group(1) if beste else "3"), (sieg.group(1) if sieg else "20")
    hilfe = os.path.join(folder_path, "_web_daten.typ")
    try:
        with open(hilfe, "w", encoding="utf-8") as f:
            f.write(BLITZ_DATEN_TYP)
        r = subprocess.run(["typst", "query", hilfe, "<bjw-daten>", "--field", "value", "--one",
                            "--input", f"beste={beste}", "--input", f"sieg={sieg}"],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"Blitzjahreswertung: HTML-Tabelle nicht möglich, nehme SVG ({r.stderr.strip()[:200]})")
            return None
        daten = json.loads(r.stdout)
        daten["beste"], daten["sieg"] = int(beste), int(sieg)
        return daten
    except Exception as e:
        print(f"Blitzjahreswertung: HTML-Tabelle nicht möglich, nehme SVG ({e})")
        return None
    finally:
        if os.path.exists(hilfe):
            os.remove(hilfe)


def _bw_turnier_kopf(t):
    name = htmllib.escape(t["name"])
    if not t["gespielt"]:
        return f'<th class="bw-offen">{name}<small>ausstehend</small></th>'
    if t.get("url"):
        return (f'<th><a href="{htmllib.escape(t["url"])}" target="_blank" rel="noopener" '
                f'title="Ergebnisse bei chess-results">{name}</a></th>')
    return f"<th>{name}</th>"


def _bw_platz(rang):
    klasse = f' class="bw-p{rang}"' if BLITZ_MEDAILLEN and rang <= 3 else ""
    return f"<td{klasse}>{rang}</td>"


def _bw_gesamt_html(d):
    w, turniere = d["wertung"], d["turniere"]
    mit_max = w["offen"] > 0
    kopf = "".join(_bw_turnier_kopf(t) for t in turniere)
    kopf = (f'<tr><th>Pl.</th><th class="bw-name">Spieler</th>{kopf}<th>Teiln.</th><th>Gesamt</th>'
            + ('<th title="höchstmögliche Endpunktzahl">Max.</th>' if mit_max else "") + "</tr>")
    zeilen = []
    for s in w["spieler"]:
        zellen = [_bw_platz(s["rang"]), f'<td class="bw-name">{htmllib.escape(s["name"])}</td>']
        for i, p in enumerate(s["einzel"]):
            if not turniere[i]["gespielt"]:
                zellen.append('<td class="bw-offen"></td>')
            elif p is None:
                zellen.append('<td class="bw-leer">–</td>')
            elif i in s["gewertet"]:
                zellen.append(f'<td><span class="bw-punkte">{p}</span></td>')
            else:
                zellen.append(f'<td class="bw-streich" title="gestrichen"><s>{p}</s></td>')
        zellen.append(f'<td class="bw-teiln">{s["teilnahmen"]}/{w["gespielt"]}</td>')
        zellen.append(f'<td class="bw-summe">{s["summe"]}</td>')
        if mit_max:
            zellen.append(f'<td class="bw-max{" bw-chance" if s["titelchance"] else ""}">{s["maximal"]}</td>')
        zeilen.append("<tr>" + "".join(zellen) + "</tr>")

    stand = f'Stand: {htmllib.escape(str(d["stand"]))} · ' if d.get("stand") else ""
    legende = (f'{stand}nach {w["gespielt"]} von {w["gesamt"]} Turnieren. '
               f'Es zählen die besten {d["beste"]} Ergebnisse (<span class="bw-punkte">grün</span>), '
               f'gestrichene sind <s>durchgestrichen</s>, – = nicht teilgenommen.')
    if mit_max:
        legende += f' Max. = höchstmögliche Endpunktzahl mit {d["sieg"]} Punkten in jedem offenen Turnier.'
        kandidaten = sorted((s for s in w["spieler"] if s["titelchance"]), key=lambda s: -s["maximal"])
        if kandidaten:
            legende += ("<br><strong>Titel noch möglich:</strong> "
                        + ", ".join(f'{htmllib.escape(s["name"])} (max. {s["maximal"]})' for s in kandidaten))
    return (f'<div class="bw-scroll"><table class="bw-tab"><thead>{kopf}</thead><tbody>{"".join(zeilen)}</tbody></table></div>'
            f'<p class="bw-legende">{legende}</p>')


def _bw_turnier_html(t):
    zeilen = "".join(f'<tr>{_bw_platz(s["platz"])}<td class="bw-name">{htmllib.escape(s["name"])}</td>'
                     f'<td>{"<span class=bw-punkte>" + str(s["punkte"]) + "</span>" if s["punkte"] else s["punkte"]}</td></tr>'
                     for s in t["rangliste"])
    link = (f'<p class="bw-legende"><a href="{htmllib.escape(t["url"])}" target="_blank" rel="noopener">'
            f'Vollständige Ergebnisse bei chess-results ↗</a></p>' if t.get("url") else "")
    return (f'<div class="bw-scroll"><table class="bw-tab bw-einzel"><thead><tr><th>Pl.</th><th class="bw-name">Spieler</th>'
            f'<th>Punkte</th></tr></thead><tbody>{zeilen}</tbody></table></div>{link}')


def _bw_html_gruppen(d):
    """[(Reitername, HTML)] – Gesamt + jedes gespielte Turnier."""
    return [("Gesamt", _bw_gesamt_html(d))] + [(t["name"], _bw_turnier_html(t)) for t in d["turniere"] if t["gespielt"]]


BLITZ_HTML_CSS = """
      .bw-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 10px; border: 1px solid var(--border, #d6dbe4); }
      .bw-tab { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: var(--surface, #fff); color: var(--text, inherit); }
      .bw-tab th, .bw-tab td { padding: 0.5rem 0.65rem; text-align: center; border-bottom: 1px solid var(--border, #e3e7ee); white-space: nowrap; }
      .bw-tab thead th { background: var(--accent, #1c2d52); color: #fff; font-weight: 700; }
      .bw-tab thead th a { color: #fff; text-decoration: none; border-bottom: 1px dotted rgba(255,255,255,0.6); }
      .bw-tab thead th a:hover { border-bottom-style: solid; }
      .bw-tab .bw-name { text-align: left; font-weight: 600; }
      .bw-tab tbody tr:nth-child(even) > * { background: var(--soft, #f5f7fa); }
      .bw-tab tbody tr:hover > * { background: color-mix(in srgb, var(--text, #000) 9%, var(--surface, #fff)); }
      .bw-punkte { display: inline-block; min-width: 2.2em; padding: 0.1rem 0.4rem; border-radius: 6px; background: #3f7d4a; color: #fff; font-weight: 700; }
      .bw-tab .bw-streich { color: color-mix(in srgb, var(--text, #000) 45%, transparent); }
      .bw-tab .bw-leer { color: color-mix(in srgb, var(--text, #000) 30%, transparent); }
      .bw-tab th.bw-offen { background: color-mix(in srgb, var(--accent, #1c2d52) 45%, #888); font-weight: 600; }
      .bw-tab th.bw-offen small { display: block; font-weight: normal; font-size: 0.72rem; opacity: 0.85; }
      .bw-tab tbody td.bw-offen { background: repeating-linear-gradient(135deg, transparent 0 6px, color-mix(in srgb, var(--text, #000) 6%, transparent) 6px 12px); }
      .bw-tab .bw-teiln { color: color-mix(in srgb, var(--text, #000) 70%, transparent); font-variant-numeric: tabular-nums; }
      .bw-tab tbody .bw-summe { font-weight: 800; font-size: 1.05rem; background: color-mix(in srgb, var(--accent, #1c2d52) 14%, var(--surface, #fff)); }
      .bw-tab .bw-max { color: color-mix(in srgb, var(--text, #000) 40%, transparent); }
      .bw-tab .bw-max.bw-chance { color: inherit; font-weight: 700; }
      .bw-tab td.bw-p1, .bw-tab td.bw-p2, .bw-tab td.bw-p3 { font-weight: 800; box-shadow: inset 4px 0 0 var(--medaille); }
      .bw-tab td.bw-p1 { --medaille: #d4a017; } .bw-tab td.bw-p2 { --medaille: #a8b0bd; } .bw-tab td.bw-p3 { --medaille: #b87333; }
      .bw-einzel { max-width: 32rem; }
      .bw-scroll:has(.bw-einzel) { max-width: 32rem; margin: 0 auto; }
      .bw-legende { font-size: 0.85rem; text-align: left; margin-top: 0.7rem; color: color-mix(in srgb, var(--text, #000) 80%, transparent); line-height: 1.6; }
      .bw-legende .bw-punkte { min-width: 0; padding: 0 0.35rem; }
      @media (max-width: 700px) {
        .bw-tab { font-size: 0.85rem; } .bw-tab th, .bw-tab td { padding: 0.4rem 0.45rem; }
        /* Handy: Namensspalte bleibt beim seitlichen Wischen stehen */
        .bw-tab .bw-name { position: sticky; left: 0; z-index: 1; background: var(--surface, #fff); box-shadow: 1px 0 0 var(--border, #e3e7ee); }
        .bw-tab thead th.bw-name { background: var(--accent, #1c2d52); }
        .bw-tab tbody tr:nth-child(even) > td.bw-name { background: var(--soft, #f5f7fa); }
      }
"""


def _blitz_seite(folder_path, html_datei, blitz_pdf, jahr, leiste, archiviert=False):
    main_typ = os.path.join(folder_path, "main.typ")
    tmp_dir = os.path.join(folder_path, "_tmp")

    code = ""
    if os.path.exists(main_typ):
        with open(main_typ, "r", encoding="utf-8") as f:
            code = f.read()

    # 0. Wertung als Daten aus Typst holen -> HTML-Tabelle (sonst None -> SVG-Bilder wie früher)
    daten = _blitz_daten(folder_path, code)

    # 1. SVG (Webansicht, nur noch als Ersatz) und PDF (A4) kompilieren.
    #    Klappt das nicht (z. B. kein Typst installiert), bleiben die alten Dateien erhalten.
    if code:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            if not daten:
                subprocess.run(["typst", "compile", "--input", "format=web", main_typ,
                                os.path.join(tmp_dir, "output-{p}.svg")], check=True)
            new_pages = glob.glob(os.path.join(tmp_dir, "output-*.svg"))
            if new_pages:
                for old in glob.glob(os.path.join(folder_path, "output*.svg")):
                    os.remove(old)
                for p in new_pages:
                    shutil.move(p, os.path.join(folder_path, os.path.basename(p)))
            subprocess.run(["typst", "compile", main_typ, blitz_pdf], check=True)
        except Exception as e:
            print(f"Typst Compiling Hinweis: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 2. SVG-Seiten einlesen (IDs eindeutig machen, sonst stören sich die Seiten gegenseitig)
    svg_files = sorted(glob.glob(os.path.join(folder_path, "output*.svg")), key=_page_no)
    pages = []
    for i, p in enumerate(svg_files):
        with open(p, "r", encoding="utf-8") as f:
            pages.append(f'<div class="svg-container">{_uniq_svg_ids(f.read(), f"p{i}-")}</div>')

    # 3. Seiten gruppieren: die letzten k Seiten sind die Einzelturniere, alles davor die Gesamtwertung
    names = _blitz_turnier_namen(code)
    n, k = len(pages), len(names)
    if daten:
        groups = [(label, [inhalt]) for label, inhalt in _bw_html_gruppen(daten)]
        pages = pages or ["html"]   # nur damit unten nicht die Notlösung greift
    elif k and n > k:
        groups = [("Gesamt", pages[:n - k])] + [(names[i], [pages[n - k + i]]) for i in range(k)]
    else:
        groups = [("Wertung", pages)]

    tab_css = ""
    if not pages and code:   # Notlösung ohne SVG: HTML-Tabelle aus dem Typst-Code
        table_content = f'<table class="custom-tabelle">{parse_typst_table_to_html(code)}</table>'
    elif not pages:
        table_content = "<p>Keine Daten für die Blitzjahreswertung vorhanden.</p>"
    elif len(groups) == 1:
        table_content = "".join(groups[0][1])
    else:
        g = len(groups)
        inputs = "".join(f'<input type="radio" name="bw" id="bw{i}"{" checked" if i == 0 else ""}>' for i in range(g))
        labels = "".join(f'<label for="bw{i}">{htmllib.escape(label)}</label>' for i, (label, _) in enumerate(groups))
        panels = "".join(f'<div class="tab-panel" id="bwp{i}">{"".join(files)}</div>' for i, (_, files) in enumerate(groups))
        table_content = f'<div class="tabs">{inputs}<div class="tab-bar">{labels}</div>{panels}</div>'

        active = ",".join(f"#bw{i}:checked ~ .tab-bar label[for=bw{i}]" for i in range(g))
        show = ",".join(f"#bw{i}:checked ~ #bwp{i}" for i in range(g))
        tab_css = ("""
      .tabs > input { position: absolute; opacity: 0; pointer-events: none; }
      .tab-bar { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }
      .tab-bar label { cursor: pointer; padding: 0.55rem 1.1rem; border-radius: 999px; background: var(--soft, #e8ecf3); color: var(--text, #0a1f44); border: 1px solid var(--border, transparent); font-weight: bold; }
      .tab-bar label:hover { border-color: var(--accent, #0a1f44); }
      .tab-panel { display: none; }
      """ + active + """ { background: var(--accent, #0a1f44); border-color: var(--accent, #0a1f44); color: #fff; }
      [data-theme="dark"] """ + active.replace(",", ', [data-theme="dark"] ') + """ { background: var(--hell); border-color: var(--hell); color: #0e1524; }
      """ + show + """ { display: block; }""")

    pdf_link = (f'<p><a href="{blitz_pdf}" download>Wertung {jahr or ""} als PDF herunterladen</a></p>'
                if os.path.exists(blitz_pdf) else "")
    jahre = ""
    if len(leiste) > 1:
        aktiv = ' aria-current="page"'
        knoepfe = "".join(f'<a href="{d}"{aktiv if d == html_datei else ""}>{htmllib.escape(t)}</a>'
                          for t, d in leiste)
        jahre = f'<nav class="bw-jahre" aria-label="Jahr">{knoepfe}</nav>'
    hinweis = (f'<p class="bw-archiv">Abgeschlossenes Jahr {jahr}. <a href="blitzjahreswertung.html">Zum aktuellen Jahr →</a></p>'
               if archiviert else "")

    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
        <h1 style="margin-top:1rem;">Blitzjahreswertung {jahr or ""}</h1>
    {jahre}
    {hinweis}
    {pdf_link}
    <div class="bw-wrap">
      {table_content}
    </div>
    """

    styles = """<style>
      .bw-wrap { width: min(96vw, """ + BLITZ_MAX_WIDTH + """); position: relative; left: 50%; transform: translateX(-50%); margin-top: 1.5rem; text-align: center; overflow-x: auto; }
      .svg-container { margin-bottom: 1rem; }
      .svg-container svg { display: block; margin: 0 auto; max-width: 100%; height: auto; background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
      .custom-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }
      .custom-tabelle th, .custom-tabelle td { padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }
      .custom-tabelle th { background-color: #0a1f44; color: white; font-weight: bold; }
      .bw-jahre { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.4rem 0 0.8rem; }
      .bw-jahre a { padding: 0.15rem 0.7rem; border-radius: 999px; border: 1px solid var(--border); text-decoration: none; background: var(--soft); color: var(--navy); }
      .bw-jahre a[aria-current="page"] { background: var(--navy); color: #fff; font-weight: bold; }
      .bw-archiv { padding: 0.5rem 0.8rem; border-left: 4px solid #b9770e; background: #fdf2e0; color: #6e4a07; border-radius: 4px; }""" + tab_css + BLITZ_HTML_CSS + """
    </style>"""

    render_page(f"Blitzjahreswertung {jahr or ''}".strip(), content, html_datei, extra_styles=styles)

# ==========================================
# 5. HALL OF FAME PARSER
# ==========================================
# Hall of Fame: Spalten der Ehrentafel (Reihenfolge = Reihenfolge der Spalten).
# Ein Titel landet in der ersten Spalte, deren Muster im Turniernamen vorkommt (Groß-/Kleinschreibung egal).
# Turniere, die zu keinem Muster passen, bekommen automatisch eine eigene Spalte.
HOF_SPALTEN = [
    ("Vereinsmeister", r"^vereinsmeist"),
    ("Pokal", r"pokal"),
    ("Blitzmeister", r"blitzschach|blitzmeist|blitzserie|blitzjahres"),   # Vereins-Blitzmeister und Sieger der Blitzjahreswertung
    ("Schnellschach", r"schnellschach"),
    ("Weihnachtsblitz", r"weihnacht"),
    ("Stadtmeister", r"stadtmeist"),
    ("Jugend", r"jugend"),
]
HOF_JUGEND_ZUERST = True   # "Jugend-Pokal" usw. zählt zur Jugend, nicht zum Pokal
HOF_TOP = 6                # so viele Spieler stehen oben bei "Meiste Titel"
HOF_DATEIEN = [            # erste vorhandene Datei mit Daten; doppelte Einträge zählen nur einmal
    os.path.join("turniere", "vereinsintern", "main.typ"),
    os.path.join("turniere", "hall_of_fame.typ"),
]

HOF_SKRIPT = """<script>
  document.getElementById("hof-wahl").addEventListener("change", function () {
    var wer = this.value;
    document.querySelectorAll(".hof-tafel td[data-spieler]").forEach(function (td) {
      td.classList.toggle("treffer", !!wer && td.dataset.spieler.split("|").indexOf(wer) >= 0);
    });
    document.querySelector(".hof-tafel").classList.toggle("gefiltert", !!wer);
  });
</script>"""

HOF_CSS = """<style>
      :root { --afk-navy: #1c2d52; }   /* fest, unabhängig von --navy aus style.css */
      .hof-zurueck { text-decoration: none; }
      .hof-top { list-style: none; padding: 0; margin: 0.8rem 0 1.6rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.6rem; counter-reset: platz; }
      .hof-top li { counter-increment: platz; display: flex; align-items: center; gap: 0.7rem; background: var(--soft); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 0.9rem; }
      .hof-top li::before { content: counter(platz) "."; color: #6b7280; font-weight: bold; min-width: 1.4em; }
      .hof-name { flex: 1; font-weight: 600; }
      .hof-zahl { background: var(--afk-navy); color: #fff; border-radius: 999px; min-width: 2em; text-align: center; padding: 0.05rem 0.5rem; font-weight: bold; }
      .hof-filter { margin: 0.4rem 0 0.6rem; }
      .hof-filter select { font: inherit; padding: 0.25rem 0.5rem; border: 1px solid var(--border); border-radius: 6px; }
      .table-responsive { overflow-x: auto; }
      .hof-breit { max-width: 1400px; }   /* breiter als der Textbereich, damit die Namen nicht umbrechen */
      .hof-tafel { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: var(--surface, transparent); color: var(--text, inherit); }
      .hof-tafel th, .hof-tafel td { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
      .hof-tafel th { white-space: nowrap; }
      @media (min-width: 1100px) { .hof-tafel td { white-space: nowrap; } .hof-tafel td.mehrere { white-space: normal; min-width: 9rem; } }
      .hof-tafel thead th { background: var(--accent, var(--afk-navy)); color: #fff; }
      .hof-tafel tbody th { color: inherit; font-weight: bold; font-variant-numeric: tabular-nums; }
      /* Streifen wie bei den anderen Tabellen der Seite (design.css: --soft), passt zu hell und dunkel */
      .hof-tafel tbody tr > * { background: transparent; color: var(--text, inherit); }
      .hof-tafel tbody tr:nth-child(even) > * { background: var(--soft, rgba(128,128,128,.08)); }
      .hof-tafel tbody tr:hover > * { background: color-mix(in srgb, var(--text, currentColor) 10%, transparent); }
      .hof-tafel tbody td.leer { color: color-mix(in srgb, var(--text, currentColor) 35%, transparent); }
      .hof-tafel.gefiltert tbody td[data-spieler] { color: color-mix(in srgb, var(--text, currentColor) 40%, transparent); }
      .hof-tafel.gefiltert tbody td.treffer { color: var(--text, inherit); background: color-mix(in srgb, #4a90d9 30%, transparent); font-weight: bold; }
    </style>"""


def hof_spalte(turnier):
    t = turnier.lower()
    if HOF_JUGEND_ZUERST and "jugend" in t:
        return "Jugend"
    return next((name for name, muster in HOF_SPALTEN if re.search(muster, t)), turnier)


def hof_spieler(text):
    """'Ronny Damaske und Pierre Tassell' -> ['Ronny Damaske', 'Pierre Tassell']"""
    return [n.strip() for n in re.split(r'\s+(?:und|u\.)\s+|\s*&\s*', text) if n.strip()]


def hof_eintraege():
    """Alle Titel aus den Typst-Dateien: [(spieler, turnier, jahr)], doppelte (Turnier, Jahr) nur einmal."""
    gesehen, eintraege = set(), []
    for pfad in HOF_DATEIEN:
        if not os.path.exists(pfad):
            continue
        with open(pfad, "r", encoding="utf-8") as f:
            code = f.read()
        block = re.search(r'#let\s+data\s*=\s*\((.*?)\n\s*\)', code, re.DOTALL)
        if not block:
            continue
        for roh in re.findall(r'\((.*?)\)', block.group(1), re.DOTALL):
            teile = [t.strip().strip('"\'') for t in roh.split(',') if t.strip()]
            if len(teile) < 3:
                continue
            spieler, turnier, jahr = teile[0], teile[1], teile[2]
            schluessel = (turnier.lower(), jahr)
            if schluessel not in gesehen:
                gesehen.add(schluessel)
                eintraege.append((spieler, turnier, jahr))
    return eintraege


def build_hall_of_fame():
    eintraege = hof_eintraege()
    if not eintraege:
        render_page("Hall of Fame", "<p>Keine Daten für die Hall of Fame gefunden.</p>", "vereinsintern.html")
        return
    tafel, titel = {}, {}
    for spieler, turnier, jahr in eintraege:
        tafel.setdefault(jahr, {}).setdefault(hof_spalte(turnier), []).append((spieler, turnier))
        for name in hof_spieler(spieler):
            titel[name] = titel.get(name, 0) + 1
    benutzt = {sp for zeile in tafel.values() for sp in zeile}
    feste = [n for n, _ in HOF_SPALTEN]
    spalten = [n for n in feste if n in benutzt] + sorted(benutzt - set(feste))
    jahre = sorted(tafel, reverse=True)
    rangliste = sorted(titel.items(), key=lambda x: (-x[1], x[0]))
    esc = htmllib.escape

    html = ['<a href="turniere.html" class="hof-zurueck">← Zurück zur Turniere-Übersicht</a>',
            '<h1>Hall of Fame</h1>',
            f'<p class="lead">Alle Sieger unserer vereinsinternen Turniere von {jahre[-1]} bis {jahre[0]}.</p>',
            '<h2>Meiste Titel</h2>', '<ol class="hof-top">']
    for name, n in rangliste[:HOF_TOP]:
        html.append(f'<li><span class="hof-name">{esc(name)}</span><span class="hof-zahl">{n}</span></li>')
    html.append('</ol>')
    optionen = "".join(f'<option>{esc(n)}</option>' for n in sorted(titel))
    html.append(f'<div class="hof-filter"><label for="hof-wahl">Spieler hervorheben:</label> '
                f'<select id="hof-wahl"><option value="">alle</option>{optionen}</select></div>')
    kopf = "".join(f'<th>{esc(sp)}</th>' for sp in spalten)
    html.append(f'<div class="table-responsive full-bleed hof-breit"><table class="hof-tafel"><thead><tr><th>Jahr</th>{kopf}</tr></thead><tbody>')
    for jahr in jahre:
        zellen = []
        for sp in spalten:
            titel_hier = tafel[jahr].get(sp)
            if titel_hier:
                alle = [n for wer, _ in titel_hier for n in hof_spieler(wer)]
                namen = esc("|".join(alle), quote=True)
                mehrere = ' class="mehrere"' if len(alle) > 1 else ''
                if len(titel_hier) == 1:
                    inhalt = esc(titel_hier[0][0])
                else:   # zwei Turniere in derselben Spalte, z. B. Jugend-VM und Jugend-Schnellschach
                    inhalt = "<br>".join(f'{esc(wer)} <small>({esc(turnier)})</small>' for wer, turnier in titel_hier)
                zellen.append(f'<td data-spieler="{namen}"{mehrere}>{inhalt}</td>')
            else:
                zellen.append('<td class="leer">–</td>')
        html.append(f'<tr><th scope="row">{esc(jahr)}</th>{"".join(zellen)}</tr>')
    html.append('</tbody></table></div>')
    html.append(HOF_SKRIPT)
    render_page("Hall of Fame", "\n".join(html), "vereinsintern.html", extra_styles="<style>" + FULL_BLEED_CSS + "</style>" + HOF_CSS)


# ==========================================
# VEREINSDOKUMENTE (Satzung, Vereinsgeschichte)
# Quellen in dokumente/*.typ, gemeinsames Aussehen in dokumente/afk-vorlage.typ.
# Beim Build werden geänderte Quellen zu PDF übersetzt; die Geschichte wird zusätzlich eine Webseite.
# ==========================================
DOKUMENTE_ORDNER = "dokumente"
DOKUMENTE = ["satzung", "historie"]

GESCHICHTE_CSS = """<style>
      :root { --afk-navy: #1c2d52; }   /* fest, unabhängig von --navy aus style.css */
      .zeitleiste { margin-top: 1.5rem; }
      .zl-jahr { display: grid; grid-template-columns: 6rem 1fr; gap: 1.2rem; margin-bottom: 1.4rem; }
      .zl-jahr h2 { margin: 0; font-size: 1.25rem; color: var(--text, var(--afk-navy)); font-variant-numeric: tabular-nums; }
      .zl-jahr > div { border-left: 3px solid #6fa3dc; padding-left: 1.1rem; }
      .zl-jahr p { margin: 0 0 0.7rem; }
      @media (max-width: 600px) { .zl-jahr { grid-template-columns: 1fr; gap: 0.3rem; } }
    </style>"""


def build_dokumente():
    vorlage = os.path.join(DOKUMENTE_ORDNER, "afk-vorlage.typ")
    for name in DOKUMENTE:
        quelle = os.path.join(DOKUMENTE_ORDNER, f"{name}.typ")
        ziel = os.path.join(DOKUMENTE_ORDNER, f"{name}.pdf")
        if not os.path.exists(quelle):
            continue
        zeit = max(os.path.getmtime(p) for p in (quelle, vorlage) if os.path.exists(p))
        if os.path.exists(ziel) and os.path.getmtime(ziel) >= zeit:
            continue   # PDF ist aktuell
        try:
            subprocess.run(["typst", "compile", quelle, ziel], check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            print(f"Hinweis: {quelle} konnte nicht übersetzt werden ({e}); das alte PDF bleibt.")


def typst_absatz_html(text):
    """Einfacher Typst-Text (Zeilenumbrüche mit Backslash, maskierte Zeichen) -> HTML."""
    text = re.sub(r'\s*\\\s*\n\s*', '\n', text.strip())
    text = re.sub(r'\\(.)', r'\1', text)
    return htmllib.escape(text, quote=False).replace('\n', '<br>')


def geschichte_chronik():
    """Chronik aus dokumente/historie.typ -> [(Jahr-Überschrift, HTML-Absätze)] (steht auf geschichte.html)."""
    quelle = os.path.join(DOKUMENTE_ORDNER, "historie.typ")
    if not os.path.exists(quelle):
        return []
    with open(quelle, "r", encoding="utf-8") as f:
        code = f.read()
    jahre = []
    for jahr, inhalt in re.findall(r'#jahr\("([^"]+)"\)\[\n(.*?)\n\]', code, re.DOTALL):
        inhalt = re.sub(r'(?m)^\s*//.*\n?', '', inhalt)   # Kommentare (offene Fragen) nicht anzeigen
        jahre.append((jahr, "".join(f'<p>{typst_absatz_html(a)}</p>' for a in re.split(r'\n\s*\n', inhalt) if a.strip())))
    return jahre


# ==========================================
# 6. BERICHTE PROCESSING
# ==========================================
MONTHS_DE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}

# Typst-Farbnamen, die im Bericht mit #text(blue)[...] benutzt werden dürfen
REPORT_COLORS = {
    "black": "#000000", "gray": "#aaaaaa", "silver": "#dddddd", "white": "#ffffff",
    "navy": "#001f3f", "blue": "#0074d9", "aqua": "#7fdbff", "teal": "#39cccc",
    "eastern": "#239dad", "purple": "#b10dc9", "fuchsia": "#f012be", "maroon": "#85144b",
    "red": "#ff4136", "orange": "#ff851b", "yellow": "#ffdc00", "olive": "#3d9970",
    "green": "#2ecc40", "lime": "#01ff70",
}

NEWS_CSS = """
      .vergangene-jahre { margin-top: 2.5rem; border-top: 2px solid #e3e6ea; padding-top: 0.5rem; }
      .vergangene-jahre > summary { cursor: pointer; font-size: 1.4rem; font-weight: bold; color: var(--navy); padding: 0.6rem 0; }
      .jahr-archiv { margin: 0.5rem 0 0.5rem 1rem; }
      .jahr-archiv > summary { cursor: pointer; font-size: 1.15rem; font-weight: bold; padding: 0.4rem 0; }
      .jahr-archiv .grid { margin-top: 0.8rem; }
      .jahr-titel { margin: 2.2rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid #e3e6ea; color: var(--navy); }
      .news-card h3 { margin: 0 0 0.2rem 0; font-size: 1.1rem; }
      .news-meta { color: #666; font-size: 0.85rem; margin: 0 0 0.6rem; }
      .news-snippet { margin: 0 0 0.8rem; font-size: 0.95rem; }
      .news-card a { font-weight: bold; text-decoration: none; }
      .news-thumb { display: block; width: 100%; height: 180px; object-fit: cover; border-radius: 6px; margin-bottom: 0.8rem; }
      .news-card { position: relative; }
      .news-card a::after { content: ""; position: absolute; inset: 0; }
      .news-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.12); }
      .news-card:hover h3 { text-decoration: underline; }
"""

ARTICLE_CSS = """
      .article-content h2 { margin-top: 2rem; color: var(--navy); }
      .article-content h3, .article-content h4 { color: var(--navy); }
      .article-content p, .article-content li { max-width: 70ch; }
      .article-content li { margin-bottom: 0.3rem; }
      .report-img { margin: 1.5rem 0; }
      .report-img img { display: block; max-width: 100%; height: auto; border-radius: 6px; }
      .report-img figcaption { font-size: 0.85rem; color: #666; margin-top: 0.4rem; }
"""


def parse_german_date(text):
    """'25. September 2026' oder '25.09.2026' -> date, sonst None."""
    t = text.strip().lower()
    m = re.match(r'(\d{1,2})\.\s*([a-zäöü]+)\s+(\d{4})', t)
    if m and m.group(2) in MONTHS_DE:
        day, month, year = int(m.group(1)), MONTHS_DE[m.group(2)], int(m.group(3))
    else:
        m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', t)
        if not m:
            return None
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def date_from_filename(stem):
    """Notlösung für die Sortierung: '2026-09-herbstblitz' -> 01.09.2026."""
    m = re.match(r'(\d{4})-(\d{2})', stem)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), 1)
        except ValueError:
            pass
    return None


def _text_span(m):
    """#text(blue, size: 20pt, style: "italic", weight: "bold")[...] -> <span style=...>"""
    args, content = m.group(1), m.group(2)
    css = []
    cm = re.match(r'\s*([a-z]+)\s*(?:,|$)', args) or re.search(r'fill:\s*([a-z]+)', args)
    if cm and cm.group(1) in REPORT_COLORS:
        css.append(f"color: {REPORT_COLORS[cm.group(1)]}")
    sm = re.search(r'size:\s*(\d+(?:\.\d+)?)(pt|em)', args)
    if sm:
        css.append(f"font-size: {sm.group(1)}{sm.group(2)}")
    if re.search(r'style:\s*"italic"', args):
        css.append("font-style: italic")
    if re.search(r'weight:\s*"bold"', args):
        css.append("font-weight: bold")
    style = f' style="{"; ".join(css)}"' if css else ""
    return f"<span{style}>{content}</span>"


def report_inline(text):
    """Typst-Auszeichnungen innerhalb eines Absatzes -> HTML.
    Maskierte Zeichen (\\*, \\_, \\#, \\[, ...) erscheinen als normale Zeichen."""
    maskiert = []

    def merken(m):
        maskiert.append(m.group(1))
        return f"\x00{len(maskiert) - 1}\x00"

    text = re.sub(r'\\([*_#$@<>`\[\]\\])', merken, text)
    t = htmllib.escape(text, quote=False)
    t = re.sub(r'#text\(([^)]*)\)\[([^\]]*)\]', _text_span, t)
    t = re.sub(r'#underline\[([^\]]*)\]', r'<u>\1</u>', t)
    t = re.sub(r'#strong\[([^\]]*)\]', r'<strong>\1</strong>', t)
    t = re.sub(r'#emph\[([^\]]*)\]', r'<em>\1</em>', t)
    t = re.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'<em>\1</em>', t)
    t = re.sub(r'#link\("((?:https?://|mailto:)[^"]+)"\)\[([^\]]*)\]',
               r'<a href="\1" target="_blank" rel="noopener">\2</a>', t)
    return re.sub(r"\x00(\d+)\x00", lambda m: htmllib.escape(maskiert[int(m.group(1))], quote=False), t)


IMG_RE = re.compile(r'^#image\(\s*"([^"]+)"\s*(?:,(.*))?\)\s*$')


def report_blocks(body, img=None, extra=None):
    """Zerlegt den Berichtstext in HTML-Blöcke (Überschriften, Absätze, Listen, Bilder, Partien, Tabellen)."""
    out, para, items, list_tag = [], [], [], None

    def flush():
        nonlocal para, items, list_tag
        if para:
            parts = []
            for l in para:
                brk = l.endswith('\\')
                l = l.rstrip('\\').rstrip()
                parts.append(report_inline(l) + ("<br>" if brk else ""))
            out.append("<p>" + " ".join(parts) + "</p>")
            para = []
        if items:
            lis = "".join(f"<li>{report_inline(i)}</li>" for i in items)
            out.append(f"<{list_tag}>{lis}</{list_tag}>")
            items, list_tag = [], None

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith('//') or re.match(r'#(set|show|let|import)\b', line):
            continue

        if extra and re.match(r'#(partien?|tabelle)\(', line):
            flush()
            x = extra(line)
            if x:
                out.append(x)
            continue

        im = IMG_RE.match(line)
        if im:
            flush()
            if img:
                alt_m = re.search(r'alt:\s*"([^"]*)"', im.group(2) or "")
                html = img(im.group(1), alt_m.group(1) if alt_m else "")
                if html:
                    out.append(html)
            continue

        h = re.match(r'^(={1,3})\s+(.*)$', line)
        if h:
            flush()
            level = len(h.group(1)) + 1          # = -> h2, == -> h3, === -> h4
            out.append(f"<h{level}>{report_inline(h.group(2))}</h{level}>")
            continue

        lm = re.match(r'^(?:(\d+\.)|([-+]))\s+(.*)$', line)
        if lm:
            tag = "ul" if lm.group(2) == "-" else "ol"
            if para or (list_tag and list_tag != tag):
                flush()
            list_tag = tag
            items.append(lm.group(3))
            continue

        if items:
            flush()
        para.append(line)

    flush()
    return out


def make_snippet(blocks, limit=200):
    """Kurzer Vorschautext aus dem ersten Absatz, möglichst an einem Satzende beendet."""
    for b in blocks:
        if b.startswith("<p>"):
            t = plain_text(b)
            out = ""
            for s in re.split(r'(?<=[.!?])\s+', t):
                if out and len(out) + 1 + len(s) > limit:
                    break
                out = (out + " " + s).strip()
            if len(out) > limit:   # erster Satz allein zu lang
                out = out[:limit].rsplit(" ", 1)[0].rstrip(",;:–- ") + " …"
            return htmllib.escape(out, quote=False)
    return ""

def typst_to_html_article(typst_text, img=None, extra=None):
    def meta(name):
        m = re.search(r'#' + name + r'\[(.*?)\]', typst_text)
        return m.group(1).strip() if m else ""

    title = meta("title") or "Turnierbericht"
    date = meta("date")
    author = meta("author")

    body = re.sub(r'#(?:title|date|author|entwurf|kategorie)\[.*?\]', '', typst_text)
    blocks = report_blocks(body, img, extra)

    esc = lambda s: htmllib.escape(s, quote=False)
    return esc(title), esc(date), esc(author), "\n".join(blocks), make_snippet(blocks)


def is_draft_report(filepath, code, title):
    """
    Entwürfe und Vorlagen werden nicht veröffentlicht, wenn
    - der Dateiname 'vorlage' enthält, oder
    - der Titel 'Vorlage' heißt, oder
    - im Bericht eine Zeile '#entwurf[ja]' steht, oder
    - irgendwo im Bericht eine Zeile '// entwurf' bzw. '// draft' steht.
    """
    if "vorlage" in filepath.lower():
        return True
    if plain_text(title).strip().lower() == "vorlage":
        return True
    if re.search(r'(?im)^\s*#entwurf\[\s*(ja|true|wahr|yes|x)\s*\]', code):
        return True
    return bool(re.search(r'(?im)^\s*//\s*(entwurf|draft)\b', code))


IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMG_WARN_KB = 1024


def report_slug(filepath):
    """berichte/2026/Kooperationsturnier_EBE/Bericht.typ -> 2026-kooperationsturnier-ebe"""
    rel = os.path.relpath(filepath, "berichte").replace(os.sep, "/")
    parts = rel[:-4].split("/")                       # ".typ" abschneiden
    if len(parts) > 1 and parts[-1].lower() == "bericht":
        parts = parts[:-1]                            # "Bericht" ist nur der Dateiname
    return slugify(" ".join(parts))


def is_hidden_report(filepath):
    """Ordner/Dateien mit '_' am Anfang (z. B. _funktionen.typ, _Vorlage) sind nie Berichte."""
    rel = os.path.relpath(filepath, "berichte").replace(os.sep, "/")
    return any(p.startswith("_") for p in rel.split("/"))


def make_img_handler(filepath, slug, images):
    """Kopiert Bilder neben der Bericht.typ nach berichte/bilder/<slug>/ und liefert das HTML."""
    folder = os.path.dirname(filepath)

    def handler(name, alt):
        base = os.path.basename(name)
        src = os.path.join(folder, base)
        if base != name or os.path.splitext(base)[1].lower() not in IMG_EXT:
            print(f"WARNUNG [{filepath}]: Bild '{name}' ungültig (nur Dateiname aus demselben Ordner; jpg/png/webp/gif).")
            return ""
        if not os.path.isfile(src):
            print(f"WARNUNG [{filepath}]: Bild '{name}' nicht gefunden (nicht mit committet?).")
            return ""
        kb = os.path.getsize(src) // 1024
        if kb > IMG_WARN_KB:
            print(f"WARNUNG [{filepath}]: Bild '{name}' hat {kb} KB, bitte verkleinern (ca. 1600 px Breite).")
        dest_dir = os.path.join("berichte", "bilder", slug)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dest_dir, base))
        url = f"bilder/{slug}/{quote(base)}"
        images.append(f"berichte/{url}")
        alt_attr = htmllib.escape(alt, quote=True)
        cap = f"<figcaption>{htmllib.escape(alt, quote=False)}</figcaption>" if alt else ""
        return f'<figure class="report-img"><img src="{url}" alt="{alt_attr}" loading="lazy">{cap}</figure>'

    return handler


def thumb_html(r):
    return f'<img class="news-thumb" src="{r["thumb"]}" alt="" loading="lazy">' if r.get('thumb') else ""


ALLE_BERICHTE = []   # wird von build_berichte() gefüllt (z. B. für die Jugendseite)


def build_berichte():
    reports = []
    seen = {}
    # Wer hat eine Profilseite? (Spielerseiten vom letzten Build + registrierte Mitglieder)
    profil_slugs = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join("spieler", "*.html"))} | set(konten.PROFILE)

    if os.path.exists("berichte"):
        # Kopierte Bilder werden bei jedem Build neu erzeugt
        shutil.rmtree(os.path.join("berichte", "bilder"), ignore_errors=True)

        for filepath in sorted(glob.glob("berichte/**/*.typ", recursive=True)):
            if is_hidden_report(filepath):
                continue
            slug = report_slug(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()

            tm = re.search(r'#title\[(.*?)\]', code)
            if is_draft_report(filepath, code, tm.group(1) if tm else ""):
                continue

            if slug in seen:
                print(f"WARNUNG: {filepath} hat dieselbe Adresse wie {seen[slug]} und wird übersprungen.")
                continue
            seen[slug] = filepath

            images = []
            dm = re.search(r'#date\[(.*?)\]', code)
            extra = bericht_extras.handler(os.path.dirname(filepath), parse_german_date(dm.group(1).strip()) if dm else None,
                                           lambda t, fp=filepath: print(f"WARNUNG [{fp}]: {t}"))
            title, date, author, body_html, snippet = typst_to_html_article(
                code, make_img_handler(filepath, slug, images), extra)

            when = parse_german_date(date)
            if when is None:
                print(f"WARNUNG [{filepath}]: Datum fehlt oder ist nicht lesbar (erwartet TT.MM.JJJJ).")
            elif when > TODAY:
                print(f"WARNUNG [{filepath}]: Datum {date} liegt in der Zukunft (Tippfehler?).")

            km = re.search(r'(?m)^\s*#kategorie\[(.*?)\]', code)
            kategorien = {k.strip().lower() for k in km.group(1).split(",")} if km else set()

            # Titelbild (Editor: "// titelbild: bild2.jpg"), sonst das erste Bild
            tb = re.search(r'(?m)^\s*//\s*titelbild:\s*(\S+)', code)
            thumb = next((i for i in images if tb and os.path.basename(i) == tb.group(1)), images[0] if images else "")
            # Autor -> Profilseite (nicht bei "// gast": Name von einem Gast, vom Admin nicht bestätigt)
            autor_slug = ""
            if author and not re.search(r'(?m)^\s*//\s*gast\s*$', code):
                s_ = spieler.slug(plain_text(author))
                if s_ in profil_slugs:
                    autor_slug = s_
            autor_html = f'<a href="../spieler/{autor_slug}.html">{author}</a>' if autor_slug else author
            meta = date + (f" · von {author}" if author and date else (f"von {author}" if author else ""))
            meta_link = date + (f" · von {autor_html}" if author and date else (f"von {autor_html}" if author else ""))
            reports.append({
                'stem': slug,
                'filename': slug + ".html",
                'title': title,
                'meta': meta,
                'body': body_html,
                'snippet': snippet,
                'thumb': thumb,
                'meta_link': meta_link,
                'autor': plain_text(author) if author else "",
                'autor_slug': autor_slug,
                'when': when or date_from_filename(slug) or datetime.date.min,
                'kategorien': kategorien,
                'partien': extra.partien,
            })

        # Neueste zuerst
        reports.sort(key=lambda r: (r['when'], r['stem']), reverse=True)
        ALLE_BERICHTE[:] = reports

        # HTML-Dateien ohne passenden Bericht (gelöscht oder Entwurf) entfernen
        valid = {r['filename'] for r in reports}
        for old in glob.glob("berichte/*.html"):
            if os.path.basename(old) not in valid:
                os.remove(old)

    article_styles = "<style>" + NEWS_CSS + ARTICLE_CSS + "</style>"

    for r in reports:
        article_content = f"""
        <a href="../berichte.html" style="text-decoration:none;">← Zurück zur Berichte-Übersicht</a>
        <h1 style="margin-top:1rem;">{r['title']}</h1>
        <p class="news-meta">{r['meta_link']}</p>
        <hr style="border:0; border-top:1px solid #eee; margin:1.5rem 0;">
        <div class="article-content">{r['body']}</div>
        {bericht_extras.SKRIPT if r['partien'] else ""}
        """
        render_page(r['title'], article_content, os.path.join("berichte", r['filename']),
                    css_path="../", nav_path="../",
                    extra_styles=(bericht_extras.kopf_html() if r['partien'] else "") + article_styles,
                    description=r['snippet'] or None)
    def overview_card(r):
        return f"""
        <div class="card news-card">
          {thumb_html(r)}
          <h3>{r['title']}</h3>
          <p class="news-meta">{r['meta']}</p>
          <p class="news-snippet">{r['snippet']}</p>
          <a href="berichte/{r['filename']}" class="btn">Bericht lesen →</a>
        </div>
        """

    def year_grid(group):
        cards = "\n".join(overview_card(r) for r in group)
        return f"<div class='grid' style='grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));'>{cards}</div>"

    def year_label(y):
        return "Ohne Datum" if y == 1 else str(y)

    by_year = [(y, list(g)) for y, g in groupby(reports, key=lambda r: r['when'].year)]
    parts = []
    if by_year:
        # Offen: neuestes Jahr mit Berichten (höchstens das aktuelle Jahr); älteres wandert ins Archiv
        candidates = [y for y, _ in by_year if y <= TODAY.year]
        current = max(candidates) if candidates else by_year[0][0]

        for y, g in by_year:
            if y >= current:
                parts.append(f"<h2 class='jahr-titel'>{year_label(y)}</h2>" + year_grid(g))

        older = [(y, g) for y, g in by_year if y < current]
        if older:
            inner = "".join(
                f"<details class='jahr-archiv'><summary>{year_label(y)}</summary>{year_grid(g)}</details>"
                for y, g in older
            )
            parts.append(f"<details class='vergangene-jahre'><summary>Vergangene Jahre</summary>{inner}</details>")

    body = "\n".join(parts) if parts else "<p>Aktuell sind noch keine Berichte vorhanden.</p>"
    overview_content = (einreichen.WEITERLEITUNG +
                        f'<div class="be-seitenkopf"><h1>Aktuelle Berichte &amp; News</h1>{einreichen.knopf()}</div>' + body)
    if einreichen.SKRIPT_URL:
        render_page("Bericht schreiben", einreichen.seite(), einreichen.SEITE,
                    extra_styles="<style>" + einreichen.CSS + "</style>",
                    description="Bericht für die Website der SG AFK schreiben – mit Fotos, Partien und Tabellen.")
    render_page("Berichte & News", overview_content, "berichte.html",
                extra_styles="<style>" + NEWS_CSS + einreichen.CSS + "</style>")

    home_news_snippets = []
    for r in reports[:2]:
        home_news_snippets.append(f"""
        <div class="card news-card">
          {thumb_html(r)}
          <h3>{r['title']}</h3>
          <p class="news-meta">{r['meta']}</p>
          <p class="news-snippet">{r['snippet']}</p>
          <a href="berichte/{r['filename']}">Weiterlesen →</a>
        </div>
        """)
    return home_news_snippets


# ==========================================
# 7. STARTSEITE BUILDEN
# ==========================================
# --- Einstellungen -------------------------------------------------
DIASHOW_ORDNER = "diashow"      # Fotos für die Diashow oben auf der Startseite (jpg/png/webp), alphabetisch
DIASHOW_SEKUNDEN = 5            # Anzeigedauer pro Foto
# Wer in Windows/Handy "Animationen reduzieren" eingeschaltet hat, sieht sonst nur das erste Foto. True = trotzdem wechseln
DIASHOW_AUCH_OHNE_ANIMATIONEN = False
# Hintergrundvideo statt Diashow: Datei in diashow/ ablegen (z. B. hero.mp4, optional hero.webm).
# Fehlt die Datei, läuft die Diashow. Das erste Diashow-Foto dient als Standbild (Poster).
HERO_VIDEO = "hero"             # Dateiname ohne Endung; "" = nie Video
HERO_TITLE = "Schach spielen in <br>Aschheim, Feldkirchen &amp; Kirchheim"
# Alternative: "Schach im Münchner Osten"

# Mitgliederzahl vom Schachbund (Wertungsportal-API)
DSB_ZPS = "22061"                        # Vereinskennzahl (kann per DSB_VKZ überschrieben werden)
DSB_API_URL = "https://www.schachbund.de/wertungsportal-api/vereinsliste"
DSB_VEREIN_URL = f"https://www.schachbund.de/dwz-vereine/{DSB_ZPS}.html"
MEMBER_CACHE = "mitglieder_anzahl.txt"   # letzter erfolgreich gelesener Wert (mit committen)
MEMBER_FALLBACK = "80+"                  # falls Abruf scheitert und noch kein Cache existiert

# Zahlenleiste: (große Zahl/Wort, Beschriftung, Link oder None); {members} wird ersetzt
# {teams} = Zahl der Mannschaften mit Liga-Daten (sonst MANNSCHAFTEN_FALLBACK)
STATS = [
    ("{members}", "Mitglieder", DSB_VEREIN_URL),
    ("{teams}", "Mannschaften", "mannschaften.html"),
]
MANNSCHAFTEN_FALLBACK = "6"

# Schließzeiten / Pausen kommen aus ausfall.txt (z. B. "19.12.2026 - 06.01.2027 = Weihnachtspause").
# Startseite: Hinweis in "Diese Woche" + farbiges Band unter dem Menü; Terminkalender: gestreifte Zeile.
PAUSE_BAND = True               # Band unter dem Menü auf der Startseite (nur bei mehrtägigen Pausen)
PAUSE_VORLAUF_TAGE = 7          # so viele Tage vor Beginn erscheinen Band und "danach ...-Pause"
PAUSE_IM_KALENDER = True        # Pausen als Zeile im Terminkalender

# Wird im Browser ausgeführt, damit "heute / in 3 Tagen" und der nächste
# Freitag immer stimmen, auch wenn die Seite schon länger nicht neu gebaut wurde.
HOME_JS = """<script>
(function () {
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var AUSFALL = __AUSFALL__;   // Spielabend-Ausfälle aus ausfall.txt
  var PAUSE_BAND = __PAUSE_BAND__, PAUSE_VORLAUF = __PAUSE_VORLAUF__;

  function two(x) { return ("0" + x).slice(-2); }
  function iso(d) { return d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate()); }
  function dm(d) { return two(d.getDate()) + "." + two(d.getMonth() + 1) + "."; }
  function rel(d) {
    var n = Math.round((d - today) / 86400000);
    if (n === 0) return "heute";
    if (n === 1) return "morgen";
    return "in " + n + " Tagen";
  }
  function dmi(s) { var p = s.split("-"); return p[2] + "." + p[1] + "."; }
  // Ausfälle, die angezeigt werden: ab dem 1. des Monats, in dem sie beginnen, bis zu ihrem Ende
  function angekuendigt() {
    var t = iso(today), out = [];
    for (var i = 0; i < AUSFALL.length; i++) {
      var a = AUSFALL[i];
      if (t >= a.start.slice(0, 8) + "01" && t <= a.end) out.push(a);
    }
    return out;
  }
  function blocked(d) {
    var s = iso(d);
    for (var i = 0; i < AUSFALL.length; i++) {
      if (s >= AUSFALL[i].start && s <= AUSFALL[i].end) return AUSFALL[i];
    }
    return null;
  }

  // Termin-Karten: vergangene ausblenden, nur die ersten N zeigen
  var grid = document.querySelector(".events-grid");
  var max = (grid && parseInt(grid.dataset.max, 10)) || 4;
  var total = 0, shown = 0, last = null;
  document.querySelectorAll(".event-card[data-date]").forEach(function (c) {
    total++;
    var p = c.dataset.date.split("-");
    var d = new Date(+p[0], p[1] - 1, +p[2]);
    if (d < today || shown >= max) { c.style.display = "none"; return; }
    var r = c.querySelector(".ev-rel");
    if (r) r.textContent = rel(d);
    if (shown === 0) c.classList.add("next", "first-visible");
    shown++;
    last = c;
  });
  if (last) last.classList.add("last-visible");
  var empty = document.getElementById("events-empty");
  if (empty && total > 0 && shown === 0) empty.hidden = false;

  // Nächster Spielabend: jeden Freitag, außer an Ausfalltagen (ausfall.txt)
  var el = document.getElementById("spielabend");
  var band = document.getElementById("pause-band");
  function zeitraum(a) { return a.start === a.end ? "am " + dmi(a.start) : "vom " + dmi(a.start) + " bis " + dmi(a.end); }
  function fett(t) { var b = document.createElement("b"); b.textContent = t; return b; }
  if (el) {
    var f = new Date(today);
    f.setDate(f.getDate() + ((5 - f.getDay() + 7) % 7));
    var pause = blocked(f), hit = pause, n = 0;
    while (hit && n++ < 30) { f.setDate(f.getDate() + 7); hit = blocked(f); }
    // Pause, die nach dem nächsten Spielabend bald beginnt (Vorschau)
    var bald = null;
    if (!pause) {
      var g = new Date(f); g.setDate(g.getDate() + 7);
      bald = blocked(g);
    }
    var grenze = new Date(today); grenze.setDate(grenze.getDate() + PAUSE_VORLAUF);
    el.textContent = "";
    if (hit) {
      el.appendChild(document.createTextNode("Aktuell kein Spielabend" + (hit.reason ? ": " + hit.reason : "")));
    } else if (pause) {
      el.classList.add("pause");
      el.appendChild(fett(pause.reason || "Pause"));
      el.appendChild(document.createTextNode(" " + zeitraum(pause) + " – nächster Spielabend: Freitag, " + dm(f) + " ab 18:00 Uhr"));
    } else {
      el.appendChild(document.createTextNode("Nächster Spielabend: Freitag, " + dm(f) + " ab 18:00 Uhr (" + rel(f) + ")"));
      if (bald) {
        el.classList.add("pause");
        el.appendChild(document.createTextNode(" – "));
        el.appendChild(fett("danach " + (bald.reason || "Pause") + (bald.start === bald.end ? "" : " bis " + dmi(bald.end))));
      }
      var ank = angekuendigt();
      for (var k = 0; k < ank.length; k++) {
        if (bald && ank[k] === bald) continue;
        var why = ank[k].reason ? " (" + ank[k].reason + ")" : "";
        var note = document.createElement("span");
        note.className = "spielabend-note";
        note.textContent = (ank[k].start === ank[k].end ? "Am " + dmi(ank[k].start) : "Vom " + dmi(ank[k].start) + " bis " + dmi(ank[k].end)) + " kein Spielabend" + why;
        el.appendChild(document.createElement("br"));
        el.appendChild(note);
      }
    }
    el.hidden = false;

    // Band unter dem Menü: während der Pause und PAUSE_VORLAUF Tage vorher
    var b = pause || null;
    if (!b) for (var i = 0; i < AUSFALL.length; i++) {
      var st = AUSFALL[i].start.split("-"), sd = new Date(+st[0], st[1] - 1, +st[2]);
      if (sd >= today && sd <= grenze && AUSFALL[i].start !== AUSFALL[i].end) { b = AUSFALL[i]; break; }
    }
    if (band && b && PAUSE_BAND) {
      var weiter = new Date(+b.end.slice(0, 4), b.end.slice(5, 7) - 1, +b.end.slice(8, 10));
      weiter.setDate(weiter.getDate() + 1);
      while (weiter.getDay() !== 5 || blocked(weiter)) weiter.setDate(weiter.getDate() + 1);
      band.appendChild(fett(b.reason || "Pause"));
      band.appendChild(document.createTextNode(" " + zeitraum(b) + " – nächster Spielabend danach am Freitag, " + dm(weiter)));
      band.hidden = false;
    }
  }
})();
</script>"""


def get_secret(name, default=""):
    """Umgebungsvariable, sonst Zeile NAME=wert aus lokaler .env (die NICHT ins Repo gehört)."""
    if os.environ.get(name):
        return os.environ[name].strip()
    if os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() == name:
                    return value.strip().strip('"\'')
    return default


_DSB_LISTE = None
def dsb_liste():
    """DSB-Vereinsliste (einmal pro Build geladen). Fehler -> Exception mit Grund (ohne Token)."""
    global _DSB_LISTE
    if _DSB_LISTE is None:
        token = get_secret("DSB_TOKEN")
        if not token:
            raise ValueError("kein DSB_TOKEN gesetzt")
        query = urllib.parse.urlencode({"token": token, "vkz": get_secret("DSB_VKZ", DSB_ZPS)})
        req = urllib.request.Request(
            f"{DSB_API_URL}?{query}",
            headers={"User-Agent": "Mozilla/5.0 (SG-AFK Website-Build)", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Schachbund-API nicht erreichbar ({type(e).__name__})") from None
        if isinstance(data, dict):                       # z. B. {"spieler": [...]} -> längste Liste nehmen
            lists = [v for v in data.values() if isinstance(v, list)]
            data = max(lists, key=len) if lists else []
        _DSB_LISTE = data
    return _DSB_LISTE


def fetch_member_count():
    """Anzahl aller Einträge der DSB-Vereinsliste; bei Fehlern letzter gespeicherter Wert, sonst Fallback."""
    try:
        n = len(dsb_liste())
        if n < 5:
            raise ValueError(f"unplausible Anzahl: {n}")

        with open(MEMBER_CACHE, "w", encoding="utf-8") as f:
            f.write(str(n))
        return str(n)
    except Exception as e:
        print(f"Hinweis: Mitgliederzahl nicht abrufbar ({e})")
        if os.path.exists(MEMBER_CACHE):
            with open(MEMBER_CACHE, encoding="utf-8") as f:
                return f.read().strip() or MEMBER_FALLBACK
        return MEMBER_FALLBACK


def find_logo():
    return next((f for f in os.listdir(".") if f.lower() == "logo.png"), None)


def _parse_any_date(text):
    """'2026-12-25' oder '25.12.2026' -> date, sonst None."""
    t = text.strip()
    m = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})', t)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', t)
        if not m:
            return None
        d, mo, y = map(int, m.groups())
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def read_ausfall(path="ausfall.txt"):
    """
    Liest Tage, an denen KEIN Spielabend stattfindet. Eine Zeile pro Eintrag:
        25.12.2026 = Weihnachten
        24.12.2026 - 08.01.2027 = Weihnachtsferien
    Datum als TT.MM.JJJJ oder JJJJ-MM-TT, Zeilen mit # am Anfang sind Kommentare.
    Rückgabe: Liste mit start/end (ISO-Datum) und reason; vergangene Einträge fallen weg.
    """
    if not os.path.exists(path):
        return []
    result = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            datepart, _, reason = line.partition("=")
            parts = re.split(r'\s+(?:-|–|bis)\s+', datepart.strip())
            start = _parse_any_date(parts[0])
            end = _parse_any_date(parts[-1]) if len(parts) > 1 else start
            if not start or not end or end < start:
                print(f"Hinweis: ausfall.txt – Zeile nicht lesbar: {line}")
                continue
            if end < TODAY:
                continue
            result.append({"start": start.isoformat(), "end": end.isoformat(), "reason": reason.strip()})
    return result


def stats_html(teams=()):
    members = fetch_member_count()
    items = []
    for big, label, href in STATS:
        text = big.replace("{members}", members).replace("{teams}", str(len(teams)) if teams else MANNSCHAFTEN_FALLBACK)
        inner = f'<strong>{text}</strong><span>{label}</span>'
        if href:
            ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
            items.append(f'<li><a href="{href}"{ext}>{inner}</a></li>')
        else:
            items.append(f'<li>{inner}</li>')
    return '<ul class="stats">' + "".join(items) + '</ul>'


def legend_html(events):
    """Kleine Erklärung der Kürzel, die in den angezeigten Terminen vorkommen."""
    text = " ".join(plain_text(e["title"]) for e in events)
    used = [f"<strong>{k}</strong> = {v}"
            for k, v in ABBREVIATIONS.items()
            if re.search(rf"\b{re.escape(k)}\b", text)]
    return f'<p class="ev-legend">{" · ".join(used)}</p>' if used else ""


def team_klasse(name):
    """'AFK 1' -> 'team-afk-1', 'Jugend' -> 'team-jugend' (Farben stehen in design.css)."""
    return "team-" + slugify(plain_text(name).strip())


def event_card_html(ev):
    teams = ""
    if ev["who"]:
        pills = "".join(f'<span class="pill {team_klasse(t)}">{t.strip()}</span>' for t in ev["who"].split(","))
        teams = f'<div class="ev-teams">{pills}</div>'
    date_attr = ev["date"].isoformat()
    inner = f"""
          <div class="ev-date">{ev["when"]} <span class="ev-rel"></span></div>
          <div class="ev-title">{ev["title"]}</div>
          {teams}"""
    # Enthält die Karte schon einen Link (z. B. zur Ausschreibung), bleibt sie ein <div>,
    # sonst ist die ganze Karte ein Link zum Spielplan (Links dürfen nicht verschachtelt sein).
    if "<a " in ev["when"] + ev["title"]:
        return f"""
        <div class="event-card" data-date="{date_attr}">{inner}
        </div>"""
    return f"""
        <a class="event-card" href="termine.html" data-date="{date_attr}">{inner}
        </a>"""


def diashow_bilder():
    if not os.path.isdir(DIASHOW_ORDNER):
        return []
    return sorted(f"{DIASHOW_ORDNER}/{quote(n)}" for n in os.listdir(DIASHOW_ORDNER)
                  if os.path.splitext(n)[1].lower() in IMG_EXT)


def hero_video_html():
    if not HERO_VIDEO:
        return ""
    quellen = [(f"{DIASHOW_ORDNER}/{HERO_VIDEO}{ext}", typ) for ext, typ in ((".webm", "video/webm"), (".mp4", "video/mp4"))
               if os.path.exists(os.path.join(DIASHOW_ORDNER, HERO_VIDEO + ext))]
    if not quellen:
        return ""
    bilder = diashow_bilder()
    poster = f' poster="{bilder[0]}"' if bilder else ""
    src = "".join(f'<source src="{quote(q)}" type="{t}">' for q, t in quellen)
    # muted + playsinline: sonst starten Handys das Video nicht automatisch
    return (f'<div class="hero-video" aria-hidden="true"><video autoplay muted loop playsinline preload="metadata"{poster}>{src}</video></div>'
            '<script>(function(){var v=document.querySelector(".hero-video video");'
            'if(v&&window.matchMedia("(prefers-reduced-motion: reduce)").matches){v.removeAttribute("autoplay");v.pause();}})();</script>')


def diashow_html():
    video = hero_video_html()
    if video:
        return video
    bilder = diashow_bilder()
    if not bilder:
        return ""
    # Erstes Bild sofort, die anderen lädt das Skript nach (data-bild)
    dias, knoepfe = [], []
    for i, bild in enumerate(bilder):
        if i == 0:
            dias.append(f'<div class="dia aktiv" style="background-image:url({bild})"></div>')
            knoepfe.append(f'<button type="button" aria-label="Foto {i + 1}" aria-current="true"></button>')
        else:
            dias.append(f'<div class="dia" data-bild="{bild}"></div>')
            knoepfe.append(f'<button type="button" aria-label="Foto {i + 1}"></button>')
    dias = "".join(dias)
    punkte = f'<div class="dia-punkte">{"".join(knoepfe)}</div>' if len(bilder) > 1 else ""
    return f'<div class="diashow" aria-hidden="true">{dias}</div>{punkte}'


DIASHOW_JS = """<script>
(function () {
  var dias = document.querySelectorAll(".diashow .dia");
  var punkte = document.querySelectorAll(".dia-punkte button");
  if (dias.length < 2) return;
  dias.forEach(function (d) { if (d.dataset.bild) d.style.backgroundImage = "url('" + d.dataset.bild + "')"; });
  var i = 0, timer = null, ms = __SEKUNDEN__ * 1000, DIASHOW_IMMER = __IMMER__;
  function zeige(n) {
    dias[i].classList.remove("aktiv"); punkte[i].removeAttribute("aria-current");
    i = (n + dias.length) % dias.length;
    dias[i].classList.add("aktiv"); punkte[i].setAttribute("aria-current", "true");
  }
  function start() { stop(); timer = setInterval(function () { zeige(i + 1); }, ms); }
  function stop() { if (timer) clearInterval(timer); timer = null; }
  punkte.forEach(function (p, n) { p.addEventListener("click", function () { zeige(n); start(); }); });
  // Anhalten nur, wenn die Maus auf den Punkten liegt (nicht über dem ganzen Bild)
  var leiste = document.querySelector(".dia-punkte");
  if (leiste) { leiste.addEventListener("mouseenter", stop); leiste.addEventListener("mouseleave", start); }
  if (DIASHOW_IMMER || !window.matchMedia("(prefers-reduced-motion: reduce)").matches) start();
})();
</script>"""


# ==========================================
# GEBURTSTAGE auf der Startseite ("Max wird heute 34") + einmal am Tag kurzes Konfetti
# Quelle: GitHub-Secret GEBURTSTAGE (lädt update_all.py hoch) oder lokal ../Geburtstag/daten/geburtstage.json
# Es landen nur die Geburtstagskinder von heute im HTML, nie die ganze Liste.
# ==========================================
GEBURTSTAGE_AN = True                 # False = keine Geburtstage auf der Startseite
GEBURTSTAG_KONFETTI = True            # False = nur die Karte, kein Konfetti
GEBURTSTAG_LOKAL = os.path.join("..", "Geburtstag", "daten", "geburtstage.json")
GEBURTSTAG_TEXT = "Alles Gute vom ganzen Verein!"


def _geburtstag_liste():
    """[{'vorname','nachname','geburtstag' (TT.MM.JJJJ)}] aus dem Secret oder der lokalen Datei."""
    roh = os.environ.get("GEBURTSTAGE", "").strip()
    try:
        if roh:
            daten = json.loads(roh)
        elif os.path.exists(GEBURTSTAG_LOKAL):
            with open(GEBURTSTAG_LOKAL, encoding="utf-8") as f:
                daten = json.load(f)
        else:
            return []
    except (OSError, ValueError) as e:
        print(f"Hinweis: Geburtstage nicht lesbar ({type(e).__name__})")
        return []
    if isinstance(daten, dict):
        daten = daten.get("mitglieder", [])
    return [m for m in daten if isinstance(m, dict)]


def geburtstage_heute(heute=None):
    """[(Anzeigename, neues Alter)]; Vorname, bei doppeltem Vornamen mit Nachname. 29.02. -> 28.02. in Nicht-Schaltjahren."""
    if not GEBURTSTAGE_AN:
        return []
    heute = heute or TODAY
    # öffentlich nur, wer seinen Geburtstag im Profil selbst freigegeben hat (Admins sehen alle nach dem Login)
    liste = [m for m in _geburtstag_liste()
             if konten.geburtstag_oeffentlich(spieler.slug(f"{m.get('vorname', '')} {m.get('nachname', '')}"))]
    vornamen = {}
    for m in liste:
        v = str(m.get("vorname", "")).strip().lower()
        vornamen[v] = vornamen.get(v, 0) + 1
    schaltjahr = heute.year % 4 == 0 and (heute.year % 100 != 0 or heute.year % 400 == 0)
    treffer = []
    for m in liste:
        try:
            tag, monat, jahr = (int(x) for x in str(m.get("geburtstag", "")).split("."))
        except ValueError:
            continue
        feiertag = (monat, tag)
        if (monat, tag) == (2, 29) and not schaltjahr:
            feiertag = (2, 28)
        alter = heute.year - jahr
        if feiertag != (heute.month, heute.day) or not 0 < alter < 120:
            continue
        v, n = str(m.get("vorname", "")).strip(), str(m.get("nachname", "")).strip()
        name = v if vornamen.get(v.lower(), 0) == 1 else f"{v} {n}".strip()
        treffer.append((name, alter))
    return sorted(treffer)


def geburtstage_woche(heute=None, tage=7):
    """[(Datum, Anzeigename)] für heute .. heute+tage (ohne Alter)."""
    if not GEBURTSTAGE_AN:
        return []
    heute = heute or TODAY
    out = []
    for i in range(tage + 1):
        tag = heute + datetime.timedelta(days=i)
        out += [(tag, n) for n, _ in geburtstage_heute(tag)]
    return out


# ==========================================
# STARTSEITE: BOX "DIESE WOCHE"
# ==========================================
DIESE_WOCHE_AN = True
DIESE_WOCHE_TAGE = 7          # Zeitraum ab heute
DIESE_WOCHE_KM = 150          # neue Turniere aus dem Turnierkalender bis zu dieser Entfernung
DIESE_WOCHE_MAX = 4           # höchstens so viele Einträge je Spalte
WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def diese_woche_html(upcoming_events, heute=None):
    """Kompakte Übersicht: Termine der nächsten 7 Tage, Geburtstage, neue Turniere in der Nähe, neue Berichte.
    Die Seite wird nachts neu gebaut; das Skript blendet zusätzlich vergangene Tage aus."""
    if not DIESE_WOCHE_AN:
        return ""
    heute = heute or TODAY
    ende = heute + datetime.timedelta(days=DIESE_WOCHE_TAGE)
    def tag_txt(d):
        return f"{WOCHENTAG[d.weekday()]} {d.day:02d}.{d.month:02d}."
    spalten = []
    termine = [ev for ev in upcoming_events if heute <= ev["date"] <= ende][:DIESE_WOCHE_MAX + 2]
    if termine:
        spalten.append(("Termine", "".join(
            f'<li data-date="{ev["date"].isoformat()}"><span class="dw-tag">{tag_txt(ev["date"])}</span> '
            f'{htmllib.escape(plain_text(ev["title"]))}</li>' for ev in termine), "termine.html", "Alle Termine"))
    gb = geburtstage_woche(heute, DIESE_WOCHE_TAGE)[:DIESE_WOCHE_MAX + 2]
    if gb:
        spalten.append(("Geburtstage", "".join(
            f'<li data-date="{d.isoformat()}"><span class="dw-tag">{"heute" if d == heute else tag_txt(d)}</span> '
            f'{htmllib.escape(n)}</li>' for d, n in gb), "", ""))
    neu = [e for e in getattr(turnierkalender, "LETZTE_EVENTS", [])
           if turnierkalender.ist_neu(e, heute) and e.get("km") is not None and e["km"] <= DIESE_WOCHE_KM]
    if neu:
        neu.sort(key=lambda e: e["von"])
        spalten.append(("Neu im Turnierkalender", "".join(
            f'<li><span class="dw-tag">{datetime.date.fromisoformat(e["von"]).strftime("%d.%m.")}</span> '
            f'{htmllib.escape(e["name"])} <span class="dw-km">{e["km"]} km</span></li>' for e in neu[:DIESE_WOCHE_MAX]),
            turnierkalender.SEITE, f"Turnierkalender ({len(neu)} neu)" if len(neu) > DIESE_WOCHE_MAX else "Turnierkalender"))
    frisch = [r for r in ALLE_BERICHTE if r['when'] != datetime.date.min and (heute - r['when']).days <= DIESE_WOCHE_TAGE
              and r['when'] <= heute][:DIESE_WOCHE_MAX]
    if frisch:
        spalten.append(("Neue Berichte", "".join(
            f'<li><a href="berichte/{r["filename"]}">{htmllib.escape(plain_text(r["title"]))}</a></li>' for r in frisch), "berichte.html", "Alle Berichte"))
    if not spalten:
        return ""
    teile = "".join(
        f'<div class="dw-spalte"><h3>{t}</h3><ul>{inhalt}</ul>'
        + (f'<a class="dw-mehr" href="{link}">{linktext} →</a>' if link else "") + "</div>"
        for t, inhalt, link, linktext in spalten)
    return f"""<section class="diese-woche" aria-label="Diese Woche">
      <h2>Diese Woche</h2><div class="dw-raster">{teile}</div>
    </section>
    <script>
    (function () {{  // vergangene Tage ausblenden (die Seite kann bis zu einem Tag alt sein)
      var h = new Date(), t = h.getFullYear() + "-" + ("0" + (h.getMonth() + 1)).slice(-2) + "-" + ("0" + h.getDate()).slice(-2);
      [].forEach.call(document.querySelectorAll(".diese-woche li[data-date]"), function (li) {{
        if (li.getAttribute("data-date") < t) li.remove();
        else if (li.getAttribute("data-date") === t) li.querySelector(".dw-tag").textContent = "heute";
      }});
      [].forEach.call(document.querySelectorAll(".diese-woche .dw-spalte"), function (s) {{ if (!s.querySelector("li")) s.remove(); }});
      [].forEach.call(document.querySelectorAll(".diese-woche ul"), function (u) {{
        [].slice.call(u.children, {DIESE_WOCHE_MAX}).forEach(function (li) {{ li.remove(); }});
      }});
      var box = document.querySelector(".diese-woche"); if (box && !box.querySelector("li")) box.remove();
    }})();
    </script>"""


DIESE_WOCHE_CSS = """<style>
  .diese-woche { margin: 0 0 1.2rem; padding: 0.9rem 1.2rem 1rem; border-radius: 12px; border: 1px solid var(--border, #e3e7ee);
    background: var(--soft, #f5f7fa); }
  .diese-woche > h2 { margin: 0 0 0.5rem; font-size: 1.15rem; }
  .dw-raster { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.6rem 1.6rem; }
  .dw-spalte h3 { margin: 0 0 0.3rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em;
    color: color-mix(in srgb, var(--text, #000) 60%, transparent); }
  .dw-spalte ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; font-size: 0.92rem; line-height: 1.35; }
  .dw-tag { display: inline-block; min-width: 4.6rem; font-weight: 600; font-variant-numeric: tabular-nums; }
  .dw-km { font-size: 0.8rem; color: color-mix(in srgb, var(--text, #000) 55%, transparent); white-space: nowrap; }
  .dw-mehr { display: inline-block; margin-top: 0.35rem; font-size: 0.85rem; }
</style>"""


def geburtstag_html(heute=None):
    leute = geburtstage_heute(heute)
    if not leute:
        return ""
    teile = [f"<strong>{htmllib.escape(n)}</strong> wird heute {a}" for n, a in leute]
    satz = teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " und " + teile[-1]
    konfetti = GEBURTSTAG_JS.replace("__TAG__", (heute or TODAY).isoformat()) if GEBURTSTAG_KONFETTI else ""
    return f"""<section class="geburtstag" aria-label="Geburtstag">
      <span class="gb-torte" aria-hidden="true">🎂</span>
      <p>{satz}! <span class="gb-gruss">{htmllib.escape(GEBURTSTAG_TEXT)}</span></p>
    </section>{konfetti}"""


GEBURTSTAG_CSS = """<style>
  .geburtstag { display: flex; align-items: center; gap: 0.9rem; margin: 0 0 1rem; padding: 0.8rem 1.1rem;
                border-radius: 12px; border: 1px solid var(--border, #e3e7ee); background: var(--soft, #f5f7fa);
                box-shadow: inset 4px 0 0 #e8b931; }
  .geburtstag p { margin: 0; line-height: 1.5; }
  .gb-torte { font-size: 2rem; line-height: 1; }
  .gb-gruss { color: color-mix(in srgb, var(--text, #000) 70%, transparent); }
  .gb-schnipsel { position: fixed; top: -12px; width: 8px; height: 13px; border-radius: 2px; z-index: 9999;
                  pointer-events: none; animation: gb-fall var(--d) cubic-bezier(.3,.6,.5,1) forwards; }
  @keyframes gb-fall { to { transform: translate(var(--x), 105vh) rotate(var(--r)); opacity: 0.2; } }
</style>"""

# Einmal pro Tag und Browser, ca. 2,5 s, ohne Konfetti bei "Animationen reduzieren"
GEBURTSTAG_JS = """<script>
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var tag = "__TAG__";
  try { if (localStorage.getItem("gb-konfetti") === tag) return; localStorage.setItem("gb-konfetti", tag); } catch (e) {}
  var farben = ["#e8b931", "#6fa3e8", "#1c2d52", "#ffffff", "#e8b931"];
  for (var i = 0; i < 45; i++) {
    var s = document.createElement("span");
    s.className = "gb-schnipsel";
    s.style.left = (Math.random() * 100) + "vw";
    s.style.background = farben[i % farben.length];
    s.style.setProperty("--x", (Math.random() * 160 - 80) + "px");
    s.style.setProperty("--r", (Math.random() * 720 - 360) + "deg");
    s.style.setProperty("--d", (1.8 + Math.random() * 1.2) + "s");
    s.style.animationDelay = (Math.random() * 0.6) + "s";
    document.body.appendChild(s);
    setTimeout(function (el) { return function () { el.remove(); }; }(s), 3600);
  }
})();
</script>"""


def build_index(upcoming_events, home_news_snippets, teams=()):
    """Startseite – Aufbau, Texte und Bilder-Ordner: startseite.py"""
    ausfall_json = json.dumps(read_ausfall(), ensure_ascii=False).replace("<", "\\u003c")
    home_js = (HOME_JS.replace("__AUSFALL__", ausfall_json)
               .replace("__PAUSE_BAND__", "true" if PAUSE_BAND else "false")
               .replace("__PAUSE_VORLAUF__", str(int(PAUSE_VORLAUF_TAGE))))

    # Termine ab heute (das Skript blendet vergangene aus und zeigt nur die ersten)
    events = [ev for ev in upcoming_events if ev["date"] >= TODAY][:startseite.TERMINE_ANZAHL + 4]

    # Letztes Ergebnis je Mannschaft
    zeilen = []
    for d in teams:
        m = liga.letztes_spiel(d)
        if not m:
            continue
        heim, gegner, mein, sein, art = liga.sicht(d, m)
        datei = liga.seite_datei(d)
        zeilen.append((d["kurz"], "team-" + datei[:-5], ("vs. " if heim else "bei ") + gegner,
                       liga.zahl(mein), liga.zahl(sein), art, m["r"], datei))

    # Geburtstage der nächsten Tage mit Alter
    geburtstage = []
    for i in range(startseite.GEBURTSTAG_TAGE + 1):
        tag = TODAY + datetime.timedelta(days=i)
        geburtstage += [(tag, n, a) for n, a in geburtstage_heute(tag)]
    konfetti = (GEBURTSTAG_JS.replace("__TAG__", TODAY.isoformat())
                if GEBURTSTAG_KONFETTI and geburtstage_heute() else "")

    content, styles = startseite.seite(
        events, ALLE_BERICHTE, zeilen, geburtstage, fetch_member_count(), len(teams) or MANNSCHAFTEN_FALLBACK,
        team_klasse, plain_text, extra_oben=read_hinweis())
    render_page("Startseite", content + home_js + konfetti, "index.html",
                extra_styles=styles + "<style>" + HINWEIS_CSS + "</style>" + GEBURTSTAG_CSS)


# ==========================================
# 8. SITEMAP & 404-SEITE
# ==========================================
def build_404():
    content = f"""
    <h1>Seite nicht gefunden</h1>
    <p>Diese Seite gibt es leider nicht (mehr). Vielleicht hilft dir einer dieser Links weiter:</p>
    <p>
      <a href="{SITE_URL}index.html" class="btn">Zur Startseite</a>
      <a href="{SITE_URL}termine.html" style="margin-left:1rem;">Zu den Terminen →</a>
    </p>
    """
    # Absolute Pfade, weil die 404-Seite unter beliebigen Adressen angezeigt werden kann
    render_page("Seite nicht gefunden", content, "404.html", css_path=SITE_URL, nav_path=SITE_URL)


def build_sitemap():
    pages = sorted(glob.glob("*.html")) + sorted(glob.glob("berichte/*.html"))
    urls = []
    for path in pages:
        name = path.replace(os.sep, "/")
        if name == "404.html" or name in WEITERLEITUNGEN:
            continue
        loc = SITE_URL if name == "index.html" else SITE_URL + quote(name)
        last = git_last_date(path)
        lastmod = f"<lastmod>{last.isoformat()}</lastmod>" if last else ""
        urls.append(f"  <url><loc>{htmllib.escape(loc)}</loc>{lastmod}</url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(xml)


def jugend_kurznamen():
    return {t.get("kurz") or t["name"] for t in jugend.TEAMS}


# ==========================================
# SAISONS (aktuelle + Archiv aus mannschaften/archiv/<Startjahr>/)
# ==========================================
SAISON_ORDNER = "saison"          # Archivseiten: saison/2022-23/afk-1.html


def saison_text(jahr):
    return f"{jahr}/{(jahr + 1) % 100:02d}"


def saison_slug(jahr):
    return f"{jahr}-{(jahr + 1) % 100:02d}"


def saisons_laden():
    """-> (aktuelles Startjahr, aktuelle Teams, {Jahr: Teams} fürs Archiv).
    Aktuell = neuestes saison_jahr in mannschaften/*.json; ältere Dateien dort (z. B. eine
    Mannschaft, die es in der neuen Saison nicht mehr gibt) werden nicht als aktuell gezeigt."""
    teams = liga.lade_teams()
    jahre = [d.get("saison_jahr") for d in teams if d.get("saison_jahr")]
    aktuell = max(jahre) if jahre else (TODAY.year if (TODAY.month, TODAY.day) >= (10, 1) else TODAY.year - 1)
    teams = [d for d in teams if d.get("saison_jahr") in (None, aktuell)]
    archiv = {}
    for ordner in sorted(glob.glob(os.path.join(liga.DATEN_ORDNER, "archiv", "*"))):
        name = os.path.basename(ordner)
        if not name.isdigit() or int(name) >= aktuell:
            continue
        ts = liga.lade_teams(ordner)
        for d in ts:
            d["archiv"] = True
            d["saison_jahr"] = int(name)
            d.setdefault("saison_text", saison_text(int(name)))
        if ts:
            archiv[int(name)] = ts
    for d in teams:
        d["saison_jahr"] = aktuell
    return aktuell, teams, archiv


def seiten_pfad(d, aktuell):
    """Pfad der Teamseite ab Website-Wurzel."""
    datei = liga.seite_datei(d)
    return datei if d["saison_jahr"] == aktuell else f"{SAISON_ORDNER}/{saison_slug(d['saison_jahr'])}/{datei}"


def saisons_verknuepfen(aktuell, teams, archiv):
    """Setzt je Team: saisons (Umschalter), historie (Reiter Saisons), aktuell_url (Archiv-Hinweis)."""
    alle = {aktuell: teams, **archiv}
    nach_key = {}
    for jahr, ts in alle.items():
        for d in ts:
            nach_key.setdefault(d["key"], {})[jahr] = d
    for jahr, ts in alle.items():
        wurzel = "" if jahr == aktuell else "../../"
        for d in ts:
            andere = nach_key[d["key"]]
            d["saisons"] = [(saison_text(j), wurzel + seiten_pfad(andere[j], aktuell), j == jahr)
                            for j in sorted(andere, reverse=True)]
            d["historie"] = [{"saison": saison_text(j), "href": wurzel + seiten_pfad(andere[j], aktuell),
                              "d": andere[j]} for j in sorted(andere, reverse=True)]
            ber = historie.bereich_von(d.get("kurz", ""))
            d["geschichte_url"] = wurzel + "geschichte.html" + (f"#{ber['key']}" if ber else "#mannschaften")
            if jahr != aktuell:
                d["aktuell_url"] = wurzel + (seiten_pfad(andere[aktuell], aktuell) if aktuell in andere
                                             else "mannschaften.html")


def build_spieler(aktuell, teams, archiv):
    """Spielerseiten (spieler/*.html) über alle Saisons; alte Seiten von Spielern, die nicht mehr
    vorkommen, werden gelöscht. Muss VOR den Teamseiten laufen (liga.SPIELER_SEITEN)."""
    alle_teams = teams + [d for ts in archiv.values() for d in ts]
    alle = spieler.sammeln(alle_teams, lambda d: seiten_pfad(d, aktuell), liga.name_von)
    liga.SPIELER_SEITEN = {spieler.seite(p["name"]) for p in alle.values()}
    try:
        dsb = dsb_liste()
    except Exception as e:
        print(f"Hinweis: DSB-Liste nicht abrufbar ({e}) - Spielerseiten mit DWZ aus der Meldeliste.")
        dsb = []
    os.makedirs(spieler.ORDNER, exist_ok=True)
    for alt in glob.glob(os.path.join(spieler.ORDNER, "*.html")):
        if alt.replace(os.sep, "/") not in liga.SPIELER_SEITEN:
            os.remove(alt)
    ACTIVE_PARENT.update({os.path.basename(x): "mannschaften.html" for x in liga.SPIELER_SEITEN})
    n = spieler.bauen(alle, dsb, render_page, liga.STYLES, aktuell, berichte=ALLE_BERICHTE,
                      tour_seiten=turnierorte.seite_fuer_name, geburtstage=_geburtstag_liste(), konten=konten.PROFILE,
                      tour_box=lambda name: (lambda u: turnierorte.profil_box(u) if u else "")(turnierorte.uebersicht_fuer_name(name)))
    print(f"Spielerseiten: {n}")


def build_archiv(aktuell, archiv):
    """saison/<2022-23>/mannschaften.html + Teamseiten jeder abgeschlossenen Saison.
    Rückgabe: Saison-Umschalter für die aktuelle mannschaften.html."""
    alle_jahre = sorted([aktuell, *archiv], reverse=True)
    for jahr, ts in archiv.items():
        ordner = os.path.join(SAISON_ORDNER, saison_slug(jahr))
        os.makedirs(ordner, exist_ok=True)
        liga.WURZEL = "../../"
        try:
            saisons = [(saison_text(j), "../../mannschaften.html" if j == aktuell
                        else f"../{saison_slug(j)}/mannschaften.html", j == jahr) for j in alle_jahre]
            content, styles = liga.uebersicht_seite(ts, saisons, {"saison_text": saison_text(jahr),
                                                                  "aktuell_url": "../../mannschaften.html"})
            render_page(f"Mannschaften {saison_text(jahr)}", content, os.path.join(ordner, "mannschaften.html"),
                        css_path="../../", nav_path="../../", extra_styles=styles)
            for d in ts:
                titel, datei, content, styles, beschreibung = liga.team_seite(d)
                ACTIVE_PARENT.setdefault(datei, "mannschaften.html")
                render_page(titel, content, os.path.join(ordner, datei), css_path="../../", nav_path="../../",
                            extra_styles=styles, description=beschreibung)
        finally:
            liga.WURZEL = ""
    for alt in glob.glob(os.path.join(SAISON_ORDNER, "*")):   # Saisons, die es nicht mehr gibt
        if os.path.basename(alt) not in {saison_slug(j) for j in archiv}:
            shutil.rmtree(alt, ignore_errors=True)
    return [(saison_text(j), "mannschaften.html" if j == aktuell
             else f"{SAISON_ORDNER}/{saison_slug(j)}/mannschaften.html", j == aktuell) for j in alle_jahre]


def build_mannschaften(teams, saisons=None):
    """mannschaften.html (Übersicht) + eine Seite pro Team aus mannschaften/*.json.
    Jugendteams (siehe jugend.TEAMS) bekommen eine Teamseite, stehen in der Übersicht aber
    nur gesammelt auf der Jugend-Karte. Ohne Daten bleibt die handgeschriebene seiten/mannschaften.html."""
    if not teams:
        return False
    jkurz = jugend_kurznamen()
    content, styles = liga.uebersicht_seite([d for d in teams if d["kurz"] not in jkurz], saisons)
    render_page("Mannschaften", content, "mannschaften.html", extra_styles=styles)
    for d in teams:
        if d["kurz"] in jkurz:
            d["zurueck_url"], d["zurueck_text"] = "jugend.html", "Jugend"
        titel, datei, content, styles, beschreibung = liga.team_seite(d)
        ACTIVE_PARENT[datei] = "jugend.html" if d["kurz"] in jkurz else "mannschaften.html"
        render_page(titel, content, datei, extra_styles=styles, description=beschreibung)
    return True


def alle_termin_eintraege(today=TODAY):
    """Alle kommenden Termine aller Spalten (für die Mail-Benachrichtigungen): [{datum, zeit, spalte, text}]."""
    pfad = os.path.join("termine", "termine.typ")
    if not os.path.exists(pfad):
        return []
    with open(pfad, "r", encoding="utf-8") as f:
        parsed = parse_typst_table(f.read())
    assign_dates(parsed['rows'])
    kopf = [plain_text(h).strip() for h in parsed['header'] or []]
    out = []
    for r in parsed['rows']:
        if r['kind'] != 'row' or not r.get('date') or r['date'] < today:
            continue
        zeit = re.search(r'(\d{1,2}:\d{2})', plain_text(r['cells'][0]['text'])) if r['cells'] else None
        spalte = 0
        for c in r['cells']:
            if spalte > 0 and spalte < len(kopf) and c['colspan'] == 1:
                text = plain_text(c['text']).strip()
                if text:
                    out.append({'datum': r['date'], 'zeit': zeit.group(1) if zeit else "", 'spalte': kopf[spalte], 'text': text})
            spalte += c['colspan']
    return out


def spalten_termine(spalte, today=TODAY):
    """Kommende Termine aus einer Spalte (z. B. "Jugend", "Senioren") in termine/termine.typ."""
    pfad = os.path.join("termine", "termine.typ")
    if not os.path.exists(pfad):
        return []
    with open(pfad, "r", encoding="utf-8") as f:
        parsed = parse_typst_table(f.read())
    if spalte not in parsed['header']:
        print(f"Hinweis: Spalte '{spalte}' fehlt in {pfad}.")
        return []
    idx = parsed['header'].index(spalte)
    assign_dates(parsed['rows'])
    events = []
    for r in parsed['rows']:
        if r['kind'] != 'row' or not r.get('date') or r['date'] < today or len(r['cells']) <= idx:
            continue
        title = r['cells'][idx]['text']
        if title and not re.search(r'spiel?frei', title, re.I):
            events.append({'date': r['date'], 'when': re.sub(r'</?(?:b|strong)\b[^>]*>', '', r['cells'][0]['text']), 'title': title, 'who': ''})
    return events


WEITERLEITUNGEN = set()          # alte Adressen, die nur weiterleiten (nicht in die Sitemap)


def weiterleitung(alt, neu):
    """Kleine Seite unter der alten Adresse, die sofort auf die neue weiterleitet (alte Links bleiben gültig)."""
    WEITERLEITUNGEN.add(alt)
    with open(alt, "w", encoding="utf-8") as f:
        f.write(f'<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><meta name="robots" content="noindex">'
                f'<meta http-equiv="refresh" content="0; url={neu}"><link rel="canonical" href="{neu}">'
                f'<title>Weiterleitung</title></head><body><a href="{neu}">Weiter zu {neu}</a></body></html>')


def build_historie(aktuell, teams, archiv):
    """Eine Seite für alles: Vereinsgeschichte (Chronik) + Mannschaftshistorie."""
    pdf = "dokumente/historie.pdf" if os.path.exists(os.path.join(DOKUMENTE_ORDNER, "historie.typ")) else ""
    content, styles = historie.seite(aktuell, teams, archiv, lambda d, a: seiten_pfad(d, a), geschichte_chronik(), pdf)
    render_page(historie.TITEL, content, historie.SEITE, extra_styles=styles + GESCHICHTE_CSS,
                description="Die Geschichte der SG Aschheim/Feldkirchen/Kirchheim von 1952 bis heute: Chronik, "
                            "Meilensteine und welche Mannschaft wann in welcher Liga spielte.")
    weiterleitung(historie.ALTE_SEITE, f"{historie.SEITE}#mannschaften")


def build_jugend(termine, liga_seiten=None, erfolge=None):
    berichte = [r for r in ALLE_BERICHTE if "jugend" in r['kategorien']]
    if erfolge:
        jugend.ERFOLGE = erfolge + [e for e in jugend.ERFOLGE_EXTRA if e not in erfolge]
    beitrag = next((preis for wer, preis in BEITRAEGE if "Kinder" in wer), "")
    content, styles = jugend.seite(termine, berichte, beitrag, liga_seiten)
    render_page("Jugend", content, "jugend.html", extra_styles=styles)


def build_senioren(termine):
    berichte = [r for r in ALLE_BERICHTE if "senioren" in r['kategorien']]
    content, styles = senioren.seite(termine, berichte)
    render_page("Senioren", content, "senioren.html", extra_styles=styles)


def build_faq():
    adresse = SPIELORT.split(", ", 1)[-1]
    content, styles = faq.seite(BEITRAEGE, adresse)
    render_page("Häufige Fragen", content, "faq.html", extra_styles=styles)


def build_static_pages(skip=()):
    """Baut die handgeschriebenen Seiten aus seiten/<name>.html in die Vorlage ein."""
    for name, title in STATIC_PAGES:
        if name in skip:
            continue
        src = os.path.join("seiten", f"{name}.html")
        if not os.path.exists(src):
            print(f"Hinweis: {src} fehlt, Seite wird übersprungen.")
            continue
        with open(src, "r", encoding="utf-8") as f:
            raw = f.read()
        style_re = r'<style[^>]*>.*?</style>'
        styles = "".join(re.findall(style_re, raw, re.DOTALL))
        content = re.sub(style_re, '', raw, flags=re.DOTALL).strip()
        render_page(title, content, f"{name}.html", extra_styles=styles)


# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # Teams zuerst laden: das Untermenü "Mannschaften" steht auf jeder Seite
    aktuell, teams, archiv = saisons_laden()
    SUBNAV["mannschaften.html"] = [(liga.seite_datei(d), d["kurz"]) for d in teams if d["kurz"] not in jugend_kurznamen()]
    SUBNAV["mannschaften.html"].append((historie.SEITE + "#mannschaften", "Historie"))
    if os.environ.get("GITHUB_ACTIONS"):     # in der Verwaltung angenommene AFK-on-Tour-Anträge eintragen (vor den Spielerseiten)
        try:
            import turnierorte_pruefen
            turnierorte_pruefen.aenderungen_anwenden()      # Bearbeiten in der Verwaltung
            turnierorte_pruefen.angenommene_eintragen()
            turnierorte_pruefen.pruefliste()               # Fehler/Hinweise für die Verwaltung
        except Exception as e:
            print(f"AFK on Tour: angenommene Anträge nicht eingetragen ({type(e).__name__}: {e})")
    # Mitgliederbereich: Liste abgleichen, öffentliche Profile holen (vor Startseite und Spielerseiten)
    konten.synchronisieren(_geburtstag_liste(), spieler.slug)
    konten.laden()
    konten.seiten_bauen(render_page)
    WEITERLEITUNGEN.update({"mein-profil.html", "verwaltung.html", "listen.html", "umfrage.html", "mitmachen.html"})   # nicht in die Sitemap
    build_chessresults()
    if senioren.LIGA_TEAM_KURZ not in {d["kurz"] for d in teams}:   # Senioren ohne Tabellenrechner-Daten: eigene Seite
        SUBNAV["mannschaften.html"].append(("senioren.html", "Senioren"))
    build_dokumente()
    upcoming = build_termine()
    build_oberlandquartett()
    build_blitzjahreswertung()
    build_hall_of_fame()
    turnierkalender.bauen(render_page, skript_url=einreichen.SKRIPT_URL)   # vor den Übersichten: die Karte "Extern" zeigt die Anzahl
    suche.zusatz(turnierkalender.SEITE, " · ".join(f"{e['name']} {e.get('ort', '')}" for e in turnierkalender.LETZTE_EVENTS))
    turnierorte.bauen(render_page, einreichen.SKRIPT_URL, ACTIVE_PARENT)
    build_turniere_overview()
    build_ausschreibungen()
    build_ueber_uns()
    news = build_berichte()
    saisons_verknuepfen(aktuell, teams, archiv)
    # Einsätze früherer Saisons für die Prognose (Gewichtung siehe aufstellung.py)
    ereignisse = {j: liga.auf.saison_ereignisse(ts) for j, ts in archiv.items()}
    for d in teams:
        d["historie_ereignisse"] = [(aktuell - j, ev) for j, ev in ereignisse.items()]
    liga.VEREIN_INDEX = liga.auf.verein_index(teams)
    liga_seiten = {d["kurz"]: liga.seite_datei(d) for d in teams}
    j_termine = spalten_termine(jugend.TERMINE_SPALTE)
    build_jugend(j_termine, liga_seiten,
                 historie.erfolge(aktuell, teams, archiv, lambda d, a: seiten_pfad(d, a), ("u20", "u16", "u14")))
    s_termine = spalten_termine(senioren.TERMINE_SPALTE)
    extra = []
    # Senioren mit Daten vom Tabellenrechner -> volle Teamseite (senioren.html) aus liga.py
    if senioren.LIGA_TEAM_KURZ not in liga_seiten:
        build_senioren(s_termine)
        extra.append(senioren.mannschaften_karte(s_termine))
    build_faq()
    liga.EXTRA_KARTEN = extra + [jugend.mannschaften_karte(j_termine), historie.karte()]
    build_historie(aktuell, teams, archiv)
    build_spieler(aktuell, teams, archiv)
    saisons = build_archiv(aktuell, archiv)
    build_index(upcoming, news, teams)
    build_404()
    build_static_pages(skip={"mannschaften"} if build_mannschaften(teams, saisons) else set())
    suche.bauen(render_page)   # nach allen Seiten (Suchindex)
    # Profil: "Berichte, in denen du vorkommst" (öffentliche Daten, das Profil filtert im Browser)
    with open(os.path.join("spieler", "meine.json"), "w", encoding="utf-8") as f:
        json.dump(benachrichtigung.meine_json(ALLE_BERICHTE, spieler.slug), f, ensure_ascii=False)
    # Mail-Benachrichtigungen: Neuigkeiten seit dem letzten Build ans Apps Script (nur im GitHub-Build)
    benachrichtigung.melden(alle_termin_eintraege(), read_ausfall(), ALLE_BERICHTE, ausschreibungen_eintraege(), teams,
                            SITE_URL, spieler.slug, liga.seite_datei,
                            lambda ev: konten._post({"typ": "n_ereignisse", "s": konten._schluessel(), "ereignisse": ev}) if konten._schluessel() else None)
    build_sitemap()   # zuletzt, damit alle erzeugten Seiten enthalten sind
    print("Build erfolgreich abgeschlossen!")
