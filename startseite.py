"""
Startseite (index.html): festes Kopfbild mit Termin-Kasten, Berichte-Slider und drei „Kästchen“
(Mannschaften, Geschichte, Über uns), jedes mit eigenen Fotos.

BILDER – alles im Ordner startseite/:
  startseite/kopfbild.jpg        festes Bild oben (wird nie gewechselt). Querformat, am besten 16:9.
  startseite/mannschaften/       Fotos für das Kästchen „Mannschaften“ (blenden ruhig über)
  startseite/historie/           alte Fotos für „Geschichte“ – erscheinen als Polaroid-Stapel
  startseite/ueber-uns/          Fotos für „Über uns / Neu hier?“
Neue Fotos einfach in den Ordner legen. Reihenfolge = alphabetisch (01-…, 02-… davorschreiben).
In den Ordnern mannschaften/ und ueber-uns/ müssen alle Fotos dasselbe Format haben (z. B. 4:3),
sonst müsste beim Überblenden etwas abgeschnitten werden: Fotos mit anderem Format werden
übersprungen (Hinweis in der Konsole). Im Polaroid-Stapel ist jedes Format erlaubt.
Bildunterschrift im Polaroid = Dateiname ohne Nummer, z. B. "03-oberlandquartett-2015.jpg" -> "Oberlandquartett 2015".

build_site.py ruft seite(...) auf und liefert die Daten (Termine, Berichte, Mannschaften, ...).
"""

import datetime
import html
import os
import re
from urllib.parse import quote

try:
    from PIL import Image, ImageOps     # nur für die Bildmaße (Seitenverhältnis); fehlt Pillow, gilt 4:3 bzw. 16:9
except ImportError:
    Image = None

# ==========================================
# EINSTELLUNGEN
# ==========================================
ORDNER = "startseite"
KOPFBILD = "kopfbild.jpg"
KAESTCHEN_ORDNER = {"mannschaften": "mannschaften", "historie": "historie", "ueber_uns": "ueber-uns"}
FORMAT_TOLERANZ = 0.03          # Fotos eines Kästchens dürfen im Seitenverhältnis um 3 % abweichen
WECHSEL_SEKUNDEN = 6            # Überblenden in den Kästchen
POLAROID_SEKUNDEN = 5           # nächstes Foto im Polaroid-Stapel
BERICHTE_ANZAHL = 9             # so viele Berichte im Slider
BERICHTE_SEKUNDEN = 9           # Slider rückt so oft eine Karte weiter (Maus darüber = Pause)
TERMINE_ANZAHL = 5              # Termine im Kasten oben
GEBURTSTAG_ALTER = True         # "wird 34" bei den Geburtstagen anzeigen
GEBURTSTAG_TAGE = 7             # Geburtstage von heute bis in so vielen Tagen

TITEL = "Schach spielen in Aschheim, Feldkirchen &amp; Kirchheim"
UNTERTITEL = ("Jeden Freitag im Gymnasium Kirchheim – Jugend 18 bis 19:30 Uhr, Erwachsene ab 19:30 Uhr. "
              "Einsteiger und Gäste willkommen.")
GRUENDUNG = 1952
HISTORIE_TEXT = ("Aus den Schachfreunden Feldkirchen von 1952 ist eine Schachgemeinschaft für drei Gemeinden "
                 "geworden – mit Mannschaften von der Jugend bis zur Bezirksliga. Chronik, Meilensteine und "
                 "welche Mannschaft wann in welcher Liga spielte.")
UEBER_UNS_TEXT = ("Komm einfach an einem Freitag vorbei – ohne Anmeldung, Schnuppern ist kostenlos. "
                  "Ob Einsteiger, Hobbyspieler oder Turnierspieler, ob jung oder alt: Bei uns findet jeder Gegner.")

WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def esc(x):
    return html.escape(str(x), quote=True)


# ==========================================
# BILDER
# ==========================================
def _format(pfad):
    """Breite/Höhe (mit EXIF-Drehung) oder None."""
    if Image is None:
        return None
    try:
        with Image.open(pfad) as im:
            w, h = ImageOps.exif_transpose(im).size if hasattr(ImageOps, "exif_transpose") else im.size
            return w / h
    except Exception:
        return None


