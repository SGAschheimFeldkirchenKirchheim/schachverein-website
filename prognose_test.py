r"""
Test der Einsatz-Prognose an alten Saisons (Backtest) + Suche nach den besten Gewichten.

  py prognose_test.py                 Test + Suche, Ergebnis nur anzeigen
  py prognose_test.py --schreiben     ... und die besten Gewichte nach prognose_parameter.json
  py prognose_test.py --ziel 2025     Test-Saison (Standard: neueste im Archiv)
  py prognose_test.py --daten ..\Tabellenrechner\db\backtest
                                      mit ALLEN Ligen (Tabellenrechner: py backtest_daten.py)

Ablauf:
  - Für JEDE Runde jeder Mannschaft der Test-Saison wird vorhergesagt, nur mit dem Wissen
    davor (frühere Saisons + Runden davor), und mit dem verglichen, was wirklich passiert ist.
  - Gesucht wird auf ALLEN Saisons vor der Test-Saison, die selbst schon Vorwissen haben
    ("Training", z. B. 2023 + 2024), geprüft auf der Test-Saison (z. B. 2025).
    --schreiben speichert nur, wenn die gefundenen Gewichte auf der Test-Saison BESSER sind
    als die aktuellen - schlechter werden kann es dadurch also nicht.
  - Zusätzlich: bringen die Vereins-Gewichte (andere Mannschaften desselben Vereins) etwas?
  - Kennzahlen:
      Brier        mittlere quadratische Abweichung (p - gespielt)^2, kleiner = besser
      Treffer      Anteil der wirklich eingesetzten Spieler, die in der voraussichtlichen
                   Aufstellung standen, größer = besser
  - Vergleich mit einfachen Regeln: "Stammspieler spielen" und "wie letzte Runde".

Daten: mannschaften/archiv/<Jahr>/*.json (mit Meldelisten, siehe Tabellenrechner: py main.py archiv --neu)
"""

import glob
import json
import os
import sys
import time

import aufstellung as auf
import liga

# ==========================================
# EINSTELLUNGEN
# ==========================================
SUCHRAUM = {                           # ausprobierte Werte je Gewicht
    "saison_zerfall": [0.0, 0.25, 0.5, 0.75, 1.0],
    "runden_zerfall": [0.5, 0.65, 0.8, 0.9, 1.0],
    "prior_gewicht": [0.25, 0.5, 1.0, 1.5, 2.5, 4.0],
    "stamm_start": [0.4, 0.55, 0.7, 0.85],
    "ersatz_start": [0.02, 0.08, 0.15, 0.25],
    "ha_gewicht": [0.0, 1.0, 3.0, 6.0, 12.0, 25.0],
    "verein_faktor": [0.0, 0.25, 0.5, 1.0],
    "oben_abzug": [0.0, 0.2, 0.4, 0.6],
}
DURCHGAENGE = 3                         # Koordinatensuche: so oft alle Gewichte nacheinander
ZIEL = "brier"                          # optimiert wird: "brier" (kleiner) oder "treffer" (größer)


def saisons_laden(basis=None):
    """{Jahr: Mannschaften}; basis = Ordner mit <Jahr>/*.json (Standard: mannschaften/archiv)."""
    saisons = {}
    for ordner in sorted(glob.glob(os.path.join(basis or os.path.join(liga.DATEN_ORDNER, "archiv"), "*"))):
        name = os.path.basename(ordner)
        if name.isdigit():
            ts = liga.lade_teams(ordner)
            if ts:
                saisons[int(name)] = ts
    return saisons


def faelle(saisons, ziel):
    """Alle Testfälle der Ziel-Saison: (d, tlnr, Runde, heim, Kader, gespielt, Historie, Verein)."""
    ereignisse = {j: auf.saison_ereignisse(ts) for j, ts in saisons.items() if j < ziel}
    historie = [(ziel - j, ev) for j, ev in ereignisse.items()]
    idx = auf.verein_index(saisons.get(ziel, []))
    liste = []
    for d in saisons.get(ziel, []):
        for tlnr in map(int, d.get("teams", {})):
            kader = auf.kader_von(d, tlnr)
            if not kader:
                continue
            namen = {k["name"] for k in kader}
            _, res = auf.ergebnisse(d, tlnr)
            for r, heim in auf.team_runden(d, tlnr):
                gespielt = {n for n, rs in res.items() if rs.get(r, {}).get("e") and n in namen}
                if gespielt:
                    liste.append((d, tlnr, r, heim, kader, gespielt, historie, auf.andere_teams(idx, d, tlnr)))
    return liste


def bewerten(fl, vorhersage):
    """vorhersage(fall) -> {Name: p}. -> (Brier, Treffer)"""
    brier = n = treffer = moeglich = 0
    for fall in fl:
        d, tlnr, r, heim, kader, gespielt, historie, verein = fall
        p = vorhersage(fall)
        bretter = d.get("bretter") or len(gespielt)
        for k in kader:
            brier += (p.get(k["name"], 0) - (k["name"] in gespielt)) ** 2
            n += 1
        tipp = {k["name"] for k in auf.voraussichtlich(kader, p, bretter)}
        treffer += len(tipp & gespielt)
        moeglich += len(gespielt)
    return brier / max(n, 1), treffer / max(moeglich, 1)


