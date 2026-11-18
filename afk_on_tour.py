"""
AFK on Tour – alles an einem Ort.

Starten: im Schach-Ordner  py afk_on_tour.py   (wie update_all.py)
         oder im Ordner schachverein-website:  py afk_on_tour.py

Menü:
  [1] Alles aktualisieren   (holt neue Anträge, lädt Änderungen hoch – wie "Alles aktualisieren.bat")
  [2] Anträge prüfen        (neue Anträge vom Website-Formular bestätigen/ablehnen)
  [3] Bearbeiten            (Profile und Turniere ändern, ausblenden, löschen, zusammenführen)
  [4] Turnier eintragen     (selbst eintragen, z. B. alte Opens)
  [0] Beenden
Nach Änderungen fragt das Programm beim Beenden, ob es gleich hochladen soll.
"""
import glob
import json
import os
import re
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HIER)
sys.path.insert(0, HIER)

import turnierkalender as tk            # noqa: E402
import turnierorte as to                # noqa: E402
import turnierorte_pruefen as tp        # noqa: E402

UPDATE_ALL = os.path.join(os.path.dirname(HIER), "update_all.py")
BEDENKZEITEN = ("klassisch", "schnell", "blitz")


# ------------------------------------------------------------
# Daten
# ------------------------------------------------------------
class Daten:
    def __init__(self):
        self.laden()

    def laden(self):
        self.konf = to.einstellungen()
        self.spieler = to.spieler_laden()
        self.besuche = to.besuche_laden()
        self.geaendert = False

    def speichern(self):
        to._speichere(os.path.join(to.ORDNER, "spieler.json"), self.spieler)
        to._speichere(os.path.join(to.ORDNER, "besuche.json"), self.besuche)
        self.geaendert = True
        print("  (gespeichert)")

    def von(self, sid):
        return sorted((b for b in self.besuche if b["spieler"] == sid), key=lambda b: b.get("von", ""), reverse=True)


def eingabe(text, standard=""):
    try:
        w = input(f"{text}{f' [{standard}]' if standard else ''}: ").strip()
    except EOFError:
        return standard
    return w or standard


def ja(text):
    return eingabe(f"{text} (j/n)").lower().startswith("j")


def wahl(text, anzahl):
    """Nummer 1..anzahl oder None."""
    w = eingabe(text)
    return int(w) if w.isdigit() and 1 <= int(w) <= anzahl else None


def titel(text):
    print("\n" + "=" * 60 + f"\n  {text}\n" + "=" * 60)


# ------------------------------------------------------------
# [1] Alles aktualisieren
# ------------------------------------------------------------
def aktualisieren(d, schnell=False):
    """schnell = nur Website holen/hochladen (ohne die anderen Programme), dauert Sekunden."""
    if not os.path.exists(UPDATE_ALL):
        print(f"update_all.py nicht gefunden ({UPDATE_ALL}).")
        return
    titel("Website hochladen" if schnell else "Alles aktualisieren")
    subprocess.call([sys.executable, UPDATE_ALL] + (["website"] if schnell else []), cwd=os.path.dirname(UPDATE_ALL))
    d.laden()          # neue Anträge / Änderungen vom anderen Rechner einlesen


# ------------------------------------------------------------
# [2] Anträge prüfen
# ------------------------------------------------------------
def antraege(d):
    dateien = sorted(glob.glob(os.path.join(to.ORDNER, "antraege", "*.json")))
    titel(f"Anträge prüfen ({len(dateien)} offen)")
    if not dateien:
        print("Keine offenen Anträge. Tipp: erst [1] Alles aktualisieren, dann kommen neue Anträge an.")
        return
    for pfad in dateien:
        with open(pfad, encoding="utf-8") as f:
            a = json.load(f)
        w = tp.antrag_pruefen(a, d.spieler, d.besuche, d.konf)
        if w in ("j", "n"):
            os.remove(pfad)
            d.speichern()
            print("  -> bestätigt" if w == "j" else "  -> abgelehnt und gelöscht")


