"""
Abzeichen für "AFK on Tour".

Jedes Abzeichen hat eine Stufe (bronze/silber/gold/legendaer -> Punkte) und eine Prüfung,
die auf den Merkmalen eines Spielers arbeitet (siehe merkmale()). Neue Abzeichen: einfach
unten in ABZEICHEN ergänzen. "Klassiker" (bestimmte Turniere/Orte) stehen in
turnierorte/einstellungen.json unter "klassiker".
"""
import datetime
import math
import re
import unicodedata

STUFEN = {"bronze": ("Bronze", 10), "silber": ("Silber", 25), "gold": ("Gold", 50), "legendaer": ("Legendär", 100)}

NACHBARN = {"Dänemark", "Polen", "Tschechien", "Österreich", "Schweiz", "Frankreich", "Luxemburg", "Belgien", "Niederlande"}
ALPEN = {"Österreich", "Schweiz", "Italien", "Slowenien", "Frankreich", "Liechtenstein", "Monaco"}
BALKAN = {"Slowenien", "Kroatien", "Bosnien und Herzegowina", "Bosnien", "Serbien", "Montenegro", "Nordmazedonien",
          "Albanien", "Kosovo", "Bulgarien", "Griechenland", "Rumänien"}
SKANDINAVIEN = {"Dänemark", "Schweden", "Norwegen"}
BENELUX = {"Belgien", "Niederlande", "Luxemburg"}
IBERIEN = {"Spanien", "Portugal", "Andorra"}
INSEL_LAENDER = {"Malta", "Zypern", "Island", "Isle of Man", "Jersey", "Guernsey", "Färöer", "Irland",
                 "Vereinigtes Königreich", "Großbritannien", "England", "Schottland", "Wales", "Nordirland"}
INSEL_REGIONEN = re.compile(r"insel|balear|kanar|sizilien|sardinien|korsika|kreta|madeira|azoren|rügen|sylt|usedom|"
                            r"fehmarn|mallorca|ibiza|teneriffa|gran canaria|rhodos|korfu", re.I)
HAUPTSTAEDTE = {"Berlin", "Wien", "Bern", "Rom", "Paris", "Madrid", "Lissabon", "Amsterdam", "Brüssel", "Luxemburg",
                "Prag", "Warschau", "Budapest", "Bratislava", "Ljubljana", "Zagreb", "Belgrad", "Sarajevo", "Podgorica",
                "Skopje", "Tirana", "Athen", "Sofia", "Bukarest", "Chișinău", "Kiew", "Minsk", "Vilnius", "Riga", "Tallinn",
                "Helsinki", "Stockholm", "Oslo", "Kopenhagen", "Reykjavík", "Dublin", "London", "Edinburgh", "Cardiff",
                "Valletta", "Nikosia", "Monaco", "Andorra la Vella", "San Marino", "Vaduz", "Pristina", "Ankara",
                "Tiflis", "Jerewan", "Baku", "Moskau"}
EUROPA_LAENDER = NACHBARN | ALPEN | BALKAN | SKANDINAVIEN | BENELUX | IBERIEN | INSEL_LAENDER | {
    "Deutschland", "Ungarn", "Slowakei", "Finnland", "Estland", "Lettland", "Litauen", "Moldau", "Republik Moldau",
    "Ukraine", "Belarus", "Russland", "San Marino", "Vatikanstadt", "Türkei"}


def kontinent(land, lat, lon):
    """Grobe Zuordnung: bekannte europäische Länder, sonst nach Koordinaten."""
    if land in EUROPA_LAENDER:
        return "Europa"
    if lat is None or lon is None:
        return ""
    if lon < -25:
        return "Nordamerika" if lat > 12 else "Südamerika"
    if lat > 35 and lon < 40:
        return "Europa"
    if lon > 110 and lat < -10 or lon > 150:
        return "Ozeanien"
    if lat < 37 and -20 <= lon <= 52 and not (lon > 34 and lat > 12):
        return "Afrika"
    return "Asien"


