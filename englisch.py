"""
Englische Fassung ausgewählter Seiten (index-en.html, ueber-uns-en.html, ...).

So funktioniert es:
  - build_site.py baut wie immer die deutsche Seite; für die Seiten in EN_SEITEN entsteht daraus
    zusätzlich <name>-en.html.
  - Übersetzt wird Textstück für Textstück über das Wörterbuch uebersetzung/en.json
    (deutscher Text -> englischer Text). Einmal übersetzt = gespeichert.
  - Neue/geänderte deutsche Texte werden beim Build automatisch übersetzt: über MyMemory (kostenlos,
    ohne Konto) bzw. DeepL, falls DEEPL_KEY gesetzt ist. Klappt das nicht (Dienst weg, Text zu lang,
    Begriff verändert), bleibt das Stück auf der englischen Seite deutsch und steht in uebersetzung/fehlt.json.
  - Eigene Übersetzungen: in uebersetzung/eigene.json eintragen ("deutsch": "englisch"); die haben Vorrang.
  - Was deutsch bleiben soll (Berichte, Termintitel, Namen …): im HTML mit translate="no" markiert.
"""

import json
import os
import re

from bs4 import BeautifulSoup, NavigableString, Comment

ORDNER = "uebersetzung"
WOERTERBUCH = os.path.join(ORDNER, "en.json")
EIGENE = os.path.join(ORDNER, "eigene.json")
FEHLT = os.path.join(ORDNER, "fehlt.json")

# Alle Seiten bekommen eine englische Fassung, außer diesen (Pfad relativ zum Website-Ordner;
# ein Eintrag mit "/" am Ende gilt für den ganzen Ordner)
OHNE_EN = ["suche.html", "404.html", "mein-profil.html", "verwaltung.html", "listen.html", "umfrage.html",
           "mitmachen.html", "mail.html", "kontakte.html", "bericht-schreiben.html"]

# Begriffe, die DeepL nicht anfassen soll (bleiben deutsch)
GESCHUETZT = [
    "SG Aschheim / Feldkirchen / Kirchheim", "SG Aschheim/Feldkirchen/Kirchheim", "SG AFK",
    "Gymnasium Kirchheim", "Heimstettner Str. 20", "Schachbezirk München", "Bezirksliga", "Kreisliga",
    "A-Klasse", "B-Klasse", "C-Klasse", "D-Klasse", "E-Klasse", "Landesliga", "Regionalliga", "Oberliga",
    "DWZ", "MMM", "Oberlandquartett", "Neujahrsblitz", "Osterblitz", "Sommerblitz", "Herbstblitz",
    "Weihnachtsblitz", "AFK on Tour", "Senioren", "U20",
] + [f"AFK {i}" for i in range(1, 10)]

# Wörter, die als einzelnes Textstück sicher übersetzt werden (Datum, Tabellen …), ohne DeepL
FEST = {
    "Mo": "Mon", "Di": "Tue", "Mi": "Wed", "Do": "Thu", "Fr": "Fri", "Sa": "Sat", "So": "Sun",
    "heute": "today", "morgen": "tomorrow", "Heim": "Home", "Auswärts": "Away", "bei": "at", "vs.": "vs.",
}
WT = {"Mo": "Mon", "Di": "Tue", "Mi": "Wed", "Do": "Thu", "Fr": "Fri", "Sa": "Sat", "So": "Sun"}

# Texte in Skripten der englischen Seite (Anführungszeichen gehören dazu)
JS_ERSETZEN = [
    ('"heute"', '"today"'), ('"morgen"', '"tomorrow"'), ('"gestern"', '"yesterday"'),
    ('"in " + ', '"in " + '), (' + " Tagen"', ' + " days"'), (' + " Tage"', ' + " days"'),
    ('"vor " + ', '"" + '), ('"läuft"', '"ongoing"'), ('"Heute"', '"Today"'), ('"Morgen"', '"Tomorrow"'),
    ('"Nächster Spielabend: Freitag, " + dm(f) + " ab 18:00 Uhr ("', '"Next club night: Friday " + dm(f) + " from 6 pm ("'),
    ('" – nächster Spielabend: Freitag, " + dm(f) + " ab 18:00 Uhr"', '" – next club night: Friday " + dm(f) + " from 6 pm"'),
    ('" – nächster Spielabend danach am Freitag, "', '" – next club night after that: Friday "'),
    ('"Aktuell kein Spielabend"', '"No club night at the moment"'),
    ('"am " + dmi(a.start)', '"on " + dmi(a.start)'), ('"vom " + dmi(a.start) + " bis "', '"from " + dmi(a.start) + " to "'),
    ('"Am " + dmi(', '"On " + dmi('), ('"Vom " + dmi(ank[k].start) + " bis "', '"From " + dmi(ank[k].start) + " to "'),
    ('" kein Spielabend"', '" no club night"'), ('"danach "', '"then "'), ('" bis " + dmi(bald.end)', '" until " + dmi(bald.end)'),
    ('["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]', '["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]'),
    ('["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]', '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]'),
]

EINHEITEN = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dt", "dd", "label", "button",
             "summary", "figcaption", "blockquote", "a", "option", "caption", "legend", "small", "em", "b",
             "strong", "span", "div"}
BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dt", "dd", "label", "button",
         "summary", "figcaption", "blockquote", "option", "caption", "legend", "div", "ul", "ol", "table",
         "tr", "section", "article", "nav", "header", "footer", "form", "details", "figure", "main"}
UEBERSPRINGEN = {"script", "style", "code", "pre", "svg", "noscript", "textarea", "template"}
ATTRIBUTE = ("title", "aria-label", "placeholder", "alt", "data-tip")

_buch = None          # deutsch -> englisch
_neu = {}             # in diesem Lauf neu übersetzt
_fehlt = {}           # deutsch -> Seite


def _lade():
    global _buch
    if _buch is not None:
        return
    _buch = {}
    for pfad in (WOERTERBUCH, EIGENE):
        try:
            with open(pfad, encoding="utf-8") as f:
                _buch.update(json.load(f))
        except (OSError, ValueError):
            pass


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def en_name(name):
    return name[:-5] + "-en.html"


def hat_en(pfad):
    """pfad = Datei relativ zum Website-Ordner, z. B. 'index.html' oder 'berichte/x.html'."""
    pfad = pfad.replace(os.sep, "/")
    if not pfad.endswith(".html") or pfad.endswith("-en.html"):
        return False
    return not any(pfad == o or (o.endswith("/") and pfad.startswith(o)) for o in OHNE_EN)


def _ist_text(t):
    return bool(re.search(r"[A-Za-zÄÖÜäöüß]{2,}", t))


def _fest(t):
    """Datumsstücke wie 'Fr 27.11.' / 'Fr 27.11. · 19:30' / '19:30 Uhr' ohne Wörterbuch."""
    if t in FEST:
        return FEST[t]
    if t in GESCHUETZT:
        return t
    m = re.fullmatch(r"<(strong|b)([^>]*)>(.*)</\1>", t)
    if m and (innen := _fest(m.group(3))) is not None:
        return f"<{m.group(1)}{m.group(2)}>{innen}</{m.group(1)}>"
    m = re.fullmatch(r'(\d{2}\.\d{2}\.) <b class="abw">(Mo|Di|Mi|Do|Fr|Sa|So)</b>(, \d{1,2}:\d{2})?( Uhr)?', t)
    if m:
        return f'<b class="abw">{WT[m.group(2)]}</b> {m.group(1)}{m.group(3) or ""}'
    m = re.fullmatch(r"(\d+) – ([\d,½]+) : ([\d,½]+) \((Sieg|Niederlage|Unentschieden) für", t)
    if m:
        return f"{m.group(1)} – {m.group(2)} : {m.group(3)} ({ {'Sieg': 'win', 'Niederlage': 'loss', 'Unentschieden': 'draw'}[m.group(4)]} for"
    # "05.12. Sa, 10:00 Uhr" / "05.12. Sa"
    m = re.fullmatch(r"(\d{1,2}\.\d{1,2}\.(?:\d{4})?) (Mo|Di|Mi|Do|Fr|Sa|So)(,? \d{1,2}:\d{2})?( Uhr)?", t)
    if m:
        return f"{WT[m.group(2)]} {m.group(1)}{m.group(3) or ''}"
    # E-Mail-Adressen (auch als Link)
    if re.fullmatch(r"[\w.+-]+@[\w.-]+", re.sub(r"<[^>]+>", "", t).strip()):
        return t
    # "Nächster Termin: <strong>05.12. Sa, 10:00 Uhr</strong>"
    m = re.fullmatch(r"Nächster Termin: <strong>(.+)</strong>", t)
    if m:
        return f"Next date: <strong>{_fest(m.group(1)) or m.group(1)}</strong>"
    # Fußzeile
    m = re.fullmatch(r"© (\d{4}) (SG Aschheim / Feldkirchen / Kirchheim e\.V\.) · Zuletzt aktualisiert: (.+)", t)
    if m:
        return f"© {m.group(1)} {m.group(2)} · Last updated: {m.group(3)}"
    m = _muster(t)
    if m is not None:
        return m
    # Startseite: "4 Siege, 1 Remis und 2 Niederlagen – 5 Spiele stehen noch an"
    e = _ergebnis_titel(t)
    if e:
        return e
    # "06.07.2026 · von Pierre Tassell"
    m = re.fullmatch(r"(\d{1,2}\.\d{1,2}\.\d{4}) · von (.+)", t)
    if m:
        return f"{m.group(1)} · by {m.group(2)}"
    m = re.fullmatch(r"(Mo|Di|Mi|Do|Fr|Sa|So)(,?\s.*)", t)
    if m and not _ist_text(m.group(2).replace("Uhr", "")):
        return WT[m.group(1)] + m.group(2).replace(" Uhr", "")
    if re.fullmatch(r"(ab |bis )?\d{1,2}[:.]\d{2} Uhr", t):
        return t.replace("ab ", "from ").replace("bis ", "until ").replace(" Uhr", "")
    return None


# ------------------------------------------------------------------
# Namen (Spieler, Mannschaften) bleiben, wie sie sind
# ------------------------------------------------------------------
_namen_rx = None