def bilder(unterordner):
    """[(url, verhältnis)] aus startseite/<unterordner>/ (alphabetisch)."""
    ordner = os.path.join(ORDNER, unterordner)
    if not os.path.isdir(ordner):
        return []
    return [(f"{ORDNER}/{quote(unterordner)}/{quote(n)}", _format(os.path.join(ordner, n)))
            for n in sorted(os.listdir(ordner)) if os.path.splitext(n)[1].lower() in IMG_EXT]


def gleiches_format(liste, name):
    """Nur Fotos im Format des ersten Fotos (sonst müsste beim Überblenden abgeschnitten werden)."""
    if not liste:
        return [], 4 / 3
    soll = next((r for _, r in liste if r), 4 / 3)
    ok = []
    for url, r in liste:
        if r and abs(r - soll) / soll > FORMAT_TOLERANZ:
            print(f"Hinweis Startseite: {url} hat ein anderes Format als die anderen in '{name}' – übersprungen.")
            continue
        ok.append(url)
    return ok, soll


def unterschrift(url):
    name = os.path.splitext(os.path.basename(url))[0]
    name = re.sub(r"^\d+[-_ ]*", "", name.replace("%20", " "))
    return name.replace("-", " ").replace("_", " ").strip().capitalize()


def wechselbild_html(urls, verhaeltnis):
    if not urls:
        return ""
    imgs = "".join(f'<img src="{u}" alt="" {zusatz}>' for u, zusatz in
                   zip(urls, ['class="an"'] + ['loading="lazy"'] * (len(urls) - 1)))
    return f'<div class="st-wechsel" style="aspect-ratio:{verhaeltnis:.4f}">{imgs}</div>'


def wechselbild_frei_html(liste):
    """Überblenden für Fotos in verschiedenen Formaten: jedes Foto ganz, mittig, nichts abgeschnitten."""
    if not liste:
        return ""
    imgs = "".join(f'<img src="{u}" alt=""{" class=an" if i == 0 else ""}>' for i, (u, _) in enumerate(liste))
    return f'<div class="st-wechsel frei">{imgs}</div>'


def polaroid_html(liste):
    if not liste:
        return ""
    drehung = [-4, 3, -1.5, 5, -3, 2]
    karten = "".join(
        f'<figure class="st-pol" style="--r:{drehung[i % len(drehung)]}deg;z-index:{len(liste) - i}">'
        f'<img src="{u}" alt=""><figcaption>{esc(unterschrift(u))}</figcaption></figure>'
        for i, (u, _) in enumerate(liste))
    return f'<div class="st-stapel">{karten}</div>'


# ==========================================
# BAUSTEINE
# ==========================================
def kopf_html(termine_html):
    pfad = os.path.join(ORDNER, KOPFBILD)
    if os.path.exists(pfad):
        r = _format(pfad) or 16 / 9
        bild = f'<img class="st-kopfbild" src="{ORDNER}/{quote(KOPFBILD)}" alt="">'
    else:
        r, bild = 16 / 9, ""
    return f"""
    <section class="st-hero st-voll" style="--verh:{r:.4f}">
      {bild}
      <div class="st-hero-raster">
        <div class="st-hero-text">
          <h1>{TITEL}</h1>
          <p>{UNTERTITEL}</p>
          <a href="ueber-uns.html#neu-hier" class="st-btn voll">Neu hier? So kommst du vorbei →</a>
        </div>
        {termine_html}
      </div>
    </section>"""


def termine_html(events, team_klasse, plain_text):
    """Glas-Kasten „Diese Woche": nächster Spielabend (Skript) + die nächsten Termine."""
    zeilen = []
    for ev in events:
        d = ev["date"]
        pills = "".join(f'<span class="pill {team_klasse(t)}">{t.strip()}</span>'
                        for t in (ev.get("who") or "").split(",") if t.strip())
        zeilen.append(
            f'<a class="event-card st-termin" href="termine.html" data-date="{d.isoformat()}">'
            f'<span class="st-tag"><b>{d.day}</b><span>{WOCHENTAG[d.weekday()]} {d.month:02d}.</span></span>'
            f'<span class="st-tt">{esc(plain_text(ev["title"]))}<span class="ev-rel"></span></span>'
            f'<span class="st-pills">{pills}</span></a>')
    return f"""
        <aside class="st-glas" aria-label="Termine">
          <h2>Diese Woche</h2>
          <p class="spielabend st-spielabend" id="spielabend" hidden></p>
          <div class="events-grid" data-max="{TERMINE_ANZAHL}">{"".join(zeilen)}</div>
          <p class="events-empty" id="events-empty" hidden>Gerade keine Termine eingetragen.</p>
          <a class="st-mehr" href="termine.html">Alle Termine →</a>
        </aside>"""


