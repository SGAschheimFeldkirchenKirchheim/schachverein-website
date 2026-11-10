"""
Aufstellungen (Meldelisten mit Ergebnissen je Runde) und Einsatz-Prognose.

Nur Daten/Modell - das HTML baut liga.py.

Prognose = geschätzte Wahrscheinlichkeit, dass ein Spieler beim NÄCHSTEN Spiel seiner
Mannschaft eingesetzt wird:
  1. Vorwissen: Einsatzquote früherer Saisons, je Saison zurück mit ZERFALL gewichtet
     (Vorsaison 1/2, davor 1/4, ...). Ohne frühere Daten: Startwert für Stamm/Ersatz.
  2. Aktuelle Saison: p = (VORWISSEN_RUNDEN * Vorwissen + Einsätze) / (VORWISSEN_RUNDEN + Runden)
     -> nach 3 Runden zählt die laufende Saison schon zur Hälfte, nach 9 zu 75 %.
  3. Zuletzt gespielt -> etwas höher, zwei Runden nicht gespielt -> etwas niedriger.
  4. Alle Werte einer Mannschaft werden so skaliert, dass die Summe = Bretterzahl ist
     (es spielen ja genau so viele).
"""

# ==========================================
# EINSTELLUNGEN (Prognose)
# ==========================================
ZERFALL = 0.5               # Gewicht je Saison zurück: Vorsaison 0.5, davor 0.25, ...
VORWISSEN_RUNDEN = 3        # so viele Runden "wiegt" das Vorwissen gegen die laufende Saison
STAMM_START = 0.7           # Startwert ohne frühere Daten: Stammspieler
ERSATZ_START = 0.2          #                               Ersatzspieler
ZULETZT_BONUS = 0.15        # letzte Runde gespielt: p += (1 - p) * Bonus
PAUSE_FAKTOR = 0.75         # die letzten zwei Runden nicht gespielt: p *= Faktor
MAX_P = 0.97                # nie 100 %


def _felder(b):
    return (list(b) + [None] * 10)[:10]


def ergebnisse(d, tlnr):
    """-> (Runden mit Brettern, {Name: {Runde: {'t': '1'|'½'|'0'|'+'|'–', 'p': Punkte|None, 'e': Einsatz?}}})"""
    runden, res = [], {}
    for m in d.get("matches", []):
        if tlnr not in (m["h"], m["g"]) or not m.get("gesp") or m.get("sf") or not m.get("bretter"):
            continue
        heim = m["h"] == tlnr
        runden.append(m["r"])
        for b in m["bretter"]:
            _, sp_h, sp_g, art, h, g, *_ = _felder(b)
            name = (sp_h if heim else sp_g) or ""
            if not name.strip() or name.strip().lower() in {"n.n.", "nn", "-", "spielfrei"}:
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


def saison_quoten(teams_einer_saison):
    """Alle Mannschaften aller Ligen einer Saison -> {Name: (Einsätze, Runden)}.
    Spielt jemand in mehreren Mannschaften, zählt die mit der höchsten Quote."""
    quoten = {}
    for d in teams_einer_saison:
        for tlnr in map(int, d.get("teams", {})):
            runden, res = ergebnisse(d, tlnr)
            if not runden:
                continue
            for name, rs in res.items():
                e = sum(1 for x in rs.values() if x["e"])
                alt = quoten.get(name)
                if alt is None or e / len(runden) > alt[0] / alt[1]:
                    quoten[name] = (e, len(runden))
    return quoten


def vorwissen(name, stamm, historie):
    """historie = [(Saisons zurück, {Name: (Einsätze, Runden)})]"""
    zaehler = nenner = 0.0
    for alter, quoten in historie:
        if name in quoten:
            e, r = quoten[name]
            w = (ZERFALL ** alter) * r
            zaehler += w * e / r
            nenner += w
    start = STAMM_START if stamm else ERSATZ_START
    return zaehler / nenner if nenner else start


def prognose(d, tlnr, kader, historie, bretter):
    """-> {Name: Wahrscheinlichkeit 0..1} für alle Gemeldeten der Mannschaft."""
    runden, res = ergebnisse(d, tlnr)
    R = len(runden)
    p = {}
    for k in kader:
        name = k["name"]
        rs = res.get(name, {})
        e = sum(1 for x in rs.values() if x["e"])
        wert = (VORWISSEN_RUNDEN * vorwissen(name, k.get("stamm"), historie) + e) / (VORWISSEN_RUNDEN + R)
        if runden and rs.get(runden[-1], {}).get("e"):
            wert += (1 - wert) * ZULETZT_BONUS
        elif R >= 2 and not any(rs.get(r, {}).get("e") for r in runden[-2:]):
            wert *= PAUSE_FAKTOR
        p[name] = wert
    # Summe = Bretterzahl (mit Obergrenze MAX_P, Überschuss wird auf die anderen verteilt)
    if p and bretter:
        for _ in range(20):
            summe = sum(p.values())
            if summe <= 0:
                break
            f = bretter / summe
            p = {n: min(MAX_P, v * f) for n, v in p.items()}
            if abs(sum(p.values()) - bretter) < 1e-6 or all(v >= MAX_P for v in p.values()):
                break
    return p


def voraussichtlich(kader, p, bretter):
    """Die `bretter` wahrscheinlichsten Spieler, in Meldereihenfolge (= Brettfolge)."""
    beste = sorted(kader, key=lambda k: -p.get(k["name"], 0))[:bretter]
    return sorted(beste, key=lambda k: k.get("nr") or 999)
