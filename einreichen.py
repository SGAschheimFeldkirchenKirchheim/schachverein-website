"""
"Bericht schreiben" – Editor-Block auf berichte.html (Logik in bericht.js, Backend AppsScript/Berichte.gs).

  - Gäste: Bericht landet als Entwurf (Ordner berichte/<Jahr>/_<Titel>), Admins geben frei.
  - Angemeldet mit Recht "berichte" (Admins automatisch) und eigenem Namen als Autor: sofort online
    (nach dem nächsten Build). Eigene Berichte lassen sich bearbeiten und zurückziehen.
  - Fotos werden im Browser verkleinert und mit hochgeladen, eins davon ist das Titelbild.

Einstellungen:
  SKRIPT_URL  – Web-App-URL aus Apps Script. Leer lassen = Block wird nicht angezeigt.
  MAX_ZEICHEN – Höchstlänge des Textes (muss zu MAX_ZEICHEN in Code.gs passen).
"""
import html
import json

SKRIPT_URL = "https://script.google.com/macros/s/AKfycbxvMU_7CRADHdkcfSHuLLwmpYOGpZ6YbFqQCXVHSNl0wcG9A0iKRzaElJ2ATgUI0qeV/exec"
MAX_ZEICHEN = 20000
KATEGORIEN = [("turnier", "Turnier"), ("jugend", "Jugend"), ("senioren", "Senioren"), ("afk 1", "AFK 1"), ("afk 2", "AFK 2"),
              ("afk 3", "AFK 3"), ("afk 4", "AFK 4"), ("afk 5", "AFK 5"), ("afk 6", "AFK 6"), ("verein", "Verein")]

INTRO = ("Turnier gespielt, Mannschaftskampf erlebt, etwas Lustiges passiert? Schreib es auf – "
         "mit Fotos. Wir schauen kurz drüber und stellen es online.")

