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
NEXT_EVENTS_COUNT = 8

# Wie viele Termin-Karten gleichzeitig sichtbar sind
HOME_EVENTS_VISIBLE = 4

# Öffentliche Adresse der Seite (für Kalender-Links)
SITE_URL = "https://sgaschheimfeldkirchenkirchheim.github.io/schachverein-website/"

# Kalender-Export
CAL_TZ = "Europe/Berlin"
EVENT_DURATION_HOURS = 3          # Standarddauer für Termine mit Uhrzeit
SPIELORT = "Gymnasium Kirchheim, Heimstettner Str. 20, 85551 Kirchheim"

TODAY = datetime.date.today()

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
    "mannschaften.html": "Unsere Mannschaften mit Links zu Ligen, Tabellen und Ergebnissen.",
    "berichte.html": "Aktuelle Berichte und News aus dem Vereinsleben der SG AFK: Turniere, Mannschaftskämpfe und mehr.",
    "turniere.html": "Turniere der SG AFK: Oberlandquartett, Blitzjahreswertung, Hall of Fame und Ausschreibungen.",
    "neu-hier.html": "Neu im Schachverein? Hier erfährst du, wann und wo wir spielen und wie du bei uns mitmachen kannst.",
    "kontakt.html": "Kontakt und Anfahrt zur SG Aschheim/Feldkirchen/Kirchheim im Gymnasium Kirchheim.",
    "ausschreibungen.html": "Alle Turnierausschreibungen der SG AFK als PDF zum Ansehen und Herunterladen.",
    "oberlandquartett.html": "Ergebnisse und Pokalstand des Oberlandquartetts.",
    "blitzjahreswertung.html": "Gesamtwertung der Blitzjahreswertung der SG AFK.",
    "vereinsintern.html": "Vereinsmeister und Sieger der vereinsinternen Turniere: die Hall of Fame der SG AFK.",
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
    ("termine.html", "Termine"),
    ("berichte.html", "Berichte"),
    ("turniere.html", "Turniere"),
    ("neu-hier.html", "Neu hier?"),
    ("kontakt.html", "Kontakt"),
]

# Unterseiten, bei denen im Menü der übergeordnete Reiter markiert wird
ACTIVE_PARENT = {
    "ausschreibungen.html": "turniere.html",
    "oberlandquartett.html": "turniere.html",
    "blitzjahreswertung.html": "turniere.html",
    "vereinsintern.html": "turniere.html",
}

# Handgeschriebene Seiten: Inhalt liegt in seiten/<name>.html
STATIC_PAGES = [
    ("ueber-uns", "Über uns"),
    ("mannschaften", "Mannschaften"),
    ("kontakt", "Kontakt &amp; Anfahrt"),
    ("impressum", "Impressum &amp; Datenschutz"),
]

# Header: Schriftzug links, Menü rechts, auf dem Handy Hamburger-Menü (ohne JavaScript)
GLOBAL_CSS = """<style>
      :root {
        --nav-accent: #f1c40f;   /* Farbe des aktiven Menüpunkts */
      }

      /* Skip-Link: erst sichtbar, wenn er per Tastatur (Tab) angesprungen wird */
      .skip-link { position: absolute; left: -999px; top: 0; background: #fff; color: var(--navy); padding: 0.5rem 1rem; z-index: 200; font-weight: bold; }
      .skip-link:focus { left: 0; }

      header { position: sticky; top: 0; z-index: 100; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.5rem 2rem; padding: 0.7rem max(1.25rem, calc((100% - 1200px) / 2)); text-align: left; }
      header .brand { display: flex; align-items: center; gap: 0.9rem; color: #fff; text-decoration: none; font-weight: bold; font-size: 1.2rem; line-height: 1.25; margin: 0; }

      header nav { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0.2rem 1.3rem; margin: 0; padding: 0; }
      header nav a { color: #fff; text-decoration: none; font-weight: bold; padding: 0.35rem 0; }
      header nav a:hover { color: var(--nav-accent); }
      nav a[aria-current="page"] { text-decoration: underline; text-decoration-color: var(--nav-accent); text-decoration-thickness: 3px; text-underline-offset: 8px; }

      .nav-toggle { position: absolute; opacity: 0; pointer-events: none; }
      .nav-burger { display: none; cursor: pointer; padding: 0.6rem; margin-left: auto; }
      .nav-burger span, .nav-burger span::before, .nav-burger span::after { display: block; width: 26px; height: 3px; background: #fff; border-radius: 2px; position: relative; content: ""; transition: transform 0.2s, background 0.2s; }
      .nav-burger span::before { position: absolute; top: -8px; }
      .nav-burger span::after { position: absolute; top: 8px; }
      .nav-toggle:checked ~ .nav-burger span { background: transparent; }
      .nav-toggle:checked ~ .nav-burger span::before { transform: translateY(8px) rotate(45deg); }
      .nav-toggle:checked ~ .nav-burger span::after { transform: translateY(-8px) rotate(-45deg); }
      .nav-toggle:focus-visible ~ .nav-burger { outline: 2px solid var(--nav-accent); border-radius: 4px; }

      @media (max-width: 960px) {
        header { gap: 0.3rem 1rem; }
        header .brand { font-size: 1rem; }
        .nav-burger { display: block; }
        header nav { display: none; width: 100%; flex-direction: column; flex-wrap: nowrap; gap: 0; padding-bottom: 0.5rem; }
        .nav-toggle:checked ~ nav { display: flex; }
        header nav a { padding: 0.7rem 0; border-top: 1px solid rgba(255,255,255,0.15); }
        nav a[aria-current="page"] { text-underline-offset: 5px; }
      }

      .footer-link { color: #aaa; }
    </style>"""


