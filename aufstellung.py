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

Zum Schluss: Summe aller p einer Mannschaft = Bretterzahl (es spielen genau so viele).
"neu" = in keiner Meldeliste/Partie früherer Saisons und in dieser Saison noch nicht gespielt.

Die Gewichte findet prognose_test.py (Test an alten Saisons) und schreibt sie nach
prognose_parameter.json; fehlt die Datei, gelten die Standardwerte unten.
"""

import json
import os

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


# ==========================================
# MODELL
# ==========================================
def wahrscheinlichkeit(stamm, ereignisse, naechst_heim, P):
    """ereignisse = [(Saisons zurück, Runden zurück, heim, gespielt)]"""
    start = P["stamm_start"] if stamm else P["ersatz_start"]
    zaehler = nenner = zh = nh = 0.0
    for alter, rueck, heim, gespielt in ereignisse:
        w = (P["saison_zerfall"] ** alter) * (P["runden_zerfall"] ** rueck)
        nenner += w
        zaehler += w * gespielt
        if naechst_heim is not None and heim == naechst_heim:
            nh += w
            zh += w * gespielt
    p = (P["prior_gewicht"] * start + zaehler) / (P["prior_gewicht"] + nenner)
    if naechst_heim is not None and P["ha_gewicht"] > 0 and nh:
        p = (P["ha_gewicht"] * p + zh) / (P["ha_gewicht"] + nh)
    return p


def prognose(d, tlnr, historie, bretter, bis_runde=None, naechst_heim="auto", P=None, kader=None):
    """-> ({Name: Wahrscheinlichkeit}, {Namen "neu"}) für alle Gemeldeten der Mannschaft.
    historie = [(Saisons zurück, saison_ereignisse(...))]; bis_runde = nur Runden davor kennen
    (für den Test); naechst_heim = Spielort des vorhergesagten Spiels ("auto" = nächstes Spiel)."""
    P = P or PARAMETER
    kader = kader if kader is not None else kader_von(d, tlnr)
    if naechst_heim == "auto":
        naechst_heim = naechstes_spiel(d, tlnr)[1]
    runden = team_runden(d, tlnr, bis_runde)
    _, res = ergebnisse(d, tlnr)
    p, neu = {}, set()
    for k in kader:
        name = k["name"]
        ev = [(0, rueck, heim, g) for rueck, heim, g in _ereignisse(runden, res.get(name, {}))]
        bekannt = any(g for *_, g in ev)
        for alter, saison in historie:
            ev += [(alter, rueck, heim, g) for rueck, heim, g in saison["spieler"].get(name, [])]
            bekannt = bekannt or name in saison["namen"]
        if not bekannt:
            neu.add(name)
        p[name] = wahrscheinlichkeit(k.get("stamm"), ev, naechst_heim, P)
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