def _namen():
    """Alle Spieler- und Mannschaftsnamen aus mannschaften/**/*.json -> ein Regex (längste zuerst)."""
    global _namen_rx
    if _namen_rx is not None:
        return _namen_rx
    namen = set()

    def sammeln(x, schluessel=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "teams" and isinstance(v, dict):
                    namen.update(t for t in v.values() if isinstance(t, str))
                sammeln(v, k)
        elif isinstance(x, list):
            for v in x:
                if isinstance(v, str) and schluessel == "bretter" and re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+){1,4}", v):
                    namen.add(v)          # Spielernamen in den Brett-Listen
                else:
                    sammeln(v, schluessel)
        elif isinstance(x, str) and schluessel in ("name", "gegner", "team", "verein", "w", "b"):
            namen.add(x)
    for wurzel, _, dateien in os.walk("mannschaften"):
        for d in dateien:
            if d.endswith(".json"):
                try:
                    with open(os.path.join(wurzel, d), encoding="utf-8") as f:
                        sammeln(json.load(f))
                except (OSError, ValueError):
                    pass
    namen = {n.strip() for n in namen if len(n.strip()) >= 4 and re.search(r"[A-Za-zÄÖÜäöü]", n)}
    teile = sorted(namen, key=len, reverse=True)
    _namen_rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(n) for n in teile) + r")(?![\w])") if teile else re.compile(r"(?!x)x")
    return _namen_rx


def _namen_schuetzen(soup, body):
    """Namen in Textknoten in <span translate="no"> packen, damit sie nie übersetzt werden."""
    rx = _namen()
    for t in list(body.find_all(string=True)):
        if isinstance(t, Comment) or _geschuetzt(t.parent):
            continue
        text = str(t)
        if not rx.search(text):
            continue
        stuecke = []
        pos = 0
        for m in rx.finditer(text):
            if m.start() > pos:
                stuecke.append(NavigableString(text[pos:m.start()]))
            sp = soup.new_tag("span", attrs={"translate": "no"})
            sp.string = m.group(0)
            stuecke.append(sp)
            pos = m.end()
        if pos < len(text):
            stuecke.append(NavigableString(text[pos:]))
        if len(stuecke) == 1 and getattr(stuecke[0], "name", None) == "span" and t.parent and \
                len([c for c in t.parent.children if not (isinstance(c, NavigableString) and not c.strip())]) == 1:
            t.parent["translate"] = "no"          # Element besteht nur aus dem Namen
            continue
        for st in stuecke:
            t.insert_before(st)
        t.extract()


# Feste Muster (Spielpläne, Prognosen …)
MUSTER = [
    (r"R(\d+): vs\.", r"R\1: vs."), (r"R(\d+): bei", r"R\1: at"), (r"R(\d+):", r"R\1:"),
    (r"– (\d+(?:[,.]5)?|\d+½?) : (\d+(?:[,.]5)?|\d+½?) \((Sieg|Niederlage|Unentschieden) für",
     lambda m: f"– {m.group(1)} : {m.group(2)} ({ {'Sieg': 'win', 'Niederlage': 'loss', 'Unentschieden': 'draw'}[m.group(3)]} for"),
    (r"– gegen uns", "– against us"), (r"\)", ")"),
    (r"–", "–"), (r"\|", "|"), (r"\| SG AFK", "| SG AFK"), (r"·", "·"),
    (r"(\d{2}\.\d{2}\.\d{4}) · von", r"\1 · by"),
    (r"Saison (\d{4}/\d{2})(.*)", r"Season \1\2"),
    (r"([SUN]) ([\d½]+:[\d½]+)", lambda m: {"S": "W", "U": "D", "N": "L"}[m.group(1)] + " " + m.group(2)),
    (r"-Schnitt ca\. (\d+)", r" average approx. \1"),
    (r"([\d,]+)<small>\+([\d,]+) evtl\.</small>", r"\1<small>+\2 poss.</small>"),
    (r"\+ ([\d,]+) % evtl\.", r"+ \1 % poss."),
    (r"(Mo|Di|Mi|Do|Fr|Sa|So) (\d{2}\.\d{2}\.)<span class=\"uhr\"> · (\d{1,2}:\d{2})</span>",
     lambda m: f'{WT[m.group(1)]} {m.group(2)}<span class="uhr"> · {m.group(3)}</span>'),
    (r"Heimspiele: (Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag) (\d{1,2}:\d{2})",
     lambda m: "Home matches: " + {"Montag": "Monday", "Dienstag": "Tuesday", "Mittwoch": "Wednesday",
                                   "Donnerstag": "Thursday", "Freitag": "Friday", "Samstag": "Saturday",
                                   "Sonntag": "Sunday"}[m.group(1)] + " " + m.group(2)),
    (r"· Nr\. (\d+)( · Stamm)?", lambda m: f"· No. {m.group(1)}" + (" · regular" if m.group(2) else "")),
    (r"Rd", "Rd"),
    (r"Platz (\d+): ([\d,]+ %)", r"Place \1: \2"), (r"(\d+) Punkte?: ([\d,]+ %)", r"\1 points: \2"),
    (r"Platz (\d+)", r"Place \1"), (r"(\d+)\. von (\d+)", r"\1 of \2"),
    (r"Heim (\d+) · Auswärts (\d+)", r"Home \1 · Away \2"),
    (r"Summe ([\d½]+) / (\d+)", r"Total \1 / \2"), (r"<strong>Summe ([\d½]+) / (\d+)</strong>", r"<strong>Total \1 / \2</strong>"),
    (r"([\d½]+) / (\d+) \((\d+) %\) seit (\d{4}/\d{2})", r"\1 / \2 (\3 %) since \4"),
    (r"heute: (.+)", r"today: \1"), (r"Beste Liga:", "Best league:"),
    (r"(\d+) Partien?", lambda m: f"{m.group(1)} game{'s' if m.group(1) != '1' else ''}"),
    (r"· DWZ-Schnitt ca\. (\d+)", r"· average DWZ approx. \1"),
    (r"(Bezirksliga|[A-E]-Klasse|\d\. Seniorenliga|\d\. Jugend-Bezirksliga|U20 Landesliga Süd)( \(\d{4}/\d{2}\))?", r"\1\2"),
    (r"((?:Bezirksliga|[A-E]-Klasse|\d\. Seniorenliga)) · Platz (\d+)", r"\1 · place \2"),
    (r"((?:Bezirksliga|[A-E]-Klasse|\d\. Seniorenliga|\d\. Jugend-Bezirksliga)) · Nr\. (\d+)( · Stamm)?",
     lambda m: f"{m.group(1)} · No. {m.group(2)}" + (" · regular" if m.group(3) else "")),
]


