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
                rows_html.append("<tr>" + "".join(current_row) + "</tr>")
                current_row = []
                
    if current_row:
        rows_html.append("<tr>" + "".join(current_row) + "</tr>")
        
    return "\n".join(rows_html)

# Build termine.html
if os.path.exists("termine.typ"):
    with open("termine.typ", "r", encoding="utf-8") as f:
        typst_code = f.read()

    table_body = parse_typst_to_html(typst_code)

    html_termine = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Termine & Spielplan | SG AFK</title>
  <link rel="stylesheet" href="style.css">
  <style>
    .table-responsive {{ overflow-x: auto; margin-top: 1.5rem; }}
    .termine-tabelle {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }}
    .termine-tabelle th, .termine-tabelle td {{ padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }}
    .termine-tabelle th {{ background-color: #1a252f; color: white; }}
    .monat-header {{ background-color: #00bfff !important; font-weight: bold; font-size: 1.1rem; }}
    .bg-yellow {{ background-color: #fff2ac !important; }}
    .bg-orange {{ background-color: #ffd8a8 !important; }}
    .termine-tabelle td:nth-child(1), .termine-tabelle td:nth-child(2) {{ text-align: left; }}
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
{table_body}
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
# 2. BERICHTE AUS BERICHTE/*.TYP GENERIEREN
# ==========================================
def typst_to_html_article(typst_text):
    # Einfacher Typst-Parser für Berichte
    title_m = re.search(r'#title\[(.*?)\]', typst_text)
    date_m = re.search(r'#date\[(.*?)\]', typst_text)
    author_m = re.search(r'#author\[(.*?)\]', typst_text)
    
    title = title_m.group(1) if title_m else "Turnierbericht"
    date = date_m.group(1) if date_m else ""
    author = author_m.group(1) if author_m else ""
    
    # Body ohne Metadaten
    body = typst_text
    body = re.sub(r'#title\[.*?\]', '', body)
    body = re.sub(r'#date\[.*?\]', '', body)
    body = re.sub(r'#author\[.*?\]', '', body)
    
    # Formatierungen umwandeln
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
            
    return title, date, author, formatted_body

berichte_cards = []

if os.path.exists("berichte"):
    typ_files = sorted(glob.glob("berichte/*.typ"), reverse=True)
    
    for filepath in typ_files:
        filename = os.path.basename(filepath).replace(".typ", ".html")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        title, date, author, body_html = typst_to_html_article(content)
        
        # Detailseite für den Bericht erstellen
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
    <p style="color:#777; font-size:0.9rem;">📅 {date} {f'| ✍️ von {author}' if author else ''}</p>
    <hr style="border:0; border-top:1px solid #eee; margin:1.5rem 0;">
    <div class="article-content">
      {body_html}
    </div>
  </main>
  <footer>
    <p>&copy; 2026 SGem Aschheim / Feldkirchen / Kirchheim e.V. | <a href="../kontakt.html" style="color:#aaa;">Impressum & Datenschutz</a></p>
  </footer>
</body>
</html>"""
        
        # Speichere die HTML-Datei im berichte-Ordner
        out_path = os.path.join("berichte", filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(article_html)
            
        # Teaser für die Übersichtsseite aufbauen
        berichte_cards.append(f"""
        <div class="card">
          <h3>{title}</h3>
          <p style="color:#777; font-size:0.85rem;">📅 {date}</p>
          <a href="berichte/{filename}" class="btn" style="background:#3498db;">Bericht lesen →</a>
        </div>
        """)

# ==========================================
# 3. BERICHTE-ÜBERSICHTSSEITE (berichte.html)
# ==========================================
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
    <p>Hier findest du Berichte über unsere Turniere, Mannschaftskämpfe und Vereinsveranstaltungen.</p>
    
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

print("Termine und Berichte erfolgreich aus Typst generiert!")