def _datum(text, ende=False):
    """'2025-04-17' -> date; '2025-04' -> 1. (bzw. letzter) des Monats; sonst None."""
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", text or "")
    if not m:
        return None
    j, mo = int(m.group(1)), int(m.group(2))
    if m.group(3):
        return datetime.date(j, mo, int(m.group(3)))
    if ende:
        return (datetime.date(j + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1))
    return datetime.date(j, mo, 1)


def _km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    x = math.sin(math.radians(c - a) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def _richtung(lat1, lon1, lat2, lon2):
    """Himmelsrichtung N/O/S/W von Punkt 1 nach Punkt 2."""
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
         - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1)))
    grad = (math.degrees(math.atan2(y, x)) + 360) % 360
    return "NOSW"[int((grad + 45) % 360 // 90)]


def _buchstabe(ort):
    t = unicodedata.normalize("NFKD", ort.strip()).encode("ascii", "ignore").decode().upper()
    return t[:1] if t[:1].isalpha() else ""


def turnier_schluessel(b):
    """Gleiches Turnier erkennen (für Reisegruppe): chess-results-Nummer, sonst Name + Monat + Ort."""
    tnr = re.search(r"tnr(\d+)", b.get("link", "") or "")
    if tnr:
        return "cr" + tnr.group(1)
    name = re.sub(r"\b(19|20)\d{2}\b|[^a-z]", "", (b.get("turnier") or "").lower())
    return f"{name}|{(b.get('von') or '')[:7]}|{b.get('ort', '')}"


def serien_schluessel(b):
    """Gleiche Turnierserie über Jahre (für Tradition): Name ohne Jahreszahlen/Nummern + Ort."""
    name = re.sub(r"\b(19|20)\d{2}\b|\b\d+\.?\b|[^a-zäöüß ]", " ", (b.get("turnier") or "").lower())
    return " ".join(name.split()) + "|" + b.get("ort", "")


# ------------------------------------------------------------
# Merkmale
# ------------------------------------------------------------
def verein_merkmale(alle):
    """Vereinsweite Infos: wer war wann zuerst wo, wie viele AFKler pro Turnier."""
    erst_ort, erst_land, turniere, ort_leute = {}, {}, {}, {}
    for b in alle:
        d = b.get("von") or "9999"
        if b["ort"] not in erst_ort or d < erst_ort[b["ort"]][0]:
            erst_ort[b["ort"]] = (d, {b["spieler"]})
        elif d == erst_ort[b["ort"]][0]:
            erst_ort[b["ort"]][1].add(b["spieler"])
        land = b.get("land", "")
        if land:
            if land not in erst_land or d < erst_land[land][0]:
                erst_land[land] = (d, {b["spieler"]})
            elif d == erst_land[land][0]:
                erst_land[land][1].add(b["spieler"])
        turniere.setdefault(turnier_schluessel(b), set()).add(b["spieler"])
        ort_leute.setdefault(b["ort"], set()).add(b["spieler"])
    return {"erst_ort": erst_ort, "erst_land": erst_land, "turniere": turniere, "ort_leute": ort_leute}


def merkmale(sid, liste, verein, heimat, konf):
    f = {}
    orte = {}
    for b in liste:
        orte[b["ort"]] = orte.get(b["ort"], 0) + 1
    f["orte"] = len(orte)
    f["max_gleich"] = max(orte.values()) if orte else 0
    laender = {b.get("land", "") for b in liste if b.get("land")}
    f["laender"] = laender
    f["ausland"] = bool(laender - {"Deutschland"})
    f["regionen_de"] = {b.get("region") for b in liste if b.get("land") == "Deutschland" and b.get("region")}
    f["bayern_orte"] = {b["ort"] for b in liste if b.get("region") == "Bayern"}
    f["ausserhalb_bayern"] = any((b.get("land") and b.get("land") != "Deutschland") or
                                 (b.get("region") and b.get("region") != "Bayern") for b in liste)
    f["kontinente"] = {kontinent(b.get("land", ""), b.get("lat"), b.get("lon")) for b in liste} - {""}
    f["hauptstaedte"] = {b.get("stadt") for b in liste if b.get("stadt") in HAUPTSTAEDTE}
    f["insel"] = any(b.get("land") in INSEL_LAENDER or INSEL_REGIONEN.search(b.get("region", "") or "")
                     or INSEL_REGIONEN.search(b.get("stadt", "") or "") for b in liste)
    km, richt, nord = [], set(), -90
    for b in liste:
        if b.get("lat") is None:
            continue
        k = _km(heimat["lat"], heimat["lon"], b["lat"], b["lon"])
        km.append(k)
        nord = max(nord, b["lat"])
        if k >= 300:
            richt.add(_richtung(heimat["lat"], heimat["lon"], b["lat"], b["lon"]))
    f["weiteste"] = max(km) if km else 0
    f["heim"] = any(k <= 50 for k in km)
    f["richtungen"] = richt
    f["nord"] = nord
    f["buchstaben"] = {_buchstabe(o) for o in orte} - {""}
    jahre, monate, pro_jahr, monat_land, dauer, silvester, jz = set(), set(), {}, {}, 0, False, set()
    for b in liste:
        v, e = _datum(b.get("von")), _datum(b.get("bis") or b.get("von"), ende=False)
        if not v:
            continue
        jahre.add(v.year)
        pro_jahr[v.year] = pro_jahr.get(v.year, 0) + 1
        monate.add(v.month)
        monat_land.setdefault((v.year, v.month), set()).add(b.get("land", ""))
        jz.add({12: "Winter", 1: "Winter", 2: "Winter", 3: "Frühling", 4: "Frühling", 5: "Frühling",
                6: "Sommer", 7: "Sommer", 8: "Sommer"}.get(v.month, "Herbst"))
        if e and len(b.get("von", "")) >= 10 and len(b.get("bis", "")) >= 10:
            dauer = max(dauer, (e - v).days + 1)
            silvester = silvester or e.year > v.year
    f.update(jahre=jahre, monate=monate, max_pro_jahr=max(pro_jahr.values()) if pro_jahr else 0,
             doppelschlag=any(len(l - {""}) >= 2 for l in monat_land.values()), dauer=dauer, silvester=silvester,
             sommer=bool(monate & {7, 8}), jahreszeiten=jz, vor2000=any(j < 2000 for j in jahre))
    serien = {}
    for b in liste:
        v = _datum(b.get("von"))
        if v:
            serien.setdefault(serien_schluessel(b), set()).add(v.year)
    tradition = 0
    for js in serien.values():
        js = sorted(js)
        lauf = 1
        for a, b2 in zip(js, js[1:]):
            lauf = lauf + 1 if b2 == a + 1 else 1
            tradition = max(tradition, lauf)
        tradition = max(tradition, 1 if js else 0)
    f["tradition"] = tradition
    f["ausnahme"] = any(b.get("ausnahme") for b in liste)
    f["gruppe"] = max([len(verein["turniere"].get(turnier_schluessel(b), ())) for b in liste] or [0])
    f["pionier"] = sum(1 for o in orte if sid in verein["erst_ort"].get(o, ("", set()))[1])
    f["entdecker"] = sum(1 for l in laender if sid in verein["erst_land"].get(l, ("", set()))[1])
    f["exklusiv"] = sum(1 for o in orte if verein["ort_leute"].get(o) == {sid})
    f["liste"] = liste
    return f


# ------------------------------------------------------------
# Abzeichen: (id, Name, Stufe, Kategorie, Beschreibung, Prüfung -> (erreicht, (stand, ziel) oder None))
# ------------------------------------------------------------
def _zahl(wert, ziel):
    return wert >= ziel, (min(wert, ziel), ziel)


def _menge(menge, ziel):
    return len(menge) >= ziel, (min(len(menge), ziel), ziel)


ABZEICHEN = [
    # Einstieg
    ("erste-reise", "Erste Reise", "bronze", "Einstieg", "Dein erstes Turnier auf Tour", lambda f: (f["orte"] >= 1, None)),
    ("grenzgaenger", "Grenzgänger", "bronze", "Einstieg", "Erstes Open im Ausland", lambda f: (f["ausland"], None)),
    ("heimspiel", "Heimspiel", "bronze", "Einstieg", "Turnier im Umkreis von 50 km um Kirchheim", lambda f: (f["heim"], None)),
    ("ehrenrunde", "Ehrenrunde", "bronze", "Einstieg", "Ein besonderes Turnier (Ausnahme), z. B. Hochschulmeisterschaft",
     lambda f: (f["ausnahme"], None)),
    ("ausflug", "Ausflug", "bronze", "Einstieg", "Erstes Turnier außerhalb Bayerns", lambda f: (f["ausserhalb_bayern"], None)),
    # Orte
    ("orte-5", "5 Orte", "bronze", "Orte sammeln", "In 5 verschiedenen Orten gespielt", lambda f: _zahl(f["orte"], 5)),
    ("orte-10", "10 Orte", "silber", "Orte sammeln", "In 10 verschiedenen Orten gespielt", lambda f: _zahl(f["orte"], 10)),
    ("orte-25", "25 Orte", "gold", "Orte sammeln", "In 25 verschiedenen Orten gespielt", lambda f: _zahl(f["orte"], 25)),
    ("orte-50", "50 Orte", "legendaer", "Orte sammeln", "In 50 verschiedenen Orten gespielt", lambda f: _zahl(f["orte"], 50)),
    ("abc", "ABC-Schütze", "silber", "Orte sammeln", "Orte mit 10 verschiedenen Anfangsbuchstaben",
     lambda f: _menge(f["buchstaben"], 10)),
    ("alphabet", "Alphabet", "legendaer", "Orte sammeln", "Orte von A bis Z (ohne Q, X, Y – 23 Buchstaben)",
     lambda f: _menge(f["buchstaben"] - {"Q", "X", "Y"}, 23)),
    # Länder & Regionen
    ("laender-3", "3 Länder", "bronze", "Länder & Regionen", "In 3 Ländern gespielt", lambda f: _menge(f["laender"], 3)),
    ("laender-5", "5 Länder", "silber", "Länder & Regionen", "In 5 Ländern gespielt", lambda f: _menge(f["laender"], 5)),
    ("laender-10", "10 Länder", "gold", "Länder & Regionen", "In 10 Ländern gespielt", lambda f: _menge(f["laender"], 10)),
    ("laender-20", "20 Länder", "legendaer", "Länder & Regionen", "In 20 Ländern gespielt", lambda f: _menge(f["laender"], 20)),
    ("dach", "DACH", "silber", "Länder & Regionen", "Deutschland, Österreich und Schweiz",
     lambda f: _menge(f["laender"] & {"Deutschland", "Österreich", "Schweiz"}, 3)),
    ("benelux", "Benelux", "gold", "Länder & Regionen", "Belgien, Niederlande und Luxemburg", lambda f: _menge(f["laender"] & BENELUX, 3)),
    ("alpen", "Alpenkönig", "gold", "Länder & Regionen", "4 Alpenländer (ohne Deutschland)", lambda f: _menge(f["laender"] & ALPEN, 4)),
    ("nachbarn", "Rund um Deutschland", "legendaer", "Länder & Regionen", "Alle 9 Nachbarländer Deutschlands",
     lambda f: _menge(f["laender"] & NACHBARN, 9)),
    ("balkan", "Balkan-Tour", "gold", "Länder & Regionen", "3 Balkanländer", lambda f: _menge(f["laender"] & BALKAN, 3)),
    ("wikinger", "Wikinger", "gold", "Länder & Regionen", "Dänemark, Schweden und Norwegen",
     lambda f: _menge(f["laender"] & SKANDINAVIEN, 3)),
    ("iberer", "Iberer", "silber", "Länder & Regionen", "Turnier in Spanien oder Portugal", lambda f: (bool(f["laender"] & IBERIEN), None)),
    ("insulaner", "Insulaner", "silber", "Länder & Regionen", "Turnier auf einer Insel (Malta, Zypern, Mallorca, Großbritannien …)",
     lambda f: (f["insel"], None)),
    ("hauptstadt-3", "Hauptstädter", "silber", "Länder & Regionen", "3 europäische Hauptstädte", lambda f: _menge(f["hauptstaedte"], 3)),
    ("hauptstadt-10", "Hauptstadt-Sammler", "legendaer", "Länder & Regionen", "10 europäische Hauptstädte",
     lambda f: _menge(f["hauptstaedte"], 10)),
    ("bayern", "Bayern-Kenner", "silber", "Länder & Regionen", "5 Orte in Bayern", lambda f: _menge(f["bayern_orte"], 5)),
    ("bundeslaender-5", "Bundesländer", "gold", "Länder & Regionen", "5 verschiedene Bundesländer", lambda f: _menge(f["regionen_de"], 5)),
    ("bundeslaender-16", "Deutschland komplett", "legendaer", "Länder & Regionen", "Alle 16 Bundesländer",
     lambda f: _menge(f["regionen_de"], 16)),
    # Kontinente
    ("weltenbummler", "Weltenbummler", "gold", "Kontinente", "Turnier außerhalb Europas", lambda f: (bool(f["kontinente"] - {"Europa"}), None)),
    ("globetrotter", "Globetrotter", "legendaer", "Kontinente", "Turniere auf 3 Kontinenten", lambda f: _menge(f["kontinente"], 3)),
    ("alle-kontinente", "Zu Hause auf jedem Kontinent", "legendaer", "Kontinente", "Alle 6 bewohnten Kontinente",
     lambda f: _menge(f["kontinente"], 6)),
    # Entfernung
    ("km-300", "300 km", "bronze", "Entfernung", "Turnier mindestens 300 km von Kirchheim", lambda f: _zahl(round(f["weiteste"]), 300)),
    ("km-1000", "1000 km", "silber", "Entfernung", "Turnier mindestens 1000 km von Kirchheim", lambda f: _zahl(round(f["weiteste"]), 1000)),
    ("km-2500", "2500 km", "gold", "Entfernung", "Turnier mindestens 2500 km von Kirchheim", lambda f: _zahl(round(f["weiteste"]), 2500)),
    ("km-8000", "8000 km", "legendaer", "Entfernung", "Turnier mindestens 8000 km von Kirchheim", lambda f: _zahl(round(f["weiteste"]), 8000)),
    ("kompass", "Kompass", "gold", "Entfernung", "Je ein Turnier im Norden, Osten, Süden und Westen (jeweils über 300 km)",
     lambda f: _menge(f["richtungen"], 4)),
    ("nordlicht", "Nordlicht", "legendaer", "Entfernung", "Turnier nördlich des Polarkreises", lambda f: (f["nord"] >= 66.56, None)),
    # Treue
    ("stammgast", "Stammgast", "silber", "Treue", "3-mal am selben Ort", lambda f: _zahl(f["max_gleich"], 3)),
    ("inventar", "Inventar", "gold", "Treue", "10-mal am selben Ort", lambda f: _zahl(f["max_gleich"], 10)),
    ("tradition", "Tradition", "gold", "Treue", "Dasselbe Turnier 5 Jahre in Folge", lambda f: _zahl(f["tradition"], 5)),
    ("dauerbrenner", "Dauerbrenner", "gold", "Treue", "In 10 verschiedenen Jahren auf Tour", lambda f: _menge(f["jahre"], 10)),
    ("veteran", "Veteran", "silber", "Treue", "Ein Turnier vor dem Jahr 2000", lambda f: (f["vor2000"], None)),
    # Kalender
    ("silvester", "Silvester am Brett", "silber", "Kalender", "Turnier über den Jahreswechsel", lambda f: (f["silvester"], None)),
    ("sommerfrische", "Sommerfrische", "bronze", "Kalender", "Turnier im Juli oder August", lambda f: (f["sommer"], None)),
    ("jahreszeiten", "Vier Jahreszeiten", "silber", "Kalender", "Turniere im Frühling, Sommer, Herbst und Winter",
     lambda f: _menge(f["jahreszeiten"], 4)),
    ("ganzjaehrig", "Ganzjährig", "gold", "Kalender", "In allen 12 Monaten gespielt (über alle Jahre)", lambda f: _menge(f["monate"], 12)),
    ("turnierjahr", "Turnierjahr", "gold", "Kalender", "5 Turniere in einem Kalenderjahr", lambda f: _zahl(f["max_pro_jahr"], 5)),
    ("doppelschlag", "Doppelschlag", "silber", "Kalender", "Zwei Turniere in zwei Ländern im selben Monat",
     lambda f: (f["doppelschlag"], None)),
    ("marathon", "Marathon", "silber", "Kalender", "Ein Turnier über 9 oder mehr Tage", lambda f: _zahl(f["dauer"], 9)),
    # Verein
    ("reisegruppe", "Reisegruppe", "bronze", "Mit dem Verein", "Mit mindestens 2 weiteren AFKlern beim selben Turnier",
     lambda f: _zahl(f["gruppe"], 3)),
    ("mannschaftsausflug", "Mannschaftsausflug", "silber", "Mit dem Verein", "Mit 5 oder mehr AFKlern beim selben Turnier",
     lambda f: _zahl(f["gruppe"], 5)),
    ("pionier", "Pionier", "silber", "Mit dem Verein", "Als erster AFKler in einer Stadt", lambda f: _zahl(f["pionier"], 1)),
    ("entdecker", "Entdecker", "gold", "Mit dem Verein", "Als erster AFKler in einem Land", lambda f: _zahl(f["entdecker"], 1)),
    ("fremdenfuehrer", "Fremdenführer", "silber", "Mit dem Verein", "3 Orte, an denen sonst noch kein AFKler war",
     lambda f: _zahl(f["exklusiv"], 3)),
]


STANDARD_KLASSIKER = [
    {"name": "Grenke-Pilger", "stufe": "silber", "text": "Grenke Open in Karlsruhe", "ort": "Karlsruhe", "turnier": "Grenke"},
    {"name": "Tegernseer", "stufe": "bronze", "text": "Ein Turnier am Tegernsee", "ort": "Tegernsee"},
]


def klassiker(konf):
    """Eigene Abzeichen aus einstellungen.json ("klassiker": [{"name", "stufe", "text", "ort", "turnier"}]).
    Fehlt der Eintrag, gelten STANDARD_KLASSIKER."""
    out = []
    for i, k in enumerate(konf.get("klassiker", STANDARD_KLASSIKER)):
        ort, turnier = (k.get("ort") or "").lower(), (k.get("turnier") or "").lower()

        def pruef(f, ort=ort, turnier=turnier):
            return any((not ort or ort in (b.get("ort", "") + " " + b.get("stadt", "")).lower())
                       and (not turnier or turnier in (b.get("turnier") or "").lower()) for b in f["liste"]), None
        out.append((f"klassiker-{i}", k.get("name", "Klassiker"), k.get("stufe", "silber"), "Klassiker",
                    k.get("text", ""), pruef))
    return out


def alle(konf):
    return ABZEICHEN + klassiker(konf)


def auswerten(spieler_listen, alle_besuche, heimat, konf):
    """-> (abzeichen_infos, pro_spieler) ; pro_spieler[sid] = {"erreicht": [...ids], "fortschritt": {id: (a, z)}, "punkte": n}"""
    verein = verein_merkmale(alle_besuche)
    liste_abz = alle(konf)
    pro = {}
    for sid, liste in spieler_listen.items():
        f = merkmale(sid, liste, verein, heimat, konf)
        erreicht, fort = [], {}
        for aid, _, stufe, _, _, pruef in liste_abz:
            ok, fs = pruef(f)
            if ok:
                erreicht.append(aid)
            elif fs:
                fort[aid] = fs
        pro[sid] = {"erreicht": erreicht, "fortschritt": fort,
                    "punkte": sum(STUFEN[s][1] for aid, _, s, _, _, _ in liste_abz if aid in erreicht)}
    n = max(len(pro), 1)
    infos = []
    for aid, name, stufe, kat, text, _ in liste_abz:
        wer = [sid for sid in pro if aid in pro[sid]["erreicht"]]
        infos.append({"id": aid, "name": name, "stufe": stufe, "stufe_name": STUFEN[stufe][0], "punkte": STUFEN[stufe][1],
                      "kat": kat, "text": text, "wer": wer, "anteil": round(100 * len(wer) / n)})
    return infos, pro
