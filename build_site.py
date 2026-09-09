import os
import re
import glob

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
# 2. TERMINE PARSER
# ==========================================
def parse_typst_table_to_html(typst_content):
    if '#table(' not in typst_content and 'table(' not in typst_content:
        return "<p>Keine Tabelle gefunden.</p>"

    typst_content = re.sub(r'#strong\s*\(\s*["\'](.*?)["\']\s*\)', r'\1', typst_content)
    typst_content = re.sub(r'#align\s*\([^)]*\)', '', typst_content)

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
            text = re.sub(r'[*_"\']', '', text).strip()
            
            html_rows.append(f'<tr><td colspan="{colspan_val}" class="monat-header">{text}</td></tr>')
        else:
            cls = ""
            if 'fill: yellow' in token: cls = ' class="bg-yellow"'
            elif 'fill: orange' in token: cls = ' class="bg-orange"'
            elif 'fill: DeepSkyBlue' in token: cls = ' class="monat-header"'
            
            content_m = re.search(r'\[(.*)\]$', token, re.DOTALL)
            text = content_m.group(1).strip() if content_m else ""
            text = re.sub(r'[*]', '', text).strip()
            
            current_row.append(f'<td{cls}>{text}</td>')
            
            if len(current_row) == 10:
                html_rows.append("<tr>" + "".join(current_row) + "</tr>")
                current_row = []
            
    if current_row:
        html_rows.append("<tr>" + "".join(current_row) + "</tr>")
        
    return "\n".join(html_rows) + "</tbody>"


def build_termine():
    path = os.path.join("termine", "termine.typ")
    if not os.path.exists(path) and os.path.exists("termine.typ"):
        path = "termine.typ"

    upcoming_events = []
    table_html = "<p>Keine Termine vorhanden.</p>"

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            typst_code = f.read()

        tokens = re.findall(r'\[(.*?)\]', typst_code)
        for i in range(len(tokens)-1):
            if re.match(r'^\d{2}\.\d{2}\.', tokens[i].strip()):
                datum = tokens[i].strip()
                event = tokens[i+1].strip()
                if event and not event.startswith("MMM") and len(upcoming_events) < 4:
                    upcoming_events.append((datum, event))

        table_html = parse_typst_table_to_html(typst_code)

    content = f"""<h1>Termine & Spielplan</h1>
    <div class="table-responsive">
      <table class="custom-tabelle">
        {table_html}
      </table>
    </div>"""

    styles = """<style>
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; }
      .custom-tabelle { width: 100%; border-collapse: collapse; font-size: 0.95rem; background: white; border-radius: 8px; overflow: hidden; }
      .custom-tabelle th, .custom-tabelle td { padding: 10px 12px; border: 1px solid #dcdcdc; text-align: center; }
      .custom-tabelle th { background-color: #1a252f; color: white; }
      .monat-header { background-color: #00bfff !important; font-weight: bold; font-size: 1.1rem; color: black; }
      .bg-yellow { background-color: #fff2ac !important; }
      .bg-orange { background-color: #ffd8a8 !important; }
    </style>"""

    render_page("Termine & Spielplan", content, "termine.html", extra_styles=styles)
    return upcoming_events


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
    output_html_path = os.path.join(folder_path, "output.html")
    
    table_content = "<p>Keine Daten für die Blitzjahreswertung vorhanden.</p>"

    if os.path.exists(output_html_path):
        with open(output_html_path, "r", encoding="utf-8") as f:
            table_content = f.read()
    else:
        main_typ = os.path.join(folder_path, "main.typ")
        if os.path.exists(main_typ):
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
      .table-responsive { overflow-x: auto; margin-top: 1.5rem; }
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

    index_content = f"""
    <section class="hero" style="margin-bottom: 2rem;">
      <h1>Schach spielen in Aschheim, Feldkirchen & Kirchheim</h1>
      <p>Egal ob Turnierspieler, Jugendlicher oder Einsteiger: Komm einfach an unserem Spielabend vorbei!</p>
    </section>

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
    """

    styles = """<style>
      .hero-layout { display: grid; grid-template-columns: 1fr 1.6fr 1fr; gap: 1.2rem; align-items: start; }
      .info-card { background: #f8f9fa; border-left: 5px solid #27ae60; padding: 1.2rem; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      .maps-btn { display: inline-block; background: #3498db; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 0.6rem; }
      .hinweis-box { background: #e8f4f8; border: 1px solid #bce8f1; color: #2c3e50; padding: 0.8rem; border-radius: 5px; margin-top: 0.8rem; font-size: 0.85rem; }
      @media (max-width: 1024px) { .hero-layout { grid-template-columns: 1fr; } }
    </style>"""

    render_page("Startseite", index_content, "index.html", extra_styles=styles)


# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    upcoming = build_termine()
    build_oberlandquartett()
    build_blitzjahreswertung()
    build_hall_of_fame()
    news = build_berichte()
    build_index(upcoming, news)
    print("Build erfolgreich mit Template-System abgeschlossen!")
