"""
Aufstellungen (Meldelisten mit Ergebnissen je Runde) und Einsatz-Prognose.
Nur Daten/Modell - das HTML baut liga.py, den Test macht prognose_test.py.

PROGNOSE = geschätzte Wahrscheinlichkeit, dass ein Spieler im NÄCHSTEN Spiel seiner Mannschaft
eingesetzt wird. Jede vergangene Runde ist ein "Ereignis" (gespielt ja/nein) mit Gewicht

    w = SAISON_ZERFALL ^ (Saisons zurück)  *  RUNDEN_ZERFALL ^ (Runden zurück innerhalb der Saison)

-> die letzte Runde zählt voll, frühere Runden und frühere Saisons immer weniger
   (der letzte Spieltag der Vorsaison zählt mehr als Runde 1 vor drei Jahren).

    p = (PRIOR_GEWICHT * Startwert + Summe w * gespielt) / (PRIOR_GEWICHT + Summe w)

    Startwert: STAMM_START bzw. ERSATZ_START.  Kleines PRIOR_GEWICHT = neue Spieler, die ein-
    zweimal spielen, bekommen schnell eine hohe Wahrscheinlichkeit.

Heim/Auswärts: dieselbe Rechnung nur über Runden mit gleichem Spielort wie das nächste Spiel,
stark zu p hingezogen (HA_GEWICHT; groß = kaum Einfluss, 0 = aus).

Verein (andere Mannschaften desselben Vereins in dieser Saison, nur was in den Daten steht):
  VEREIN_FAKTOR: Runden in den anderen Mannschaften zählen mit diesem Faktor mit (0 = aus)
  OBEN_ABZUG:    hat er zuletzt in einer HÖHEREN Mannschaft gespielt: p *= (1 - Abzug) (0 = aus)
  Beide stehen auf 0, bis prognose_test.py zeigt, dass sie etwas bringen.

Zum Schluss: Summe aller p einer Mannschaft = Bretterzahl (es spielen genau so viele).
"neu" = in keiner Meldeliste/Partie früherer Saisons und in dieser Saison noch nicht gespielt.

Die Gewichte findet prognose_test.py (Test an alten Saisons) und schreibt sie nach
prognose_parameter.json; fehlt die Datei, gelten die Standardwerte unten.
"""

import json
import os
import re

# ==========================================
# EINSTELLUNGEN (Standardwerte; prognose_parameter.json hat Vorrang)
# ==========================================
STANDARD = {
    "saison_zerfall": 0.5,     # Gewicht je Saison zurück (Vorsaison 0.5, davor 0.25 ...)
    "runden_zerfall": 0.8,     # Gewicht je Runde zurück innerhalb einer Saison
    "prior_gewicht": 1.5,      # so viele (volle) Runden "wiegt" der Startwert
    "stamm_start": 0.7,        # Startwert Stammspieler
    "ersatz_start": 0.15,      # Startwert Ersatzspieler
    "ha_gewicht": 6.0,         # Heim/Auswärts-Effekt: je kleiner, desto stärker (0 = aus)
    "verein_faktor": 0.0,      # Einsätze in anderen Mannschaften des Vereins zählen mit (0 = aus)
    "oben_abzug": 0.0,         # zuletzt in höherer Mannschaft des Vereins gespielt -> Abzug (0 = aus)
    "max_p": 0.97,             # nie 100 %
}
PARAMETER_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prognose_parameter.json")
KEIN_SPIELER = {"", "n.n.", "nn", "-", "spielfrei"}


def lade_parameter(pfad=PARAMETER_DATEI):
    p = dict(STANDARD)
    try:
        with open(pfad, encoding="utf-8") as f:
            p.update({k: float(v) for k, v in json.load(f).items() if k in STANDARD})
    except (OSError, ValueError):
        pass
    return p


PARAMETER = lade_parameter()


# ==========================================
# DATEN
# ==========================================
def _felder(b):
    return (list(b) + [None] * 10)[:10]