def _muster(t):
    for rx, ers in MUSTER:
        m = re.fullmatch(rx, t)
        if m:
            return m.expand(ers) if isinstance(ers, str) else ers(m)
    return None


def _ergebnis_titel(t):
    teile = re.split(r" – ", t)
    raus = []
    for teil in teile:
        if (m := re.fullmatch(r"Diese Woche (?:spielt 1 Mannschaft|spielen (\d+) Mannschaften)", teil)):
            raus.append(f"{m.group(1) or 1} team{'s' if m.group(1) else ''} playing this week")
            continue
        stuecke = re.split(r", | und ", teil)
        en = []
        for st in stuecke:
            m = re.fullmatch(r"(\d+) (Sieg|Siege|Remis|Niederlage|Niederlagen|Spiel steht noch an|Spiele stehen noch an|"
                             r"Ergebnis fehlt noch|Ergebnisse fehlen noch)", st)
            if not m:
                return None
            n, w = int(m.group(1)), m.group(2)
            en.append({"Sieg": "win", "Siege": "wins", "Remis": "draw" if n == 1 else "draws", "Niederlage": "loss",
                       "Niederlagen": "losses", "Spiel steht noch an": "match still to play",
                       "Spiele stehen noch an": "matches still to play", "Ergebnis fehlt noch": "result still missing",
                       "Ergebnisse fehlen noch": "results still missing"}[w])
            en[-1] = f"{n} {en[-1]}"
        raus.append(", ".join(en[:-1]) + " and " + en[-1] if len(en) > 1 else en[0])
    return " – ".join(raus)


def uebersetze_mit_namen(t, seite=""):
    """Wie uebersetze, aber Namen (Spieler/Mannschaften) bleiben stehen; für Attribute und <title>."""
    en = uebersetze(t, seite) if not _namen().search(t) else None
    if en is not None:
        return en
    teile = _namen().split(t)
    if len(teile) == 1:
        return uebersetze(t, seite)
    raus = []
    for i, teil in enumerate(teile):
        if i % 2 == 1 or not _ist_text(teil):
            raus.append(teil)
            continue
        e = uebersetze(teil, seite)
        if e is None:
            return None
        vorne = re.match(r"\s*", teil).group(0)
        hinten = re.search(r"\s*$", teil).group(0)
        raus.append(vorne + e + hinten)
    return "".join(raus)


_ZAHL = re.compile(r"(?<![\d§])\d+(?:[.,:/]\d+)*(?![\d])")
_HREF = re.compile(r'href="[^"]*"')


def schablone(k):
    """Text -> (Schablone, Links, Zahlen): Links werden zu href="§H", Zahlen zu §N.
    So reicht eine Übersetzung für "Platz 3 von 10" und "Platz 7 von 12"."""
    links = _HREF.findall(k)
    s = _HREF.sub('href="§H"', k)
    zahlen = _ZAHL.findall(s)
    return _ZAHL.sub("§N", s), links, zahlen


def fuellen(en, links, zahlen):
    if en.count('href="§H"') != len(links) or en.count("§N") != len(zahlen):
        return None
    for l in links:
        en = en.replace('href="§H"', l, 1)
    for z in zahlen:
        en = en.replace("§N", z, 1)
    return en


def uebersetze(t, seite=""):
    """Ein Textstück (darf Inline-HTML enthalten) -> englisch oder None."""
    _lade()
    k = norm(t)
    if not k or not _ist_text(k):
        return None
    if k in _buch:
        return _buch[k]
    f = _fest(k)
    if f is not None:
        return f
    sch, links, zahlen = schablone(k)
    if sch != k and sch in _buch:
        en = fuellen(_buch[sch], links, zahlen)
        if en is not None:
            return en
    _fehlt.setdefault(sch, seite)
    return None