def modell(P):
    def f(fall):
        d, tlnr, r, heim, kader, gespielt, historie, verein = fall
        return auf.prognose(d, tlnr, historie, d.get("bretter") or 0, bis_runde=r, naechst_heim=heim,
                            P=P, kader=kader, verein=verein)[0]
    return f


def regel_stamm(fall):
    return {k["name"]: 1.0 if k.get("stamm") else 0.0 for k in fall[4]}


def regel_letzte_runde(fall):
    d, tlnr, r, heim, kader, gespielt, historie, verein = fall
    vorher = auf.team_runden(d, tlnr, r)
    if not vorher:
        return regel_stamm(fall)
    _, res = auf.ergebnisse(d, tlnr)
    letzte = vorher[-1][0]
    return {k["name"]: 1.0 if res.get(k["name"], {}).get(letzte, {}).get("e") else 0.0 for k in kader}


def wert(ergebnis):
    brier, treffer = ergebnis
    return brier if ZIEL == "brier" else -treffer


def suchen(fl, start):
    """Koordinatensuche: ein Gewicht nach dem anderen auf den besten Wert setzen."""
    P = dict(start)
    bestes = wert(bewerten(fl, modell(P)))
    for durchgang in range(DURCHGAENGE):
        verbessert = False
        for name, werte in SUCHRAUM.items():
            for v in werte:
                versuch = {**P, name: v}
                w = wert(bewerten(fl, modell(versuch)))
                if w < bestes - 1e-9:
                    bestes, P, verbessert = w, versuch, True
        print(f"   Durchgang {durchgang + 1}: {ZIEL} = {abs(bestes):.4f}")
        if not verbessert:
            break
    return P


def zeile(name, ergebnis):
    brier, treffer = ergebnis
    return f"  {name:<28} Brier {brier:.4f}   Treffer {100 * treffer:5.1f} %"


def main():
    args = sys.argv[1:]
    saisons = saisons_laden(args[args.index("--daten") + 1] if "--daten" in args else None)
    if len(saisons) < 2:
        raise SystemExit("Zu wenige Saisons im Archiv (mind. 2). Erst im Tabellenrechner: py main.py archiv --neu")
    ziel = int(args[args.index("--ziel") + 1]) if "--ziel" in args else max(saisons)
    training = [j for j in sorted(saisons) if min(saisons) < j < ziel]   # Saisons mit Vorwissen
    if not training:
        training = [j for j in sorted(saisons) if j < ziel][-1:]
        print("Hinweis: Für das Training gibt es keine Saison mit Vorwissen - Ergebnis nur grob.")
    test_faelle = faelle(saisons, ziel)
    train_faelle = [f for j in training for f in faelle(saisons, j)]
    if not test_faelle or not any(auf.kader_von(d, int(t)) for d in saisons[ziel] for t in d.get("teams", {})):
        raise SystemExit("Keine Meldelisten im Archiv - im Tabellenrechner: py main.py archiv --neu")
    print(f"Saisons: {', '.join(map(str, sorted(saisons)))}")
    print(f"Training: {' + '.join(map(str, training))} ({len(train_faelle)} Mannschafts-Runden) | "
          f"Test: {ziel} ({len(test_faelle)})\n")

    t = time.time()
    print("Suche beste Gewichte auf den Trainings-Saisons ...")
    beste = suchen(train_faelle or test_faelle, auf.PARAMETER)
    print(f"   ({time.time() - t:.0f} s)\n")
    ohne_verein = {**beste, "verein_faktor": 0.0, "oben_abzug": 0.0}

    aktuell_erg, beste_erg = bewerten(test_faelle, modell(auf.PARAMETER)), bewerten(test_faelle, modell(beste))
    print(f"Ergebnis auf der Test-Saison {ziel}:")
    print(zeile("Regel: Stamm spielt", bewerten(test_faelle, regel_stamm)))
    print(zeile("Regel: wie letzte Runde", bewerten(test_faelle, regel_letzte_runde)))
    print(zeile("Modell aktuelle Gewichte", aktuell_erg))
    print(zeile("Modell gefunden, ohne Verein", bewerten(test_faelle, modell(ohne_verein))))
    print(zeile("Modell gefunden, mit Verein", beste_erg))
    print("\nGefundene Gewichte:")
    for k, v in beste.items():
        alt = auf.PARAMETER[k]
        print(f"  {k:<16} {v:<6g}" + (f"  (bisher {alt:g})" if v != alt else ""))

    besser = wert(beste_erg) < wert(aktuell_erg) - 1e-9
    if "--schreiben" in args:
        if besser:
            with open(auf.PARAMETER_DATEI, "w", encoding="utf-8") as f:
                json.dump(beste, f, indent=1)
            print(f"\n✅ Gespeichert in {os.path.basename(auf.PARAMETER_DATEI)} - gilt ab dem nächsten Website-Build.")
        else:
            print("\nNICHT gespeichert: die gefundenen Gewichte sind auf der Test-Saison nicht besser als die aktuellen.")
    elif besser:
        print("\nAuf der Test-Saison besser als die aktuellen. Übernehmen mit:  py prognose_test.py --schreiben ...")
    else:
        print("\nAuf der Test-Saison NICHT besser als die aktuellen -> aktuelle Gewichte behalten.")


if __name__ == "__main__":
    main()