def kader_von(d, tlnr):
    return (d.get("kader_alle") or {}).get(str(tlnr)) or (d.get("kader") if tlnr == d.get("eigen") else None) or []


def team_runden(d, tlnr, bis_runde=None):
    """Gespielte Runden einer Mannschaft mit Brettern -> [(Runde, heim?)] (nur Runden < bis_runde)."""
    return sorted((m["r"], m["h"] == tlnr) for m in d.get("matches", [])
                  if tlnr in (m["h"], m["g"]) and m.get("gesp") and not m.get("sf") and m.get("bretter")
                  and (bis_runde is None or m["r"] < bis_runde))


def naechstes_spiel(d, tlnr):
    """Nächstes ungespieltes Spiel -> (Runde, heim?) oder (None, None)."""
    for m in sorted(d.get("matches", []), key=lambda m: m["r"]):
        if tlnr in (m["h"], m["g"]) and not m.get("gesp") and not m.get("sf"):
            return m["r"], m["h"] == tlnr
    return None, None


_ERGEBNISSE = {}                 # Zwischenspeicher (gleiche Daten werden beim Test tausendfach gebraucht)


def ergebnisse(d, tlnr):
    """-> (Runden mit Brettern, {Name: {Runde: {'t': '1'|'½'|'0'|'+'|'–', 'p': Punkte|None, 'e': Einsatz?}}})"""
    schluessel = (id(d), tlnr)
    if schluessel in _ERGEBNISSE and _ERGEBNISSE[schluessel][0] is d:
        return _ERGEBNISSE[schluessel][1]
    ergebnis = _ergebnisse(d, tlnr)
    _ERGEBNISSE[schluessel] = (d, ergebnis)
    return ergebnis


def _ergebnisse(d, tlnr):
    runden, res = [], {}
    for m in d.get("matches", []):
        if tlnr not in (m["h"], m["g"]) or not m.get("gesp") or m.get("sf") or not m.get("bretter"):
            continue
        heim = m["h"] == tlnr
        runden.append(m["r"])
        for b in m["bretter"]:
            _, sp_h, sp_g, art, h, g, *_ = _felder(b)
            name = (sp_h if heim else sp_g) or ""
            if name.strip().lower() in KEIN_SPIELER:
                continue
            if art == "score":
                p = h if heim else g
                eintrag = {"t": {1.0: "1", 0.5: "½", 0.0: "0"}.get(float(p), str(p)), "p": p, "e": True}
            elif art == "annulliert":
                eintrag = {"t": "–", "p": None, "e": False}
            else:
                gewonnen = (art == "forfeit_heim") == heim
                eintrag = {"t": "+" if gewonnen else "–", "p": 1.0 if gewonnen else 0.0, "e": gewonnen}
            res.setdefault(name, {})[m["r"]] = eintrag
    return sorted(set(runden)), res


def _ereignisse(runden, res_spieler):
    """[(Runde, heim)] + Ergebnisse eines Spielers -> [(Runden zurück, heim, gespielt)]"""
    n = len(runden)
    return [(n - 1 - i, heim, bool(res_spieler.get(r, {}).get("e"))) for i, (r, heim) in enumerate(runden)]


def saison_ereignisse(teams_einer_saison):
    """Alle Mannschaften aller Ligen einer (abgeschlossenen) Saison ->
    {"spieler": {Name: [(Runden zurück, heim, gespielt)]}, "namen": alle bekannten Namen}.
    Steht jemand in mehreren Mannschaften, zählt die mit den meisten Einsätzen."""
    beste, namen = {}, set()
    for d in teams_einer_saison:
        for tlnr in map(int, d.get("teams", {})):
            runden = team_runden(d, tlnr)
            _, res = ergebnisse(d, tlnr)
            kader = {k["name"] for k in kader_von(d, tlnr)}
            namen |= kader | set(res)
            if not runden:
                continue
            for name in kader | set(res):
                ev = _ereignisse(runden, res.get(name, {}))
                e = sum(1 for x in ev if x[2])
                if name not in beste or e > beste[name][0]:
                    beste[name] = (e, ev)
    return {"spieler": {n: ev for n, (_, ev) in beste.items()}, "namen": namen}