def berichte_html(berichte):
    karten = []
    for r in berichte[:BERICHTE_ANZAHL]:
        bild = f'<img src="{r["thumb"]}" alt="" loading="lazy">' if r.get("thumb") else ""
        auszug = "" if bild else f'<span class="st-auszug">{r.get("snippet") or ""}</span>'
        karten.append(f"""
        <a class="st-bkarte{"" if bild else " ohne-bild"}" href="berichte/{r['filename']}">{bild}
          <span class="st-btext"><span class="st-meta">{r['meta']}</span><b>{r['title']}</b>{auszug}
          {"" if bild else '<span class="st-weiter">Bericht lesen →</span>'}</span></a>""")
    if not karten:
        return ""
    return f"""
    <section class="st-block">
      <div class="st-kopfzeile"><h2>Berichte</h2><a href="berichte.html">Alle Berichte →</a></div>
      <div class="st-slider" data-sek="{BERICHTE_SEKUNDEN}">
        <div class="st-fenster"><div class="st-spur">{"".join(karten)}</div></div>
        <div class="st-steuer"><button type="button" class="st-zurueck" aria-label="Zurück">←</button>
          <button type="button" class="st-vor" aria-label="Weiter">→</button><span class="st-punkte"></span></div>
      </div>
    </section>"""


def ergebnisse_html(zeilen):
    """zeilen = [(kurz, css-Klasse, Gegnertext, mein, sein, art 's'/'u'/'n', Runde, Link)]"""
    if not zeilen:
        return "<p>Die Saison hat noch nicht begonnen.</p>", ""
    s = sum(1 for z in zeilen if z[5] == "s")
    u = sum(1 for z in zeilen if z[5] == "u")
    n = sum(1 for z in zeilen if z[5] == "n")
    teile = [f"{s} {'Sieg' if s == 1 else 'Siege'}"] if s else []
    teile += [f"{u} {'Remis'}"] if u else []
    teile += [f"{n} {'Niederlage' if n == 1 else 'Niederlagen'}"] if n else []
    titel = ", ".join(teile[:-1]) + " und " + teile[-1] if len(teile) > 1 else (teile[0] if teile else "")
    rows = "".join(
        f'<tr class="{cls}"><td><a href="{link}">{esc(kurz)}</a></td><td>{esc(geg)}</td>'
        f'<td class="st-rd">R{rd}</td><td class="st-erg-{art}">{mein} : {sein}</td></tr>'
        for kurz, cls, geg, mein, sein, art, rd, link in zeilen)
    return f'<table class="st-erg">{rows}</table>', titel


def geburtstage_html(liste):
    """liste = [(datum, name, alter)] – nur öffentlich freigegebene. Für Admins füllt konto.js die Liste nach dem Login."""
    if not liste:
        return f'<div class="st-geb" data-geb-woche="{GEBURTSTAG_TAGE}" hidden><h3>Geburtstage diese Woche</h3><ul></ul></div>'
    heute = datetime.date.today()
    z = "".join(
        f'<li data-date="{d.isoformat()}"><span><b>{esc(n)}</b> <span class="st-meta">'
        f'{"heute" if d == heute else f"{WOCHENTAG[d.weekday()]} {d.day:02d}.{d.month:02d}."}</span></span>'
        f'{f"<em>wird {a}</em>" if GEBURTSTAG_ALTER and a else ""}</li>' for d, n, a in liste)
    return f'<div class="st-geb" data-geb-woche="{GEBURTSTAG_TAGE}"><h3>Geburtstage diese Woche</h3><ul>{z}</ul></div>'


def kaestchen(bild, inhalt, umgedreht=False):
    return f"""
    <section class="st-split st-voll{" um" if umgedreht else ""}">
      <div class="st-bild">{bild}</div>
      <div class="st-inhalt">{inhalt}</div>
    </section>"""