KLASSEN_NEIN = {"no-translate", "brand", "pill", "sprache", "sprache-mobil", "article-content", "team-zelle",
               "ev-title", "sp-berichte", "news-snippet"}


def _geschuetzt(el):
    for p in [el, *el.parents]:
        if getattr(p, "name", None) in UEBERSPRINGEN:
            return True
        attrs = getattr(p, "attrs", None) or {}
        if attrs.get("translate") == "no" or KLASSEN_NEIN & set(attrs.get("class") or []):
            return True
    return False


def _einheit(el):
    """Element, das als Ganzes übersetzt wird: enthält Text, aber keine Block-Elemente."""
    if el.name not in EINHEITEN or _geschuetzt(el):
        return False
    if el.find(lambda x: x.name in BLOCK or x.name in UEBERSPRINGEN):
        return False
    # nur Kinder-Elemente ohne eigenen Text dazwischen (z. B. Menü aus Links, <b>27</b><span>Fr</span>) -> einzeln
    eigener_text = any(isinstance(c, NavigableString) and not isinstance(c, Comment) and _ist_text(str(c))
                       for c in el.children)
    kinder = [c for c in el.children if getattr(c, "name", None) and c.name != "br"]
    if not eigener_text and len(kinder) >= 2:
        return False
    return _ist_text(el.get_text())


def seite_uebersetzen(html, name, en_dateien=None):
    """Deutsche fertige Seite -> englische Seite (Links auf andere übersetzte Seiten zeigen auf -en).
    name = Pfad relativ zum Website-Ordner; en_dateien = Menge aller Seiten mit englischer Fassung."""
    soup = BeautifulSoup(html, "html.parser")
    if soup.html:
        soup.html["lang"] = "en"
    body = soup.body or soup
    if name.startswith("berichte/"):          # Berichte: Titel und Text bleiben deutsch
        for h in body.select("main h1"):
            h["translate"] = "no"
    _namen_schuetzen(soup, body)
    erledigt = set()
    # 1. ganze Einheiten (Absatz, Listenpunkt, Zelle, Knopf …) – von außen nach innen
    for el in body.find_all(True):
        vorfahren = list(el.parents)
        if not any(p is body for p in vorfahren) or any(id(p) in erledigt for p in vorfahren):
            continue              # schon übersetzt (Teil einer größeren Einheit) bzw. ersetzt
        if not _einheit(el):
            continue
        # die größte Einheit nehmen, deren Inhalt nur Inline-Elemente hat;
        # geschützte Teile darin (Namen, translate="no") werden zu §P und bleiben unverändert
        innen = el.decode_contents()
        en = _buch.get(norm(innen)) if _buch is not None else None
        if en is None:
            fest = [x for x in el.find_all(True) if _geschuetzt(x) and not _geschuetzt(x.parent) or
                    (x.parent is el and _geschuetzt(x))]
            fest = [x for x in fest if not any(p in fest for p in x.parents)]
            maske = innen
            teile = []
            for x in fest:
                h = str(x)
                if h in maske:
                    maske = maske.replace(h, "§P", 1)
                    teile.append(h)
            if not _ist_text(re.sub(r"§P|<[^>]+>", "", maske)):
                continue          # nur Geschütztes -> nichts zu tun
            en = uebersetze(maske, name)
            if en is not None:
                if en.count("§P") != len(teile):
                    en = None
                else:
                    for h in teile:
                        en = en.replace("§P", h, 1)
        if en is None and el.name in ("span", "em", "b", "strong", "small", "div"):
            continue              # kleine Stücke: einzeln über die Textknoten
        erledigt.add(id(el))
        if en is not None:
            el.clear()
            for k in list(BeautifulSoup(en, "html.parser").contents):
                el.append(k)
    # 2. übrige Textknoten
    for t in body.find_all(string=True):
        if isinstance(t, Comment) or any(id(p) in erledigt for p in t.parents) or _geschuetzt(t.parent):
            continue
        k = norm(str(t))
        en = uebersetze(k, name)
        if en is not None:
            vorne = re.match(r"\s*", str(t)).group(0)
            hinten = re.search(r"\s*$", str(t)).group(0)
            t.replace_with(NavigableString(vorne + en + hinten))
    # 3. Attribute
    for el in soup.find_all(True):
        if _geschuetzt(el):
            continue
        for a in ATTRIBUTE:
            if el.has_attr(a):
                en = uebersetze_mit_namen(el[a], name)
                if en is not None:
                    el[a] = BeautifulSoup(en, "html.parser").get_text()
    namensseite = name.startswith(("berichte/", "spieler/", "tour-"))
    for meta in soup.find_all("meta"):
        if namensseite and meta.get("property") == "og:title":
            continue
        if meta.get("name") == "description" or meta.get("property") in ("og:description", "og:title"):
            en = uebersetze(meta.get("content", ""), name)
            if en is not None:
                meta["content"] = BeautifulSoup(en, "html.parser").get_text()
        if meta.get("property") == "og:locale":
            meta["content"] = "en_GB"
    if soup.title and not namensseite:
        en = uebersetze_mit_namen(soup.title.get_text(), name)
        if en is not None:
            soup.title.string = BeautifulSoup(en, "html.parser").get_text()
    for pill in soup.select(".pill"):
        if pill.get_text(strip=True) in ("Jugend", "Senioren"):
            pill.string = {"Jugend": "Youth", "Senioren": "Seniors"}[pill.get_text(strip=True)]
    # 4. Links auf übersetzte Seiten
    ordner = os.path.dirname(name)
    for a in soup.find_all("a", href=True):
        if a.has_attr("data-sprache"):
            continue
        m = re.fullmatch(r"((?:\.\./)*(?:[\w.-]+/)*)([\w.-]+\.html)(#.*)?", a["href"])
        if not m:
            continue
        ziel = os.path.normpath(os.path.join(ordner, m.group(1) + m.group(2))).replace(os.sep, "/")
        if en_dateien is not None and ziel in en_dateien:
            a["href"] = m.group(1) + en_name(m.group(2)) + (m.group(3) or "")
    # 5. Skripte
    for s in soup.find_all("script"):
        if s.string:
            js = s.string
            for alt, neu in JS_ERSETZEN:
                js = js.replace(alt, neu)
            s.string.replace_with(js)
    return str(soup)


