import os
import re
import glob

# ==========================================
# HELPER: TYPST TABELLEN IN HTML WANDELN
# ==========================================
def parse_typst_table_to_html(typst_content):
    if '#table(' not in typst_content and 'table(' not in typst_content:
        return "<p>Keine Tabelle gefunden.</p>"

    table_match = re.search(r'table\((.*?)\)\s*\]?$', typst_content, re.DOTALL)
    table_body = table_match.group(1) if table_match else typst_content

    tokens = re.findall(r'(table\.cell\(.*?\)?\[.*?\]|table\.header\(.*?\)|\[.*?\])', table_body, re.DOTALL)
    
    html_rows = []
    current_row = []
    
    for token in tokens:
        token = token.strip()
        
        if token.startswith('align:') or token.startswith('columns:') or token.startswith('stroke:'):
            continue
            
        if 'table.header' in token:
            headers = re.findall(r'\[(.*?)\]', token)
            header_cells = "".join([f"<th>{re.sub(r'[*_]', '', h).strip()}</th>" for h in headers if h.strip()])
            html_rows.append(f"<thead><tr>{header_cells}</tr></thead><tbody>")
            continue

        if 'colspan:' in token:
            if current_row:
                html_rows.append("<tr>" + "".join(current_row) + "</tr>")
                current_row = []
            colspan_m = re.search(r'colspan:\s*(\d+)', token)
            colspan_val = colspan_m.group(1) if colspan_m else "1"
            
            content_m = re.search(r'\[(.*)\]$', token, re.DOTALL)
            text = content_m.group(1).strip() if content_m else ""
            text = re.sub(r'#align\(.*?\)' , '', text)
            text = re.sub(r'#strong\[(.*?)\]', r'<strong>\1</strong>', text)
            text = re.sub(r'[*_]', '', text)
            
            html_rows.append(f'<tr><td colspan="{colspan_val}" class="monat-header">{text}</td></tr>')
        else:
            cls = ""
            if 'fill: yellow' in token: cls = ' class="bg-yellow"'
            elif 'fill: orange' in token: cls = ' class="bg-orange"'
            elif 'fill: DeepSkyBlue' in token: cls = ' class="monat-header"'
            
            content_m = re.search(r'\[(.*)\]$', token, re.DOTALL)
            text = content_m.group(1).strip() if content_m else ""
            text = re.sub(r'[*]', '', text)
            
            current_row.append(f'<td{cls}>{text}</td>')
            
    if current_row:
        html_rows.append("<tr>" + "".join(current_row) + "</tr>")
        
    return "\n".join(html_rows) + "</tbody>"


# ==========================================
# 1. TERMINE (termine/termine.typ -> termine.html)
# ==========================================
upcoming_events = []
typst_termine_path = os.path.join("termine", "termine.typ")
if not os.path.exists(typst_termine_path) and os.path.exists("termine.typ"):
    typst_termine_path = "termine.typ"

