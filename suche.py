"""
Seitenweite Suche.

build_site.render_page() ruft merken() für jede erzeugte Seite auf; am Ende schreibt bauen()
den Suchindex (suche.json) und die Seite suche.html. Gesucht wird im Browser (kein Server nötig).
Oben im Kopf jeder Seite erscheint ein Such-Knopf (siehe KNOPF).
"""
import html
import json
import re

SEITE = "suche.html"
INDEX = "suche.json"
TITEL = "Suche"

# ==========================================
# EINSTELLUNGEN
# ==========================================
TEXT_LAENGE = 2500             # so viele Zeichen Text je Seite kommen in den Index
TEXT_LAENGE_BERICHT = 8000     # Berichte ganz (bis zu dieser Länge)
MAX_TREFFER = 40
AUSLASSEN = {"404.html", SEITE}    # diese Seiten nie finden
# Seiten, die bei gleichem Treffer weiter oben stehen (Wurzel-Dateinamen)
WICHTIG = {"index.html", "termine.html", "mannschaften.html", "berichte.html", "jugend.html",
           "turniere.html", "neu-hier.html", "kontakt.html", "faq.html"}

_seiten = {}


def _text(inhalt):
    t = re.sub(r"(?is)<(script|style|svg|nav)\b.*?</\1>", " ", inhalt)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?s)<a\b[^>]*>\s*←.*?</a>", " ", t)          # "← Zurück zu …"-Links
    t = re.sub(r"(?is)<h1\b.*?</h1>", " ", t, count=1)           # Überschrift = Titel
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def zusatz(dateiname, text):
    """Weiterer Suchtext für eine Seite, deren Inhalt erst im Browser entsteht (z. B. Turnierkalender)."""
    url = dateiname.replace("\\", "/")
    if url in _seiten:
        _seiten[url]["x"] = (_seiten[url]["x"] + " " + text)[:TEXT_LAENGE_BERICHT * 3]


def merken(titel, inhalt, dateiname, beschreibung=""):
    url = dateiname.replace("\\", "/").lstrip("./")
    if url.split("/")[-1] in AUSLASSEN or url.startswith("saison/"):
        return
    laenge = TEXT_LAENGE_BERICHT if url.startswith("berichte/") else TEXT_LAENGE
    art = ("Bericht" if url.startswith("berichte/") else "Spieler" if url.startswith("spieler/")
           else "AFK on Tour" if url.startswith("tour-") else "Seite")
    _seiten[url] = {"t": _text(titel), "u": url, "a": art, "d": _text(beschreibung or "")[:200],
                    "x": _text(inhalt)[:laenge], "w": 1 if url in WICHTIG else 0}


KNOPF = ('<a class="kopf-knopf such-knopf" href="{nav_path}suche.html" aria-label="Suche" title="Suche">'
         '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" '
         'stroke="currentColor" stroke-width="2.2"/><path d="M15.5 15.5 21 21" stroke="currentColor" '
         'stroke-width="2.4" stroke-linecap="round"/></svg></a>')

KNOPF_CSS = ""   # Aussehen des Such-Knopfs: design.css (Abschnitt Header)


def knopf_einbauen(seite_html, nav_path):
    """Setzt den Such-Knopf vor den Hell/Dunkel-Schalter im Kopf."""
    marke = '<button type="button" class="kopf-knopf theme-schalter"'
    if marke not in seite_html or 'such-knopf"' in seite_html:
        return seite_html
    return seite_html.replace(marke, KNOPF.format(nav_path=nav_path) + "\n    " + marke, 1)


CSS = """<style>
  .su-feld { display: flex; gap: 0.5rem; margin: 1rem 0 0.4rem; max-width: 640px; }
  .su-feld input { flex: 1; font: inherit; font-size: 1.05rem; padding: 0.65rem 0.9rem; border-radius: 10px;
    border: 1px solid var(--line, #ccc); background: var(--soft, #fff); color: var(--text, #222); }
  .su-info { color: var(--muted, #777); font-size: 0.9rem; min-height: 1.3em; }
  .su-liste { list-style: none; padding: 0; margin: 1rem 0; display: grid; gap: 0.7rem; max-width: 820px; }
  .su-liste li { padding: 0.75rem 1rem; border: 1px solid var(--line, #ddd); border-radius: 10px; background: var(--surface, #fff); }
  .su-liste a { font-weight: 700; font-size: 1.05rem; text-decoration: none; }
  .su-liste a:hover { text-decoration: underline; }
  .su-art { display: inline-block; font-size: 0.72rem; padding: 0.05rem 0.5rem; border-radius: 999px; margin-left: 0.5rem;
    border: 1px solid var(--line, #ccc); color: var(--muted, #777); vertical-align: middle; }
  .su-text { margin: 0.3rem 0 0; font-size: 0.9rem; line-height: 1.45; color: var(--muted, #666); }
  .su-text mark { background: #f5d76e; color: #222; border-radius: 2px; padding: 0 1px; }
  .su-url { font-size: 0.75rem; color: var(--muted, #888); }
</style>"""