# ------------------------------------------------------------------
# Umschalter DE/EN, Hinweis, hreflang
# ------------------------------------------------------------------
SCHALTER_CSS = """<style>
.sprache{position:relative}
.sprache-knopf{width:auto!important;padding:0 .7rem!important;gap:.25rem;font-weight:700;font-size:.85rem;letter-spacing:.03em;display:inline-flex;align-items:center}
.sprache-knopf svg{width:.7rem;height:.7rem}
.sprache-menue{position:absolute;right:0;top:calc(100% + .45rem);background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 30px #0006;padding:.35rem;min-width:9.5rem;z-index:50}
.sprache-menue[hidden]{display:none}
.sprache-menue a{display:flex;justify-content:space-between;gap:1rem;padding:.5rem .7rem;border-radius:8px;color:var(--text);text-decoration:none;font-weight:600}
.sprache-menue a:hover,.sprache-menue a.an{background:color-mix(in srgb,var(--hell,#6f9fd8) 16%,transparent)}
.sprache-menue small{color:var(--muted);font-weight:500}
.sprache-mobil{display:none}
@media (max-width:900px){.sprache{display:none}.sprache-mobil{display:flex;gap:.4rem;padding:.6rem 1rem .2rem;font-weight:700}
 .sprache-mobil a{padding:.35rem .8rem;border-radius:8px;border:1px solid var(--line);text-decoration:none;color:var(--text)}
 .sprache-mobil a.an{background:color-mix(in srgb,var(--hell,#6f9fd8) 22%,transparent);border-color:transparent}}
.ue-hinweis{position:fixed;right:1.2rem;bottom:1.2rem;max-width:23rem;background:var(--surface);border:1px solid var(--hell,#6f9fd8);border-radius:14px;box-shadow:0 14px 40px #0007;padding:1rem 1.1rem;z-index:9000;font-size:.95rem;line-height:1.45;color:var(--text)}
.ue-hinweis b{color:var(--head);display:block;margin-bottom:.25rem;font-size:1.02rem}
.ue-hinweis .k{display:flex;gap:.5rem;margin-top:.8rem;flex-wrap:wrap}
.ue-hinweis button,.ue-hinweis a{font:inherit;font-weight:600;font-size:.88rem;padding:.45rem .8rem;border-radius:8px;border:1px solid var(--line);background:none;color:var(--text);text-decoration:none;cursor:pointer}
.ue-hinweis button{background:var(--hell,#6f9fd8);color:#0d1730;border-color:transparent}
@media(max-width:600px){.ue-hinweis{left:.8rem;right:.8rem;bottom:.8rem;max-width:none}}
</style>"""

PFEIL = '<svg viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'


def _ziele(pfad, nav_path):
    """(deutsche Adresse, englische Adresse) für den Umschalter, relativ zur Seite."""
    datei = os.path.basename(pfad)
    if hat_en(pfad):
        return datei, en_name(datei)
    return datei, nav_path + "index-en.html"


def schalter(name, nav_path, en):
    de_ziel, en_ziel = _ziele(name, nav_path)
    menue = (f'<div class="sprache-menue" hidden><a href="{de_ziel or "#"}" data-sprache="de"{" class=an" if not en else ""}>'
             f'Deutsch{" <small>✓</small>" if not en else ""}</a>'
             f'<a href="{en_ziel}" data-sprache="en"{" class=an" if en else ""}>English{" <small>✓</small>" if en else ""}</a></div>')
    return (f'<div class="sprache" translate="no"><button type="button" class="kopf-knopf sprache-knopf" '
            f'aria-label="{"Language" if en else "Sprache"}" aria-haspopup="true">{"EN" if en else "DE"}{PFEIL}</button>{menue}</div>\n        ')