if os.path.exists(typst_termine_path):
    with open(typst_termine_path, "r", encoding="utf-8") as f:
        typst_code = f.read()

    tokens = re.findall(r'\[(.*?)\]', typst_code)
    for i in range(len(tokens)-1):
        if re.match(r'^\d{2}\.\d{2}\.', tokens[i].strip()):
            datum = tokens[i].strip()
            event = tokens[i+1].strip()
            if event and not event.startswith("MMM") and len(upcoming_events) < 4:
                upcoming_events.append((datum, event))

    table_html = parse_typst_table_to_html(typst_code)

    html_termine = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Termine & Spielplan | SG AFK</title>
  <link rel="stylesheet" href="style.css">
  <style>
    .table-responsive {{ overflow-x: auto; margin-top: 1.5rem; }}
    .custom-tabelle {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }}
    .custom-tabelle th, .custom-tabelle td {{ padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }}
    .custom-tabelle th {{ background-color: #1a252f; color: white; }}
    .monat-header {{ background-color: #00bfff !important; font-weight: bold; font-size: 1.1rem; color: black; }}
    .bg-yellow {{ background-color: #fff2ac !important; }}
    .bg-orange {{ background-color: #ffd8a8 !important; }}
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
      <a href="turniere.html">Turniere</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <h1>Termine & Spielplan</h1>
    <div class="table-responsive">
      <table class="custom-tabelle">
        {table_html}
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
# 2. TURNIERE-UNTERSEITEN DYNAMISCH AUS ORDNERN LESEN
# ==========================================
def read_typst_from_dir(folder_path):
    """Liest den Typst-Code aus einem Turniere-Ordner aus (sucht nach main.typ, table.typ oder kombiniert alle .typ)."""
    if not os.path.exists(folder_path):
        return ""
    
    # 1. Bevorzuge main.typ oder table.typ, falls vorhanden
    main_file = os.path.join(folder_path, "main.typ")
    table_file = os.path.join(folder_path, "table.typ")
    
    combined_code = ""
    if os.path.exists(table_file):
        with open(table_file, "r", encoding="utf-8") as f:
            combined_code += f.read() + "\n"
    if os.path.exists(main_file):
        with open(main_file, "r", encoding="utf-8") as f:
            combined_code += f.read() + "\n"
            
    if not combined_code:
        for fpath in glob.glob(os.path.join(folder_path, "*.typ")):
            if not fpath.endswith("template.typ"): # Ignoriere bloße Template-Definitionen
                with open(fpath, "r", encoding="utf-8") as f:
                    combined_code += f.read() + "\n"
                    
    return combined_code

def generate_custom_typst_page(folder_name, html_filename, title_text):
    table_content = "<p>Keine Daten vorhanden.</p>"
    
    folder_path = os.path.join("turniere", folder_name)
    code = read_typst_from_dir(folder_path)

    if code:
        table_content = f'<table class="custom-tabelle">{parse_typst_table_to_html(code)}</table>'

    page_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_text} | SG AFK</title>
  <link rel="stylesheet" href="style.css">
  <style>
    .table-responsive {{ overflow-x: auto; margin-top: 1.5rem; }}
    .custom-tabelle {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }}
    .custom-tabelle th, .custom-tabelle td {{ padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }}
    .custom-tabelle th {{ background-color: #1a252f; color: white; }}
    .monat-header {{ background-color: #3498db !important; color: white; font-weight: bold; font-size: 1.1rem; }}
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
      <a href="turniere.html">Turniere</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">{title_text}</h1>
    <div class="table-responsive">
      {table_content}
    </div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""
    
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(page_html)

generate_custom_typst_page("oberlandquartett", "oberlandquartett.html", "Oberlandquartett")
generate_custom_typst_page("vereinsintern", "vereinsintern.html", "Vereinsinterne Turniere & Hall of Fame")


# ==========================================
# 3. TURNIERE-ÜBERSICHTSSEITE (turniere.html)
# ==========================================
html_turniere = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Turniere | SG AFK</title>
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
      <a href="turniere.html">Turniere</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>
  <main class="container">
    <h1>Turniere & Ergebnisse</h1>
    <p>Hier findest du Übersichten zu unseren regionalen Wettkämpfen sowie die Hall of Fame unserer vereinsinternen Meisterschaften.</p>
    
    <div class="grid-2" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:1.5rem; margin-top:2rem;">
      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #3498db; border-radius:6px;">
        <h2>🏆 Oberlandquartett</h2>
        <p>Ergebnisse, Platzierungen und Rundenübersichten des traditionellen Oberlandquartetts.</p>
        <a href="oberlandquartett.html" class="btn" style="background:#3498db; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zum Oberlandquartett →</a>
      </div>

      <div class="card" style="padding:1.5rem; background:#f8f9fa; border-top:4px solid #27ae60; border-radius:6px;">
        <h2>🥇 Vereinsintern & Hall of Fame</h2>
        <p>Die historischen Vereinsmeister, Blitzschach-Champions und Pokalsieger unseres Vereins auf einen Blick.</p>
        <a href="vereinsintern.html" class="btn" style="background:#27ae60; display:inline-block; margin-top:1rem; color:white; padding:0.6rem 1.2rem; text-decoration:none; border-radius:4px;">Zur Hall of Fame →</a>
      </div>
    </div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""

with open("turniere.html", "w", encoding="utf-8") as f:
    f.write(html_turniere)


# ==========================================
# 4. BERICHTE VERARBEITEN
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
    body = re.sub(r'#underline\[(.*?)\]', r'<u>\1</u>', body)
    
    def parse_text_func(match):
        args = match.group(1)
        content = match.group(2)
        style_rules = []
        if 'blue' in args: style_rules.append('color: blue;')
        if 'red' in args: style_rules.append('color: red;')
        if 'green' in args: style_rules.append('color: green;')
        size_m = re.search(r'size:\s*(\d+pt)', args)
        if size_m: style_rules.append(f'font-size: {size_m.group(1)};')
        if 'italic' in args: style_rules.append('font-style: italic;')
        if 'bold' in args: style_rules.append('font-weight: bold;')
        style_attr = f' style="{" ".join(style_rules)}"' if style_rules else ''
        return f'<span{style_attr}>{content}</span>'

    body = re.sub(r'#text\((.*?)\)\[(.*?)\]', parse_text_func, body, flags=re.DOTALL)
    
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    formatted_body = ""
    for p in paragraphs:
        if p.startswith('<h1') or p.startswith('<h2') or p.startswith('<h3'):
            formatted_body += f"{p}\n"
        else:
            formatted_body += f"<p>{p}</p>\n"
            
    return title, date, author, formatted_body, preview_snippet

berichte_cards = []
home_news_snippets = []

if os.path.exists("berichte"):
    typ_files = sorted(glob.glob("berichte/*.typ"), reverse=True)
    
    for filepath in typ_files:
        # Ignoriere reine Vorlagen
        if "vorlage" in filepath.lower():
            continue
            
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
      <a href="../turniere.html">Turniere</a>
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
      <a href="turniere.html">Turniere</a>
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
# 5. STARTSEITE GENERIEREN
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
      <a href="turniere.html">Turniere</a>
      <a href="kontakt.html">Kontakt</a>
    </nav>
  </header>

  <section class="hero">
    <h1>Schach spielen in Aschheim, Feldkirchen & Kirchheim</h1>
    <p>Egal ob Turnierspieler, Jugendlicher oder Einsteiger: Komm einfach an unserem Spielabend vorbei!</p>
  </section>

  <main class="container" style="max-width: 1300px;">

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

    <div class="grid-3">
      <div class="card">
        <h3>♟️ Hobbyspieler & Einsteiger</h3>
        <p>Du spielst gerne Schach oder möchtest es lernen? Bei uns kannst du ganz zwanglos freie Partien spielen, ohne Turnierdruck.</p>
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

  </main>

  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>

</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_index)

print("Build erfolgreich für modulare Turnier-Ordner abgeschlossen!")