# ==========================================
# SEITE
# ==========================================
def seite(events, berichte, ergebnis_zeilen, geburtstage, mitglieder, mannschaften, team_klasse, plain_text, extra_oben=""):
    k1, r1 = gleiches_format(bilder(KAESTCHEN_ORDNER["mannschaften"]), "mannschaften")
    k3, r3 = gleiches_format(bilder(KAESTCHEN_ORDNER["ueber_uns"]), "ueber-uns")
    k2 = bilder(KAESTCHEN_ORDNER["historie"])
    tabelle, ergebnis_titel = ergebnisse_html(ergebnis_zeilen)

    mannschaften_inhalt = f"""
      <div class="st-kl">Mannschaften · zuletzt gespielt</div>
      <h2>{ergebnis_titel or "Unsere Mannschaften"}</h2>
      {tabelle}
      <p class="st-knoepfe"><a class="st-btn" href="mannschaften.html">Alle Mannschaften →</a></p>"""
    historie_inhalt = f"""
      <div class="st-kl">Geschichte</div>
      <h2>Seit {GRUENDUNG} am Brett</h2>
      <p>{HISTORIE_TEXT}</p>
      <div class="st-fakten"><div><b>{GRUENDUNG}</b><span>gegründet</span></div>
        <div><b>{mannschaften}</b><span>Mannschaften heute</span></div>
        <div><b>{mitglieder}</b><span>Mitglieder</span></div></div>
      <p class="st-knoepfe"><a class="st-btn" href="geschichte.html">Zur Geschichte →</a></p>"""
    ueber_inhalt = f"""
      <div class="st-kl">Über uns · Neu hier?</div>
      <h2>Komm einfach vorbei</h2>
      <p>{UEBER_UNS_TEXT}</p>
      <ul class="st-wann"><li><b>Wann?</b> Jeden Freitag ab 18 Uhr – Jugend bis 19:30, Erwachsene ab 19:30 Uhr</li>
        <li><b>Wo?</b> Gymnasium Kirchheim, Heimstettner Str. 20, 85551 Kirchheim</li></ul>
      <p class="st-knoepfe"><a class="st-btn voll" href="ueber-uns.html#neu-hier">Über uns &amp; Neu hier →</a>
        <a class="st-btn" href="mitgliederantrag.pdf" download>Mitgliedsantrag (PDF)</a></p>
      {geburtstage_html(geburtstage)}"""

    content = f"""
    <div class="st-voll pause-band" id="pause-band" hidden></div>
    {extra_oben}
    {kopf_html(termine_html(events, team_klasse, plain_text))}
    {berichte_html(berichte)}
    {kaestchen(wechselbild_html(k1, r1), mannschaften_inhalt)}
    {kaestchen(wechselbild_frei_html(k2), historie_inhalt, umgedreht=True)}
    {kaestchen(wechselbild_html(k3, r3), ueber_inhalt)}
    {JS.replace("__WECHSEL__", str(WECHSEL_SEKUNDEN * 1000)).replace("__POLAROID__", str(POLAROID_SEKUNDEN * 1000))}"""
    return content, CSS