def mobil(name, nav_path, en):
    de_ziel, en_ziel = _ziele(name, nav_path)
    return (f'<div class="sprache-mobil" translate="no"><a href="{de_ziel or "#"}" data-sprache="de"{" class=an" if not en else ""}>Deutsch</a>'
            f'<a href="{en_ziel}" data-sprache="en"{" class=an" if en else ""}>English</a></div>')


SCHALTER_JS = """<script>
(function () {
  var en = document.documentElement.lang === "en";
  var box = document.querySelector(".sprache");
  if (box) {
    var k = box.querySelector(".sprache-knopf"), m = box.querySelector(".sprache-menue");
    k.addEventListener("click", function (e) { e.stopPropagation(); m.hidden = !m.hidden; });
    document.addEventListener("click", function () { m.hidden = true; });
  }
  document.querySelectorAll("[data-sprache]").forEach(function (a) {
    a.addEventListener("click", function () { try { localStorage.setItem("afk-sprache", a.dataset.sprache); } catch (e) {} });
  });
  var wahl = null; try { wahl = localStorage.getItem("afk-sprache"); } catch (e) {}
  var alt = document.querySelector('link[rel=alternate][hreflang="en"]');
  // gemerkte Wahl: deutsche Seite mit englischer Fassung -> dorthin
  if (!en && wahl === "en" && alt) { location.replace(alt.getAttribute("href") + location.hash); return; }
  if (en) {
    var schon = false; try { schon = localStorage.getItem("afk-ue-hinweis") === "1"; } catch (e) {}
    if (schon) return;
    var de = document.querySelector('link[rel=alternate][hreflang="de"]');
    var h = document.createElement("div");
    h.className = "ue-hinweis"; h.setAttribute("role", "dialog"); h.setAttribute("translate", "no");
    h.innerHTML = "<b>Automatically translated</b>This English version is translated automatically from German, so some wording may be a little off. Match reports, event titles and documents stay in German." +
      '<div class="k"><button type="button">Got it</button><a data-sprache="de" href="' + (de ? de.getAttribute("href") : "index.html") + '">Deutsche Version</a></div>';
    document.body.appendChild(h);
    function weg() { try { localStorage.setItem("afk-ue-hinweis", "1"); } catch (e) {} h.remove(); }
    h.querySelector("button").onclick = weg;
    h.querySelector("a").onclick = function () { try { localStorage.setItem("afk-sprache", "de"); localStorage.setItem("afk-ue-hinweis", "1"); } catch (e) {} };
  } else if (!wahl && alt && /^en\\b/i.test(navigator.language || "")) {
    // Browser auf Englisch: einmal fragen
    var gefragt = false; try { gefragt = localStorage.getItem("afk-en-frage") === "1"; } catch (e) {}
    if (gefragt) return;
    var f = document.createElement("div");
    f.className = "ue-hinweis"; f.setAttribute("translate", "no");
    f.innerHTML = '<b>English version available</b>Parts of this website are available in English.<div class="k"><a data-sprache="en" href="' + alt.getAttribute("href") + '">Switch to English</a><button type="button">Auf Deutsch bleiben</button></div>';
    document.body.appendChild(f);
    f.querySelector("button").onclick = function () { try { localStorage.setItem("afk-en-frage", "1"); localStorage.setItem("afk-sprache", "de"); } catch (e) {} f.remove(); };
    f.querySelector("a").onclick = function () { try { localStorage.setItem("afk-sprache", "en"); } catch (e) {} };
  }
})();
</script>"""


def einbauen(html, name, nav_path, en=False):
    """Umschalter, hreflang und Skript in eine fertige Seite einsetzen (name = Pfad relativ zum Website-Ordner)."""
    html = html.replace('<div class="kopf-tools">', '<div class="kopf-tools">\n        ' + schalter(name, nav_path, en), 1)
    html = re.sub(r'(<nav aria-label="[^"]*">)', lambda m: m.group(1) + mobil(name, nav_path, en), html, count=1)
    kopf = SCHALTER_CSS
    if hat_en(name):
        d = os.path.basename(name)
        kopf += (f'\n  <link rel="alternate" hreflang="de" href="{d}">'
                 f'\n  <link rel="alternate" hreflang="en" href="{en_name(d)}">')
    html = html.replace("</head>", kopf + "\n</head>", 1)
    return html.replace("</body>", SCHALTER_JS + "\n</body>", 1)


# ------------------------------------------------------------------
# DeepL (optional) + Speichern
# ------------------------------------------------------------------
def _schuetzen(t):
    for w in sorted(GESCHUETZT, key=len, reverse=True):
        t = re.sub(r"(?<![\w>])" + re.escape(w) + r"(?![\w<])", lambda m: f"<x>{m.group(0)}</x>", t)
    return t


MYMEMORY_MAIL = "sgafk1952@gmail.com"   # erhöht das freie Tageskontingent von MyMemory (kein Konto nötig)


def _pruefen(de, en):
    """Maschinelle Übersetzung nur übernehmen, wenn Tags, Platzhalter und geschützte Begriffe erhalten blieben."""
    if not en or en.count("<") != de.count("<") or en.count("§N") != de.count("§N") or en.count("§P") != de.count("§P") \
            or en.count('href="§H"') != de.count('href="§H"'):
        return False
    return all(w in en for w in GESCHUETZT if re.search(r"(?<![\w])" + re.escape(w) + r"(?![\w])", de))


