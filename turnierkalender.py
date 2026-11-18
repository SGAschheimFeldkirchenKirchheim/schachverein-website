"""
Turnierkalender (extern): Opens in Bayern, Deutschland und Europa auf turnierkalender.html.

Die Turniere kommen automatisch aus
  - dem FIDE-Kalender (fide.com/calendar)        -> Europa, mit Koordinaten und Bedenkzeit
  - chess-results.com (Länder aus der Einstellung) -> Bayern/Deutschland/Österreich, inkl. AFK-Abgleich
  - der eigenen Liste in turniere/turnierkalender.json ("eigene")
Läuft im nächtlichen Build (build_site.py ruft bauen(render_page) auf). Neue Turniere kommen dazu,
vergangene fallen raus. Fällt eine Quelle aus, bleibt der letzte Stand aus dem Cache stehen.

Dateien:
  turniere/turnierkalender.json     Einstellungen, eigene Turniere, empfohlen/ausblenden
  turniere/ferien_bayern.json       Schulferien + Vorlesungszeiten (Semesterferien)
  turniere/turnierkalender_cache/   Zwischenspeicher (nicht von Hand ändern)

Diagnose (lokal, wenn eine Quelle nichts liefert):
  python turnierkalender.py --probe   -> speichert Rohseiten in turniere/turnierkalender_probe/
"""

import datetime
import html
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ==========================================
# EINSTELLUNGEN (das meiste steht in turniere/turnierkalender.json)
# ==========================================
SEITE = "turnierkalender.html"
ANZAHL = 0                        # nach bauen(): Anzahl Turniere (für die Karte auf der Turniere-Seite)
TITEL = "Turnierkalender"
KONFIG = os.path.join("turniere", "turnierkalender.json")
FERIEN = os.path.join("turniere", "ferien_bayern.json")
CACHE = os.path.join("turniere", "turnierkalender_cache")
PROBE = os.path.join("turniere", "turnierkalender_probe")

FIDE_LISTE = "https://fide.com/calendar"
FIDE_EVENT = "https://fide.com/calendar/{id}"
FIDE_START_ID = 54500            # nur falls die Kalenderliste keine Links liefert: ab hier vorwärts suchen
FIDE_LUECKE = 40                 # so viele leere IDs hintereinander = Ende erreicht
CR_LISTE = "https://chess-results.com/fed.aspx?lan=0&fed={land}"
CR_DETAIL = "https://chess-results.com/tnr{tnr}.aspx?lan=0&turdet=YES"
CR_START = "https://chess-results.com/tnr{tnr}.aspx?lan=0&art=0&turdet=NO"
CR_LINK = "https://chess-results.com/tnr{tnr}.aspx?lan=0"
FERIEN_API = ("https://openholidaysapi.org/SchoolHolidays?countryIsoCode=DE&subdivisionCode=DE-BY"
              "&languageIsoCode=DE&validFrom={von}&validTo={bis}")
GEOCODER = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"

PAUSE = 0.8                       # Sekunden zwischen zwei Abrufen derselben Seite (Server schonen)
GEO_PRO_LAUF = 300                # höchstens so viele Orte pro Lauf nachschlagen (OpenStreetMap: max. 1 pro Sekunde)
AFK_ALLE_TAGE = 2                 # Teilnehmerlisten höchstens alle 2 Tage neu prüfen
VEREIN_MUSTER = re.compile(r"Aschheim|Feldkirchen|Kirchheim|\bAFK\b", re.I)
LIGA_MUSTER = re.compile(r"\bliga\b|bundesliga|league|mannschaft|\bteam|vereinspokal|schulschach|"
                         r"olympiad|seminar|kongress|congress|arbiter|vereinsmeisterschaft|\bvm\b|"
                         r"club-?meisterschaft|klubmeisterschaft|vereinsturnier|clubturnier|klubturnier|"
                         r"vereinsinterne?|\bintern\b|jahreswertung|ranglistenturnier|training", re.I)
MAX_DAUER = 21                    # Turniere, die länger laufen (Vereinsmeisterschaften über Monate), fallen raus
HEADERS = {"User-Agent": "SG-AFK-Turnierkalender/1.0 (Schachverein; +sgafk1952@gmail.com)",
           "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}
BROWSER = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/130.0 Safari/537.36"),
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}
BROWSER_HOSTS = ("fide.com", "chess-results.com")   # diese Seiten bekommen eine normale Browser-Kennung
CR_AUSWAHL = ["2", "3"]          # chess-results-Liste: in den nächsten 7 Tagen / in mehr als 7 Tagen beginnende Turniere
STATUS = {}                      # letzter HTTP-Status je Adresse (für --probe)

EUROPA = {  # Ländernamen, wie sie in FIDE/chess-results vorkommen (englisch/deutsch) -> deutscher Name
    "germany": "Deutschland", "deutschland": "Deutschland", "ger": "Deutschland",
    "austria": "Österreich", "österreich": "Österreich", "aut": "Österreich",
    "switzerland": "Schweiz", "schweiz": "Schweiz", "sui": "Schweiz",
    "italy": "Italien", "italien": "Italien", "ita": "Italien",
    "czech republic": "Tschechien", "czechia": "Tschechien", "tschechien": "Tschechien", "cze": "Tschechien",
    "france": "Frankreich", "frankreich": "Frankreich", "fra": "Frankreich",
    "netherlands": "Niederlande", "niederlande": "Niederlande", "ned": "Niederlande",
    "belgium": "Belgien", "belgien": "Belgien", "bel": "Belgien",
    "luxembourg": "Luxemburg", "luxemburg": "Luxemburg", "lux": "Luxemburg",
    "liechtenstein": "Liechtenstein", "lie": "Liechtenstein",
    "denmark": "Dänemark", "dänemark": "Dänemark", "den": "Dänemark",
    "poland": "Polen", "polen": "Polen", "pol": "Polen",
    "slovakia": "Slowakei", "slowakei": "Slowakei", "svk": "Slowakei",
    "slovenia": "Slowenien", "slowenien": "Slowenien", "slo": "Slowenien",
    "hungary": "Ungarn", "ungarn": "Ungarn", "hun": "Ungarn",
    "croatia": "Kroatien", "kroatien": "Kroatien", "cro": "Kroatien",
    "spain": "Spanien", "spanien": "Spanien", "esp": "Spanien",
    "portugal": "Portugal", "por": "Portugal",
    "united kingdom": "Großbritannien", "england": "England", "eng": "England", "scotland": "Schottland",
    "wales": "Wales", "ireland": "Irland", "irland": "Irland", "irl": "Irland",
    "sweden": "Schweden", "schweden": "Schweden", "swe": "Schweden",
    "norway": "Norwegen", "norwegen": "Norwegen", "nor": "Norwegen",
    "finland": "Finnland", "finnland": "Finnland", "fin": "Finnland",
    "iceland": "Island", "island": "Island", "isl": "Island",
    "greece": "Griechenland", "griechenland": "Griechenland", "gre": "Griechenland",
    "romania": "Rumänien", "rumänien": "Rumänien", "rou": "Rumänien",
    "bulgaria": "Bulgarien", "bulgarien": "Bulgarien", "bul": "Bulgarien",
    "serbia": "Serbien", "serbien": "Serbien", "srb": "Serbien",
    "bosnia and herzegovina": "Bosnien", "bih": "Bosnien", "montenegro": "Montenegro", "mne": "Montenegro",
    "north macedonia": "Nordmazedonien", "mkd": "Nordmazedonien", "albania": "Albanien", "alb": "Albanien",
    "malta": "Malta", "mlt": "Malta", "cyprus": "Zypern", "cyp": "Zypern", "monaco": "Monaco", "mnc": "Monaco",
    "andorra": "Andorra", "and": "Andorra", "san marino": "San Marino", "smr": "San Marino",
    "estonia": "Estland", "est": "Estland", "latvia": "Lettland", "lat": "Lettland",
    "lithuania": "Litauen", "ltu": "Litauen", "kosovo": "Kosovo", "kos": "Kosovo",
    "moldova": "Moldau", "mda": "Moldau", "ukraine": "Ukraine", "ukr": "Ukraine",
    "turkey": "Türkei", "türkiye": "Türkei", "tur": "Türkei", "georgia": "Georgien", "geo": "Georgien",
    "armenia": "Armenien", "arm": "Armenien", "faroe islands": "Färöer", "far": "Färöer", "fai": "Färöer",
    "azerbaijan": "Aserbaidschan", "aze": "Aserbaidschan", "israel": "Israel", "isr": "Israel",
    "belarus": "Belarus", "blr": "Belarus", "russia": "Russland", "rus": "Russland",
    "isle of man": "Isle of Man", "iom": "Isle of Man", "jersey": "Jersey", "jci": "Jersey",
    "guernsey": "Guernsey", "gci": "Guernsey", "sco": "Schottland", "wls": "Wales",
}