# ------------------------------------------------------------
# [4] Turnier eintragen
# ------------------------------------------------------------
def eintragen(d, name=""):
    titel("Turnier eintragen")
    print("Tipp: Mit chess-results-Link werden Turnier, Datum, Ort und Bedenkzeit automatisch geholt.")
    while True:
        name = eingabe("Vor- und Nachname (leer = zurück)", name)
        if not name:
            return
        if len(name.split()) < 2 and not any(s.get("name") == name for s in d.spieler.values()):
            print("  Bitte Vor- UND Nachname eingeben, sonst entsteht ein zweites Profil.")
            name = ""
            continue
        a = {"name": name, "link": eingabe("chess-results-Link (oder leer)")}
        if not a["link"]:
            a.update(turnier=eingabe("Turnier"), stadt=eingabe("Stadt"), land=eingabe("Land", "Deutschland"),
                     monat=eingabe("Monat (JJJJ-MM)"), bedenkzeit=eingabe("Bedenkzeit (klassisch/schnell/blitz)", "klassisch"))
        grund = eingabe("Ausnahme? Begründung (leer = keine)")
        a["ausnahme"], a["begruendung"] = bool(grund), grund
        if tp.antrag_pruefen(a, d.spieler, d.besuche, d.konf) == "j":
            d.speichern()
        if not ja("Noch ein Turnier für " + name):
            return


# ------------------------------------------------------------
# [3] Bearbeiten
# ------------------------------------------------------------
def profil_waehlen(d, text="Profil wählen"):
    ids = sorted(d.spieler, key=lambda k: d.spieler[k].get("name", k).lower())
    if not ids:
        print("Noch keine Profile.")
        return None
    for i, sid in enumerate(ids, 1):
        n = len(d.von(sid))
        aus = sum(1 for b in d.von(sid) if b.get("ausgeblendet"))
        print(f"  {i:2d}  {d.spieler[sid].get('name', sid):28s} {n} {'Turnier' if n == 1 else 'Turniere'}"
              + (f" ({aus} ausgeblendet)" if aus else ""))
    n = wahl(f"{text} (Nummer, leer = zurück)", len(ids))
    return ids[n - 1] if n else None


def bearbeiten(d):
    while True:
        titel("Bearbeiten – Profile")
        sid = profil_waehlen(d)
        if not sid:
            return
        profil_menue(d, sid)


def profil_menue(d, sid):
    while sid in d.spieler:
        p = d.spieler[sid]
        liste = d.von(sid)
        titel(f"{p.get('name', sid)}   (angezeigt als „{p.get('anzeige', '')}“)")
        for i, b in enumerate(liste, 1):
            aus = "  [AUSGEBLENDET]" if b.get("ausgeblendet") else ""
            print(f"  {i:2d}  {b.get('von', '')[:10]:10s}  {b.get('stadt', '')}, {b.get('land', '')}  –  {b.get('turnier') or '-'}{aus}")
        print("\n  [Nummer] Turnier bearbeiten   [t] Turnier hinzufügen\n"
              "  [n] Name ändern   [a] Anzeigename ändern   [z] mit anderem Profil zusammenführen\n"
              "  [x] Profil löschen   [leer] zurück")
        w = eingabe("Auswahl").lower()
        if not w:
            return
        if w.isdigit() and 1 <= int(w) <= len(liste):
            turnier_menue(d, liste[int(w) - 1])
        elif w == "t":
            eintragen(d, p.get("name", ""))
        elif w == "n":
            neu = eingabe("Neuer Vor- und Nachname", p.get("name", ""))
            if neu and neu != p.get("name"):
                nid = to.spieler_id(neu)
                if nid != sid and nid in d.spieler:
                    print(f"  Es gibt schon ein Profil {d.spieler[nid].get('name')} – dafür [z] zusammenführen nehmen.")
                    continue
                p["name"] = neu
                if ja(f"Anzeigename auf „{to.anzeige_name(neu)}“ setzen"):
                    p["anzeige"] = to.anzeige_name(neu)
                if nid != sid:                       # ID folgt dem Namen
                    d.spieler[nid] = d.spieler.pop(sid)
                    for b in d.besuche:
                        if b["spieler"] == sid:
                            b["spieler"] = nid
                    sid = nid
                d.speichern()
        elif w == "a":
            p["anzeige"] = eingabe("Anzeigename auf der Website (z. B. Korbinian R.)", p.get("anzeige", ""))
            d.speichern()
        elif w == "z":
            print("Mit welchem Profil zusammenführen? Die Turniere von dort kommen hierher, das andere Profil wird gelöscht.")
            andere = profil_waehlen(d, "Anderes Profil")
            if andere == sid:
                print("  Das ist dasselbe Profil.")
            elif andere and ja(f"„{d.spieler[andere].get('name')}“ in „{p.get('name')}“ übernehmen"):
                for b in d.besuche:
                    if b["spieler"] == andere:
                        b["spieler"] = sid
                d.spieler.pop(andere)
                d.speichern()
        elif w == "x":
            if eingabe(f"Profil {p.get('name')} mit {len(liste)} Turnieren löschen? Zum Bestätigen 'ja' tippen").lower() == "ja":
                d.besuche[:] = [b for b in d.besuche if b["spieler"] != sid]
                d.spieler.pop(sid)
                d.speichern()
                return


