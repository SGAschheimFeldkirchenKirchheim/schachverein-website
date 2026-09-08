import re

def parse_typst_to_html(typst_content):
    # Monats-Überschriften und Zellen mit Farben erkennen
    tokens = re.findall(r'(table\.cell\(.*?\)?\[.*?\]|\[.*?\])', typst_content, re.DOTALL)
    
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

# Typst einlesen und HTML generieren
with open("termine.typ", "r", encoding="utf-8") as f:
    typst_code = f.read()

table_body = parse_typst_to_html(typst_code)

# Vorlage in termine.html schreiben
html_template = f"""<!DOCTYPE html>
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
    f.write(html_template)

print("termine.html erfolgreich automatisch aus termine.typ generiert!")