# ==========================================
# HILFSFUNKTIONEN
# ==========================================
def _lade_json(pfad, standard):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return standard


def _speichere_json(pfad, daten):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, pfad)


_letzter_abruf = {}
_sitzung = requests.Session() if requests else None


def _hole(url, roh=False, daten=None):
    """Seite laden (mit Pause je Server); daten = Formularfelder für POST. None bei Fehler oder 404."""
    host = urllib.parse.urlparse(url).netloc
    warte = (1.1 if "nominatim" in host else PAUSE) - (time.time() - _letzter_abruf.get(host, 0))
    if warte > 0:
        time.sleep(warte)
    _letzter_abruf[host] = time.time()
    kopf = BROWSER if any(h in host for h in BROWSER_HOSTS) else HEADERS
    try:
        if _sitzung:
            r = (_sitzung.post(url, data=daten, headers=kopf, timeout=(10, 40)) if daten is not None
                 else _sitzung.get(url, headers=kopf, timeout=(10, 30)))
            STATUS[url] = r.status_code
            if r.status_code != 200:
                return None
            if not roh and (r.encoding or "").lower() in ("", "iso-8859-1") and b"charset=utf-8" in r.content[:3000].lower():
                r.encoding = "utf-8"
            return r.content if roh else r.text
        body = urllib.parse.urlencode(daten).encode() if daten is not None else None
        req = urllib.request.Request(url, data=body, headers=kopf)
        with urllib.request.urlopen(req, timeout=30) as r:
            daten = r.read()
            return daten if roh else daten.decode(r.headers.get_content_charset() or "utf-8", "replace")
    except Exception as e:  # Netzwerkfehler sind normal (Quelle down) -> nicht abbrechen
        STATUS[url] = type(e).__name__
        print(f"  Turnierkalender: {url} nicht erreichbar ({type(e).__name__})")
        return None