def turnier_menue(d, b):
    while b in d.besuche:
        titel(b.get("turnier") or "Turnier")
        felder = [("Turnier", "turnier"), ("Datum von", "von"), ("Datum bis", "bis"), ("Stadt", "stadt"), ("Land", "land"),
                  ("Link", "link"), ("Bedenkzeit", "bedenkzeit"), ("Ausnahme", "ausnahme")]
        for i, (t, k) in enumerate(felder, 1):
            print(f"  [{i}] {t:11s} {b.get(k) or '-'}")
        print(f"      Koordinaten {b.get('lat')}, {b.get('lon')}" + ("   ** AUSGEBLENDET **" if b.get("ausgeblendet") else ""))
        print("\n  [o] Ort neu suchen (Stadt + Land + Karte)   [c] Daten von chess-results neu holen\n"
              "  [s] Spieler ändern   [h] aus-/einblenden   [l] löschen   [leer] zurück")
        w = eingabe("Auswahl").lower()
        if not w:
            return
        if w.isdigit() and 1 <= int(w) <= len(felder):
            t, k = felder[int(w) - 1]
            if k == "bedenkzeit":
                neu = eingabe("Bedenkzeit (klassisch/schnell/blitz)", b.get(k, ""))
                if neu not in BEDENKZEITEN:
                    print("  Nur klassisch, schnell oder blitz.")
                    continue
            elif k in ("von", "bis"):
                neu = eingabe(f"{t} (JJJJ-MM-TT oder JJJJ-MM)", b.get(k, ""))
                if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", neu):
                    print("  Format: 2025-04-17 oder 2025-04")
                    continue
            elif k == "link":
                neu = eingabe("chess-results-Link (leer lassen = behalten, '-' = entfernen)", "")
                neu = "" if neu == "-" else (neu or b.get("link", ""))
                tnr = re.search(r"tnr(\d{5,8})", neu)
                if tnr:
                    neu = tk.CR_LINK.format(tnr=tnr.group(1))
            elif k == "ausnahme":
                neu = eingabe("Begründung der Ausnahme (leer = keine Ausnahme)", "")
            else:
                neu = eingabe(t, b.get(k, ""))
            b[k] = neu
            if k == "von" and (not b.get("bis") or b["bis"] < neu):
                b["bis"] = neu
            if k in ("stadt", "land") and ja("Koordinaten für die Karte neu suchen"):
                ort_neu(b, f"{b.get('stadt', '')}, {b.get('land', '')}")
            d.speichern()
        elif w == "o":
            if ort_neu(b, eingabe("Stadt, Land")):
                d.speichern()
        elif w == "c":
            tnr = re.search(r"tnr(\d{5,8})", b.get("link", "") or "")
            if not tnr:
                print("  Kein chess-results-Link eingetragen.")
                continue
            seite = tk._hole(tk.CR_DETAIL.format(tnr=tnr.group(1)))
            x = tk.cr_details(tnr.group(1), seite) if seite else {}
            if not x.get("name"):
                print("  chess-results nicht erreichbar.")
                continue
            print(f"  chess-results: {x['name']} · {x.get('von')} bis {x.get('bis')} · {x.get('ort')} · {x.get('bedenkzeit')}")
            if ja("Übernehmen (Turnier, Datum, Bedenkzeit)"):
                b.update(turnier=x["name"], von=x.get("von") or b.get("von", ""), bis=x.get("bis") or b.get("bis", ""),
                         bedenkzeit=x.get("bedenkzeit") or b.get("bedenkzeit", ""))
                if x.get("ort") and ja(f"Auch den Ort aus „{x['ort']}, {x.get('land', '')}“ neu suchen"):
                    ort_neu(b, f"{x['ort']}, {x.get('land', '')}")
                d.speichern()
        elif w == "s":
            print("Zu welchem Spieler gehört das Turnier?")
            neu = profil_waehlen(d, "Spieler")
            if neu:
                b["spieler"] = neu
                d.speichern()
                return
        elif w == "h":
            if b.get("ausgeblendet"):
                b.pop("ausgeblendet")
                print("  -> wieder sichtbar")
            else:
                b["ausgeblendet"] = True
                print("  -> ausgeblendet (zählt nicht, bleibt gespeichert)")
            d.speichern()
        elif w == "l":
            if ja(f"„{b.get('turnier') or b.get('stadt')}“ wirklich löschen"):
                d.besuche.remove(b)
                d.speichern()
                return