CSS = """
      .einreichen { margin: 2.5rem 0 0; padding: 0; }
      .einreichen > summary { cursor: pointer; list-style: none; padding: 0.9rem 1.2rem; display: flex;
        align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
      .einreichen > summary::-webkit-details-marker { display: none; }
      .einreichen[open] > summary .btn { opacity: 0.6; }
      .be-app { padding: 0 1.2rem 1.3rem; }
      .be-hinweis { padding: .7rem 1rem; border-radius: 10px; margin: 0 0 1rem; font-size: .95rem; background: var(--soft); color: var(--soft-text); }
      .be-hinweis.gruen { background: #3fae6c22; border: 1px solid #3fae6c66; color: #2f8f55; }
      :root[data-theme="dark"] .be-hinweis.gruen { color: #6fd59a; }
      .be-reihe { display: grid; grid-template-columns: 2fr 1.4fr 1fr; gap: .8rem; margin-bottom: .8rem; }
      .be-app label { display: grid; gap: .25rem; font-weight: 600; font-size: .9rem; }
      .be-app input[type=text], .be-app input[type=email], .be-app textarea { font: inherit; font-weight: normal; padding: .55rem .7rem;
        border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--text); width: 100%; box-sizing: border-box; }
      .be-kat { display: flex; gap: .4rem; flex-wrap: wrap; margin: .3rem 0 1rem; }
      .be-kat button { font: inherit; font-size: .88rem; padding: .3rem .8rem; border-radius: 20px; border: 1px solid var(--line);
        background: none; color: var(--muted); cursor: pointer; }
      .be-kat button.an { background: var(--link-c); border-color: var(--link-c); color: #0e1524; font-weight: 600; }
      :root:not([data-theme="dark"]) .be-kat button.an { background: #1c2d52; border-color: #1c2d52; color: #fff; }
      .be-tabs { display: flex; gap: .2rem; border-bottom: 1px solid var(--line); }
      .be-tabs button { font: inherit; font-weight: 600; padding: .5rem 1rem; border: 0; border-bottom: 2px solid transparent; background: none;
        color: var(--muted); cursor: pointer; margin-bottom: -1px; }
      .be-tabs button.an { color: var(--head); border-color: var(--link-c); }
      .be-leiste { display: flex; flex-wrap: wrap; gap: .2rem; padding: .35rem; background: var(--bg); border: 1px solid var(--line); border-top: 0; }
      .be-leiste button { font: inherit; font-size: .9rem; min-width: 2.2rem; height: 2.1rem; padding: 0 .55rem; border: 0; border-radius: 6px;
        background: none; color: var(--text); cursor: pointer; }
      .be-leiste button:hover { background: var(--soft); }
      .be-leiste i.tr { width: 1px; background: var(--line); margin: .2rem .3rem; }
      .be-app textarea.be-text { border-top: 0; border-radius: 0 0 10px 10px; min-height: 16rem; resize: vertical; line-height: 1.6; }
      .be-vorschau { border: 1px solid var(--line); border-top: 0; border-radius: 0 0 10px 10px; padding: 1rem 1.2rem; min-height: 16rem; background: var(--bg); }
      .be-vorschau h1 { font-size: 1.6rem; margin: 0 0 .3rem; }
      .be-vorschau figure { margin: 1rem 0; } .be-vorschau img { max-width: 100%; border-radius: 6px; display: block; }
      .be-vorschau figcaption { font-size: .85rem; color: var(--muted); margin-top: .3rem; }
      .be-hilfe { font-size: .82rem; color: var(--muted); margin: .4rem 0 0; }
      .be-hilfe code { background: var(--soft); padding: 0 .3rem; border-radius: 4px; }
      .be-bilder { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: .8rem; margin-top: 1rem; }
      .be-bild { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; background: var(--bg); position: relative; }
      .be-bild img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
      .be-bild input[type=text] { border: 0 !important; border-top: 1px solid var(--line) !important; border-radius: 0 !important; font-size: .85rem !important; }
      .be-bild .be-titel { position: absolute; left: .5rem; top: .5rem; background: #e0a84f; color: #1b1b1b; font-size: .75rem; font-weight: 700; padding: .12rem .5rem; border-radius: 20px; }
      .be-bild .be-nr { position: absolute; right: .5rem; top: .5rem; background: rgba(0,0,0,.65); color: #fff; font-size: .75rem; padding: .1rem .45rem; border-radius: 6px; }
      .be-bild .be-akt { display: flex; flex-wrap: wrap; border-top: 1px solid var(--line); }
      .be-bild .be-akt button { flex: 1 0 auto; font: inherit; font-size: .76rem; padding: .4rem .35rem; white-space: nowrap; border: 0; background: none; color: var(--text); cursor: pointer; }
      .be-bild .be-akt button + button { border-left: 1px solid var(--line); }
      .be-bild .be-akt button.rot { color: #d0544a; }
      .be-drop { border: 2px dashed var(--line); border-radius: 10px; display: grid; place-items: center; text-align: center; color: var(--muted);
        font-size: .9rem; padding: 1rem; min-height: 9rem; cursor: pointer; }
      .be-drop.ueber { border-color: var(--link-c); color: var(--link-c); }
      .be-fuss { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; margin-top: 1rem; }
      .be-falle { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
      .be-meldung { margin: .8rem 0 0; padding: .7rem 1rem; border-radius: 10px; font-weight: 600; }
      .be-meldung.ok { background: #3fae6c22; color: #2f8f55; } .be-meldung.fehler { background: #e0675c22; color: #c0453b; }
      :root[data-theme="dark"] .be-meldung.ok { color: #6fd59a; } :root[data-theme="dark"] .be-meldung.fehler { color: #ff8a80; }
      .be-meine { margin-top: 1.6rem; }
      .be-meine table { width: 100%; border-collapse: collapse; font-size: .95rem; }
      .be-meine td { padding: .6rem .4rem; border-bottom: 1px solid var(--line); vertical-align: middle; }
      .be-st { font-size: .76rem; font-weight: 700; padding: .12rem .5rem; border-radius: 20px; white-space: nowrap; }
      .be-st.online { background: #3fae6c26; color: #2f8f55; } .be-st.entwurf { background: #e0a84f26; color: #9a6510; }
      :root[data-theme="dark"] .be-st.online { color: #6fd59a; } :root[data-theme="dark"] .be-st.entwurf { color: #f2c37a; }
      @media (max-width: 700px) { .be-reihe { grid-template-columns: 1fr; } .be-bilder { grid-template-columns: 1fr 1fr; }
        .be-meine tr { display: grid; grid-template-columns: 1fr auto; border-bottom: 1px solid var(--line); padding: .5rem 0; }
        .be-meine td { border: 0; padding: .15rem .3rem; }
        .be-meine td.be-k { grid-column: 1 / -1; text-align: left !important; } }
"""


def block(css_path=""):
    """Editor-Block unten auf der Berichte-Übersicht (leer, wenn SKRIPT_URL fehlt)."""
    if not SKRIPT_URL:
        return ""
    kat = html.escape(json.dumps(KATEGORIEN, ensure_ascii=False), quote=True)
    return f"""
      <details class="card einreichen" id="einreichen">
        <summary><span><strong>Selbst etwas erlebt?</strong><br><span class="klein">{html.escape(INTRO)}</span></span>
          <span class="btn">Bericht schreiben</span></summary>
        <div class="be-app" id="be-app" data-skript="{html.escape(SKRIPT_URL)}" data-max="{MAX_ZEICHEN}" data-kat="{kat}">
          <noscript><p>Für den Editor wird JavaScript benötigt.</p></noscript>
        </div>
      </details>
      <script src="{css_path}bericht.js" defer></script>"""