def _zeilen(seite):
    """Sichtbarer Text einer HTML-Seite als Liste nicht-leerer Zeilen."""
    if BeautifulSoup:
        soup = BeautifulSoup(seite, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        text = soup.get_text("\n")
    else:
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", seite, flags=re.S | re.I)
        text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    return [z.strip() for z in text.splitlines() if z.strip()]


def _feld(zeilen, *labels):
    """Wert hinter 'Label:' (gleiche Zeile oder nächste Zeile)."""
    for label in labels:
        lab = label.lower().rstrip(":")
        for i, z in enumerate(zeilen):
            zl = z.lower()
            if zl == lab or zl == lab + ":":
                return zeilen[i + 1] if i + 1 < len(zeilen) else ""
            if zl.startswith(lab + ":"):
                rest = z[len(lab) + 1:].strip()
                return rest or (zeilen[i + 1] if i + 1 < len(zeilen) else "")
    return ""


MONATE = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONATE.update({"mär": 3, "mai": 5, "okt": 10, "dez": 12})


def _datum(text):
    """'26-Oct-2024', '26 Oct 2024', '2026/12/27', '27.12.2026', '2026-12-27' -> date oder None."""
    if not text:
        return None
    t = text.strip()
    for muster, reihenfolge in ((r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", "jmt"), (r"(\d{1,2})\.(\d{1,2})\.(\d{4})", "tmj")):
        m = re.search(muster, t)
        if m:
            w = dict(zip(reihenfolge, map(int, m.groups())))
            try:
                return datetime.date(w["j"], w["m"], w["t"])
            except ValueError:
                return None
    m = re.search(r"(\d{1,2})[\s-]+([A-Za-zäÄ]{3})[a-zä]*\.?[\s-]+(\d{4})", t)
    if m and m.group(2).lower()[:3] in MONATE:
        try:
            return datetime.date(int(m.group(3)), MONATE[m.group(2).lower()[:3]], int(m.group(1)))
        except ValueError:
            return None
    return None


def _land(text):
    """Land aus 'Ort, Land' oder Kürzel -> (deutscher Name oder Original, ist_europa)."""
    if not text:
        return "", False
    teile = [t.strip() for t in re.split(r"[,(/]", text.replace(")", "")) if t.strip()]
    for t in reversed(teile):
        k = t.lower()
        if k in EUROPA:
            return EUROPA[k], True
    return (teile[-1] if teile else text.strip()), False


def _ohne_land(text):
    """'Gmund am Tegernsee, Germany' -> 'Gmund am Tegernsee' (Land steht extra)."""
    teile = [t.strip() for t in (text or "").split(",") if t.strip()]
    while len(teile) > 1 and teile[-1].lower() in EUROPA:
        teile.pop()
    return ", ".join(dict.fromkeys(teile))


def _km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(d))


def _bedenkzeit(art, text):
    """-> 'klassisch' | 'schnell' | 'blitz' | ''"""
    a = (art or "").lower()
    if "standard" in a or "klassisch" in a or "classic" in a:
        return "klassisch"
    if "rapid" in a or "schnell" in a:
        return "schnell"
    if "blitz" in a:
        return "blitz"
    minuten = grundzeit(text)
    if minuten is None:
        return ""
    return "klassisch" if minuten >= 60 else "schnell" if minuten >= 10 else "blitz"


def grundzeit(text):
    """Längste Bedenkzeit-Angabe in Minuten: '90 min + 30 s' -> 90, '40/1,5 + 30 sec' -> 90 (Stunden!),
    '2 h' -> 120, '40/90' -> 90, '3+2' -> 3. None, wenn nichts erkennbar."""
    t = (text or "").lower().replace(",", ".")
    werte = []
    for zahl, einheit in re.findall(r"(\d+(?:\.\d+)?)\s*(h\b|std|stunde|min|minute|'|m\b)", t):
        werte.append(float(zahl) * (60 if einheit[0] in "hs" else 1))
    # Züge/Zeit: "40/1.5" (Stunden, wenn klein) oder "40/90" (Minuten)
    for zuege, zeit in re.findall(r"\b(\d{2})\s*/\s*(\d+(?:\.\d+)?)", t):
        z = float(zeit)
        werte.append(z * 60 if z <= 4 else z)
    if not werte:
        m = re.search(r"\b(\d{1,3})\s*\+\s*\d", t)        # "3+2", "15 + 10"
        if m:
            werte.append(float(m.group(1)))
    return max(werte) if werte else None


def _gruppen(name):
    n = name.lower()
    g = []
    if re.search(r"jugend|youth|junior|\bu ?\d{1,2}\b|kinder|schüler|cadet|kids", n):
        g.append("jugend")
    if re.search(r"senior|50\+|65\+|ü ?50|ü ?60", n):
        g.append("senioren")
    if re.search(r"frauen|women|damen|ladies|girls|mädchen|female", n):
        g.append("frauen")
    return g


def _schluessel(name):
    """Name vereinheitlicht für den Duplikat-Abgleich."""
    n = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    n = re.sub(r"\b(19|20)\d{2}\b|\b\d+(st|nd|rd|th|\.)?\b|\b[ivx]+\.?\b", " ", n)
    n = re.sub(r"\b(open|offene?|turnier|tournament|chess|schach|festival|international|internationales?|the|der|die|das|e\.?v\.?)\b", " ", n)
    return " ".join(sorted(set(re.findall(r"[a-z]{3,}", n))))


# ==========================================
# QUELLE: FIDE-KALENDER
# ==========================================
def fide_event(eid, seite):
    z = _zeilen(seite)
    if not any(l.lower().startswith("place") for l in z):
        return None
    name = ""
    for i, l in enumerate(z):
        if l.lower().startswith("place"):
            name = z[i - 1] if i else ""
            break
    if BeautifulSoup:
        soup = BeautifulSoup(seite, "html.parser")
        for tag in soup.find_all(["h1", "h2"]):
            t = tag.get_text(" ", strip=True)
            if t and t not in ("Calendar", "Tournaments", "International Chess Federation"):
                name = t
                break
    ort_roh = _feld(z, "Place")
    ort = _ohne_land(ort_roh)
    von, bis = _datum(_feld(z, "Start")), _datum(_feld(z, "End"))
    koord = re.findall(r"-?\d+\.\d+", _feld(z, "Address coordinates"))
    web = _feld(z, "Official website")
    pdf = ""
    if BeautifulSoup:
        a = BeautifulSoup(seite, "html.parser").find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        pdf = urllib.parse.urljoin(FIDE_EVENT.format(id=eid), a["href"]) if a else ""
    land, europa = _land(ort_roh)
    tc = _feld(z, "Time control description", "Time control")
    return {
        "id": f"fide:{eid}", "quelle": "FIDE", "name": name, "ort": ort, "land": land, "europa": europa,
        "von": von.isoformat() if von else "", "bis": (bis or von).isoformat() if (bis or von) else "",
        "lat": float(koord[0]) if len(koord) >= 2 else None, "lon": float(koord[1]) if len(koord) >= 2 else None,
        "bedenkzeit": _bedenkzeit(_feld(z, "Time control type"), tc), "bedenkzeit_text": tc,
        "runden": _feld(z, "Number of rounds"), "elo": True,
        "links": {k: v for k, v in (("website", web if web.startswith("http") else ""),
                                     ("ausschreibung", pdf), ("fide", FIDE_EVENT.format(id=eid))) if v},
    }


def quelle_fide(cache, budget, heute):
    """Neue Events aus der Kalenderliste + Vorwärtssuche über die Event-Nummern."""
    bekannt = cache.setdefault("events", {})
    ids = set()
    seite = _hole(FIDE_LISTE)
    if not seite:      # FIDE gerade nicht erreichbar/gesperrt -> diesmal nicht weiter suchen, alten Stand behalten
        return [v for v in bekannt.values() if v and v.get("bis", "") >= heute.isoformat()]
    ids |= {int(x) for x in re.findall(r"/calendar/(\d{4,7})", seite)}
    neu = sorted(i for i in ids if str(i) not in bekannt)
    # Vorwärts suchen ab der höchsten bekannten Nummer (neue Turniere bekommen höhere Nummern)
    hoechste = max([int(k) for k, v in bekannt.items() if v] + list(ids) + [cache.get("hoechste", FIDE_START_ID)])
    leer, eid = 0, hoechste + 1
    kandidaten = neu + list(range(eid, eid + 100000))
    for eid in kandidaten:
        if budget[0] <= 0:
            break
        if str(eid) in bekannt:
            continue
        budget[0] -= 1
        seite = _hole(FIDE_EVENT.format(id=eid))
        ev = fide_event(eid, seite) if seite else None
        if ev:
            bekannt[str(eid)] = ev
            cache["hoechste"] = max(cache.get("hoechste", 0), eid)
            leer = 0
        elif eid > hoechste:
            leer += 1
            if leer >= FIDE_LUECKE:
                break
        else:
            bekannt[str(eid)] = None   # Nummer aus der Liste, aber keine Turnierseite
    # Vergangene aus dem Cache werfen (Nummern bleiben als 'erledigt' gemerkt)
    for k, v in list(bekannt.items()):
        if v and v.get("bis") and v["bis"] < heute.isoformat():
            bekannt[k] = None
    return [v for v in bekannt.values() if v]


# ==========================================
# QUELLE: CHESS-RESULTS
# ==========================================
def cr_details(tnr, seite):
    paare = {}
    if BeautifulSoup:
        soup = BeautifulSoup(seite, "html.parser")
        for tr in soup.find_all("tr"):
            td = tr.find_all("td", recursive=False)
            if len(td) == 2:
                k = td[0].get_text(" ", strip=True).rstrip(":").lower()
                if k and k not in paare:
                    paare[k] = td[1].get_text(" ", strip=True)
        h2 = soup.find("h2")
        name = h2.get_text(" ", strip=True) if h2 else ""
        if not name and soup.title:
            name = soup.title.get_text(" ", strip=True).split(" - ", 1)[-1]
    else:
        name = ""

    def wert(*schluessel):
        for s in schluessel:
            for k, v in paare.items():
                if k.startswith(s):
                    return v, k
        return "", ""

    datum, _ = wert("datum", "von", "date", "from")
    daten = re.findall(r"\d{4}/\d{1,2}/\d{1,2}|\d{1,2}\.\d{1,2}\.\d{4}", datum)
    von = _datum(daten[0]) if daten else None
    bis = _datum(daten[-1]) if daten else von
    tc, tc_label = wert("bedenkzeit", "time control")
    ort, _ = wert("ort", "location")
    fed, _ = wert("föderation", "federation")
    typ, _ = wert("turniermodus", "turniertyp", "tournament type")
    links = {}
    if BeautifulSoup:
        zeile = next((tr for tr in soup.find_all("tr") if (tr.find("td") and tr.find("td").get_text(strip=True) in ("Links", "Link"))), None)
        for a in (zeile.find_all("a", href=True) if zeile else []):
            t, href = a.get_text(" ", strip=True).lower(), a["href"].replace("\\", "/")
            if "homepage" in t and "website" not in links:
                links["website"] = href
            elif "ausschreibung" in t or "invitation" in t:
                links.setdefault("ausschreibung", urllib.parse.quote(urllib.parse.urljoin("https://chess-results.com/", href),
                                                                     safe=":/?&=%#+~"))
    wertung, _ = wert("elorechnung", "rating calculation", "wertung")
    schnitt_text, _ = wert("eloschnitt", "rating-ø", "average rating")
    schnitt = re.search(r"\d{3,4}", schnitt_text)
    land, europa = _land(fed) if fed else _land(ort)
    ort = _ohne_land(ort)
    return {
        "id": f"cr:{tnr}", "quelle": "chess-results", "name": name, "ort": ort, "land": land, "europa": europa,
        "von": von.isoformat() if von else "", "bis": bis.isoformat() if bis else "",
        "lat": None, "lon": None, "bedenkzeit": _bedenkzeit(tc_label, tc), "bedenkzeit_text": tc, "bz_label": tc_label,
        "schnitt": int(schnitt.group()) if schnitt and int(schnitt.group()) >= 500 else None, "v": 2,
        "runden": wert("rundenanzahl", "anzahl runden", "number of rounds")[0], "typ": typ,
        # "Elo national" zählt nicht; chess-results schreibt manchmal "intnational"
        "elo": bool(re.search(r"\bint\w*national|fide", wertung, re.I)) if wertung else None,
        "links": dict(links, chessresults=CR_LINK.format(tnr=tnr)),
    }


def cr_kommende(land):
    """tnr-Nummern kommender Turniere eines Landes (Auswahlliste 'beginnende Turniere' per Postback)."""
    url = CR_LISTE.format(land=land)
    seite = _hole(url)
    if not seite:
        return []
    tnrs = []
    if BeautifulSoup:
        # Erst die Zeilen der Startseite, die als 'Nicht begonnen' (Symbol p_5) markiert sind
        for tr in BeautifulSoup(seite, "html.parser").find_all("tr"):
            a, st = tr.find("a", href=re.compile(r"tnr\d+")), tr.find("div", class_="p_5")
            if a and st and len(tr.find_all("td", recursive=False)) <= 4:
                tnrs += re.findall(r"tnr(\d{5,8})", a["href"])
        form = {i["name"]: i.get("value", "") for i in BeautifulSoup(seite, "html.parser").find_all("input", type="hidden") if i.get("name")}
        if "__VIEWSTATE" in form:
            for auswahl in CR_AUSWAHL:
                antwort = _hole(url, daten=dict(form, __EVENTTARGET="combo_sel", __EVENTARGUMENT="",
                                                combo_tur_sel=auswahl, combo_sort="0"))
                if antwort:
                    tnrs += re.findall(r"tnr(\d{5,8})\.aspx", antwort)
    else:
        tnrs = re.findall(r"tnr(\d{5,8})\.aspx", seite)
    return list(dict.fromkeys(tnrs))


def quelle_chessresults(cache, laender, budget, heute):
    bekannt = cache.setdefault("events", {})
    for land in laender:
        for tnr in cr_kommende(land):
            if tnr in bekannt or budget[0] <= 0:
                continue
            budget[0] -= 1
            d = _hole(CR_DETAIL.format(tnr=tnr))
            ev = cr_details(tnr, d) if d else None
            # Nur kommende Turniere behalten; der Rest wird als 'erledigt' gemerkt
            bekannt[tnr] = ev if ev and ev["bis"] and ev["bis"] >= heute.isoformat() else None
    # Ältere Einträge (vor Version 2, ohne Elo-Schnitt) mit dem halben Restbudget auffrischen
    alt = [k for k, v in bekannt.items() if v and v.get("v", 1) < 2]
    for tnr in alt[: max(0, budget[0] // 2)]:
        budget[0] -= 1
        d = _hole(CR_DETAIL.format(tnr=tnr))
        ev = cr_details(tnr, d) if d else None
        if ev and ev.get("von"):
            ev["lat"], ev["lon"] = bekannt[tnr].get("lat"), bekannt[tnr].get("lon")
            bekannt[tnr] = ev
    for k, v in list(bekannt.items()):
        if v and v.get("bis") and v["bis"] < heute.isoformat():
            bekannt[k] = None
    return [v for v in bekannt.values() if v]


def afk_abgleich(events, cache, heimat, max_km, budget, heute):
    """Zählt Spieler aus unserem Verein in den Teilnehmerlisten (nur chess-results)."""
    stand = cache.setdefault("afk", {})
    for ev in events:
        if not ev["id"].startswith("cr:") or (ev.get("km") or 0) > max_km:
            continue
        tnr = ev["id"][3:]
        alt = stand.get(tnr)
        if alt and alt.get("geprueft", "") >= (heute - datetime.timedelta(days=AFK_ALLE_TAGE)).isoformat():
            ev["afk"] = alt.get("anzahl", 0)
            continue
        if budget[0] <= 0:
            if alt:
                ev["afk"] = alt.get("anzahl", 0)
            continue
        budget[0] -= 1
        seite = _hole(CR_START.format(tnr=tnr))
        if seite is None:
            continue
        anzahl = 0
        if BeautifulSoup:
            for tr in BeautifulSoup(seite, "html.parser").find_all("tr"):
                if VEREIN_MUSTER.search(tr.get_text(" ", strip=True)):
                    anzahl += 1
        stand[tnr] = {"anzahl": anzahl, "geprueft": heute.isoformat()}
        ev["afk"] = anzahl


# ==========================================
# ORTE -> KOORDINATEN (nur wenn die Quelle keine liefert)
# ==========================================
def koordinaten(events, cache):
    orte = cache.setdefault("orte", {})
    rest = GEO_PRO_LAUF
    for ev in events:
        if ev.get("lat") is not None or not ev.get("ort"):
            continue
        q = ev["ort"] if not ev.get("land") or ev["land"].lower() in ev["ort"].lower() else f'{ev["ort"]}, {ev["land"]}'
        if q not in orte and rest > 0:
            # Versuche: "PLZ Ort, Land" (aus einer vollen Adresse), dann der ganze Text, dann das letzte Stück
            plz = re.search(r"\b(\d{4,5})\s+([A-ZÄÖÜ][\wäöüßÄÖÜ.\- ]*?)\s*(?:,|$)", ev["ort"])
            versuche = ([f"{plz.group(1)} {plz.group(2)}, {ev.get('land', '')}"] if plz else []) + [q]
            letzt = ev["ort"].split(",")[-1].strip()
            if letzt and letzt != ev["ort"]:
                versuche.append(f"{letzt}, {ev.get('land', '')}")
            ergebnis = None
            for v in versuche:
                if rest <= 0:
                    break
                rest -= 1
                antwort = _hole(GEOCODER.format(q=urllib.parse.quote(v)))
                try:
                    treffer = json.loads(antwort) if antwort else None
                except ValueError:
                    treffer = None
                if treffer is None:      # Netzfehler -> nicht merken, nächstes Mal wieder versuchen
                    ergebnis = "fehler"
                    break
                if treffer:
                    ergebnis = [float(treffer[0]["lat"]), float(treffer[0]["lon"])]
                    break
            if ergebnis != "fehler":
                orte[q] = ergebnis
        if orte.get(q):
            ev["lat"], ev["lon"] = orte[q]


# ==========================================
# FERIEN
# ==========================================
def ferien(heute):
    daten = _lade_json(FERIEN, {})
    schule = [list(x) for x in daten.get("schulferien", [])]
    # Neue Schulferien automatisch ergänzen (wenn erreichbar)
    antwort = _hole(FERIEN_API.format(von=heute.isoformat(), bis=(heute + datetime.timedelta(days=900)).isoformat()))
    try:
        for f in json.loads(antwort) if antwort else []:
            name = next((n.get("text") for n in f.get("name", []) if n.get("text")), "Ferien")
            eintrag = [f["startDate"][:10], f["endDate"][:10], name]
            if not any(e[0] == eintrag[0] for e in schule):
                schule.append(eintrag)
    except (ValueError, KeyError, TypeError):
        pass
    schule.sort()
    vl = sorted(daten.get("vorlesungszeiten", []))
    semester = []
    for (_, ende, name), (beginn, _, _) in zip(vl, vl[1:]):
        a = datetime.date.fromisoformat(ende) + datetime.timedelta(days=1)
        b = datetime.date.fromisoformat(beginn) - datetime.timedelta(days=1)
        if a <= b:
            semester.append([a.isoformat(), b.isoformat(), "Semesterferien nach " + name])
    return ([e for e in schule if e[1] >= heute.isoformat()],
            [e for e in semester if e[1] >= heute.isoformat()])


# ==========================================
# ZUSAMMENFÜHREN
# ==========================================
def zusammenfuehren(listen, konfig, heute):
    heimat = konfig.get("heimat") or {}
    bis_max = (heute + datetime.timedelta(days=int(konfig.get("tage_voraus", 400)))).isoformat()
    ausblenden = [s.lower() for s in konfig.get("ausblenden", []) if s]
    empfohlen = [s.lower() for s in konfig.get("empfohlen", []) if s]
    alle, gesehen = [], {}
    for ev in [e for liste in listen for e in liste]:
        if not ev.get("name") or not ev.get("von") or ev["bis"] < heute.isoformat() or ev["von"] > bis_max:
            continue
        if konfig.get("nur_europa", True) and not ev.get("europa") and not ev.get("eigen"):
            continue
        if not ev.get("eigen") and (LIGA_MUSTER.search(ev["name"]) or LIGA_MUSTER.search(ev.get("typ", ""))):
            continue
        if not ev.get("eigen") and (datetime.date.fromisoformat(ev["bis"]) - datetime.date.fromisoformat(ev["von"])).days \
                > int(konfig.get("max_dauer_tage", MAX_DAUER)):
            continue
        if "bz_label" not in ev and ev.get("bedenkzeit_text"):      # ältere Cache-Einträge neu einordnen
            ev["bedenkzeit"] = _bedenkzeit("", ev["bedenkzeit_text"]) or ev.get("bedenkzeit", "")
        if any(s in ev["name"].lower() for s in ausblenden):
            continue
        # Duplikate: gleicher Start (±1 Tag), gleiches Land, ähnlicher Name -> zusammenlegen
        k = _schluessel(ev["name"])
        doppelt = None
        for andere in gesehen.get(ev.get("land", ""), []):
            if ev["quelle"] in andere["quelle"].split(" + "):
                continue   # innerhalb einer Quelle nie zusammenlegen (z. B. U12- und U14-Gruppe)
            tage = abs((datetime.date.fromisoformat(andere["von"]) - datetime.date.fromisoformat(ev["von"])).days)
            a, b = set(k.split()), set(andere["_k"].split())
            if tage <= 1 and a and b and len(a & b) / min(len(a), len(b)) >= 0.5:
                doppelt = andere
                break
        if doppelt:
            doppelt["links"] = {**ev.get("links", {}), **doppelt.get("links", {})}
            for feld in ("lat", "lon", "bedenkzeit", "bedenkzeit_text", "afk", "elo", "runden"):
                if doppelt.get(feld) in (None, "") and ev.get(feld) not in (None, ""):
                    doppelt[feld] = ev[feld]
            doppelt["quelle"] = " + ".join(dict.fromkeys(doppelt["quelle"].split(" + ") + [ev["quelle"]]))
            continue
        ev = dict(ev, _k=k)
        gesehen.setdefault(ev.get("land", ""), []).append(ev)
        alle.append(ev)
    for ev in alle:
        ev.pop("_k", None)
        ev.pop("typ", None)
        ev["gruppen"] = _gruppen(ev["name"])
        ev["empfohlen"] = bool(ev.get("empfohlen")) or any(s in ev["name"].lower() for s in empfohlen)
        if ev.get("lat") is not None and heimat.get("lat") is not None:
            ev["km"] = round(_km(heimat["lat"], heimat["lon"], ev["lat"], ev["lon"]))
    alle.sort(key=lambda e: (e["von"], e["name"].lower()))
    return alle


GRUPPE_MUSTER = [
    re.compile(r"[\s,\-–:(]+(?:gruppe|gr\.?|group|turnier|open|klasse|class|section)\s*([A-H]|[IVX]{1,3}|\d)\)?\s*$", re.I),
    re.compile(r"[\s,\-–:(]+([A-H])[\s\-]*(?:gruppe|group|turnier|open|klasse|class)\)?\s*$", re.I),
    re.compile(r"[\s,\-–:(]+(jugend\w*|u\s?\d{1,2}(?:\s?[-/]\s?u?\d{1,2})?|begleitturnier|nebenturnier|blitz\w*|"
               r"schnellschach\w*|rapid|ladies|damen|frauen|senioren\w*|amateur\w*|elite|masters?|haupt\w*|"
               r"kinder\w*|mädchen)\)?\s*$", re.I),
    re.compile(r"\s+([A-H])\s*$"),
]


def gruppe_trennen(name):
    """'Open Braunau 2026 B' -> ('Open Braunau 2026', 'B'); ohne Gruppe -> (name, '')."""
    n = name.strip()
    for m in GRUPPE_MUSTER:
        t = m.search(n)
        if t and len(n[:t.start()].strip()) >= 6:
            return n[:t.start()].strip(" -–,:("), t.group(1).strip().replace("Gr.", "").upper() if len(t.group(1)) <= 3 else t.group(1).strip().capitalize()
    return n, ""


def gruppieren(events):
    """Gruppen eines Turniers (A/B/C, Jugend, Blitz-Begleitturnier ...) zu einer Karte zusammenfassen."""
    karten = []
    offen = {}
    for ev in sorted(events, key=lambda e: (e["von"], e["name"])):
        basis, gruppe = gruppe_trennen(ev["name"])
        teil = {"gruppe": gruppe or "", "name": ev["name"], "link": ev.get("links", {}).get("chessresults", ""),
                "schnitt": ev.get("schnitt"), "bedenkzeit": ev.get("bedenkzeit", ""), "elo": ev.get("elo"),
                "afk": ev.get("afk") or 0, "gruppen": _gruppen(ev["name"])}
        k = (_schluessel(basis), ev.get("land", ""))
        karte = None
        for c in offen.get(k, []):
            if ev["von"] <= c["bis"] and ev["bis"] >= c["von"]:      # Zeiträume überschneiden sich
                karte = c
                break
        if karte is None:
            karte = dict(ev, name=basis if gruppe else ev["name"], teile=[])
            karte["links"] = {k2: v for k2, v in ev.get("links", {}).items() if k2 != "chessresults"}
            offen.setdefault(k, []).append(karte)
            karten.append(karte)
        else:
            karte["von"], karte["bis"] = min(karte["von"], ev["von"]), max(karte["bis"], ev["bis"])
            for k2, v in ev.get("links", {}).items():
                if k2 != "chessresults":
                    karte["links"].setdefault(k2, v)
            for feld in ("lat", "lon", "km", "ort"):
                if karte.get(feld) in (None, "") and ev.get(feld) not in (None, ""):
                    karte[feld] = ev[feld]
            karte["empfohlen"] = karte.get("empfohlen") or ev.get("empfohlen")
        karte["teile"].append(teil)
    for c in karten:
        c["teile"].sort(key=lambda t: (t["gruppe"] == "", -(t["schnitt"] or 0), t["gruppe"]))
        if len(c["teile"]) == 1 and not c["teile"][0]["gruppe"]:
            c["name"] = c["teile"][0]["name"]
        c["bz"] = sorted({t["bedenkzeit"] or "?" for t in c["teile"]})
        c["bedenkzeit"] = c["teile"][0]["bedenkzeit"] if len(c["bz"]) == 1 else ""
        c["elo"] = any(t["elo"] for t in c["teile"])
        c["afk"] = sum(t["afk"] for t in c["teile"])
        c["gruppen"] = sorted({g for t in c["teile"] for g in (t["gruppen"] or ["offen"])})
        for f in ("schnitt", "v", "bz_label", "quelle"):
            c.pop(f, None)
    karten.sort(key=lambda e: (e["von"], e["name"].lower()))
    return karten


def eigene(konfig):
    out = []
    for i, e in enumerate(konfig.get("eigene", [])):
        if not e.get("name") or not e.get("von"):
            continue
        land = e.get("land", "Deutschland")
        out.append({
            "id": f"eigen:{i}", "quelle": "eigene Liste", "eigen": True, "name": e["name"],
            "ort": _ohne_land(e.get("ort", "")), "land": land, "europa": True, "von": e["von"], "bis": e.get("bis") or e["von"],
            "lat": e.get("lat"), "lon": e.get("lon"), "bedenkzeit": e.get("bedenkzeit", ""),
            "bedenkzeit_text": e.get("bedenkzeit_text", ""), "elo": e.get("elo"), "empfohlen": e.get("empfohlen", False),
            "notiz": e.get("notiz", ""),
            "links": {k: e[k] for k in ("website", "ausschreibung", "chessresults") if e.get(k)},
        })
    return out


def aktualisieren(heute=None):
    """Quellen abfragen, Cache pflegen -> (events, schulferien, semesterferien, stand)."""
    heute = heute or datetime.date.today()
    konfig = _lade_json(KONFIG, {})
    quellen = konfig.get("quellen", {})
    budget = [int(konfig.get("max_abrufe_pro_lauf", 250))]
    listen = [eigene(konfig)]
    if quellen.get("fide", True):
        c = _lade_json(os.path.join(CACHE, "fide.json"), {})
        try:
            listen.append(quelle_fide(c, budget, heute))
        except Exception as e:
            print(f"  Turnierkalender: FIDE-Fehler {type(e).__name__}: {e}")
            listen.append([v for v in c.get("events", {}).values() if v])
        _speichere_json(os.path.join(CACHE, "fide.json"), c)
    cr = _lade_json(os.path.join(CACHE, "chessresults.json"), {})
    if quellen.get("chessresults", True):
        try:
            listen.append(quelle_chessresults(cr, konfig.get("chessresults_laender", ["GER"]), budget, heute))
        except Exception as e:
            print(f"  Turnierkalender: chess-results-Fehler {type(e).__name__}: {e}")
            listen.append([v for v in cr.get("events", {}).values() if v])
    geo = _lade_json(os.path.join(CACHE, "orte.json"), {})
    for liste in listen:
        koordinaten(liste, geo)
    _speichere_json(os.path.join(CACHE, "orte.json"), geo)
    events = zusammenfuehren(listen, konfig, heute)
    if quellen.get("chessresults", True):
        afk_abgleich(events, cr, konfig.get("heimat", {}), konfig.get("afk_abgleich_km", 400), budget, heute)
        _speichere_json(os.path.join(CACHE, "chessresults.json"), cr)
    events = gruppieren(events)
    schule, semester = ferien(heute)
    print(f"  Turnierkalender: {len(events)} Turniere ({budget[0]} Abrufe übrig)")
    return events, schule, semester, konfig


# ==========================================
# SEITE
# ==========================================
CSS = """
  .tk-intro { max-width: 60rem; }
  .tk-box { margin: 1rem 0; }
  .tk-box > summary { cursor: pointer; font-weight: 700; padding: 0.6rem 0.9rem; border: 1px solid var(--line); border-radius: 10px;
    background: var(--surface); list-style: none; }
  .tk-box > summary::-webkit-details-marker { display: none; }
  .tk-box > summary::after { content: " ▾"; }
  .tk-box[open] > summary { display: none; }
  .tk-box .tk-filter { margin: 0; }
  .tk-filter { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.7rem 1rem;
    padding: 1rem; margin: 1rem 0; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
  .tk-filter label, .tk-filter fieldset { display: grid; gap: 0.25rem; font-size: 0.85rem; font-weight: 600; margin: 0; padding: 0; border: 0; min-width: 0; }
  .tk-filter legend { padding: 0; margin-bottom: 0.25rem; }
  .tk-filter select, .tk-filter input[type=month], .tk-filter input[type=search] { font: inherit; font-weight: normal; padding: 0.4rem 0.5rem;
    border: 1px solid var(--line); border-radius: 6px; background: var(--soft); color: var(--text); width: 100%; box-sizing: border-box; }
  .tk-land { display: grid; gap: 0.25rem; font-size: 0.85rem; font-weight: 600; position: relative; min-width: 0; }
  .tk-land-dd > summary { list-style: none; cursor: pointer; font-weight: normal; padding: 0.4rem 0.5rem; border: 1px solid var(--line);
    border-radius: 6px; background: var(--soft); color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tk-land-dd > summary::-webkit-details-marker { display: none; }
  .tk-land-dd > summary::after { content: " ▾"; float: right; }
  .tk-land-pop { position: absolute; z-index: 20; left: 0; right: 0; min-width: 13rem; max-height: 18rem; overflow-y: auto; margin-top: 0.2rem;
    padding: 0.4rem; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); box-shadow: 0 6px 18px rgba(0,0,0,.25); }
  .tk-land-pop label { display: flex; align-items: center; gap: 0.4rem; font-weight: normal; padding: 0.2rem 0.3rem; border-radius: 4px; cursor: pointer; }
  .tk-land-pop label:hover { background: var(--soft); }
  .tk-land-pop input { accent-color: var(--accent); margin: 0; }
  .tk-land-pop button { width: 100%; margin-bottom: 0.3rem; font: inherit; font-size: 0.85rem; padding: 0.3rem; border-radius: 6px;
    border: 1px solid var(--line); background: transparent; color: var(--text); cursor: pointer; }
  .tk-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .tk-chips label { display: inline-flex; align-items: center; gap: 0.3rem; font-weight: normal; padding: 0.2rem 0.55rem;
    border: 1px solid var(--line); border-radius: 999px; cursor: pointer; background: var(--soft); }
  .tk-chips input { margin: 0; accent-color: var(--accent); }
  .tk-zeile2 { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; align-items: center; font-weight: normal; }
  .tk-zeile2 label { display: inline-flex; flex-direction: row; align-items: center; gap: 0.3rem; font-weight: normal; }
  .tk-zeile2 button { margin-left: auto; font: inherit; font-size: 0.85rem; padding: 0.3rem 0.7rem; border-radius: 6px;
    border: 1px solid var(--line); background: transparent; color: var(--text); cursor: pointer; }
  .tk-legende { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.85rem; color: var(--muted); margin: 0.2rem 0 1rem; align-items: center; }
  .tk-anzahl { font-weight: 600; color: var(--text); }
  .tk-monat { margin: 1.6rem 0 0.6rem; font-size: 1.15rem; display: flex; gap: 0.6rem; align-items: baseline; flex-wrap: wrap; }
  .tk-monat small { font-weight: normal; font-size: 0.8rem; color: var(--muted); }
  .tk-liste { display: grid; gap: 0.6rem; }
  .tk-karte { display: grid; grid-template-columns: 7rem 1fr; gap: 0.9rem; padding: 0.8rem 1rem; border: 1px solid var(--line);
    border-left: 5px solid var(--line); border-radius: 10px; background: var(--surface); }
  .tk-karte.tk-schule { border-left-color: var(--tk-schule); }
  .tk-karte.tk-semester { border-left-color: var(--tk-semester); }
  .tk-karte.tk-schule.tk-semester { border-image: linear-gradient(var(--tk-schule) 50%, var(--tk-semester) 50%) 0 0 0 5; border-left-style: solid; }
  .tk-karte.tk-empf { box-shadow: 0 0 0 2px var(--hell, #6f9fd8) inset; }
  .tk-datum { font-weight: 800; line-height: 1.2; font-variant-numeric: tabular-nums; }
  .tk-datum small { display: block; font-weight: normal; font-size: 0.78rem; color: var(--muted); }
  .tk-name { margin: 0; font-size: 1.02rem; line-height: 1.3; }
  .tk-ort { margin: 0.15rem 0 0.35rem; font-size: 0.88rem; color: var(--muted); }
  .tk-badges { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.4rem; }
  .tk-b { font-size: 0.74rem; padding: 0.08rem 0.45rem; border-radius: 999px; border: 1px solid var(--line); white-space: nowrap; }
  .tk-b.klassisch { background: #2c6e49; color: #fff; border-color: transparent; }
  .tk-b.schnell { background: #b7791f; color: #fff; border-color: transparent; }
  .tk-b.blitz { background: #b83232; color: #fff; border-color: transparent; }
  .tk-b.schule { background: var(--tk-schule); color: #fff; border-color: transparent; }
  .tk-b.semester { background: var(--tk-semester); color: #fff; border-color: transparent; }
  .tk-b.afk { background: var(--hell, #6f9fd8); color: #0e1524; border-color: transparent; font-weight: 700; }
  .tk-b.empf { border-color: var(--hell, #6f9fd8); font-weight: 700; }
  .tk-links { display: flex; flex-wrap: wrap; gap: 0.3rem 0.9rem; font-size: 0.85rem; }
  .tk-links a, .tk-links button { color: var(--link-c, #2c5d99); text-decoration: underline; background: none; border: 0; padding: 0; font: inherit; cursor: pointer; }
  .tk-teile { list-style: none; margin: 0 0 0.45rem; padding: 0; display: grid; gap: 0.25rem; font-size: 0.86rem; }
  .tk-teile li { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
  .tk-teile a { color: var(--link-c, #2c5d99); }
  .tk-ausgeblendet { margin: 0 0 0.4rem; font-size: 0.8rem; color: var(--muted); }
  .tk-mehr { text-align: center; margin: 1.2rem 0; }
  .tk-mehr button { font: inherit; font-weight: 600; padding: 0.55rem 1.2rem; border-radius: 8px; border: 1px solid var(--line);
    background: var(--surface); color: var(--text); cursor: pointer; }
  .tk-filter input[type=number] { font: inherit; font-weight: normal; padding: 0.4rem 0.5rem; border: 1px solid var(--line);
    border-radius: 6px; background: var(--soft); color: var(--text); width: 100%; box-sizing: border-box; }
  .tk-leer { padding: 1.5rem; text-align: center; color: var(--muted); border: 1px dashed var(--line); border-radius: 10px; }
  .tk-quellen { font-size: 0.8rem; color: var(--muted); margin-top: 2rem; }
  :root { --tk-schule: #1f8a70; --tk-semester: #7b4fbf; }
  @media (max-width: 600px) {
    .tk-karte { grid-template-columns: 1fr; gap: 0.3rem; }
    .tk-datum small { display: inline; margin-left: 0.4rem; }
  }
"""

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById("tk-daten").textContent);
  // Am PC Filter offen, am Handy eingeklappt (spart Platz)
  if (window.matchMedia("(min-width: 701px)").matches) document.getElementById("tk-box").open = true;
  var f = document.getElementById("tk-filter"), out = document.getElementById("tk-out"), zahl = document.getElementById("tk-zahl");
  var MON = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"];
  var KURZ = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"];
  var TAGE = ["So","Mo","Di","Mi","Do","Fr","Sa"];
  var BZ = {klassisch: "Klassisch", schnell: "Schnellschach", blitz: "Blitz"};
  var SPEICHER = "afk-turnierkalender";
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function dt(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function iso(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function ueberlapp(e, liste) { return liste.filter(function (x) { return e.von <= x[1] && e.bis >= x[0]; }); }

  // Länder-Auswahl füllen
  var laender = {}; D.events.forEach(function (e) { if (e.land) laender[e.land] = 1; });
  var landBox = document.getElementById("tk-laender"), landText = document.getElementById("tk-land-text");
  Object.keys(laender).sort(function (a, b) { return a.localeCompare(b, "de"); }).forEach(function (l) {
    var lab = document.createElement("label"), c = document.createElement("input");
    c.type = "checkbox"; c.name = "land"; c.value = l; lab.appendChild(c); lab.appendChild(document.createTextNode(" " + l));
    landBox.appendChild(lab);
  });
  function landListe() { return [].map.call(f.querySelectorAll("[name=land]:checked"), function (c) { return c.value; }); }
  function landAnzeige() {
    var l = landListe();
    landText.textContent = !l.length ? "alle Länder" : l.length <= 3 ? l.join(", ") : l.slice(0, 2).join(", ") + " + " + (l.length - 2) + " weitere";
  }
  document.getElementById("tk-land-alle").addEventListener("click", function () {
    [].forEach.call(f.querySelectorAll("[name=land]"), function (c) { c.checked = false; }); zeige();
  });

  // Standardwerte
  var h = new Date(), bis = new Date(h.getFullYear(), h.getMonth() + D.standard.monate, 1);
  var STANDARD = {von: iso(h).slice(0, 7), bis: iso(bis).slice(0, 7), km: String(D.standard.km), land: [], q: "", meinelo: "",
    bz: ["klassisch", "schnell", "blitz", "?"], gr: ["offen", "jugend", "senioren", "frauen"],
    elo: false, ferien: false, semester: false, empf: false, afk: false};
  function setze(w) {
    f.elements.von.value = w.von; f.elements.bis.value = w.bis; f.elements.km.value = w.km;
    var wl = Array.isArray(w.land) ? w.land : (w.land ? [w.land] : []);
    [].forEach.call(f.querySelectorAll("[name=land]"), function (c) { c.checked = wl.indexOf(c.value) >= 0; });
    f.elements.q.value = w.q; f.elements.meinelo.value = w.meinelo || "";
    [].forEach.call(f.querySelectorAll("[name=bz]"), function (c) { c.checked = w.bz.indexOf(c.value) >= 0; });
    [].forEach.call(f.querySelectorAll("[name=gr]"), function (c) { c.checked = w.gr.indexOf(c.value) >= 0; });
    ["elo", "ferien", "semester", "empf", "afk"].forEach(function (n) { f.elements[n].checked = !!w[n]; });
  }
  function lies() {
    var w = {von: f.elements.von.value, bis: f.elements.bis.value, km: f.elements.km.value, land: landListe(),
      q: f.elements.q.value.trim(), meinelo: +f.elements.meinelo.value || 0, bz: [], gr: []};
    [].forEach.call(f.querySelectorAll("[name=bz]:checked"), function (c) { w.bz.push(c.value); });
    [].forEach.call(f.querySelectorAll("[name=gr]:checked"), function (c) { w.gr.push(c.value); });
    ["elo", "ferien", "semester", "empf", "afk"].forEach(function (n) { w[n] = f.elements[n].checked; });
    return w;
  }
  var gespeichert = null;
  try { gespeichert = JSON.parse(localStorage.getItem(SPEICHER) || "null"); } catch (e) {}
  setze(gespeichert && gespeichert.von >= STANDARD.von ? gespeichert : STANDARD);

  function ics(e) {
    var ende = dt(e.bis); ende.setDate(ende.getDate() + 1);
    var link = e.links.ausschreibung || e.links.website || e.links.chessresults || e.links.fide || "";
    var txt = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SG AFK//Turnierkalender//DE", "BEGIN:VEVENT",
      "UID:" + e.id.replace(/[^\w]/g, "") + "@sgafk", "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z",
      "DTSTART;VALUE=DATE:" + e.von.replace(/-/g, ""), "DTEND;VALUE=DATE:" + iso(ende).replace(/-/g, ""),
      "SUMMARY:" + e.name.replace(/[,;]/g, "\\$&"), "LOCATION:" + (e.ort || "").replace(/[,;]/g, "\\$&"),
      "URL:" + link, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([txt], {type: "text/calendar"}));
    a.download = e.name.replace(/[^\wäöüÄÖÜß -]/g, "").slice(0, 60) + ".ics";
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function datumText(e) {
    var a = dt(e.von), b = dt(e.bis);
    if (e.von === e.bis) return a.getDate() + ". " + KURZ[a.getMonth()] + "<small>" + TAGE[a.getDay()] + "</small>";
    var tage = Math.round((b - a) / 864e5) + 1;
    var t = a.getMonth() === b.getMonth() ? a.getDate() + ".–" + b.getDate() + ". " + KURZ[b.getMonth()]
      : a.getDate() + ". " + KURZ[a.getMonth()] + " – " + b.getDate() + ". " + KURZ[b.getMonth()];
    return t + "<small>" + TAGE[a.getDay()] + "–" + TAGE[b.getDay()] + " · " + tage + " Tage</small>";
  }

  var SEITE_N = 20, anzeigen = SEITE_N, letzterFilter = "";
  function passendeTeile(e, w) {
    return e.teile.filter(function (t) {
      if (w.bz.indexOf(t.bedenkzeit || "?") < 0) return false;
      var g = t.gruppen.length ? t.gruppen : ["offen"];
      if (!g.some(function (x) { return w.gr.indexOf(x) >= 0; })) return false;
      if (w.elo && !t.elo) return false;
      if (w.meinelo && t.schnitt != null && (t.schnitt < w.meinelo - D.elo.unten || t.schnitt > w.meinelo + D.elo.oben)) return false;
      return true;
    });
  }
  function zeige() {
    landAnzeige();
    var w = lies(), km = w.km === "alle" ? Infinity : +w.km, q = w.q.toLowerCase();
    try { localStorage.setItem(SPEICHER, JSON.stringify(w)); } catch (e) {}
    var sig = JSON.stringify(w); if (sig !== letzterFilter) { anzeigen = SEITE_N; letzterFilter = sig; }
    var von = w.von ? w.von + "-01" : "0000", bisM = w.bis ? w.bis + "-31" : "9999";
    var liste = D.events.filter(function (e) {
      if (e.bis < von || e.von > bisM) return false;
      if (w.land.length && w.land.indexOf(e.land) < 0) return false;
      if (km !== Infinity && !(e.km != null && e.km <= km)) return false;
      e._t = passendeTeile(e, w);
      if (!e._t.length) return false;
      if (w.empf && !e.empfohlen) return false;
      if (w.afk && !e.afk) return false;
      var s = ueberlapp(e, D.schule).length, m = ueberlapp(e, D.semester).length;
      if ((w.ferien || w.semester) && !((w.ferien && s) || (w.semester && m))) return false;
      if (q && (e.name + " " + e.ort + " " + e.land).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    zahl.textContent = liste.length + (liste.length === 1 ? " Turnier" : " Turniere");
    if (!liste.length) {
      out.innerHTML = '<p class="tk-leer">' + (D.events.length ? "Keine Turniere für diese Filter. Probier eine größere Entfernung oder einen längeren Zeitraum."
        : "Noch keine Turniere geladen. Der Kalender füllt sich beim nächsten nächtlichen Update.") + "</p>";
      return;
    }
    var html = "", monat = "";
    liste.slice(0, anzeigen).forEach(function (e) {
      var m = e.von.slice(0, 7);
      if (m !== monat) {
        if (monat) html += "</div>";
        monat = m;
        var md = dt(m + "-01"), fer = ueberlapp({von: m + "-01", bis: m + "-31"}, D.schule).map(function (x) { return x[2]; });
        html += '<h3 class="tk-monat">' + MON[md.getMonth()] + " " + md.getFullYear() +
          (fer.length ? " <small>" + esc(fer.filter(function (v, j) { return fer.indexOf(v) === j; }).join(", ")) + "</small>" : "") + '</h3><div class="tk-liste">';
      }
      var T = e._t, s = ueberlapp(e, D.schule), sem = ueberlapp(e, D.semester), b = "", bzs = {};
      T.forEach(function (t) { if (t.bedenkzeit) bzs[t.bedenkzeit] = 1; });
      ["klassisch", "schnell", "blitz"].forEach(function (z) { if (bzs[z]) b += '<span class="tk-b ' + z + '">' + BZ[z] + "</span>"; });
      if (T.some(function (t) { return t.elo; })) b += '<span class="tk-b">Elo</span>';
      var grp = {}; T.forEach(function (t) { t.gruppen.forEach(function (g) { grp[g] = 1; }); });
      ["jugend", "senioren", "frauen"].forEach(function (g) { if (grp[g]) b += '<span class="tk-b">' + {jugend: "Jugend", senioren: "Senioren", frauen: "Frauen"}[g] + "</span>"; });
      if (s.length) b += '<span class="tk-b schule" title="' + esc(s.map(function (x) { return x[2]; }).join(", ")) + '">Schulferien</span>';
      if (sem.length) b += '<span class="tk-b semester">Semesterferien</span>';
      if (e.afk) b += '<span class="tk-b afk">' + e.afk + " AFK gemeldet</span>";
      if (e.empfohlen) b += '<span class="tk-b empf">★ Empfehlung</span>';
      var L = e.links, l = "", einzel = e.teile.length === 1 && !e.teile[0].gruppe, teile = "";
      if (L.ausschreibung) l += '<a href="' + esc(L.ausschreibung) + '" target="_blank" rel="noopener">Ausschreibung</a>';
      if (L.website) l += '<a href="' + esc(L.website) + '" target="_blank" rel="noopener">Website</a>';
      if (einzel && e.teile[0].link) l += '<a href="' + esc(e.teile[0].link) + '" target="_blank" rel="noopener">chess-results</a>';
      if (L.chessresults) l += '<a href="' + esc(L.chessresults) + '" target="_blank" rel="noopener">chess-results</a>';
      if (L.fide) l += '<a href="' + esc(L.fide) + '" target="_blank" rel="noopener">FIDE</a>';
      l += '<button type="button" data-ics="' + D.events.indexOf(e) + '">In Kalender</button>';
      if (einzel) {
        if (e.teile[0].schnitt) b += '<span class="tk-b" title="Elo-Schnitt der bisher gemeldeten Spieler">Ø ' + e.teile[0].schnitt + "</span>";
      } else {
        teile = '<ul class="tk-teile">' + T.map(function (t) {
          return "<li><b>" + esc(t.gruppe || "Hauptturnier") + "</b>" +
            (t.schnitt ? ' <span title="Elo-Schnitt der bisher gemeldeten Spieler">Ø ' + t.schnitt + "</span>" : "") +
            (t.bedenkzeit ? ' <span class="tk-b ' + t.bedenkzeit + '">' + BZ[t.bedenkzeit] + "</span>" : "") +
            (t.afk ? ' <span class="tk-b afk">' + t.afk + " AFK</span>" : "") +
            (t.link ? ' <a href="' + esc(t.link) + '" target="_blank" rel="noopener">chess-results</a>' : "") + "</li>";
        }).join("") + "</ul>" +
          (T.length < e.teile.length ? '<p class="tk-ausgeblendet">' + (e.teile.length - T.length) + " weitere Gruppe(n) passen nicht zum Filter</p>" : "");
      }
      var ort = [e.ort, e.land].filter(Boolean).join(", ");
      html += '<article class="tk-karte' + (s.length ? " tk-schule" : "") + (sem.length ? " tk-semester" : "") + (e.empfohlen ? " tk-empf" : "") + '">' +
        '<div class="tk-datum">' + datumText(e) + "</div><div>" +
        '<h4 class="tk-name">' + esc(e.name) + "</h4>" +
        '<p class="tk-ort">' + esc(ort) + (e.km != null ? " · " + e.km + " km" : "") + (e.bedenkzeit_text && einzel ? " · " + esc(e.bedenkzeit_text) : "") + "</p>" +
        (b ? '<div class="tk-badges">' + b + "</div>" : "") + teile + (e.notiz ? '<p class="tk-ort">' + esc(e.notiz) + "</p>" : "") +
        '<div class="tk-links">' + l + "</div></div></article>";
    });
    html += "</div>";
    if (liste.length > anzeigen) {
      html += '<p class="tk-mehr"><button type="button" id="tk-mehr">Mehr anzeigen (noch ' + (liste.length - anzeigen) + ")</button></p>";
    }
    out.innerHTML = html;
  }
  out.addEventListener("click", function (ev) {
    if (ev.target.id === "tk-mehr") { anzeigen += SEITE_N; zeige(); return; }
    var k = ev.target.closest("[data-ics]"); if (k) ics(D.events[+k.getAttribute("data-ics")]);
  });
  f.addEventListener("input", zeige); f.addEventListener("change", zeige);
  document.addEventListener("click", function (ev) {
    var dd = document.querySelector(".tk-land-dd"); if (dd.open && !dd.contains(ev.target)) dd.open = false;
  });
  document.getElementById("tk-reset").addEventListener("click", function () { setze(STANDARD); zeige(); });
  zeige();
})();
"""


def seite_html(events, schule, semester, konfig, stand):
    std = konfig.get("standard_filter", {})
    daten = {"events": events, "schule": schule, "semester": semester,
             "standard": {"km": std.get("km", 200), "monate": std.get("monate", 6)},
             "elo": {"unten": (konfig.get("elo_toleranz") or {}).get("unten", 350),
                     "oben": (konfig.get("elo_toleranz") or {}).get("oben", 200)}}
    km_optionen = "".join(f'<option value="{k}">bis {k} km</option>' for k in (50, 100, 200, 400, 800, 1500))
    heimat = html.escape((konfig.get("heimat") or {}).get("name", "uns"))
    fide_an = (konfig.get("quellen") or {}).get("fide", False)
    quellen_text = "aus dem FIDE-Kalender und von chess-results.com" if fide_an else "von chess-results.com"
    quellen_links = ('<a href="https://fide.com/calendar" target="_blank" rel="noopener">FIDE-Kalender</a>, ' if fide_an else "") + \
        '<a href="https://chess-results.com" target="_blank" rel="noopener">chess-results.com</a>'
    js_daten = json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")
    return f"""
    <a href="turniere.html" style="text-decoration:none;">← Zurück zur Turniere-Übersicht</a>
    <h1 style="margin-top:1rem;">{TITEL}</h1>
    <p class="tk-intro">Opens und Turniere in Bayern, Deutschland und Europa – automatisch gesammelt {quellen_text},
      jede Nacht aktualisiert. Die Entfernung wird ab {heimat} gerechnet.
      Unsere eigenen Turniere findest du unter <a href="ausschreibungen.html">Ausschreibungen (intern)</a>.</p>
    <details class="tk-box" id="tk-box"><summary>Filter anzeigen</summary>
    <form id="tk-filter" class="tk-filter" onsubmit="return false">
      <label>Von <input type="month" name="von"></label>
      <label>Bis <input type="month" name="bis"></label>
      <label>Entfernung <select name="km">{km_optionen}<option value="alle">ganz Europa</option></select></label>
      <div class="tk-land"><span class="tk-land-titel">Länder</span>
        <details class="tk-land-dd"><summary id="tk-land-text">alle Länder</summary>
          <div class="tk-land-pop"><button type="button" id="tk-land-alle">alle Länder</button><div id="tk-laender"></div></div>
        </details></div>
      <fieldset><legend>Bedenkzeit</legend><div class="tk-chips">
        <label><input type="checkbox" name="bz" value="klassisch"> Klassisch</label>
        <label><input type="checkbox" name="bz" value="schnell"> Schnell</label>
        <label><input type="checkbox" name="bz" value="blitz"> Blitz</label>
        <label><input type="checkbox" name="bz" value="?"> unbekannt</label></div></fieldset>
      <fieldset><legend>Für wen</legend><div class="tk-chips">
        <label><input type="checkbox" name="gr" value="offen"> Offen</label>
        <label><input type="checkbox" name="gr" value="jugend"> Jugend</label>
        <label><input type="checkbox" name="gr" value="senioren"> Senioren</label>
        <label><input type="checkbox" name="gr" value="frauen"> Frauen</label></div></fieldset>
      <label>Meine Elo <input type="number" name="meinelo" min="0" max="3000" step="50" placeholder="z. B. 1600"
        title="Zeigt nur Gruppen, deren Elo-Schnitt zu dir passt"></label>
      <label>Suche <input type="search" name="q" placeholder="Name oder Ort"></label>
      <div class="tk-zeile2">
        <label><input type="checkbox" name="ferien"> nur in Schulferien</label>
        <label><input type="checkbox" name="semester"> nur in Semesterferien</label>
        <label><input type="checkbox" name="elo"> nur Elo-gewertet</label>
        <label><input type="checkbox" name="afk"> mit AFK-Spielern</label>
        <label><input type="checkbox" name="empf"> nur Empfehlungen</label>
        <button type="button" id="tk-reset">Filter zurücksetzen</button>
      </div>
    </form></details>
    <div class="tk-legende"><span class="tk-anzahl" id="tk-zahl"></span>
      <span class="tk-b schule">Schulferien Bayern</span><span class="tk-b semester">Semesterferien (bayer. Unis)</span>
      <span class="tk-b afk">AFK gemeldet</span><span class="tk-b empf">★ Empfehlung</span></div>
    <div id="tk-out" aria-live="polite"></div>
    <p class="tk-quellen">Quellen: {quellen_links}, eigene Liste. Stand: {stand}.
      Angaben ohne Gewähr – bitte immer die Ausschreibung prüfen. Noch mehr deutsche Turniere:
      <a href="https://chessdates.com" target="_blank" rel="noopener">chessdates.com</a>.</p>
    <script type="application/json" id="tk-daten">{js_daten}</script>
    <script>{JS}</script>
    """


def bauen(render_page, heute=None):
    """Von build_site.py aufgerufen. Gibt (SEITE, TITEL) zurück oder None."""
    heute = heute or datetime.date.today()
    try:
        events, schule, semester, konfig = aktualisieren(heute)
    except Exception as e:  # der Website-Build darf nie am Kalender scheitern
        print(f"WARNUNG: Turnierkalender übersprungen ({type(e).__name__}: {e})")
        events, schule, semester, konfig = [], [], [], _lade_json(KONFIG, {})
    global ANZAHL
    ANZAHL = len(events)
    inhalt = seite_html(events, schule, semester, konfig, heute.strftime("%d.%m.%Y"))
    render_page(TITEL, inhalt, SEITE, extra_styles="<style>" + CSS + "</style>")
    return SEITE, TITEL


# ==========================================
# DIAGNOSE
# ==========================================
def probe():
    """Lädt je Quelle Liste + eine Detailseite und speichert sie roh ab (zum Anpassen der Auswertung)."""
    os.makedirs(PROBE, exist_ok=True)
    konfig = _lade_json(KONFIG, {})

    def sichern(name, url):
        daten = _hole(url, roh=True)
        print(f"{name:28s} {'OK ' + str(len(daten)) + ' Bytes' if daten else 'FEHLER ' + str(STATUS.get(url))}  {url}")
        if daten:
            with open(os.path.join(PROBE, name), "wb") as f:
                f.write(daten)
        return daten.decode("utf-8", "replace") if daten else ""

    liste = sichern("fide_liste.html", FIDE_LISTE)
    ids = sorted({int(x) for x in re.findall(r"/calendar/(\d{4,7})", liste)})
    print(f"  FIDE: {len(ids)} Event-Links in der Liste" + (f" ({ids[0]}–{ids[-1]})" if ids else ""))
    for eid in (ids[-1:] if ids else []) + [54288]:
        s = sichern(f"fide_event_{eid}.html", FIDE_EVENT.format(id=eid))
        if s:
            print("  ->", json.dumps(fide_event(eid, s), ensure_ascii=False)[:400])
    for land in konfig.get("chessresults_laender", ["GER"])[:2]:
        s = sichern(f"cr_liste_{land}.html", CR_LISTE.format(land=land))
        tnrs = cr_kommende(land)
        print(f"  chess-results {land}: {len(tnrs)} kommende Turniere (Liste + Auswahl)")
        for tnr in tnrs[:2]:
            d = sichern(f"cr_{tnr}.html", CR_DETAIL.format(tnr=tnr))
            if d:
                print("  ->", json.dumps(cr_details(tnr, d), ensure_ascii=False)[:400])
    sichern("ferien_api.json", FERIEN_API.format(von=datetime.date.today().isoformat(),
                                                 bis=(datetime.date.today() + datetime.timedelta(days=900)).isoformat()))
    sichern("geocoder.json", GEOCODER.format(q=urllib.parse.quote("Bad Wiessee, Deutschland")))
    print(f"\nFertig. Bitte den Ordner {PROBE} als Zip schicken.")


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe()
    else:
        ev, sch, sem, _ = aktualisieren()
        for e in ev[:40]:
            print(f'{e["von"]}  {e.get("km", "?"):>5} km  {e.get("bedenkzeit") or "?":9s} {e["name"]} ({e.get("ort")})')
