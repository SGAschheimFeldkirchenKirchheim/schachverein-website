import os
import re
import glob
import datetime
import subprocess
import html as htmllib
from urllib.parse import quote

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

# Wie viele "Nächste Termine" auf der Startseite erscheinen
NEXT_EVENTS_COUNT = 6

# Öffentliche Adresse der Seite (für Kalender-Links)
SITE_URL = "https://sgaschheimfeldkirchenkirchheim.github.io/schachverein-website/"

# Kalender-Export
CAL_TZ = "Europe/Berlin"
EVENT_DURATION_HOURS = 3          # Standarddauer für Termine mit Uhrzeit
SPIELORT = "Gymnasium Kirchheim, Heimstettner Str. 3, 85551 Kirchheim"

TODAY = datetime.date.today()

# Gelbes Hinweisbanner (Text kommt aus hinweis.txt)
HINWEIS_CSS = """
      .hinweis-banner { background: #fff3cd; border: 1px solid #ffe08a; color: #664d03; padding: 0.8rem 1.2rem; border-radius: 6px; margin-bottom: 1.2rem; font-weight: bold; }
"""

# Lässt einen Block die volle Fensterbreite nutzen, auch wenn der Seiten-Container schmal ist
FULL_BLEED_CSS = """
      .full-bleed { width: min(96vw, 1900px); position: relative; left: 50%; transform: translateX(-50%); }
"""