# ==========================================
# 1. HELPER: RENDER PAGE MIT TEMPLATE
# ==========================================
def build_nav(nav_path, active):
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ''
        links.append(f'<a href="{nav_path}{href}"{cur}>{label}</a>')
    return "\n      ".join(links)


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
        nav=build_nav(nav_path, active),
        extra_styles=GLOBAL_CSS + extra_styles,
        logo=logo,
        head_icon=head_icon,
        description=desc,
        og_image_tag=og_image_tag,
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_html)


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

    txt = re.sub(r'#strong\s*\(\s*"(.*?)"\s*\)', r'\1', txt, flags=re.DOTALL)
    txt = re.sub(r'#align\s*\([^)]*\)\[(.*)\]', r'\1', txt, flags=re.DOTALL)
    txt = re.sub(r'#(?:strong|underline|emph)\[(.*)\]', r'\1', txt, flags=re.DOTALL)
    txt = txt.replace('*', '').strip()
    return htmllib.escape(txt, quote=False)


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


def render_table_inner_html(parsed, today=TODAY):
    out = []
    if parsed['header']:
        out.append('<thead><tr>' + ''.join(f'<th>{h}</th>' for h in parsed['header']) + '</tr></thead>')
    out.append('<tbody>')
    for r in parsed['rows']:
        if r['kind'] == 'month':
            out.append(f'<tr class="monat-row"><td colspan="{r["colspan"]}" class="monat-header">{r["text"]}</td></tr>')
            continue
        past = r.get('date') is not None and r['date'] < today
        tr_cls = ' class="past"' if past else ''
        tds = []
        for c in r['cells']:
            cls = f' class="bg-{c["fill"].lower()}"' if c['fill'] else ''
            span = f' colspan="{c["colspan"]}"' if c['colspan'] > 1 else ''
            tds.append(f'<td{cls}{span}>{c["text"]}</td>')
        out.append(f'<tr{tr_cls}>' + ''.join(tds) + '</tr>')
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
            f'<a href="{webcal_base}kalender/{fname}"><span aria-hidden="true">📲</span> Abonnieren</a> '
            f'<a href="{https_url}" data-url="{https_url}" '
            f'onclick="navigator.clipboard.writeText(this.dataset.url);this.textContent=\'✓ Link kopiert\';return false;"><span aria-hidden="true">🔗</span> Link kopieren</a></li>'
        )
    return f"""
    <details class="kalender-box">
      <summary><span aria-hidden="true">📆</span> Termine im Handy-Kalender abonnieren</summary>
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
    return '<div class="hinweis-banner"><span aria-hidden="true">📢</span> ' + '<br>'.join(lines) + '</div>'


def build_turniere_overview():
    content = """
    <h1>Turniere & Ergebnisse</h1>
    <p>Hier findest du Übersichten zu unseren regionalen Wettkämpfen, die Gesamtwertung der Blitzschach-Serie sowie die Hall of Fame unserer Vereinsmeister.</p>
    
    <div class="grid-3" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-top:2rem;">
      
      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #3498db; border-radius:6px;">
        <h2>Oberlandquartett</h2>
        <p>Ergebnisse, Platzierungen und Rundenübersichten des traditionellen Oberlandquartetts.</p>
        <a href="oberlandquartett.html" class="btn" style="background:#3498db; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zum Oberlandquartett →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #e67e22; border-radius:6px;">
        <h2>Blitzjahreswertung</h2>
        <p>Die aktuelle Gesamtwertung und Zwischenstände unserer monatlichen Blitzschach-Turnierserie.</p>
        <a href="blitzjahreswertung.html" class="btn" style="background:#e67e22; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Blitzjahreswertung →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #27ae60; border-radius:6px;">
        <h2><span aria-hidden="true">🥇</span> Vereinsintern & Hall of Fame</h2>
        <p>Die historischen Vereinsmeister, Blitzschach-Champions und Pokalsieger unseres Vereins auf einen Blick.</p>
        <a href="vereinsintern.html" class="btn" style="background:#27ae60; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Hall of Fame →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #8e44ad; border-radius:6px;">
        <h2><span aria-hidden="true">📄</span> Ausschreibungen</h2>
        <p>Alle Turnierausschreibungen als PDF zum Ansehen und Herunterladen.</p>
        <a href="ausschreibungen.html" class="btn" style="background:#8e44ad; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zu den Ausschreibungen →</a>
      </div>

    </div>
    """
    render_page("Turniere & Ergebnisse", content, "turniere.html")


# Zusätzliche Zellfarben
# Typst-Name (kleingeschrieben) -> (Hintergrund, Textfarbe), Werte aus package.typ
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


def build_termine():
    folder_path = "termine"
    main_typ = os.path.join(folder_path, "termine.typ")
    svg_path = os.path.join(folder_path, "output.svg")

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

    content = f"""{read_hinweis()}
    <h1>Termine & Spielplan</h1>
    {calendar_html}
    <div class="full-bleed">
      <div class="table-responsive">
        {table_html}
      </div>
    </div>"""

    styles = """<style>""" + FULL_BLEED_CSS + HINWEIS_CSS + """
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; text-align: center; }
      .svg-container svg { max-width: 100%; height: auto; background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
      .custom-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }
      .custom-tabelle th, .custom-tabelle td { padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }
      .custom-tabelle th { background-color: #1a252f; color: white; }
      .custom-tabelle td:first-child { white-space: nowrap; }
      .custom-tabelle td:nth-child(n+3) { white-space: nowrap; }
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
    </style>"""

    styles = styles.replace("</style>", farben_css() + "</style>")
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


def build_ausschreibungen():
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

    if entries:
        items = ""
        for e in entries:
            stand = f" · Stand {e['date'].strftime('%d.%m.%Y')}" if e['date'] else ""
            items += f"""
            <a class="pdf-card" href="{e['url']}" target="_blank" rel="noopener">
              <span class="pdf-icon" aria-hidden="true">📄</span>
              <span class="pdf-text"><strong>{e['label']}</strong><br><small>PDF · {e['size']} KB{stand}</small></span>
            </a>"""
        body = f'<div class="pdf-grid">{items}</div>'
    else:
        body = "<p>Aktuell sind keine Ausschreibungen vorhanden.</p>"

    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;"><span aria-hidden="true">📄</span> Ausschreibungen</h1>
    <p>Hier findest du die Ausschreibungen unserer Turniere. Ein Klick öffnet die PDF direkt.</p>
    {body}
    """
    styles = """<style>
      .pdf-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
      .pdf-card { display: flex; gap: 0.9rem; align-items: center; background: #f8f9fa; border-left: 4px solid #8e44ad; border-radius: 6px; padding: 1rem 1.2rem; text-decoration: none; color: #1a252f; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .pdf-card:hover { background: #eef1f8; }
      .pdf-icon { font-size: 1.8rem; }
      .pdf-card small { color: #777; }
    </style>"""
    render_page("Ausschreibungen", content, "ausschreibungen.html", extra_styles=styles)


def build_neu_hier():
    content = f"""
    <h1>Neu hier? So kommst du vorbei</h1>
    <p>Egal ob Einsteiger, Jugendlicher oder Turnierspieler: Komm einfach an einem Freitag bei uns vorbei.</p>

    <div class="neu-grid">
      <div class="neu-card">
        <h3><span aria-hidden="true">🕒</span> Wann?</h3>
        <p><strong>Jeden Freitag.</strong> Das Gebäude ist ab 18:00 Uhr geöffnet.</p>
        <ul>
          <li><strong>Jugendtraining:</strong> 18:00 – 19:30 Uhr</li>
          <li><strong>Erwachsene &amp; Spielabend:</strong> ab 19:30 Uhr (open end)</li>
        </ul>
        <p>Die Zeiten sind flexibel: Erwachsene dürfen schon ab 18:00 Uhr kommen, Jugendliche müssen um 19:30 Uhr nicht gehen.</p>
      </div>

      <div class="neu-card">
        <h3><span aria-hidden="true">📍</span> Wo?</h3>
           <p><strong>Gymnasium Kirchheim</strong><br>Heimstettner Str. 20<br>85551 Kirchheim</p>
        <a href="https://maps.app.goo.gl/L8YRrvs52HD5cpDCA" target="_blank" rel="noopener" class="btn" style="background:#3498db; display:inline-block; color:white; padding:0.5rem 1rem; text-decoration:none; border-radius:4px; font-size:0.9rem;"><span aria-hidden="true">📍</span> Auf Google Maps öffnen</a>
      </div>

      <div class="neu-card">
        <h3><span aria-hidden="true">♟️</span> Was erwartet dich?</h3>
        <ul>
          <li><strong>Hobbyspieler &amp; Einsteiger:</strong> zwanglos freie Partien, ohne Turnierdruck</li>
          <li><strong>Kinder &amp; Jugendliche:</strong> strukturiertes Jugendtraining für alle Alters- und Spielklassen</li>
          <li><strong>Mannschaftsschach:</strong> Teams von der E-Klasse bis zur Bezirksliga, für jedes Spielniveau</li>
        </ul>
        <a href="mannschaften.html">Unsere Teams →</a>
      </div>

      <div class="neu-card">
        <h3><span aria-hidden="true">📝</span> Mitglied werden</h3>
        <p>Gefällt es dir bei uns? Den Mitgliedsantrag kannst du hier herunterladen:</p>
        <a href="mitgliederantrag.pdf" download><span aria-hidden="true">📄</span> Mitgliedsantrag (PDF) →</a>
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
    render_page("Neu hier?", content, "neu-hier.html", extra_styles=styles)


# ==========================================
# 3. OBERLANDQUARTETT PARSER
# ==========================================
def compute_pokal_wins(teams_count, data_list):
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
            if streak[j] >= 3 or total[j] >= 5:
                wins.append((i, j))
                streak = [0] * teams_count
                total = [0] * teams_count

    return wins


def build_oberlandquartett():
    path = os.path.join("turniere", "oberlandquartett", "main.typ")
    if not os.path.exists(path):
        path = os.path.join("turniere", "oberlandquartett.typ")

    if not os.path.exists(path):
        content = "<p>Keine Daten für Oberlandquartett gefunden.</p>"
    else:
        with open(path, "r", encoding="utf-8") as f:
            content_code = f.read()

        teams_m = re.search(r'#let\s+teams\s*=\s*\((.*?)\)', content_code, re.DOTALL)
        teams = []
        if teams_m:
            teams = [t.strip().strip('"\'') for t in teams_m.group(1).split(',') if t.strip()]

        data = []
        data_block_m = re.search(r'#let\s+data\s*=\s*\((.*?)\n\s*\)', content_code, re.DOTALL)
        if data_block_m:
            raw_tuples = re.findall(r'\((.*?)\)', data_block_m.group(1), re.DOTALL)
            for raw_tuple in raw_tuples:
                parts = [p.strip() for p in raw_tuple.split(',') if p.strip()]
                if len(parts) >= 3:
                    datum = parts[0].strip('()"\'')
                    ausrichter = parts[1].strip('()"\'')
                    results = []
                    for res_val in parts[2:]:
                        res_val = res_val.strip('()"\'')
                        if res_val.isdigit():
                            results.append(int(res_val))
                        else:
                            results.append(res_val)
                    data.append((datum, ausrichter, results))

        pokal_wins = compute_pokal_wins(len(teams), data)

        html = ['<a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>']
        html.append('<h1 style="margin-top:1rem;">Oberlandquartett</h1>')
        html.append('<div class="table-responsive"><table class="oq-tabelle">')
        html.append('<thead><tr><th>Datum</th><th>Ausrichter</th>')
        for t in teams:
            html.append(f'<th>{t}</th>')
        html.append('</tr></thead><tbody>')

        for i, (datum, ausrichter, results) in enumerate(data):
            row_bg = '#eef1f8' if i % 2 == 1 else '#ffffff'
            html.append(f'<tr style="background-color: {row_bg};">')
            html.append(f'<td style="text-align:left;">{datum}</td>')
            html.append(f'<td style="text-align:left;">{ausrichter}</td>')

            for j, val in enumerate(results):
                is_win = (i, j) in pokal_wins
                bg_color = ""
                text_color = ""
                font_weight = "normal"

                if is_win:
                    bg_color = "background-color: #0a1f44;"
                    text_color = "color: white;"
                    font_weight = "bold"
                elif isinstance(val, int) and val == 1:
                    bg_color = "background-color: #ffd54a;"
                    font_weight = "bold"

                style = f'style="{bg_color} {text_color} font-weight:{font_weight};"' if bg_color or text_color or font_weight != "normal" else ""
                html.append(f'<td {style}>{val}</td>')

            html.append('</tr>')

        html.append('</tbody></table></div>')
        html.append('<p style="font-size:0.85rem; font-style:italic; margin-top:1rem; color:#555;">')
        html.append('Den Pokal gewinnt die Mannschaft, die entweder 3x hintereinander gewinnt oder insgesamt 5x.<br>')
        html.append('Nach dem Pokalgewinn beginnt die Zählung von vorne! Der Gewinner spendiert den neuen Pokal.')
        html.append('</p>')
        content = "\n".join(html)

    styles = """<style>
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; }
      .oq-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #0a1f44; }
      .oq-tabelle th, .oq-tabelle td { padding: 10px 12px; border: 1px solid #0a1f44; text-align: center; }
      .oq-tabelle th { background-color: #0a1f44; color: white; font-weight: bold; }
    </style>"""

    render_page("Oberlandquartett", content, "oberlandquartett.html", extra_styles=styles)


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


def build_blitzjahreswertung():
    folder_path = os.path.join("turniere", "blitzjahreswertung")
    main_typ = os.path.join(folder_path, "main.typ")
    tmp_dir = os.path.join(folder_path, "_tmp")

    code = ""
    if os.path.exists(main_typ):
        with open(main_typ, "r", encoding="utf-8") as f:
            code = f.read()

    # 1. SVG (Webansicht, Gesamtwertung auf einer Seite) und PDF (A4) kompilieren.
    #    Klappt das nicht (z. B. kein Typst installiert), bleiben die alten Dateien erhalten.
    if code:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            subprocess.run(["typst", "compile", "--input", "format=web", main_typ,
                            os.path.join(tmp_dir, "output-{p}.svg")], check=True)
            new_pages = glob.glob(os.path.join(tmp_dir, "output-*.svg"))
            if new_pages:
                for old in glob.glob(os.path.join(folder_path, "output*.svg")):
                    os.remove(old)
                for p in new_pages:
                    shutil.move(p, os.path.join(folder_path, os.path.basename(p)))
            subprocess.run(["typst", "compile", main_typ, BLITZ_PDF], check=True)
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
    if k and n > k:
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
      .tab-bar label { cursor: pointer; padding: 0.55rem 1.1rem; border-radius: 6px; background: #e8ecf3; color: #0a1f44; font-weight: bold; }
      .tab-bar label:hover { background: #d5dcea; }
      .tab-panel { display: none; }
      """ + active + """ { background: #0a1f44; color: #fff; }
      """ + show + """ { display: block; }""")

    pdf_link = (f'<p><a href="{BLITZ_PDF}" download>📄 Aktuelle Wertung als PDF herunterladen</a></p>'
                if os.path.exists(BLITZ_PDF) else "")

    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
        <h1 style="margin-top:1rem;">Blitzjahreswertung</h1>
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
      .custom-tabelle th { background-color: #0a1f44; color: white; font-weight: bold; }""" + tab_css + """
    </style>"""

    render_page("Blitzjahreswertung", content, "blitzjahreswertung.html", extra_styles=styles)

# ==========================================
# 5. HALL OF FAME PARSER
# ==========================================
def build_hall_of_fame():
    path = os.path.join("turniere", "vereinsintern", "main.typ")
    if not os.path.exists(path):
        path = os.path.join("turniere", "hall_of_fame.typ")

    if not os.path.exists(path):
        content = "<p>Keine Daten für Hall of Fame gefunden.</p>"
    else:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        data_block_m = re.search(r'#let\s+data\s*=\s*\((.*?)\n\s*\)', code, re.DOTALL)
        entries = []
        if data_block_m:
            raw_tuples = re.findall(r'\((.*?)\)', data_block_m.group(1), re.DOTALL)
            for raw_tuple in raw_tuples:
                parts = [p.strip().strip('"\'') for p in raw_tuple.split(',') if p.strip()]
                if len(parts) >= 3:
                    entries.append((parts[1], parts[2], parts[0]))

        html = ['<a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>']
        html.append('<h1 style="margin-top:1rem;">Vereinsinterne Turniere & Hall of Fame</h1>')
        html.append('<div class="table-responsive"><table class="hof-tabelle">')
        html.append('<thead><tr><th>Turnier</th><th>Jahr</th><th>Spieler</th></tr></thead><tbody>')

        for i, (turnier, jahr, spieler) in enumerate(entries):
            row_bg = '#eef1f8' if i % 2 == 1 else '#ffffff'
            html.append(f'<tr style="background-color: {row_bg};">')
            html.append(f'<td style="text-align:left;">{turnier}</td>')
            html.append(f'<td style="text-align:center;">{jahr}</td>')
            html.append(f'<td style="text-align:left;">{spieler}</td>')
            html.append('</tr>')

        html.append('</tbody></table></div>')
        content = "\n".join(html)

    styles = """<style>
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; }
      .hof-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #0a1f44; }
      .hof-tabelle th, .hof-tabelle td { padding: 10px 12px; border: 1px solid #0a1f44; }
      .hof-tabelle th { background-color: #0a1f44; color: white; font-weight: bold; text-align: center; }
    </style>"""

    render_page("Vereinsinterne Turniere & Hall of Fame", content, "vereinsintern.html", extra_styles=styles)


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
    """Typst-Auszeichnungen innerhalb eines Absatzes -> HTML."""
    t = htmllib.escape(text, quote=False)
    t = re.sub(r'#text\(([^)]*)\)\[([^\]]*)\]', _text_span, t)
    t = re.sub(r'#underline\[([^\]]*)\]', r'<u>\1</u>', t)
    t = re.sub(r'#strong\[([^\]]*)\]', r'<strong>\1</strong>', t)
    t = re.sub(r'#emph\[([^\]]*)\]', r'<em>\1</em>', t)
    t = re.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'<em>\1</em>', t)
    t = re.sub(r'#link\("((?:https?://|mailto:)[^"]+)"\)\[([^\]]*)\]',
               r'<a href="\1" target="_blank" rel="noopener">\2</a>', t)
    return t


IMG_RE = re.compile(r'^#image\(\s*"([^"]+)"\s*(?:,(.*))?\)\s*$')


def report_blocks(body, img=None):
    """Zerlegt den Berichtstext in HTML-Blöcke (Überschriften, Absätze, Listen, Bilder)."""
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

def typst_to_html_article(typst_text, img=None):
    def meta(name):
        m = re.search(r'#' + name + r'\[(.*?)\]', typst_text)
        return m.group(1).strip() if m else ""

    title = meta("title") or "Turnierbericht"
    date = meta("date")
    author = meta("author")

    body = re.sub(r'#(?:title|date|author|entwurf)\[.*?\]', '', typst_text)
    blocks = report_blocks(body, img)

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


def build_berichte():
    reports = []
    seen = {}

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
            title, date, author, body_html, snippet = typst_to_html_article(
                code, make_img_handler(filepath, slug, images))

            when = parse_german_date(date)
            if when is None:
                print(f"WARNUNG [{filepath}]: Datum fehlt oder ist nicht lesbar (erwartet TT.MM.JJJJ).")
            elif when > TODAY:
                print(f"WARNUNG [{filepath}]: Datum {date} liegt in der Zukunft (Tippfehler?).")

            meta = date + (f" · von {author}" if author and date else (f"von {author}" if author else ""))
            reports.append({
                'stem': slug,
                'filename': slug + ".html",
                'title': title,
                'meta': meta,
                'body': body_html,
                'snippet': snippet,
                'thumb': images[0] if images else "",
                'when': when or date_from_filename(slug) or datetime.date.min,
            })

        # Neueste zuerst
        reports.sort(key=lambda r: (r['when'], r['stem']), reverse=True)

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
        <p class="news-meta">{r['meta']}</p>
        <hr style="border:0; border-top:1px solid #eee; margin:1.5rem 0;">
        <div class="article-content">{r['body']}</div>
        """
        render_page(r['title'], article_content, os.path.join("berichte", r['filename']),
                    css_path="../", nav_path="../", extra_styles=article_styles,
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
    overview_content = "<h1>Aktuelle Berichte &amp; News</h1>" + body
    render_page("Berichte & News", overview_content, "berichte.html",
                extra_styles="<style>" + NEWS_CSS + "</style>")

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
HERO_TITLE = "Schach spielen in Aschheim, Feldkirchen &amp; Kirchheim"
# Alternative: "Schach im Münchner Osten"

# Mitgliederzahl vom Schachbund (Wertungsportal-API)
DSB_ZPS = "22061"                        # Vereinskennzahl (kann per DSB_VKZ überschrieben werden)
DSB_API_URL = "https://www.schachbund.de/wertungsportal-api/vereinsliste"
DSB_VEREIN_URL = f"https://www.schachbund.de/dwz-vereine/{DSB_ZPS}.html"
MEMBER_CACHE = "mitglieder_anzahl.txt"   # letzter erfolgreich gelesener Wert (mit committen)
MEMBER_FALLBACK = "80+"                  # falls Abruf scheitert und noch kein Cache existiert

# Zahlenleiste: (große Zahl/Wort, Beschriftung, Link oder None); {members} wird ersetzt
# ACHTUNG: Mannschaftszahl bitte prüfen, nur ein Platzhalter!
STATS = [
    ("{members}", "Mitglieder", DSB_VEREIN_URL),
    ("6", "Mannschaften", "mannschaften.html"),
]

# Wird im Browser ausgeführt, damit "heute / in 3 Tagen" und der nächste
# Freitag immer stimmen, auch wenn die Seite schon länger nicht neu gebaut wurde.
HOME_JS = """<script>
(function () {
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var AUSFALL = __AUSFALL__;   // Spielabend-Ausfälle aus ausfall.txt

  function two(x) { return ("0" + x).slice(-2); }
  function iso(d) { return d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate()); }
  function dm(d) { return two(d.getDate()) + "." + two(d.getMonth() + 1) + "."; }
  function rel(d) {
    var n = Math.round((d - today) / 86400000);
    if (n === 0) return "heute";
    if (n === 1) return "morgen";
    return "in " + n + " Tagen";
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
  var total = 0, shown = 0;
  document.querySelectorAll(".event-card[data-date]").forEach(function (c) {
    total++;
    var p = c.dataset.date.split("-");
    var d = new Date(+p[0], p[1] - 1, +p[2]);
    if (d < today || shown >= max) { c.style.display = "none"; return; }
    var r = c.querySelector(".ev-rel");
    if (r) r.textContent = rel(d);
    if (shown === 0) c.classList.add("next");
    shown++;
  });
  var empty = document.getElementById("events-empty");
  if (empty && total > 0 && shown === 0) empty.hidden = false;

  // Nächster Spielabend: jeden Freitag, außer an Ausfalltagen
  var el = document.getElementById("spielabend");
  if (el) {
    var f = new Date(today);
    f.setDate(f.getDate() + ((5 - f.getDay() + 7) % 7));
    var skipped = [];
    var hit = blocked(f);
    while (hit && skipped.length < 30) {
      skipped.push({ d: new Date(f), reason: hit.reason });
      f.setDate(f.getDate() + 7);
      hit = blocked(f);
    }

    el.textContent = "";
    var icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "🗓️ ";
    el.appendChild(icon);

    if (hit) {
      el.appendChild(document.createTextNode("Aktuell kein Spielabend" + (hit.reason ? ": " + hit.reason : "")));
    } else {
      el.appendChild(document.createTextNode(
        "Nächster Spielabend: Freitag, " + dm(f) + " ab 18:00 Uhr (" + rel(f) + ")"));
      if (skipped.length) {
        var first = skipped[0], last = skipped[skipped.length - 1];
        var why = first.reason ? " (" + first.reason + ")" : "";
        var note = document.createElement("span");
        note.className = "spielabend-note";
        note.textContent = skipped.length === 1
          ? "Am " + dm(first.d) + " kein Spielabend" + why
          : "Vom " + dm(first.d) + " bis " + dm(last.d) + " kein Spielabend" + why;
        el.appendChild(document.createElement("br"));
        el.appendChild(note);
      }
    }
    el.hidden = false;
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


def fetch_member_count():
    """Anzahl aller Einträge der DSB-Vereinsliste; bei Fehlern letzter gespeicherter Wert, sonst Fallback."""
    try:
        token = get_secret("DSB_TOKEN")
        if not token:
            raise ValueError("kein DSB_TOKEN gesetzt")
        query = urllib.parse.urlencode({"token": token, "vkz": get_secret("DSB_VKZ", DSB_ZPS)})
        req = urllib.request.Request(
            f"{DSB_API_URL}?{query}",
            headers={"User-Agent": "Mozilla/5.0 (SG-AFK Website-Build)", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))

        if isinstance(data, dict):                       # z. B. {"members": [...]} -> längste Liste nehmen
            lists = [v for v in data.values() if isinstance(v, list)]
            data = max(lists, key=len) if lists else []
        n = len(data)
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


def stats_html():
    members = fetch_member_count()
    items = []
    for big, label, href in STATS:
        text = big.replace("{members}", members)
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


def event_card_html(ev):
    teams = ""
    if ev["who"]:
        pills = "".join(f'<span class="pill">{t.strip()}</span>' for t in ev["who"].split(","))
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


def build_index(upcoming_events, home_news_snippets):
    news_html = "\n".join(home_news_snippets) if home_news_snippets else "<p>Noch keine Berichte vorhanden.</p>"
    event_cards = "".join(event_card_html(ev) for ev in upcoming_events) or "<p>Keine anstehenden Termine gefunden.</p>"
    legend = legend_html(upcoming_events)
    ausfall_json = json.dumps(read_ausfall(), ensure_ascii=False).replace("<", "\\u003c")
    home_js = HOME_JS.replace("__AUSFALL__", ausfall_json)

    logo_file = find_logo()
    hero_logo = (f'<img src="{logo_file}" alt="Wappen der SG Aschheim / Feldkirchen / Kirchheim" class="hero-logo">'
                 if logo_file else "")

    index_content = f"""
    {read_hinweis()}

    <section class="hero">
      {hero_logo}
      <h1>{HERO_TITLE}</h1>
      <p>Egal ob Turnierspieler, Jugendlicher oder Einsteiger: Komm einfach an unserem Spielabend vorbei!</p>

      <ul class="hero-facts">
        <li>
          <strong><span aria-hidden="true">📅</span> Jeden Freitag</strong>
          <span>Gebäude ab 18:00 Uhr geöffnet</span>
        </li>
        <li>
          <strong><span aria-hidden="true">🕒</span> Jugendtraining 18:00 – 19:30 Uhr</strong>
          <span>Spielabend für Erwachsene ab 19:30 Uhr, open end</span>
        </li>
        <li>
          <strong><span aria-hidden="true">📍</span> Gymnasium Kirchheim</strong>
             <span>Heimstettner Str. 20, 85551 Kirchheim<br>
            <a href="https://maps.app.goo.gl/L8YRrvs52HD5cpDCA" target="_blank" rel="noopener">Auf Google Maps öffnen</a></span>
        </li>
      </ul>
      <p class="hero-note">Erwachsene dürfen schon ab 18:00 Uhr kommen, Jugendliche dürfen auch länger bleiben.</p>

      <a href="neu-hier.html" class="btn">Neu hier? So kommst du vorbei →</a>
    </section>

    {stats_html()}

    <section>
      <div class="section-head">
        <h2>Nächste Termine</h2>
        <a href="termine.html">Termine ansehen →</a>
      </div>
      <p class="spielabend" id="spielabend" hidden></p>
      <div class="events-grid" data-max="{HOME_EVENTS_VISIBLE}">
        {event_cards}
      </div>
      <p class="events-empty" id="events-empty" hidden>Aktuell sind keine anstehenden Termine eingetragen. <a href="termine.html">Zum Spielplan →</a></p>
      {legend}
    </section>

    <section>
      <div class="section-head">
        <h2>Aktuelle Berichte</h2>
        <a href="berichte.html">Alle Berichte ansehen →</a>
      </div>
      <div class="news-grid">
        {news_html}
      </div>
    </section>

    <section class="cta-band">
      <div>
        <h2>Lust auf eine Partie?</h2>
        <p>Komm freitags einfach vorbei oder schreib uns, wenn du vorab Fragen hast.</p>
      </div>
      <div class="cta-buttons">
        <a href="kontakt.html" class="btn">Kontakt aufnehmen</a>
        <a href="mitgliederantrag.pdf" class="btn btn-ghost" download>Mitgliedsantrag (PDF)</a>
      </div>
    </section>

    {home_js}
    """

    styles = """<style>""" + HINWEIS_CSS + """
      :root { --hero-logo-h: 200px; --hero-logo-h-mobile: 140px; --next-accent: #27ae60; }

      .container { max-width: 1200px; }
      .hero { border-radius: 8px; margin-bottom: 1.5rem; }
      .hero-logo { display: block; height: var(--hero-logo-h); width: auto; margin: 0 auto 1.2rem; mix-blend-mode: multiply; }
      @media (max-width: 600px) { .hero-logo { height: var(--hero-logo-h-mobile); } }

      .hero-facts { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; padding: 0; margin: 1.5rem auto 1rem; max-width: 960px; text-align: left; }
      .hero-facts li { background: #fff; border-radius: 8px; padding: 0.9rem 1.1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 0.2rem; }
      .hero-facts strong { color: var(--navy); font-size: 1.05rem; }
      .hero-facts span { color: #555; font-size: 0.95rem; }
      .hero-note { font-size: 0.95rem; color: #555; margin: 0 0 0.5rem; }

      .stats { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1rem; padding: 0; margin: 0 0 1rem; }
      .stats li, .stats li a { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.15rem; }
      .stats li { background: #fff; border: 1px solid #e3e6ea; border-radius: 8px; padding: 1rem 0.8rem; }
      .stats li a { text-decoration: none; color: inherit; width: 100%; }
      .stats li:has(a):hover { border-color: var(--link); }
      .stats strong { font-size: 1.5rem; color: var(--navy); line-height: 1.2; }
      .stats span { font-size: 0.9rem; color: #555; }

      .section-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; flex-wrap: wrap; margin: 2.5rem 0 1rem; }
      .section-head h2 { margin: 0; font-size: 1.4rem; color: var(--navy); }
      .section-head a { font-weight: bold; text-decoration: none; }

      .spielabend { margin: 0 0 1rem; padding: 0.7rem 1.1rem; background: #eaf6ee; border-left: 4px solid var(--next-accent); border-radius: 6px; font-weight: bold; color: #1e5631; }
      .spielabend[hidden] { display: none; }

      .events-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
      .event-card { background: var(--soft); border-left: 4px solid var(--link); border-radius: 6px; padding: 0.9rem 1.1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .event-card.next { border-left-color: var(--next-accent); box-shadow: 0 3px 10px rgba(39,174,96,0.25); }
      .ev-date { font-size: 0.95rem; font-weight: bold; color: #444; margin-bottom: 0.3rem; }
      .ev-rel:not(:empty) { display: inline-block; margin-left: 0.4rem; padding: 0.05rem 0.55rem; border-radius: 999px; background: #e3e6ea; color: #333; font-size: 0.75rem; }
      .event-card.next .ev-rel:not(:empty) { background: var(--next-accent); color: #fff; }
      .ev-title { font-size: 1.1rem; font-weight: bold; color: var(--navy); line-height: 1.35; }
      .ev-teams { margin-top: 0.4rem; }
      .pill { display: inline-block; background: #dcebf7; color: #1b4f7a; border-radius: 999px; padding: 0.1rem 0.7rem; font-size: 0.85rem; font-weight: bold; margin: 0.2rem 0.3rem 0 0; }
      .ev-legend { font-size: 0.85rem; color: #555; margin: 0.9rem 0 0; }
      .events-empty { margin: 0.5rem 0 0; }
      .events-empty[hidden] { display: none; }

      a.event-card { display: block; color: inherit; text-decoration: none; }
      a.event-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.12); }
      .spielabend-note { display: inline-block; margin-top: 0.2rem; font-weight: normal; font-size: 0.9rem; }

      @media (max-width: 600px) {
        .stats { grid-template-columns: 1fr 1fr; gap: 0.6rem; }
        .stats li { padding: 0.6rem 0.4rem; }
        .stats strong { font-size: 1.25rem; }
        .stats span { font-size: 0.8rem; }
      }

      .news-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1rem; }
      .news-grid .card { margin-bottom: 0 !important; }

      .cta-band { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem 2rem; margin: 3rem 0 1rem; padding: 1.6rem 2rem; background: var(--navy); color: #fff; border-radius: 8px; }
      .cta-band h2 { margin: 0 0 0.3rem; color: #fff; font-size: 1.4rem; }
      .cta-band p { margin: 0; color: #dfe6ee; }
      .cta-buttons { display: flex; flex-wrap: wrap; gap: 0.8rem; }
      .btn-ghost { background: transparent !important; border: 2px solid #fff; color: #fff !important; }
      .btn-ghost:hover { background: rgba(255,255,255,0.12) !important; }
    </style>"""

    render_page("Startseite", index_content, "index.html",
                extra_styles=styles.replace("</style>", NEWS_CSS + "</style>"))


# ==========================================
# 8. SITEMAP & 404-SEITE
# ==========================================
def build_404():
    content = f"""
    <h1>Seite nicht gefunden</h1>
    <p>Diese Seite gibt es leider nicht (mehr). Vielleicht hilft dir einer dieser Links weiter:</p>
    <p>
      <a href="{SITE_URL}index.html" class="btn" style="background:#3498db; display:inline-block; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Startseite</a>
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
        if name == "404.html":
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


def build_static_pages():
    """Baut die handgeschriebenen Seiten aus seiten/<name>.html in die Vorlage ein."""
    for name, title in STATIC_PAGES:
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
    upcoming = build_termine()
    build_oberlandquartett()
    build_blitzjahreswertung()
    build_hall_of_fame()
    build_turniere_overview()
    build_ausschreibungen()
    build_neu_hier()
    news = build_berichte()
    build_index(upcoming, news)
    build_404()
    build_static_pages()
    build_sitemap()   # zuletzt, damit alle erzeugten Seiten enthalten sind
    print("Build erfolgreich abgeschlossen!")