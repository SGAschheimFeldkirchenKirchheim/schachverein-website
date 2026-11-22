"""
AFK on Tour – Anträge prüfen und Turniere eintragen.

  py turnierorte_pruefen.py          offene Anträge aus turnierorte/antraege/ abarbeiten
  py turnierorte_pruefen.py --neu    selbst ein Turnier eintragen (z. B. eigene alte Opens)
  py turnierorte_pruefen.py --verwalten   Einträge eines Spielers löschen, ausblenden oder korrigieren

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
            region = a.get("state", "")
            if not region and a.get("ISO3166-2-lvl4"):     # Stadtstaaten (Berlin, Hamburg …): Stadt = Bundesland
                region = a.get("city") or a.get("town") or stadt
            return {"stadt": stadt, "land": a.get("country", ""), "region": region,
                    "lat": float(treffer[0]["lat"]), "lon": float(treffer[0]["lon"])}
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


def offene_dateien():
    """Offene Anträge, Rückfragen und auf der Website angenommene (falls der Build sie noch nicht eingetragen hat)."""
    return [p for unter in ("", "rueckfrage", "angenommen")
            for p in sorted(glob.glob(os.path.join(to.ORDNER, "antraege", unter, "*.json")))]


def frage(text, erlaubt):
    while True:
        a = input(text).strip().lower()
        if a in erlaubt:
            return a


def auswerten(a):
    """chess-results-Daten und Ort zu einem Antrag holen -> (info, ort, gefunden)."""
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
    return info, ort, gefunden


def eintrag_anlegen(a, info, ort, spieler, besuche):
    sid = to.spieler_id(a.get("name", ""))
    if sid not in spieler:
        spieler[sid] = {"name": a.get("name", "").strip(), "anzeige": to.anzeige_name(a.get("name", "").strip())}
    besuche.append({
        "spieler": sid, "turnier": info.get("turnier", ""), "stadt": ort["stadt"], "land": ort["land"],
        "region": ort.get("region", ""),
        "lat": round(ort["lat"], 5), "lon": round(ort["lon"], 5), "von": info.get("von", ""), "bis": info.get("bis", ""),
        "link": info.get("link", ""), "bedenkzeit": info.get("bedenkzeit", ""),
        "ausnahme": (a.get("begruendung") or "ja") if a.get("ausnahme") else "",
        "bestaetigt": datetime.date.today().isoformat(),
    })


def doppelt_eingetragen(sid, info, besuche):
    return any(b["spieler"] == sid and ((info.get("link") and b.get("link") == info.get("link")) or
               (b.get("turnier") == info.get("turnier") and b.get("von", "")[:7] == info.get("von", "")[:7])) for b in besuche)


def aehnliches_profil(name, spieler):
    """Neues Profil, aber es gibt schon jemanden mit gleichem Nachnamen bzw. gleichem Vornamen + Initial?"""
    teile = norm(name).split()
    if not teile:
        return ""
    for p in spieler.values():
        t = norm(p.get("name", "")).split()
        if t and ((len(teile) > 1 and len(t) > 1 and t[-1] == teile[-1]) or t[0] == teile[0] and t[-1][:1] == teile[-1][:1]):
            return p.get("name", "")
    return ""


def antrag_pruefen(a, spieler, besuche, konf):
    """Zeigt den Antrag mit Prüfergebnis und fragt nach. Gibt 'j', 'n' oder 's' zurück."""
    if a.get("rueckfrage"):
        print(f"\n  RÜCKFRAGE: {a['rueckfrage']}")
    if a.get("angenommen_von"):
        print(f"  (auf der Website angenommen von {a['angenommen_von']})")
    info, ort, gefunden = auswerten(a)
    while True:
        gruppe = to.ort_gruppe(ort["stadt"], konf.get("ort_gruppen")) if ort else "?"
        sid = to.spieler_id(a.get("name", ""))
        doppelt = doppelt_eingetragen(sid, info, besuche)
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
            eintrag_anlegen(a, info, ort, spieler, besuche)
        return w


# ------------------------------------------------------------
# Auf der Website angenommene Anträge (Verwaltung -> Turniere) automatisch eintragen.
# Läuft im GitHub-Build (build_site.py). Unklare Fälle landen in antraege/rueckfrage/ und
# erscheinen in der Verwaltung und in  py afk_on_tour.py  [2].
# ------------------------------------------------------------
def angenommene_eintragen():
    dateien = sorted(glob.glob(os.path.join(to.ORDNER, "antraege", "angenommen", "*.json")))
    if not dateien:
        return 0
    alt_cache, tk._nur_cache = tk._nur_cache, False          # hier immer aus dem Netz holen
    spieler, besuche, n = to.spieler_laden(), to.besuche_laden(), 0
    try:
        for pfad in dateien:
            try:
                with open(pfad, encoding="utf-8") as f:
                    a = json.load(f)
            except (OSError, ValueError):
                continue
            info, ort, gefunden = auswerten(a)
            sid = to.spieler_id(a.get("name", ""))
            grund = ""
            if not ort:
                grund = "Ort nicht gefunden"
            elif doppelt_eingetragen(sid, info, besuche):
                grund = "Turnier ist für den Spieler schon eingetragen"
            elif sid not in spieler and aehnliches_profil(a.get("name", ""), spieler):
                grund = f"Neues Profil, aber es gibt schon „{aehnliches_profil(a.get('name', ''), spieler)}“ – dieselbe Person?"
            elif sid in spieler and spieler[sid].get("name", "").strip().lower() != a.get("name", "").strip().lower():
                grund = f"Kürzel gehört schon zu „{spieler[sid].get('name')}“ – dieselbe Person?"
            if grund:
                a["rueckfrage"] = grund
                ziel = os.path.join(to.ORDNER, "antraege", "rueckfrage", os.path.basename(pfad))
                to._speichere(ziel, a)
                print(f"AFK on Tour: Rückfrage zu {a.get('name')}: {grund}")
            else:
                eintrag_anlegen(a, info, ort, spieler, besuche)
                n += 1
                print(f"AFK on Tour: eingetragen – {a.get('name')}, {info.get('turnier') or ort['stadt']}"
                      + ("" if not info.get("link") or gefunden else " (Name nicht in der chess-results-Teilnehmerliste)"))
            os.remove(pfad)
    finally:
        tk._nur_cache = alt_cache
    if n:
        to._speichere(os.path.join(to.ORDNER, "spieler.json"), spieler)
        to._speichere(os.path.join(to.ORDNER, "besuche.json"), besuche)
    return n


# ------------------------------------------------------------
# Änderungen aus der Website-Verwaltung (Reiter Turniere -> Alle Einträge).
# Das Apps Script legt antraege/aenderungen/<Zeit>.json an, der GitHub-Build wendet sie hier an.
# Was nicht klappt (Ort nicht gefunden, Eintrag weg), steht in antraege/aenderungen_fehler.json.
# ------------------------------------------------------------
AENDERUNG_FELDER = ("spieler", "turnier", "von", "link", "stadt")


def _passt(b, key):
    return all((b.get(f) or "") == (key.get(f) or "") for f in AENDERUNG_FELDER)


def aenderungen_anwenden():
    ordner = os.path.join(to.ORDNER, "antraege", "aenderungen")
    dateien = sorted(glob.glob(os.path.join(ordner, "*.json")))
    if not dateien:
        return 0
    alt_cache, tk._nur_cache = tk._nur_cache, False
    spieler, besuche, n = to.spieler_laden(), to.besuche_laden(), 0
    fehler_pfad = os.path.join(to.ORDNER, "antraege", "aenderungen_fehler.json")
    fehler = to._lade(fehler_pfad, [])
    try:
        for pfad in dateien:
            try:
                with open(pfad, encoding="utf-8") as f:
                    a = json.load(f)
            except (OSError, ValueError):
                os.remove(pfad)
                continue
            art, w, sid = a.get("aktion", ""), a.get("werte") or {}, a.get("sid", "")
            text = ""
            if art in ("profil_loeschen", "profil_ausblenden", "profil_einblenden"):
                if sid not in spieler:
                    text = "Profil gibt es nicht mehr"
                elif art == "profil_loeschen":
                    besuche[:] = [b for b in besuche if b["spieler"] != sid]
                    spieler.pop(sid)
                elif art == "profil_ausblenden":
                    spieler[sid]["ausgeblendet"] = True
                else:
                    spieler[sid].pop("ausgeblendet", None)
            else:
                b = next((x for x in besuche if _passt(x, a.get("key") or {})), None)
                if b is None:
                    text = "Eintrag nicht gefunden (inzwischen geändert?)"
                elif art == "loeschen":
                    besuche.remove(b)
                elif art in ("ausblenden", "einblenden"):
                    if art == "ausblenden":
                        b["ausgeblendet"] = True
                    else:
                        b.pop("ausgeblendet", None)
                elif art == "aendern":
                    if "link" in w and w["link"] != b.get("link", ""):
                        tnr = re.search(r"tnr(\d{5,8})", w["link"] or "")
                        b["link"] = tk.CR_LINK.format(tnr=tnr.group(1)) if tnr else (w["link"] or "")
                        if tnr and w.get("cr_holen"):
                            seite = tk._hole(tk.CR_DETAIL.format(tnr=tnr.group(1)))
                            d = tk.cr_details(tnr.group(1), seite) if seite else {}
                            if d.get("name"):
                                b["turnier"], b["von"], b["bis"] = d["name"], d.get("von") or b.get("von", ""), d.get("bis") or b.get("bis", "")
                            else:
                                text = "chess-results nicht erreichbar – nur der Link wurde geändert"
                    if w.get("turnier"):
                        b["turnier"] = w["turnier"]
                    if w.get("datum"):
                        b["von"] = b["bis"] = w["datum"]
                    if w.get("bedenkzeit") in ("klassisch", "schnell", "blitz"):
                        b["bedenkzeit"] = w["bedenkzeit"]
                    if w.get("ort"):
                        ort = ort_suchen(w["ort"])
                        if ort:
                            b.update(stadt=ort["stadt"], land=ort["land"], region=ort.get("region", ""),
                                     lat=round(ort["lat"], 5), lon=round(ort["lon"], 5))
                        else:
                            text = (text + "; " if text else "") + f"Ort „{w['ort']}“ nicht gefunden – Rest übernommen"
                else:
                    text = "Unbekannte Aktion"
            if text:
                fehler.append({"zeit": a.get("zeit", ""), "wer": a.get("wer", ""), "was": a.get("beschreibung", art), "fehler": text})
                print(f"AFK on Tour: Änderung „{a.get('beschreibung', art)}“: {text}")
            else:
                print(f"AFK on Tour: Änderung übernommen – {a.get('beschreibung', art)}")
            n += 1
            os.remove(pfad)
    finally:
        tk._nur_cache = alt_cache
    to._speichere(os.path.join(to.ORDNER, "spieler.json"), spieler)
    to._speichere(os.path.join(to.ORDNER, "besuche.json"), besuche)
    if fehler:
        to._speichere(fehler_pfad, fehler[-20:])
    return n


def verwalten(spieler, besuche, konf):
    """Einträge eines Spielers anzeigen und löschen / aus- und einblenden / Link, Ort oder Datum ändern."""
    geaendert = False
    while True:
        ids = sorted(spieler, key=lambda k: spieler[k].get("name", k).lower())
        if not ids:
            print("Noch keine Profile.")
            return geaendert
        print("\nProfile:")
        for i, sid in enumerate(ids, 1):
            n = sum(1 for b in besuche if b["spieler"] == sid)
            print(f"  {i:2d}  {spieler[sid].get('name', sid)}  ({n} {'Eintrag' if n == 1 else 'Einträge'})")
        w = input("Nummer des Spielers (leer = fertig): ").strip()
        if not w:
            return geaendert
        if not w.isdigit() or not 1 <= int(w) <= len(ids):
            continue
        sid = ids[int(w) - 1]
        while True:
            eigene = [b for b in besuche if b["spieler"] == sid]
            eigene.sort(key=lambda b: b.get("von", ""), reverse=True)
            print(f"\n{spieler[sid].get('name', sid)}:")
            for i, b in enumerate(eigene, 1):
                aus = "  [AUSGEBLENDET]" if b.get("ausgeblendet") else ""
                print(f"  {i:2d}  {b.get('von', '')[:7]}  {b.get('stadt', '')}  –  {b.get('turnier', '') or '-'}{aus}")
                if b.get("link"):
                    print(f"        {b['link']}")
            print("  Befehle: l3 = Nr. 3 löschen · a3 = aus-/einblenden · k3 = Link ändern · o3 = Ort ändern · "
                  "d3 = Datum ändern · p = ganzes Profil löschen · leer = zurück")
            befehl = input("  > ").strip().lower()
            if not befehl:
                break
            if befehl == "p":
                if input(f"  Profil {spieler[sid].get('name', sid)} mit allen Einträgen löschen? (ja/nein) ").strip().lower() == "ja":
                    besuche[:] = [b for b in besuche if b["spieler"] != sid]
                    spieler.pop(sid, None)
                    geaendert = True
                    print("  -> Profil gelöscht")
                    break
                continue
            m = re.fullmatch(r"([lakod])\s*(\d+)", befehl)
            if not m or not 1 <= int(m.group(2)) <= len(eigene):
                print("  ?")
                continue
            b = eigene[int(m.group(2)) - 1]
            art = m.group(1)
            if art == "l":
                if input(f"  '{b.get('turnier') or b.get('stadt')}' wirklich löschen? (j/n) ").strip().lower() == "j":
                    besuche.remove(b)
                    geaendert = True
            elif art == "a":
                b["ausgeblendet"] = not b.get("ausgeblendet")
                if not b["ausgeblendet"]:
                    b.pop("ausgeblendet")
                geaendert = True
            elif art == "k":
                link = input("  Neuer chess-results-Link (leer = Link entfernen): ").strip()
                tnr = re.search(r"tnr(\d{5,8})", link)
                b["link"] = tk.CR_LINK.format(tnr=tnr.group(1)) if tnr else link
                if tnr and input("  Turniername/Datum von chess-results übernehmen? (j/n) ").strip().lower() == "j":
                    seite = tk._hole(tk.CR_DETAIL.format(tnr=tnr.group(1)))
                    d = tk.cr_details(tnr.group(1), seite) if seite else {}
                    if d.get("name"):
                        b["turnier"], b["von"], b["bis"] = d["name"], d.get("von") or b.get("von", ""), d.get("bis") or b.get("bis", "")
                        print(f"  -> {b['turnier']}, {b['von']}")
                    else:
                        print("  chess-results nicht erreichbar – nur der Link wurde geändert")
                geaendert = True
            elif art == "o":
                ort = ort_suchen(input("  Stadt, Land: ").strip())
                if ort:
                    b.update(stadt=ort["stadt"], land=ort["land"], region=ort.get("region", ""),
                             lat=round(ort["lat"], 5), lon=round(ort["lon"], 5))
                    print(f"  -> {ort['stadt']}, {ort['land']}")
                    geaendert = True
                else:
                    print("  Ort nicht gefunden")
            elif art == "d":
                b["von"] = b["bis"] = input("  Datum (JJJJ-MM oder JJJJ-MM-TT): ").strip()
                geaendert = True


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    konf = to.einstellungen()
    spieler = to.spieler_laden()
    besuche = to.besuche_laden()
    geaendert = False
    if "--verwalten" in sys.argv:
        geaendert = verwalten(spieler, besuche, konf)
    elif "--neu" in sys.argv:
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
        dateien = offene_dateien()
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
