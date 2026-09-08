import os
import re
import glob

# ==========================================
# 1. TYPST TERMIN-TABELLE VERARBEITEN
# ==========================================
def parse_typst_to_html(typst_content):
    if 'table.cell(colspan: 10' in typst_content:
        body_part = 'table.cell(colspan: 10' + typst_content.split('table.cell(colspan: 10', 1)[1]
    else:
        body_part = typst_content

    body_part = re.sub(r'\n\s*\)\s*\]\s*$', '', body_part)
    tokens = re.findall(r'(table\.cell\(.*?\)?\[.*?\]|\[.*?\])', body_part, re.DOTALL)
    
    rows_html = []
    current_row = []
    upcoming_events = []
    
    for token in tokens:
        token = token.strip()
        if 'colspan: 10' in token:
            if current_row:
                rows_html.append("<tr>" + "".join(current_row) + "</tr>")
                current_row = []
            month_match = re.search(r'"(.*?)"', token)
            month_name = month_match.group(1) if month_match else "Monat"
            rows_html.append(f'<tr><td colspan="10" class="monat-header">{month_name}</td></tr>')
        else:
            cls = ""
            if 'fill: yellow' in token:
                cls = ' class="bg-yellow"'
            elif 'fill: orange' in token:
                cls = ' class="bg-orange"'
            
            content_match = re.search(r'\[(.*)\]$', token, re.DOTALL)
            text = content_match.group(1).strip() if content_match else ""
            current_row.append(f'<td{cls}>{text}</td>')
            
            if len(current_row) == 10:
                datum = re.sub(r'<.*?>', '', current_row[0]).strip()
                event_info = re.sub(r'<.*?>', '', current_row[1]).strip()
                
                if not event_info:
                    teams = ["AFK 1", "AFK 2", "AFK 3", "AFK 4", "AFK 5", "AFK 6", "Senioren", "Jugend"]
                    for idx, cell in enumerate(current_row[2:], start=0):
                        clean_cell = re.sub(r'<.*?>', '', cell).strip()
                        if clean_cell:
                            event_info = f"{clean_cell} ({teams[idx]})"
                            break
                
                if datum and event_info and len(upcoming_events) < 5:
                    upcoming_events.append((datum, event_info))

                rows_html.append("<tr>" + "".join(current_row) + "</tr>")
                current_row = []
                
    if current_row:
        rows_html.append("<tr>" + "".join(current_row) + "</tr>")
        
    return "\n".join(rows_html), upcoming_events

table_body = ""
upcoming_events = []