JS = """
(function () {
  var feld = document.getElementById("su-q"), liste = document.getElementById("su-liste"), info = document.getElementById("su-info");
  var MAX = __MAX__, DATEN = null;
  function norm(s) {
    return String(s || "").toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
      .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
  // Ausschnitt um den ersten Treffer, Treffer markiert (Positionen im normalisierten Text ~ Original)
  function ausschnitt(text, woerter) {
    var n = norm(text), pos = -1;
    woerter.forEach(function (w) { var p = n.indexOf(w); if (p >= 0 && (pos < 0 || p < pos)) pos = p; });
    var start = Math.max(0, pos - 80), stueck = text.slice(start, start + 240);
    var out = esc(stueck);
    woerter.forEach(function (w) {
      if (w.length < 2) return;
      var re = new RegExp("(" + w.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&").replace(/ae/g, "(?:ae|ä)").replace(/oe/g, "(?:oe|ö)")
        .replace(/ue/g, "(?:ue|ü)").replace(/ss/g, "(?:ss|ß)") + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return (start > 0 ? "… " : "") + out + (start + 240 < text.length ? " …" : "");
  }
  function suchen() {
    var q = feld.value.trim(), woerter = norm(q).split(/\\s+/).filter(Boolean);
    try { history.replaceState(null, "", q ? "?q=" + encodeURIComponent(q) : location.pathname); } catch (e) {}
    if (!woerter.length) { liste.innerHTML = ""; info.textContent = ""; return; }
    if (!DATEN) { info.textContent = "Lade …"; return; }
    var treffer = [];
    DATEN.forEach(function (s) {
      var t = s._t, x = s._x, punkte = 0;
      for (var i = 0; i < woerter.length; i++) {
        var w = woerter[i], inT = t.indexOf(w) >= 0, inX = x.indexOf(w) >= 0;
        if (!inT && !inX) return;
        punkte += (inT ? 10 : 0) + (inX ? 1 + Math.min(4, x.split(w).length - 2) : 0);
        if (t === w || t.indexOf(w) === 0) punkte += 5;
      }
      treffer.push([punkte + s.w * 3, s]);
    });
    treffer.sort(function (a, b) { return b[0] - a[0]; });
    info.textContent = treffer.length ? treffer.length + (treffer.length === 1 ? " Treffer" : " Treffer") +
      (treffer.length > MAX ? ", die besten " + MAX + " werden gezeigt" : "") : "Nichts gefunden. Probier ein anderes Wort.";
    liste.innerHTML = treffer.slice(0, MAX).map(function (z) {
      var s = z[1], quelle = s._x && s.x.length ? s.x : s.d;
      return '<li><a href="' + esc(s.u) + '">' + esc(s.t) + '</a><span class="su-art">' + esc(s.a) + "</span>" +
        '<p class="su-text">' + (quelle ? ausschnitt(quelle, woerter) : "") + "</p></li>";
    }).join("");
  }
  var warte;
  feld.addEventListener("input", function () { clearTimeout(warte); warte = setTimeout(suchen, 120); });
  var start = new URLSearchParams(location.search).get("q");
  if (start) feld.value = start;
  fetch("__INDEX__").then(function (r) { return r.json(); }).then(function (d) {
    DATEN = d.map(function (s) { s._t = norm(s.t); s._x = norm(s.t + " " + s.d + " " + s.x); return s; });
    suchen();
  }).catch(function () { info.textContent = "Der Suchindex konnte nicht geladen werden."; });
  feld.focus();
})();
"""


def bauen(render_page):
    """Schreibt suche.json + suche.html. Als LETZTES aufrufen (nach allen anderen Seiten)."""
    daten = sorted(_seiten.values(), key=lambda s: s["u"])
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, separators=(",", ":"))
    inhalt = f"""
    <h1>{TITEL}</h1>
    <form class="su-feld" role="search" onsubmit="return false">
      <input type="search" id="su-q" placeholder="Name, Turnier, Thema …" autocomplete="off" aria-label="Suchbegriff">
    </form>
    <p class="su-info" id="su-info" aria-live="polite"></p>
    <ol class="su-liste" id="su-liste"></ol>
    <script>{JS.replace("__MAX__", str(MAX_TREFFER)).replace("__INDEX__", INDEX)}</script>"""
    render_page(TITEL, inhalt, SEITE, extra_styles=CSS, description="Suche auf der Website der SG AFK.")
    print(f"Suche: {len(daten)} Seiten im Index")