def mymemory_nachholen():
    """Ohne DeepL: fehlende Stücke über MyMemory (kostenlos, ohne Konto/Kreditkarte). -> Anzahl."""
    if not _fehlt or os.environ.get("UEBERSETZEN", "1") == "0":
        return 0
    import requests
    n = 0
    for de in list(_fehlt):
        if len(de.encode("utf-8")) > 480:
            continue                                   # zu lang für den Dienst -> bleibt in fehlt.json
        try:
            r = requests.get("https://api.mymemory.translated.net/get", timeout=20,
                             params={"q": de, "langpair": "de|en-GB", "de": MYMEMORY_MAIL})
            j = r.json()
        except Exception as e:
            print(f"Hinweis: Übersetzungsdienst nicht erreichbar ({type(e).__name__}) – Rest bleibt deutsch.")
            break
        if j.get("quotaFinished") or j.get("responseStatus") not in (200, "200"):
            print("Hinweis: Tageskontingent des Übersetzungsdienstes erreicht – Rest morgen.")
            break
        import html as _h
        en = _h.unescape(j.get("responseData", {}).get("translatedText") or "") if "&" not in de else \
            (j.get("responseData", {}).get("translatedText") or "")
        if _pruefen(de, en):
            _buch[de] = en
            _neu[de] = en
            _fehlt.pop(de, None)
            n += 1
    return n


def deepl_nachholen():
    """Fehlende Stücke mit DeepL übersetzen (mit DEEPL_KEY), sonst MyMemory. -> Anzahl neu übersetzt."""
    key = os.environ.get("DEEPL_KEY", "").strip()
    if not key:
        return mymemory_nachholen()
    if not _fehlt:
        return 0
    import requests
    url = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    texte = list(_fehlt)
    n = 0
    for i in range(0, len(texte), 40):
        teil = texte[i:i + 40]
        try:
            r = requests.post(url, headers={"Authorization": f"DeepL-Auth-Key {key}"}, timeout=60, data={
                "text": [_schuetzen(t) for t in teil], "source_lang": "DE", "target_lang": "EN-GB",
                "tag_handling": "html", "ignore_tags": "x", "preserve_formatting": "1"})
            r.raise_for_status()
            for de, ue in zip(teil, r.json()["translations"]):
                en = re.sub(r"</?x>", "", ue["text"])
                _buch[de] = en
                _neu[de] = en
                _fehlt.pop(de, None)
                n += 1
        except Exception as e:
            print(f"Hinweis: DeepL-Übersetzung fehlgeschlagen ({type(e).__name__}) – Rest bleibt deutsch.")
            break
    return n


def speichern():
    """Am Ende des Builds: neue Übersetzungen ins Wörterbuch, fehlende Stücke nach fehlt.json."""
    _lade()
    if _neu:
        try:
            with open(WOERTERBUCH, encoding="utf-8") as f:
                alt = json.load(f)
        except (OSError, ValueError):
            alt = {}
        alt.update(_neu)
        os.makedirs(ORDNER, exist_ok=True)
        with open(WOERTERBUCH, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(alt.items())), f, ensure_ascii=False, indent=1)
    os.makedirs(ORDNER, exist_ok=True)
    with open(FEHLT, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(_fehlt.items())), f, ensure_ascii=False, indent=1)
    if _fehlt:
        print(f"Englisch: {len(_fehlt)} Textstücke noch ohne Übersetzung (uebersetzung/fehlt.json)"
              )


# ------------------------------------------------------------------
# Ablauf im Build
# ------------------------------------------------------------------
_seiten = {}          # Pfad -> (html, nav_path)


def merken(html, name, nav_path=""):
    """render_page: fertige deutsche Seite (mit Umschalter) für die englische Fassung vormerken."""
    name = name.replace(os.sep, "/")
    if hat_en(name):
        _seiten[name] = (html, nav_path)


def alles_schreiben():
    """Am Ende von build_site.py: alle vorgemerkten Seiten übersetzen und als <name>-en.html schreiben."""
    if not _seiten:
        return
    en_dateien = set(_seiten)
    for name, (html, _) in _seiten.items():     # 1. Durchgang: fehlende Stücke sammeln
        seite_uebersetzen(html, name, en_dateien)
    neu = deepl_nachholen()
    if neu:
        print(f"Englisch: {neu} Textstücke automatisch übersetzt.")
        _fehlt.clear()
    for name, (html, nav_path) in _seiten.items():   # 2. Durchgang: schreiben
        en = seite_uebersetzen(einbauen_en(html, name, nav_path), name, en_dateien)
        with open(en_name(name), "w", encoding="utf-8") as f:
            f.write(en)
    speichern()
    print(f"Englisch: {len(_seiten)} Seiten (…-en.html).")


def einbauen_en(html_de, name, nav_path=""):
    """Deutsche Seite (mit DE-Umschalter) -> Umschalter auf EN stellen."""
    html = html_de.replace(schalter(name, nav_path, False), schalter(name, nav_path, True), 1)
    return html.replace(mobil(name, nav_path, False), mobil(name, nav_path, True), 1)