def ort_neu(b, text):
    ort = tp.ort_suchen(text) if text.strip(", ") else None
    if not ort:
        print("  Ort nicht gefunden. Tipp: nur 'Stadt, Land' eingeben, z. B. 'Feffernitz, Österreich'.")
        return False
    gruppe = to.ort_gruppe(ort["stadt"], to.einstellungen().get("ort_gruppen"))
    print(f"  Gefunden: {ort['stadt']}, {ort['land']}" + (f"  (zählt als {gruppe})" if gruppe != ort["stadt"] else ""))
    if not ja("Übernehmen"):
        return False
    b.update(stadt=ort["stadt"], land=ort["land"], region=ort.get("region", ""), lat=round(ort["lat"], 5), lon=round(ort["lon"], 5))
    return True


def regionen_nachholen(d):
    """Ältere Einträge ohne Bundesland/Region (für Abzeichen wie Bayern-Kenner) einmal nachschlagen."""
    fehlt = [b for b in d.besuche if "region" not in b and b.get("stadt")]
    if not fehlt or not ja(f"{len(fehlt)} Einträge haben noch kein Bundesland/Region (für Abzeichen). Jetzt nachschlagen"):
        return
    for b in fehlt:
        ort = tp.ort_suchen(f"{b['stadt']}, {b.get('land', '')}")
        b["region"] = (ort or {}).get("region", "")
        print(f"  {b['stadt']}: {b['region'] or '?'}")
    d.speichern()


# ------------------------------------------------------------
# Hauptmenü
# ------------------------------------------------------------
def main():
    d = Daten()
    regionen_nachholen(d)
    while True:
        offen = len(glob.glob(os.path.join(to.ORDNER, "antraege", "*.json")))
        titel(f"AFK on Tour   ·   {len(d.spieler)} Profile · {len(d.besuche)} Turniere · {offen} offene Anträge")
        print("  [1] Alles aktualisieren\n  [2] Anträge prüfen\n  [3] Bearbeiten\n  [4] Turnier eintragen\n  [0] Beenden")
        w = eingabe("Auswahl")
        if w == "1":
            aktualisieren(d)
        elif w == "2":
            antraege(d)
        elif w == "3":
            bearbeiten(d)
        elif w == "4":
            eintragen(d)
        elif w in ("0", "q", ""):
            if d.geaendert and ja("Es gibt Änderungen. Jetzt hochladen (dauert nur kurz)"):
                aktualisieren(d, schnell=True)
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