CSS = """<style>
  /* Startseite: Abschnitte über die volle Bildschirmbreite (main ist sonst schmaler) */
  html, body { overflow-x: clip; }
  main.container { margin-top: 0 !important; }
  .st-voll { width: 100vw; margin-left: calc(50% - 50vw); }
  .st-kl { font-size: 0.95rem; font-weight: 600; color: var(--hell); margin-bottom: 0.5rem; }
  .st-btn { display: inline-flex; align-items: center; gap: .5rem; padding: .8rem 1.5rem; font-weight: 700; font-size: 1rem;
    border: 1.5px solid currentColor; color: var(--head); text-decoration: none; border-radius: 6px; transition: background .25s, color .25s; }
  .st-btn:hover { background: var(--head); color: var(--bg); }
  .st-btn.voll { background: var(--hell); border-color: var(--hell); color: #0e1524; }
  .st-btn.voll:hover { background: #fff; border-color: #fff; }
  .st-meta { color: var(--muted); font-size: .9rem; font-weight: 400; }

  /* Kopfbild: Höhe folgt dem Foto -> nichts abgeschnitten, kein Rand */
  .st-hero { position: relative; aspect-ratio: var(--verh); background: #0b111d; overflow: hidden; display: flex; }
  .st-kopfbild { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center top; }
  .st-hero::after { content: ""; position: absolute; inset: 0;
    background: linear-gradient(90deg, #0b111de6 0%, #0b111d99 45%, #0b111d55 100%), linear-gradient(transparent 70%, var(--bg)); }
  .st-hero-raster { position: relative; z-index: 1; flex: 1; padding: 2.5rem max(1.5rem, calc((100% - 1280px) / 2)) 3rem;
    display: grid; grid-template-columns: 1.1fr .9fr; gap: 3rem; align-items: end; }
  .st-hero h1 { color: #fff; font-size: clamp(2.4rem, 3.8vw, 3.8rem); line-height: 1.05; margin: 0; }
  .st-hero-text p { color: #e3e8f1; font-size: 1.2rem; margin: 1.1rem 0 1.7rem; max-width: 38rem; }

  /* Termin-Kasten */
  .st-glas { background: #0b111da6; backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid #ffffff26;
    border-radius: 12px; padding: 1.3rem 1.5rem; color: #e3e8f1; }
  .st-glas h2 { color: #fff; font-size: 1.5rem; margin: 0 0 .6rem; }
  .st-glas .st-spielabend { margin: 0 0 .4rem; padding: .5rem .8rem; background: #6f9fd833; border: 0; border-left: 3px solid var(--hell);
    border-radius: 6px; font-weight: 700; color: #fff; font-size: .98rem; }
  .st-glas .events-grid { display: block; }
  .st-glas a.event-card.st-termin { display: grid; grid-template-columns: 3.2rem 1fr auto; gap: .9rem; align-items: center;
    padding: .5rem .15rem; margin: 0; background: none; border: 0; border-bottom: 1px solid #ffffff1f; border-radius: 0;
    box-shadow: none; color: #fff; text-decoration: none; transition: background .2s; }
  .st-glas a.event-card.st-termin:hover { background: #ffffff0d; }
  .st-glas .event-card .ev-rel:not(:empty), .st-glas .event-card.next .ev-rel:not(:empty) { background: none; color: var(--hell); padding: 0; }
  .st-tag { text-align: center; line-height: 1; } .st-tag b { display: block; font-family: var(--font-head); font-size: 1.45rem; color: #fff; }
  .st-tag span { font-size: .78rem; color: #b9c4d6; font-weight: 600; }
  .st-tt { font-weight: 600; font-size: 1.02rem; color: #fff; line-height: 1.3; }
  .st-tt .ev-rel:not(:empty) { display: block; font-size: .78rem; font-weight: 600; }
  .st-pills .pill { font-size: .75rem; margin: 0; padding: .12rem .55rem; border-radius: 999px; font-weight: 700; white-space: nowrap; }
  .st-mehr { display: inline-block; margin-top: .8rem; color: var(--hell); font-weight: 600; text-decoration: none; }
  .st-glas .events-empty { margin: .4rem 0; color: #e3e8f1; }

  /* Berichte-Slider: rückt Karte für Karte weiter (kein Dauerlauf) */
  .st-block { padding: 4.5rem 0 3.5rem; }
  .st-kopfzeile { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 1.4rem; }
  .st-kopfzeile h2 { font-size: 2.5rem; margin: 0; } .st-kopfzeile a { font-weight: 600; text-decoration: none; }
  .st-fenster { overflow: hidden; }
  .st-spur { display: flex; gap: 1.4rem; align-items: flex-start; transition: transform .8s cubic-bezier(.65,0,.35,1); }
  .st-bkarte { flex: 0 0 calc((100% - 2.8rem) / 3); background: var(--surface); border-radius: 10px; overflow: hidden;
    color: inherit; text-decoration: none; transition: transform .3s; }
  .st-bkarte:hover { transform: translateY(-5px); }
  .st-bkarte img { display: block; width: 100%; height: auto; max-height: 340px; object-fit: contain; background: var(--surface); }
  .st-spur { align-items: stretch; }
  .st-bkarte.ohne-bild { display: flex; border-top: 4px solid var(--hell); }
  .st-bkarte.ohne-bild .st-btext { display: flex; flex-direction: column; padding: 1.6rem 1.5rem; }
  .st-bkarte.ohne-bild b { font-size: 1.6rem; line-height: 1.2; margin: .5rem 0 1rem; }
  .st-auszug { color: var(--muted); display: -webkit-box; -webkit-line-clamp: 7; -webkit-box-orient: vertical; overflow: hidden; }
  .st-weiter { margin-top: auto; padding-top: 1rem; color: var(--hell); font-weight: 600; }
  .st-btext { display: block; padding: 1rem 1.2rem 1.3rem; } .st-btext b { display: block; font-family: var(--font-head); font-size: 1.25rem; color: var(--head); margin-top: .3rem; }
  .st-steuer { display: flex; align-items: center; gap: .9rem; margin-top: 1.2rem; }
  .st-steuer button { width: 2.8rem; height: 2.8rem; border-radius: 50%; border: 1.5px solid var(--line); background: none; color: var(--head); font-size: 1.15rem; cursor: pointer; }
  .st-steuer button:hover { background: var(--head); color: var(--bg); }
  .st-punkte { display: flex; gap: .45rem; } .st-punkte i { width: .55rem; height: .55rem; border-radius: 999px; background: var(--line); cursor: pointer; transition: width .3s; }
  .st-punkte i.an { background: var(--hell); width: 1.6rem; }

  /* Kästchen: Bild + Inhalt nebeneinander, abwechselnd */
  .st-split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: center; background: var(--bg); }
  .st-split.um .st-bild { order: 2; }
  .st-inhalt { padding: 3.5rem max(1.5rem, 6vw); }
  .st-inhalt h2 { font-size: clamp(2rem, 3.2vw, 3rem); line-height: 1.1; margin: 0 0 1rem; }
  .st-inhalt p { font-size: 1.12rem; }
  .st-knoepfe { display: flex; flex-wrap: wrap; gap: .8rem; margin-top: 1.5rem; }
  .st-wechsel { position: relative; width: 100%; overflow: hidden; }
  .st-wechsel img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 1.6s ease; }
  .st-wechsel img.an { opacity: 1; }
  .st-wechsel.frei { display: grid; align-items: center; overflow: visible; }
  .st-wechsel.frei img { position: static; grid-area: 1 / 1; height: auto; object-fit: initial; }

  .st-erg { width: 100%; border-collapse: collapse; font-size: 1.05rem; background: none !important; }
  .st-erg td { padding: .6rem .4rem; border-bottom: 1px solid var(--line); }
  .st-erg td:first-child { font-weight: 700; width: 6rem; } .st-erg td:first-child a { color: var(--team, var(--head)); text-decoration: none; }
  .st-erg td:last-child { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .st-erg .st-rd { color: var(--muted); font-size: .85rem; width: 2.5rem; }
  .st-erg-s { color: #5fd08a; } .st-erg-n { color: #ff8f84; } .st-erg-u { color: #e6c15a; }
  :root[data-theme="light"] .st-erg-s { color: #2e7d4f; } :root[data-theme="light"] .st-erg-n { color: #b03a2e; } :root[data-theme="light"] .st-erg-u { color: #9a6a12; }

  .st-fakten { display: flex; flex-wrap: wrap; gap: 2.6rem; margin: 1.6rem 0 .5rem; }
  .st-fakten b { display: block; font-family: var(--font-head); font-size: 2.4rem; color: var(--head); line-height: 1.1; }
  .st-fakten span { color: var(--muted); }
  .st-wann { list-style: none; padding: 0; margin: 1rem 0; font-size: 1.08rem; display: grid; gap: .4rem; }
  .st-geb[hidden] { display: none; }
  .st-geb { margin-top: 2rem; padding-top: 1.2rem; border-top: 1px solid var(--line); }
  .st-geb h3 { font-size: 1.1rem; margin: 0 0 .5rem; }
  .st-geb ul { list-style: none; padding: 0; margin: 0; }
  .st-geb li { display: flex; justify-content: space-between; padding: .4rem 0; border-bottom: 1px solid var(--line); }
  .st-geb b { color: var(--head); } .st-geb em { font-style: normal; color: var(--hell); font-weight: 600; }

  /* Polaroid-Stapel für alte Fotos: jedes Foto in seinem Format */
  .st-stapel { position: relative; height: clamp(380px, 38vw, 560px); }
  .st-pol { position: absolute; left: 50%; top: 50%; margin: 0; background: #fbfaf6; padding: 12px 12px 42px;
    box-shadow: 0 12px 30px #0008; transform: translate(-50%, -50%) rotate(var(--r)); transition: transform 1s ease, opacity 1s ease; }
  .st-pol img { display: block; max-width: min(34vw, 520px); max-height: clamp(260px, 28vw, 420px); width: auto; height: auto; }
  .st-pol figcaption { position: absolute; left: 0; right: 0; bottom: 10px; text-align: center; color: #333;
    font-family: "Segoe Print", "Bradley Hand", cursive; font-size: 1rem; }
  .st-pol.weg { transform: translate(10%, -50%) rotate(calc(var(--r) + 12deg)); opacity: 0; }

  @media (max-width: 900px) {
    .st-hero { aspect-ratio: auto; min-height: 0; }
    .st-hero-raster { position: relative; grid-template-columns: minmax(0, 1fr); padding-top: 2.5rem; }
    .st-kopfbild { opacity: .55; }
    .st-split, .st-split.um { grid-template-columns: minmax(0, 1fr); } .st-split.um .st-bild { order: 0; }
    .st-inhalt { padding: 2.2rem 1.2rem 2.8rem; }
    .st-bkarte { flex-basis: 85%; }
    .st-stapel { height: 420px; } .st-pol img { max-width: 72vw; max-height: 300px; }
    .st-kopfzeile h2 { font-size: 2rem; }
    .st-erg { font-size: .95rem; } .st-erg .st-rd { display: none; } .st-erg td:first-child { width: auto; white-space: nowrap; }
  }
  @media (prefers-reduced-motion: reduce) { .st-spur, .st-wechsel img, .st-pol { transition: none; } }
</style>"""

