"""
AFK on Tour – Anträge prüfen und Turniere eintragen.

  py turnierorte_pruefen.py          offene Anträge aus turnierorte/antraege/ abarbeiten
  py turnierorte_pruefen.py --neu    selbst ein Turnier eintragen (z. B. eigene alte Opens)

Vorher und nachher "Alles aktualisieren" drücken.
Bei einem chess-results-Link holt das Skript Turniername, Datum, Ort und Bedenkzeit selbst
und schaut nach, ob der Name in der Teilnehmerliste steht.
"""
import datetime
import glob
import json
import os
import re
import sys
import unicodedata
import urllib.parse

import turnierkalender as tk
import turnierorte as to

GEOCODER = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&addressdetails=1"
            "&accept-language=de&q={q}")


def norm(text):
    t = unicodedata.normalize("NFKD", (text or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]+", " ", t)


def ort_suchen(text):
    """'Gmund am Tegernsee, Deutschland' -> {'stadt': 'Gmund am Tegernsee', 'land': 'Deutschland', 'lat':…, 'lon':…}"""
    if not text.strip():
        return None
    versuche = [text]
    plz = re.search(r"\b(\d{4,5})[\s-]+([A-ZÄÖÜ][\wäöüßÄÖÜ.\- ]*?)\s*(?:,|$|\()", text)
    if plz:
        versuche.insert(0, f"{plz.group(1)} {plz.group(2)}")
    for v in versuche:
        antwort = tk._hole(GEOCODER.format(q=urllib.parse.quote(v)))
        try:
            treffer = json.loads(antwort) if antwort else []
        except ValueError:
            treffer = []
        if treffer:
            a = treffer[0].get("address", {})
            stadt = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or a.get("county") or v
            return {"stadt": stadt, "land": a.get("country", ""), "lat": float(treffer[0]["lat"]), "lon": float(treffer[0]["lon"])}
    return None


def name_in_teilnehmern(name, seite):
    teile = [t for t in norm(name).split() if len(t) > 1]
    if not seite or not teile:
        return False
    if tk.BeautifulSoup:
        zeilen = [norm(tr.get_text(" ", strip=True)) for tr in tk.BeautifulSoup(seite, "html.parser").find_all("tr")]
    else:
        zeilen = norm(seite).splitlines()
    return any(all(re.search(r"\b" + t + r"\b", z) for t in teile) for z in zeilen)


def frage(text, erlaubt):
    while True:
        a = input(text).strip().lower()
        if a in erlaubt:
            return a


def antrag_pruefen(a, spieler, besuche, konf):
    """Zeigt den Antrag mit Prüfergebnis und fragt nach. Gibt 'j', 'n' oder 's' zurück."""
    info = dict(a)
    gefunden = None
    tnr = re.search(r"tnr(\d{5,8})", a.get("link", "") or "")
    if tnr:
        tnr = tnr.group(1)
        details = tk._hole(tk.CR_DETAIL.format(tnr=tnr))
        d = tk.cr_details(tnr, details) if details else {}
        info["turnier"] = a.get("turnier") or d.get("name", "")
        info["von"] = d.get("von") or ""
        info["bis"] = d.get("bis") or ""
        info["bedenkzeit"] = d.get("bedenkzeit") or a.get("bedenkzeit", "")
        info["cr_ort"] = ", ".join(x for x in (d.get("ort", ""), d.get("land", "")) if x)
        info["link"] = tk.CR_LINK.format(tnr=tnr)
        gefunden = name_in_teilnehmern(a.get("name", ""), tk._hole(tk.CR_START.format(tnr=tnr)))
    if not info.get("von") and a.get("monat"):
        info["von"] = info["bis"] = a["monat"]
    suchtext = ", ".join(x for x in (a.get("stadt", ""), a.get("land", "")) if x) or info.get("cr_ort", "")
    ort = ort_suchen(suchtext) if suchtext else None
    while True:
        gruppe = to.ort_gruppe(ort["stadt"], konf.get("ort_gruppen")) if ort else "?"
        sid = to.spieler_id(a.get("name", ""))
        doppelt = any(b["spieler"] == sid and ((info.get("link") and b.get("link") == info.get("link")) or
                      (b.get("turnier") == info.get("turnier") and b.get("von", "")[:7] == info.get("von", "")[:7])) for b in besuche)
        schon_ort = ort and any(b["spieler"] == sid and to.ort_gruppe(b.get("stadt", ""), konf.get("ort_gruppen")) == gruppe for b in besuche)
        print("\n" + "=" * 70)
        print(f"  Spieler:     {a.get('name')}" + ("" if sid in spieler else "   (NEUES PROFIL)"))
        print(f"  Turnier:     {info.get('turnier') or '-'}")
        print(f"  Datum:       {info.get('von') or '-'}" + (f" bis {info['bis']}" if info.get("bis") and info["bis"] != info.get("von") else ""))
        print(f"  Ort:         {ort['stadt'] + ', ' + ort['land'] if ort else 'NICHT GEFUNDEN'}"
              + (f"  -> zählt als '{gruppe}'" if ort and gruppe != ort["stadt"] else ""))
        print(f"  Bedenkzeit:  {info.get('bedenkzeit') or '-'}")
        if a.get("ausnahme"):
            print(f"  AUSNAHME:    {a.get('begruendung') or '(keine Begründung)'}")
        if info.get("link"):
            print(f"  Link:        {info['link']}")
            print(f"  chess-results: {'Name in der Teilnehmerliste GEFUNDEN' if gefunden else 'Name NICHT in der Teilnehmerliste'}")
        else:
            print("  chess-results: kein Link -> bitte selbst prüfen")
        if info.get("bedenkzeit") and info["bedenkzeit"] != "klassisch" and not a.get("ausnahme"):
            print("  ACHTUNG: nicht klassisch und keine Ausnahme beantragt")
        if doppelt:
            print("  ACHTUNG: dieses Turnier ist für den Spieler schon eingetragen")
        elif schon_ort:
            print(f"  Hinweis: {gruppe} hat der Spieler schon – zählt nicht als neuer Ort (wird trotzdem gelistet)")
        w = frage("  [j] bestätigen  [n] ablehnen  [s] später  [o] Ort ändern  [d] Datum ändern > ", ("j", "n", "s", "o", "d"))
        if w == "o":
            neu = input("  Stadt, Land: ").strip()
            ort = ort_suchen(neu) or ort
            continue
        if w == "d":
            info["von"] = info["bis"] = input("  Datum (JJJJ-MM oder JJJJ-MM-TT): ").strip()
            continue
        if w == "j" and not ort:
            print("  Ohne Ort geht es nicht – bitte [o] wählen.")
            continue
        if w == "j":
            if sid not in spieler:
                spieler[sid] = {"name": a.get("name", "").strip(), "anzeige": to.anzeige_name(a.get("name", "").strip())}
            besuche.append({
                "spieler": sid, "turnier": info.get("turnier", ""), "stadt": ort["stadt"], "land": ort["land"],
                "lat": round(ort["lat"], 5), "lon": round(ort["lon"], 5), "von": info.get("von", ""), "bis": info.get("bis", ""),
                "link": info.get("link", ""), "bedenkzeit": info.get("bedenkzeit", ""),
                "ausnahme": (a.get("begruendung") or "ja") if a.get("ausnahme") else "",
                "bestaetigt": datetime.date.today().isoformat(),
            })
        return w


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    konf = to.einstellungen()
    spieler = to.spieler_laden()
    besuche = to.besuche_laden()
    geaendert = False
    if "--neu" in sys.argv:
        while True:
            print("\nNeues Turnier eintragen (leer lassen = fertig)")
            name = input("  Name (Vor- und Nachname): ").strip()
            if not name:
                break
            a = {"name": name, "link": input("  chess-results-Link (oder leer): ").strip()}
            if not a["link"]:
                a.update(turnier=input("  Turnier: ").strip(), stadt=input("  Stadt: ").strip(),
                         land=input("  Land [Deutschland]: ").strip() or "Deutschland",
                         monat=input("  Monat (JJJJ-MM): ").strip(),
                         bedenkzeit=input("  Bedenkzeit [klassisch]: ").strip() or "klassisch")
            a["ausnahme"] = input("  Ausnahme? (Begründung oder leer): ").strip()
            a["begruendung"] = a["ausnahme"]
            a["ausnahme"] = bool(a["ausnahme"])
            if antrag_pruefen(a, spieler, besuche, konf) == "j":
                geaendert = True
    else:
        dateien = sorted(glob.glob(os.path.join(to.ORDNER, "antraege", "*.json")))
        if not dateien:
            print("Keine offenen Anträge. (Vorher 'Alles aktualisieren' gedrückt?)")
        for pfad in dateien:
            with open(pfad, encoding="utf-8") as f:
                a = json.load(f)
            w = antrag_pruefen(a, spieler, besuche, konf)
            if w in ("j", "n"):
                os.remove(pfad)
                geaendert = True
                print("  -> bestätigt" if w == "j" else "  -> abgelehnt und gelöscht")
    if geaendert:
        to._speichere(os.path.join(to.ORDNER, "spieler.json"), spieler)
        to._speichere(os.path.join(to.ORDNER, "besuche.json"), besuche)
        print("\nGespeichert. Jetzt 'Alles aktualisieren' drücken, dann ist es online.")


if __name__ == "__main__":
    main()