# ==========================================
# 1. HELPER: RENDER PAGE MIT TEMPLATE
# ==========================================
def render_page(title, content, filename, css_path="", nav_path="", extra_styles=""):
    template_path = os.path.join("templates", "base.html")
    if not os.path.exists(template_path):
        print(f"Fehler: Template {template_path} nicht gefunden!")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    full_html = template.format(
        title=title,
        content=content,
        css_path=css_path,
        nav_path=nav_path,
        extra_styles=extra_styles
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
            f'<a href="{webcal_base}kalender/{fname}">📲 Abonnieren</a> '
            f'<a href="{https_url}" data-url="{https_url}" '
            f'onclick="navigator.clipboard.writeText(this.dataset.url);this.textContent=\'✓ Link kopiert\';return false;">🔗 Link kopieren</a></li>'
        )
    return f"""
    <details class="kalender-box">
      <summary>📆 Termine im Handy-Kalender abonnieren</summary>
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
    return '<div class="hinweis-banner">📢 ' + '<br>'.join(lines) + '</div>'


def build_turniere_overview():
    content = """
    <h1>Turniere & Ergebnisse</h1>
    <p>Hier findest du Übersichten zu unseren regionalen Wettkämpfen, die Gesamtwertung der Blitzschach-Serie sowie die Hall of Fame unserer Vereinsmeister.</p>
    
    <div class="grid-3" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-top:2rem;">
      
      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #3498db; border-radius:6px;">
        <h2>🏆 Oberlandquartett</h2>
        <p>Ergebnisse, Platzierungen und Rundenübersichten des traditionellen Oberlandquartetts.</p>
        <a href="oberlandquartett.html" class="btn" style="background:#3498db; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zum Oberlandquartett →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #e67e22; border-radius:6px;">
        <h2>⚡ Blitzjahreswertung</h2>
        <p>Die aktuelle Gesamtwertung und Zwischenstände unserer monatlichen Blitzschach-Turnierserie.</p>
        <a href="blitzjahreswertung.html" class="btn" style="background:#e67e22; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Blitzjahreswertung →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #27ae60; border-radius:6px;">
        <h2>🥇 Vereinsintern & Hall of Fame</h2>
        <p>Die historischen Vereinsmeister, Blitzschach-Champions und Pokalsieger unseres Vereins auf einen Blick.</p>
        <a href="vereinsintern.html" class="btn" style="background:#27ae60; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Hall of Fame →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #8e44ad; border-radius:6px;">
        <h2>📄 Ausschreibungen</h2>
        <p>Alle Turnierausschreibungen als PDF zum Ansehen und Herunterladen.</p>
        <a href="ausschreibungen.html" class="btn" style="background:#8e44ad; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zu den Ausschreibungen →</a>
      </div>

    </div>
    """
    render_page("Turniere & Ergebnisse", content, "turniere.html")


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
              <span class="pdf-icon">📄</span>
              <span class="pdf-text"><strong>{e['label']}</strong><br><small>PDF · {e['size']} KB{stand}</small></span>
            </a>"""
        body = f'<div class="pdf-grid">{items}</div>'
    else:
        body = "<p>Aktuell sind keine Ausschreibungen vorhanden.</p>"

    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">📄 Ausschreibungen</h1>
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
        <h3>🕒 Wann?</h3>
        <p><strong>Jeden Freitag.</strong> Das Gebäude ist ab 18:00 Uhr geöffnet.</p>
        <ul>
          <li><strong>Jugendtraining:</strong> 18:00 – 19:30 Uhr</li>
          <li><strong>Erwachsene &amp; Spielabend:</strong> ab 19:30 Uhr (open end)</li>
        </ul>
        <p>Die Zeiten sind flexibel: Erwachsene dürfen schon ab 18:00 Uhr kommen, Jugendliche müssen um 19:30 Uhr nicht gehen.</p>
      </div>

      <div class="neu-card">
        <h3>📍 Wo?</h3>
        <p><strong>Gymnasium Kirchheim</strong><br>Heimstettner Str. 3<br>85551 Kirchheim</p>
        <a href="https://maps.app.goo.gl/L8YRrvs52HD5cpDCA" target="_blank" rel="noopener" class="btn" style="background:#3498db; display:inline-block; color:white; padding:0.5rem 1rem; text-decoration:none; border-radius:4px; font-size:0.9rem;">📍 Auf Google Maps öffnen</a>
      </div>

      <div class="neu-card">
        <h3>♟️ Was erwartet dich?</h3>
        <ul>
          <li><strong>Hobbyspieler &amp; Einsteiger:</strong> zwanglos freie Partien, ohne Turnierdruck</li>
          <li><strong>Kinder &amp; Jugendliche:</strong> strukturiertes Jugendtraining für alle Alters- und Spielklassen</li>
          <li><strong>Mannschaftsschach:</strong> Teams von der C-Klasse bis zur Bezirksliga, für jedes Spielniveau</li>
        </ul>
        <a href="mannschaften.html">Unsere Teams →</a>
      </div>

      <div class="neu-card">
        <h3>📝 Mitglied werden</h3>
        <p>Gefällt es dir bei uns? Den Mitgliedsantrag kannst du hier herunterladen:</p>
        <a href="mitgliederantrag.pdf" download>📄 Mitgliedsantrag (PDF) →</a>
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
def build_blitzjahreswertung():
    folder_path = os.path.join("turniere", "blitzjahreswertung")
    main_typ = os.path.join(folder_path, "main.typ")
    output_svg_path = os.path.join(folder_path, "output.svg")
    
    # 1. Lokales Compiling als SVG (falls lokal ausgeführt)
    if os.path.exists(main_typ):
        try:
            subprocess.run(["typst", "compile", main_typ, output_svg_path], check=True)
        except Exception as e:
            print(f"Typst Compiling Hinweis: {e}")

    table_content = "<p>Keine Daten für die Blitzjahreswertung vorhanden.</p>"

    # 2. Falls SVG existiert, direkt als Vektorgrafik einbetten
    if os.path.exists(output_svg_path):
        with open(output_svg_path, "r", encoding="utf-8") as f:
            svg_data = f.read()
        table_content = f'<div class="svg-container">{svg_data}</div>'
    elif os.path.exists(main_typ):
        with open(main_typ, "r", encoding="utf-8") as f:
            code = f.read()
        table_content = f'<table class="custom-tabelle">{parse_typst_table_to_html(code)}</table>'

    content = f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">⚡ Blitzjahreswertung</h1>
    <div class="table-responsive">
      {table_content}
    </div>
    """

    styles = """<style>
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; text-align: center; }
      .svg-container svg { max-width: 100%; height: auto; background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
      .custom-tabelle, table { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }
      th, td { padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }
      th { background-color: #0a1f44; color: white; font-weight: bold; }
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
def typst_to_html_article(typst_text):
    title_m = re.search(r'#title\[(.*?)\]', typst_text)
    date_m = re.search(r'#date\[(.*?)\]', typst_text)
    author_m = re.search(r'#author\[(.*?)\]', typst_text)
    
    title = title_m.group(1) if title_m else "Turnierbericht"
    date = date_m.group(1) if date_m else ""
    author = author_m.group(1) if author_m else ""
    
    body = typst_text
    body = re.sub(r'#title\[.*?\]', '', body)
    body = re.sub(r'#date\[.*?\]', '', body)
    body = re.sub(r'#author\[.*?\]', '', body)
    
    raw_text = re.sub(r'#\w+(\[.*?\]|\(.*?\))', '', body)
    raw_text = re.sub(r'[=#*_]', '', raw_text).strip()
    preview_snippet = raw_text[:110] + "..." if len(raw_text) > 110 else raw_text

    body = re.sub(r'===\s*(.*?)\n', r'<h3>\1</h3>\n', body)
    body = re.sub(r'==\s*(.*?)\n', r'<h2>\1</h2>\n', body)
    body = re.sub(r'=\s*(.*?)\n', r'<h1>\1</h1>\n', body)
    body = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', body)
    body = re.sub(r'_(.*?)_', r'<em>\1</em>', body)
    
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    formatted_body = "".join([f"{p}\n" if p.startswith('<h') else f"<p>{p}</p>\n" for p in paragraphs])
            
    return title, date, author, formatted_body, preview_snippet


def build_berichte():
    berichte_cards = []
    home_news_snippets = []

    if os.path.exists("berichte"):
        typ_files = sorted(glob.glob("berichte/*.typ"), reverse=True)
        for filepath in typ_files:
            if "vorlage" in filepath.lower():
                continue
                
            filename = os.path.basename(filepath).replace(".typ", ".html")
            with open(filepath, "r", encoding="utf-8") as f:
                content_code = f.read()
                
            title, date, author, body_html, snippet = typst_to_html_article(content_code)
            author_str = f" | ✍️ von {author}" if author else ""
            
            article_content = f"""
            <a href="../berichte.html" style="text-decoration:none;">← Zurück zur Berichte-Übersicht</a>
            <h1 style="margin-top:1rem;">{title}</h1>
            <p style="color:#777; font-size:0.9rem;">📅 {date}{author_str}</p>
            <hr style="border:0; border-top:1px solid #eee; margin:1.5rem 0;">
            <div class="article-content">{body_html}</div>
            """
            
            out_path = os.path.join("berichte", filename)
            render_page(title, article_content, out_path, css_path="../", nav_path="../")
                
            berichte_cards.append(f"""
            <div class="card">
              <h3>{title}</h3>
              <p style="color:#777; font-size:0.85rem;">📅 {date}</p>
              <a href="berichte/{filename}" class="btn" style="background:#3498db;">Bericht lesen →</a>
            </div>
            """)
            
            if len(home_news_snippets) < 2:
                home_news_snippets.append(f"""
                <div class="card" style="margin-bottom: 1rem; padding: 1rem;">
                  <h4 style="margin: 0 0 0.3rem 0; font-size:1.05rem;">{title}</h4>
                  <p style="color:#777; font-size:0.75rem; margin:0 0 0.5rem 0;">📅 {date}</p>
                  <p style="font-size:0.85rem; margin: 0 0 0.5rem 0; line-height: 1.3;">{snippet}</p>
                  <a href="berichte/{filename}" style="color:#3498db; font-weight:bold; text-decoration:none; font-size:0.85rem;">Weiterlesen →</a>
                </div>
                """)

    cards_html = "\n".join(berichte_cards) if berichte_cards else "<p>Aktuell sind noch keine Berichte vorhanden.</p>"
    overview_content = f"<h1>Aktuelle Berichte & News</h1><div class='grid' style='grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));'>{cards_html}</div>"
    
    render_page("Berichte & News", overview_content, "berichte.html")
    return home_news_snippets


# ==========================================
# 7. STARTSEITE BUILDEN
# ==========================================
def build_index(upcoming_events, home_news_snippets):
    news_html = "\n".join(home_news_snippets) if home_news_snippets else "<p style='font-size:0.9rem;'>Noch keine Berichte vorhanden.</p>"

    event_cards = ""
    for ev in upcoming_events:
        who = f'<div class="ev-who">{ev["who"]}</div>' if ev["who"] else ""
        event_cards += f"""
        <div class="event-card">
          <div class="ev-date">{ev["when"]}</div>
          <div class="ev-title">{ev["title"]}</div>
          {who}
        </div>
        """
    if not event_cards:
        event_cards = "<p style='font-size:0.9rem;'>Keine anstehenden Termine gefunden.</p>"

    index_content = f"""
    {read_hinweis()}
    <section class="hero" style="margin-bottom: 2rem;">
      <h1>Schach spielen in Aschheim, Feldkirchen & Kirchheim</h1>
      <p>Egal ob Turnierspieler, Jugendlicher oder Einsteiger: Komm einfach an unserem Spielabend vorbei!</p>
      <a href="neu-hier.html" class="btn" style="background:#27ae60; display:inline-block; margin-top:0.6rem;">Neu hier? So kommst du vorbei →</a>
    </section>

    <div class="full-bleed">

      <div class="hero-layout">
        <div>
          <h3 style="margin-top:0;">📰 Aktuelle Berichte</h3>
          {news_html}
          <a href="berichte.html" style="display:inline-block; color:#3498db; font-weight:bold; font-size:0.85rem;">Alle Berichte ansehen →</a>
        </div>

        <div class="info-card">
          <h3 style="margin-top:0;">🕒 Wann & Wo wir spielen</h3>
          <p style="font-size:0.9rem;"><strong>Jeden Freitag</strong> (Gebäude ab 18:00 Uhr geöffnet)</p>
          <ul style="font-size:0.85rem; padding-left: 1.2rem;">
            <li><strong>Jugendtraining:</strong> 18:00 – 19:30 Uhr</li>
            <li><strong>Erwachsene & Spielabend:</strong> Ab 19:30 Uhr (open end)</li>
          </ul>
          <div class="hinweis-box">
            💡 <strong>Volle Flexibilität:</strong> Keine starren Grenzen! Erwachsene dürfen schon ab 18:00 Uhr kommen, Jugendliche müssen um 19:30 Uhr nicht gehen.
          </div>
          <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 1rem 0;">
          <p style="font-size:0.85rem; margin:0;"><strong>Spielort:</strong> Gymnasium Kirchheim<br>Heimstettner Str. 3, 85551 Kirchheim</p>
          <a href="https://maps.app.goo.gl/L8YRrvs52HD5cpDCA" target="_blank" rel="noopener" class="maps-btn">📍 Auf Google Maps öffnen</a>
        </div>
      </div>

      <section class="next-events">
        <div class="next-events-head">
          <h3 style="margin:0;">📅 Nächste Termine</h3>
          <a href="termine.html" class="btn" style="background:#3498db; font-size:0.85rem; padding: 0.5rem 1rem;">Zum Spielplan →</a>
        </div>
        <div class="events-grid">
          {event_cards}
        </div>
      </section>

      <div class="grid-3" style="margin-top: 2rem;">
        <div class="card">
          <h3>♟️ Hobbyspieler & Einsteiger</h3>
          <p>Du spielst gerne Schach oder möchtest es lernen? Bei uns kannst du ganz zwanglos freie Partien spielen, ohne Turnierdruck.</p>
          <a href="mitgliederantrag.pdf" download style="display:inline-block; margin-top:0.8rem; color:#27ae60; font-weight:bold; font-size:0.85rem; text-decoration:none;">
            📄 Mitgliedsantrag (PDF) herunterladen →
          </a>
        </div>
        <div class="card">
          <h3>♟️ Kinder & Jugendliche</h3>
          <p>Freitags ab 18:00 Uhr bieten wir ein strukturiertes Jugendtraining für alle Alters- und Spielklassen an.</p>
        </div>
        <div class="card">
          <h3>♟️ Mannschaftsschach</h3>
          <p>Mit mehreren Teams von der C-Klasse bis zur Bezirksliga bieten wir für jedes Spielniveau die passende Mannschaft.</p>
          <a href="mannschaften.html" class="btn" style="background:#3498db; width:100%; text-align:center; box-sizing:border-box;">Unsere Teams</a>
        </div>
      </div>

    </div>
    """

    styles = """<style>""" + FULL_BLEED_CSS + HINWEIS_CSS + """
      .hero-layout { display: grid; grid-template-columns: 1.3fr 1fr; gap: 1.5rem; align-items: start; margin-bottom: 2rem; }
      .info-card { background: #f8f9fa; border-left: 5px solid #27ae60; padding: 1.2rem; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .maps-btn { display: inline-block; background: #3498db; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 0.6rem; }
      .hinweis-box { background: #e8f4f8; border: 1px solid #bce8f1; color: #2c3e50; padding: 0.8rem; border-radius: 5px; margin-top: 0.8rem; font-size: 0.85rem; }
      .next-events { margin-top: 1rem; }
      .next-events-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 0.8rem; flex-wrap: wrap; }
      .events-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1rem; }
      .event-card { background: #f8f9fa; border-left: 4px solid #3498db; border-radius: 6px; padding: 0.9rem 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .ev-date { font-size: 0.8rem; font-weight: bold; color: #555; margin-bottom: 0.25rem; }
      .ev-title { font-size: 0.95rem; font-weight: bold; color: #1a252f; }
      .ev-title a { color: #3498db; }
      .ev-who { font-size: 0.8rem; color: #777; margin-top: 0.25rem; }
      @media (max-width: 1024px) { .hero-layout { grid-template-columns: 1fr; } }
    </style>"""

    render_page("Startseite", index_content, "index.html", extra_styles=styles)


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
    build_sitemap()   # zuletzt, damit alle erzeugten Seiten enthalten sind
    print("Build erfolgreich abgeschlossen!")