JS = """<script>
(function () {
  var ruhig = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Berichte-Slider
  document.querySelectorAll(".st-slider").forEach(function (sl) {
    var spur = sl.querySelector(".st-spur"), karten = spur.children, punkte = sl.querySelector(".st-punkte"), i = 0, t = null;
    function sicht() { return window.innerWidth <= 900 ? 1 : 3; }
    function max() { return Math.max(0, karten.length - sicht()); }
    function geh(k) {
      i = ((k % (max() + 1)) + max() + 1) % (max() + 1);
      var x = karten[i] ? karten[i].offsetLeft - karten[0].offsetLeft : 0;
      spur.style.transform = "translateX(" + (-x) + "px)";
      [].forEach.call(punkte.children, function (p, j) { p.classList.toggle("an", j === i); });
    }
    function punkteBauen() {
      punkte.innerHTML = "";
      for (var k = 0; k <= max(); k++) { var p = document.createElement("i"); p.onclick = (function (n) { return function () { geh(n); }; })(k); punkte.appendChild(p); }
      geh(Math.min(i, max()));
    }
    function start() { stop(); if (!ruhig) t = setInterval(function () { geh(i + 1); }, (+sl.dataset.sek || 9) * 1000); }
    function stop() { if (t) clearInterval(t); t = null; }
    sl.querySelector(".st-vor").onclick = function () { geh(i + 1); start(); };
    sl.querySelector(".st-zurueck").onclick = function () { geh(i - 1); start(); };
    sl.addEventListener("mouseenter", stop); sl.addEventListener("mouseleave", start);
    addEventListener("resize", punkteBauen); punkteBauen(); start();
  });
  if (ruhig) return;
  // Kästchen: ruhig überblenden, versetzt gestartet
  document.querySelectorAll(".st-wechsel").forEach(function (w, nr) {
    var b = w.querySelectorAll("img"), i = 0;
    if (b.length < 2) return;
    setTimeout(function () { setInterval(function () { b[i].classList.remove("an"); i = (i + 1) % b.length; b[i].classList.add("an"); }, __WECHSEL__); }, nr * 2000);
  });
  // Polaroid-Stapel: oberstes Foto gleitet weg und kommt unten wieder dazu
  document.querySelectorAll(".st-stapel").forEach(function (s) {
    var k = [].slice.call(s.children);
    if (k.length < 2) return;
    setInterval(function () {
      var oben = k.shift(); oben.classList.add("weg");
      setTimeout(function () { k.push(oben); k.forEach(function (el, j) { el.style.zIndex = k.length - j; }); oben.classList.remove("weg"); }, 1000);
    }, __POLAROID__);
  });
})();
</script>"""
