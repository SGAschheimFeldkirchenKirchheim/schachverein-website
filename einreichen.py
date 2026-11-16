"""
"Bericht einreichen" – Formular-Block oben auf berichte.html.

Das Formular schickt Titel, Autor, Datum und Text an ein Google-Apps-Script
(bericht_einreichen.gs). Das Skript legt daraus berichte/<Jahr>/_<Titel>/Bericht.typ
im GitHub-Repo an und schickt eine Mail. Der Unterstrich vorne = Entwurf, noch nicht online.

Einstellungen:
  SKRIPT_URL  – Web-App-URL aus Apps Script (Bereitstellen -> Neue Bereitstellung -> Web-App).
                Leer lassen = Block wird nicht angezeigt.
  MAX_ZEICHEN – Höchstlänge des Textes (muss zum Wert im Apps Script passen).
"""
import datetime
import html

SKRIPT_URL = "https://script.google.com/macros/s/AKfycbxvMU_7CRADHdkcfSHuLLwmpYOGpZ6YbFqQCXVHSNl0wcG9A0iKRzaElJ2ATgUI0qeV/exec"
MAX_ZEICHEN = 20000

TITEL = "Bericht einreichen"
INTRO = ("Turnier gespielt, Mannschaftskampf erlebt, etwas Lustiges passiert? Schreib es auf. "
         "Wir schauen kurz drüber und stellen es online.")
FOTO_HINWEIS = "Fotos bitte per WhatsApp oder E-Mail an den Webmaster schicken. Die bauen wir dann ein."
DANKE = "Danke! Dein Bericht ist angekommen und erscheint, sobald er durchgesehen ist."


CSS = """
      .einreichen { margin: 2.5rem 0 0; padding: 0; }
      .einreichen > summary { cursor: pointer; list-style: none; padding: 0.9rem 1.2rem; display: flex;
        align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
      .einreichen > summary::-webkit-details-marker { display: none; }
      .einreichen > summary strong { font-size: 1rem; }
      .einreichen > summary .btn { white-space: nowrap; }
      .einreichen[open] > summary .btn { opacity: 0.6; }
      .einreichen form { display: grid; gap: 0.8rem; padding: 0 1.2rem 1.2rem; }
      .einreichen .ein-reihe { display: grid; grid-template-columns: 2fr 1.4fr 1fr; gap: 0.8rem; }
      @media (max-width: 700px) { .einreichen .ein-reihe { grid-template-columns: 1fr; } }
      .einreichen label { display: grid; gap: 0.25rem; font-weight: 600; font-size: 0.9rem; }
      .einreichen input, .einreichen textarea { font: inherit; font-weight: normal; padding: 0.55rem 0.7rem;
        border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--text); width: 100%; box-sizing: border-box; }
      .einreichen textarea { min-height: 14rem; resize: vertical; }
      .einreichen .ein-klein { font-size: 0.85rem; color: var(--muted); font-weight: normal; margin: 0; }
      .einreichen .ein-falle { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
      .einreichen .ein-meldung { margin: 0; font-weight: 600; }
      .einreichen .ein-meldung.ok { color: #2e8b57; }
      .einreichen .ein-meldung.fehler { color: #c0392b; }
      .einreichen button[disabled] { opacity: 0.6; cursor: wait; }
"""


def block():
    """HTML-Block unten auf der Berichte-Übersicht (leer, wenn SKRIPT_URL fehlt)."""
    if not SKRIPT_URL:
        return ""
    heute = datetime.date.today().isoformat()
    return f"""
      <details class="card einreichen" id="einreichen">
        <summary><span><strong>Selbst etwas erlebt?</strong><br><span class="ein-klein">{html.escape(INTRO)}</span></span>
          <span class="btn">{TITEL}</span></summary>
        <form id="ein-form" autocomplete="on">
          <div class="ein-reihe">
            <label>Titel <input name="titel" required maxlength="120" placeholder="z. B. AFK 2 gewinnt das Derby"></label>
            <label>Autor/in <input name="autor" required maxlength="80" autocomplete="name" placeholder="Vor- und Nachname"></label>
            <label>Datum <input name="datum" type="date" required value="{heute}"></label>
          </div>
          <label>Text
            <textarea name="text" required maxlength="{MAX_ZEICHEN}" placeholder="Leere Zeile = neuer Absatz"></textarea>
          </label>
          <label>E-Mail für Rückfragen (optional, wird nicht veröffentlicht)
            <input name="mail" type="email" maxlength="120" autocomplete="email">
          </label>
          <label class="ein-falle" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
          <p class="ein-klein">{html.escape(FOTO_HINWEIS)}</p>
          <div><button class="btn" type="submit">Absenden</button></div>
          <p class="ein-meldung" role="status"></p>
        </form>
      </details>
      <script>
      (function () {{
        var f = document.getElementById("ein-form"), d = document.getElementById("einreichen");
        if (location.hash === "#einreichen") d.open = true;
        var felder = ["titel", "autor", "text", "mail"], SPEICHER = "afk-bericht-entwurf";
        // Entwurf im Browser merken, damit nichts verloren geht
        try {{
          var alt = JSON.parse(localStorage.getItem(SPEICHER) || "{{}}");
          felder.forEach(function (n) {{ if (alt[n]) f.elements[n].value = alt[n]; }});
        }} catch (e) {{}}
        f.addEventListener("input", function () {{
          try {{
            var w = {{}}; felder.forEach(function (n) {{ w[n] = f.elements[n].value; }});
            localStorage.setItem(SPEICHER, JSON.stringify(w));
          }} catch (e) {{}}
        }});
        f.addEventListener("submit", function (ev) {{
          ev.preventDefault();
          var knopf = f.querySelector("button"), meldung = f.querySelector(".ein-meldung");
          var daten = {{}}; ["titel", "autor", "datum", "text", "mail", "website"].forEach(function (n) {{ daten[n] = f.elements[n].value.trim(); }});
          knopf.disabled = true; meldung.className = "ein-meldung"; meldung.textContent = "Wird gesendet …";
          fetch({SKRIPT_URL!r}, {{ method: "POST", body: JSON.stringify(daten) }})
            .then(function (r) {{ return r.json(); }})
            .then(function (a) {{
              if (!a.ok) throw new Error(a.fehler || "Unbekannter Fehler");
              meldung.className = "ein-meldung ok"; meldung.textContent = {DANKE!r};
              f.reset(); f.elements.datum.value = {heute!r};
              try {{ localStorage.removeItem(SPEICHER); }} catch (e) {{}}
            }})
            .catch(function (e) {{
              meldung.className = "ein-meldung fehler";
              meldung.textContent = "Das hat nicht geklappt (" + e.message + "). Dein Text bleibt gespeichert – bitte später nochmal versuchen.";
            }})
            .finally(function () {{ knopf.disabled = false; }});
        }});
      }})();
      </script>"""