if os.path.exists("termine.typ"):
    with open("termine.typ", "r", encoding="utf-8") as f:
        typst_code = f.read()

    table_body, upcoming_events = parse_typst_to_html(typst_code)

    html_termine = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Termine & Spielplan | SG AFK</title>
  <link rel="stylesheet" href="style.css">
  <style>
    .table-responsive { overflow-x: auto; margin-top: 1.5rem; }
    .termine-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }
    .termine-tabelle th, .termine-tabelle td { padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }
    .termine-tabelle th { background-color: #1a252f; color: white; }
    .monat-header { background-color: #00bfff !important; font-weight: bold; font-size: 1.1rem; }
    .bg-yellow { background-color: #fff2ac !important; }
    .bg-orange { background-color: #ffd8a8 !important; }
    .termine-tabelle td:nth-child(1), .termine-tabelle td:nth-child(2) { text-align: left; }
  </style>
</head>
<body>
  <header>
    <h2>♟️ SG Aschheim / Feldkirchen / Kirchheim</h2>
    <nav>
      <a href="index.html">Start</a>
      <a href="ueber-uns.html">Über uns</a>
      <a href="mannschaften.html">Mannschaften</a>
      <a href="termine.html">Termine</a>
      <a href="berichte.html">Berichte</a>
      <a href="jugend.html">Jugend</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <h1>Termine & Spielplan</h1>
    <div class="table-responsive">
      <table class="termine-tabelle">
        <thead>
          <tr>
            <th>Termin</th><th>Verein</th><th>AFK 1</th><th>AFK 2</th><th>AFK 3</th>
            <th>AFK 4</th><th>AFK 5</th><th>AFK 6</th><th>Senioren</th><th>Jugend</th>
          </tr>
        </thead>
        <tbody>
""" + table_body + """
        </tbody>
      </table>
    </div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""

    with open("termine.html", "w", encoding="utf-8") as f:
        f.write(html_termine)

# ==========================================
# 2. BERICHTE VERARBEITEN
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
    
    raw_text = re.sub(r'[=#*]', '', body).strip()
    preview_snippet = raw_text[:110] + "..." if len(raw_text) > 110 else raw_text

    body = re.sub(r'= (.*?)\n', r'<h2>\1</h2>\n', body)
    body = re.sub(r'== (.*?)\n', r'<h3>\1</h3>\n', body)
    body = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', body)
    
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    formatted_body = ""
    for p in paragraphs:
        if p.startswith('<h2>') or p.startswith('<h3>'):
            formatted_body += f"{p}\n"
        else:
            formatted_body += f"<p>{p}</p>\n"
            
    return title, date, author, formatted_body, preview_snippet

berichte_cards = []
home_news_snippets = []

if os.path.exists("berichte"):
    typ_files = sorted(glob.glob("berichte/*.typ"), reverse=True)
    
    for filepath in typ_files:
        filename = os.path.basename(filepath).replace(".typ", ".html")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        title, date, author, body_html, snippet = typst_to_html_article(content)
        
        author_str = f" | ✍️ von {author}" if author else ""
        article_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | SG AFK</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
  <header>
    <h2>♟️ SG Aschheim / Feldkirchen / Kirchheim</h2>
    <nav>
      <a href="../index.html">Start</a>
      <a href="../ueber-uns.html">Über uns</a>
      <a href="../mannschaften.html">Mannschaften</a>
      <a href="../termine.html">Termine</a>
      <a href="../berichte.html">Berichte</a>
      <a href="../jugend.html">Jugend</a>
      <a href="../kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <a href="../berichte.html" style="text-decoration:none;">← Zurück zur Berichte-Übersicht</a>
    <h1 style="margin-top:1rem;">{title}</h1>
    <p style="color:#777; font-size:0.9rem;">📅 {date}{author_str}</p>
    <hr style="border:0; border-top:1px solid #eee; margin:1.5rem 0;">
    <div class="article-content">{body_html}</div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="../kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""
        
        out_path = os.path.join("berichte", filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(article_html)
            
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
html_berichte_overview = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Berichte & News | SG AFK</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h2>♟️ SG Aschheim / Feldkirchen / Kirchheim</h2>
    <nav>
      <a href="index.html">Start</a>
      <a href="ueber-uns.html">Über uns</a>
      <a href="mannschaften.html">Mannschaften</a>
      <a href="termine.html">Termine</a>
      <a href="berichte.html">Berichte</a>
      <a href="jugend.html">Jugend</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <h1>Aktuelle Berichte & News</h1>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
      {cards_html}
    </div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""

with open("berichte.html", "w", encoding="utf-8") as f:
    f.write(html_berichte_overview)

# ==========================================
# 3. STARTSEITE (3-SPALTEN-LAYOUT) GENERIEREN
# ==========================================
news_html = "\n".join(home_news_snippets) if home_news_snippets else "<p style='font-size:0.9rem;'>Noch keine Berichte vorhanden.</p>"

events_list_items = ""
for datum, event in upcoming_events[:4]:
    events_list_items += f"""
    <li style="margin-bottom:0.6rem; padding-bottom:0.4rem; border-bottom:1px solid #eee; font-size:0.85rem;">
      <strong>{datum}</strong><br>
      <span style="color:#555;">{event}</span>
    </li>
    """
if not events_list_items:
    events_list_items = "<li style='font-size:0.9rem;'>Keine anstehenden Termine gefunden.</li>"

html_index = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SGem Aschheim / Feldkirchen / Kirchheim e.V.</title>
  <link rel="stylesheet" href="style.css">
  <style>
    /* 3-Spalten-Layout für große Monitore */
    .hero-layout {{
      display: grid;
      grid-template-columns: 1fr 1.6fr 1fr;
      gap: 1.2rem;
      align-items: start;
      margin-bottom: 2rem;
    }}
    
    .info-card {{
      background: #f8f9fa;
      border-left: 5px solid #27ae60;
      padding: 1.2rem;
      border-radius: 6px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    .maps-btn {{
      display: inline-block;
      background: #3498db;
      color: white;
      padding: 0.5rem 1rem;
      text-decoration: none;
      border-radius: 4px;
      font-size: 0.85rem;
      font-weight: bold;
      margin-top: 0.6rem;
    }}
    
    .hinweis-box {{
      background: #e8f4f8;
      border: 1px solid #bce8f1;
      color: #2c3e50;
      padding: 0.8rem;
      border-radius: 5px;
      margin-top: 0.8rem;
      font-size: 0.85rem;
    }}

    /* Auf Smartphones untereinander stapeln */
    @media (max-width: 1024px) {{
      .hero-layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>

  <header>
    <h2>♟️ SG Aschheim / Feldkirchen / Kirchheim</h2>
    <nav>
      <a href="index.html">Start</a>
      <a href="ueber-uns.html">Über uns</a>
      <a href="mannschaften.html">Mannschaften</a>
      <a href="termine.html">Termine</a>
      <a href="berichte.html">Berichte</a>
      <a href="jugend.html">Jugend</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>

  <section class="hero">
    <h1>Schach spielen in Aschheim, Feldkirchen & Kirchheim</h1>
    <p>Egal ob Turnierspieler, Jugendlicher oder Einsteiger: Komm einfach an unserem Spielabend vorbei!</p>
  </section>

  <main class="container" style="max-width: 1300px;">

    <!-- Das gewünschte 3-Spalten-Layout -->
    <div class="hero-layout">
      
      <!-- SPALTE 1: GELB (Berichte) -->
      <div>
        <h3 style="margin-top:0;">📰 Aktuelle Berichte</h3>
        {news_html}
        <a href="berichte.html" style="display:inline-block; color:#3498db; font-weight:bold; font-size:0.85rem;">Alle Berichte ansehen →</a>
      </div>

      <!-- SPALTE 2: MITTE (Wann & Wo) -->
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

      <!-- SPALTE 3: BLAU (Termine) -->
      <div>
        <h3 style="margin-top:0;">📅 Nächste Termine</h3>
        <div class="card" style="padding: 1rem;">
          <ul style="list-style:none; padding:0; margin:0;">
            {events_list_items}
          </ul>
          <a href="termine.html" class="btn" style="background:#3498db; width:100%; text-align:center; box-sizing:border-box; margin-top:0.8rem; font-size:0.85rem; padding: 0.5rem;">Zum Spielplan</a>
        </div>
      </div>

    </div>

    <!-- 3 Kacheln unten -->
    <div class="grid-3">
      <div class="card">
        <h3>♟️ Hobbyspieler & Einsteiger</h3>
        <p>Du spielst gerne Schach oder möchtest es lernen? Bei uns kannst du ganz zwanglos freie Partien spielen, ohne Turnierdruck.</p>
      </div>
      <div class="card">
        <h3>♟️ Kinder & Jugendliche</h3>
        <p>Freitags ab 18:00 Uhr bieten wir ein strukturiertes Jugendtraining für alle Alters- und Spielklassen an.</p>
        <a href="jugend.html" class="btn" style="background:#3498db; width:100%; text-align:center; box-sizing:border-box;">Mehr zur Jugend</a>
      </div>
      <div class="card">
        <h3>♟️ Mannschaftsschach</h3>
        <p>Mit mehreren Teams von der C-Klasse bis zur Bezirksliga bieten wir für jedes Spielniveau die passende Mannschaft.</p>
        <a href="mannschaften.html" class="btn" style="background:#3498db; width:100%; text-align:center; box-sizing:border-box;">Unsere Teams</a>
      </div>
    </div>

  </main>

  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>

</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_index)

print("Startseite erfolgreich ins 3-Spalten-Layout umgebaut!")