def _verein_nummer(name):
    """'SC Haar 1931 2' -> ('SC Haar 1931', 2); ohne Nummer -> (Name, 1)"""
    m = re.match(r"^(.*?)\s+(\d+)\s*$", (name or "").strip())
    if m and int(m.group(2)) < 50:          # "SC Haar 1931" ohne Nummer: 1931 ist keine Mannschaftsnummer
        return m.group(1), int(m.group(2))
    return (name or "").strip(), 1


def verein_index(teams_einer_saison):
    """Alle Mannschaften einer Saison nach Verein -> {Verein: [(d, tlnr, Nummer)]}.
    Nur MMM-Mannschaften untereinander (Senioren laufen in eigenen Runden)."""
    idx = {}
    for d in teams_einer_saison:
        if "senior" in (d.get("klasse") or "").lower():
            continue
        for t, name in d.get("teams", {}).items():
            verein, nr = _verein_nummer(name)
            idx.setdefault(verein, []).append((d, int(t), nr))
    return idx


def andere_teams(idx, d, tlnr):
    """Die anderen Mannschaften desselben Vereins -> ([(d, tlnr, Nummer)], eigene Nummer)"""
    verein, nr = _verein_nummer(d.get("teams", {}).get(str(tlnr), ""))
    return [x for x in idx.get(verein, []) if not (x[0] is d and x[1] == tlnr)], nr


# ==========================================
# MODELL
# ==========================================
def wahrscheinlichkeit(stamm, ereignisse, naechst_heim, P):
    """ereignisse = [(Saisons zurück, Runden zurück, heim, gespielt, Faktor)]"""
    start = P["stamm_start"] if stamm else P["ersatz_start"]
    zaehler = nenner = zh = nh = 0.0
    for alter, rueck, heim, gespielt, faktor in ereignisse:
        w = faktor * (P["saison_zerfall"] ** alter) * (P["runden_zerfall"] ** rueck)
        nenner += w
        zaehler += w * gespielt
        if naechst_heim is not None and heim == naechst_heim:
            nh += w
            zh += w * gespielt
    p = (P["prior_gewicht"] * start + zaehler) / (P["prior_gewicht"] + nenner)
    if naechst_heim is not None and P["ha_gewicht"] > 0 and nh:
        p = (P["ha_gewicht"] * p + zh) / (P["ha_gewicht"] + nh)
    return p


def prognose(d, tlnr, historie, bretter, bis_runde=None, naechst_heim="auto", P=None, kader=None, verein=None):
    """-> ({Name: Wahrscheinlichkeit}, {Namen "neu"}) für alle Gemeldeten der Mannschaft.
    historie = [(Saisons zurück, saison_ereignisse(...))]; bis_runde = nur Runden davor kennen
    (für den Test); naechst_heim = Spielort des vorhergesagten Spiels ("auto" = nächstes Spiel);
    verein = andere_teams(...) für die Vereins-Gewichte."""
    P = P or PARAMETER
    kader = kader if kader is not None else kader_von(d, tlnr)
    if naechst_heim == "auto":
        naechst_heim = naechstes_spiel(d, tlnr)[1]
    runden = team_runden(d, tlnr, bis_runde)
    _, res = ergebnisse(d, tlnr)
    andere, eigene_nr = verein if verein else ([], 1)
    nutzt_verein = andere and (P.get("verein_faktor", 0) > 0 or P.get("oben_abzug", 0) > 0)
    if nutzt_verein:      # bis zur gleichen Runde (MMM: gleiche Runde = gleiche Woche)
        andere = [(team_runden(d2, t2, bis_runde if bis_runde else None), ergebnisse(d2, t2)[1], nr2)
                  for d2, t2, nr2 in andere]
    p, neu = {}, set()
    for k in kader:
        name = k["name"]
        ev = [(0, rueck, heim, g, 1.0) for rueck, heim, g in _ereignisse(runden, res.get(name, {}))]
        bekannt = any(e[3] for e in ev)
        for alter, saison in historie:
            ev += [(alter, rueck, heim, g, 1.0) for rueck, heim, g in saison["spieler"].get(name, [])]
            bekannt = bekannt or name in saison["namen"]
        oben = False
        if nutzt_verein:
            for runden2, res2, nr2 in andere:
                rs2 = res2.get(name)
                if not rs2:
                    continue
                if P.get("verein_faktor", 0) > 0:
                    ev += [(0, rueck, heim, g, P["verein_faktor"]) for rueck, heim, g in _ereignisse(runden2, rs2)]
                if nr2 < eigene_nr and runden2 and rs2.get(runden2[-1][0], {}).get("e"):
                    oben = True
        if not bekannt:
            neu.add(name)
        p[name] = wahrscheinlichkeit(k.get("stamm"), ev, naechst_heim, P)
        if oben:
            p[name] *= 1 - P.get("oben_abzug", 0)
    # Summe = Bretterzahl (Obergrenze max_p, Überschuss wird auf die anderen verteilt)
    if p and bretter:
        for _ in range(30):
            summe = sum(p.values())
            if summe <= 0:
                break
            p = {n: min(P["max_p"], v * bretter / summe) for n, v in p.items()}
            if abs(sum(p.values()) - bretter) < 1e-6 or all(v >= P["max_p"] for v in p.values()):
                break
    return p, neu


def voraussichtlich(kader, p, bretter):
    """Die `bretter` wahrscheinlichsten Spieler, in Meldereihenfolge (= Brettfolge)."""
    beste = sorted(kader, key=lambda k: -p.get(k["name"], 0))[:bretter]
    return sorted(beste, key=lambda k: k.get("nr") or 999)


def top_aufstellungen(kader, p, bretter, anzahl=3):
    """Die `anzahl` wahrscheinlichsten Aufstellungen (welche `bretter` Spieler spielen).
    Modell: genau `bretter` spielen; P(Aufstellung) ~ Produkt der Chancen p/(1-p) der Spieler darin.
    -> [(Wahrscheinlichkeit, [Kader-Einträge in Meldereihenfolge])], beste zuerst.
    Die zweit- und drittbeste unterscheiden sich von der besten höchstens durch 1-2 Tausche,
    deshalb reicht es, diese durchzuprobieren."""
    from itertools import combinations
    spieler = [k for k in kader if p.get(k["name"], 0) > 0]
    if not spieler or not bretter:
        return []
    if len(spieler) <= bretter:
        return [(1.0, sorted(spieler, key=lambda k: k.get("nr") or 999))]
    chance = {k["name"]: min(p[k["name"]], 0.999) / (1 - min(p[k["name"]], 0.999)) for k in spieler}

    # Normierung: Summe über ALLE Aufstellungen = elementarsymmetrisches Polynom e_n(Chancen)
    e = [1.0] + [0.0] * bretter
    for k in spieler:
        for j in range(bretter, 0, -1):
            e[j] += e[j - 1] * chance[k["name"]]

    def gewicht(menge):
        w = 1.0
        for k in menge:
            w *= chance[k["name"]]
        return w

    beste = sorted(spieler, key=lambda k: -chance[k["name"]])[:bretter]
    rest = [k for k in spieler if k not in beste]
    kandidaten = {frozenset(k["name"] for k in beste): beste}
    for anz in (1, 2):
        for raus in combinations(beste, anz):
            for rein in combinations(rest, anz):
                menge = [k for k in beste if k not in raus] + list(rein)
                kandidaten[frozenset(k["name"] for k in menge)] = menge
    reihe = sorted(kandidaten.values(), key=gewicht, reverse=True)[:anzahl]
    return [(gewicht(m) / e[bretter], sorted(m, key=lambda k: k.get("nr") or 999)) for m in reihe]

