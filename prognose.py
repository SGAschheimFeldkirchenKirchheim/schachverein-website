"""
Prognose Saisonende (wie das "LigaOrakel"): die restlichen Mannschaftskämpfe einer Liga werden
viele Male zufällig ausgespielt und ausgezählt.

Grundlage (alles aus mannschaften/<key>.json, kommt vom Tabellenrechner):
  - Ergebnisse der gespielten Runden, Spielplan der restlichen
  - Spielstärke je Mannschaft: DWZ-Schnitt der bisher gespielten Aufstellungen, gemischt mit dem
    DWZ-Schnitt der besten Stammspieler laut Meldeliste (je mehr gespielt, desto mehr zählt das Gespielte)
  - Auf-/Abstiegsplätze ("auf", "auf_evtl", "ab", "ab_evtl") wie in der Tabelle (Schachbezirk-Färbung)

Je Brett: Erwartungswert nach DWZ-Formel, dazu Remis-Anteil; die Aufstellung schwankt von Kampf zu Kampf
(Ersatzspieler) -> zusätzliche Streuung. Wertung wie im Tabellenrechner: MP, BP, Mannschaftssiege,
dann Los. Ergebnis ist reproduzierbar (fester Zufallsstartwert je Liga und Stand).

Saisonverlauf: dieselbe Rechnung für den Stand nach jeder bisherigen Runde (rückwirkend, nichts muss
gespeichert werden).

Nur Standardbibliothek (der GitHub-Build hat kein numpy).
"""

import bisect
import json
import math
import random

# ---------- Einstellungen ----------
SIMULATIONEN = 10000          # für den aktuellen Stand
SIMULATIONEN_VERLAUF = 3000   # je frühere Runde (Saisonverlauf)
REMIS_MAX = 0.32              # Remis-Anteil bei gleich starken Spielern (sinkt mit dem Stärkeunterschied)
AUFSTELLUNG_STREUUNG = 70     # DWZ-Schwankung der Aufstellung von Kampf zu Kampf
DWZ_OHNE_WERTUNG = 1000       # Spieler ohne DWZ
GEWICHT_MELDELISTE = 2        # zählt wie so viele gespielte Kämpfe
# -----------------------------------

_GH = [(-2.0202, 0.0200), (-0.9586, 0.3936), (0.0, 0.9453), (0.9586, 0.3936), (2.0202, 0.0200)]
_GH_SUMME = sum(w for _, w in _GH)


def _brett_verteilung(e):
    """Erwartungswert e (0..1) -> (P Sieg, P Remis, P Niederlage)."""
    remis = REMIS_MAX * (1 - abs(2 * e - 1))
    sieg = max(0.0, e - remis / 2)
    niederlage = max(0.0, 1 - sieg - remis)
    return sieg, remis, niederlage


def _kampf_verteilung(d_heim, d_gast, bretter):
    """Verteilung der Heim-Brettpunkte (in halben Punkten 0..2*bretter), über Aufstellungs-Schwankung gemittelt."""
    gesamt = [0.0] * (2 * bretter + 1)
    for z, w in _GH:
        diff = d_heim - d_gast + z * AUFSTELLUNG_STREUUNG * math.sqrt(2)
        s, r, n = _brett_verteilung(1 / (1 + 10 ** (-diff / 400)))
        vert = [1.0]
        for _ in range(bretter):
            neu = [0.0] * (len(vert) + 2)
            for k, p in enumerate(vert):
                if p:
                    neu[k] += p * n
                    neu[k + 1] += p * r
                    neu[k + 2] += p * s
            vert = neu
        for k, p in enumerate(vert):
            gesamt[k] += p * w / _GH_SUMME
    kum, s = [], 0.0
    for p in gesamt:
        s += p
        kum.append(s)
    kum[-1] = 1.0
    return kum


def _meldeliste_staerke(d, tlnr, bretter):
    kader = (d.get("kader_alle") or {}).get(str(tlnr)) or []
    stamm = [k.get("dwz") or DWZ_OHNE_WERTUNG for k in kader if k.get("stamm")]
    rest = [k.get("dwz") or DWZ_OHNE_WERTUNG for k in kader if not k.get("stamm")]
    werte = sorted(stamm, reverse=True)[:bretter]
    if len(werte) < bretter:
        werte += sorted(rest, reverse=True)[:bretter - len(werte)]
    return sum(werte) / len(werte) if werte else None


def staerken(d, bis_runde):
    """DWZ-Schnitt je Mannschaft (nur Kämpfe bis einschließlich bis_runde zählen als gespielt)."""
    bretter = d.get("bretter") or 8
    gespielt = {}
    for m in d["matches"]:
        if m.get("gesp") and m["r"] <= bis_runde:
            for seite, t in (("dh", m["h"]), ("dg", m["g"])):
                if m.get(seite):
                    gespielt.setdefault(t, []).append(m[seite])
    werte = {}
    for t in d["teams"]:
        t = int(t)
        melde = _meldeliste_staerke(d, t, bretter)
        g = gespielt.get(t, [])
        if g and melde:
            werte[t] = (sum(g) + GEWICHT_MELDELISTE * melde) / (len(g) + GEWICHT_MELDELISTE)
        elif g:
            werte[t] = sum(g) / len(g)
        else:
            werte[t] = melde
    bekannt = [v for v in werte.values() if v]
    schnitt = sum(bekannt) / len(bekannt) if bekannt else 1500
    return {t: (v or schnitt) for t, v in werte.items()}


def zonen(d, n):
    """Platz -> 'auf' | 'auf_evtl' | 'ab' | 'ab_evtl' | '' (wie die Färbung der Tabelle)."""
    auf, ae, ab, abe = (d.get(k) or 0 for k in ("auf", "auf_evtl", "ab", "ab_evtl"))
    z = {}
    for p in range(1, n + 1):
        z[p] = ("auf" if p <= auf else "auf_evtl" if p <= auf + ae else
                "ab" if p > n - ab else "ab_evtl" if p > n - ab - abe else "")
    return z


def simulieren(d, bis_runde, anzahl, seed):
    teams = [int(t) for t in d["teams"]]
    n, bretter = len(teams), d.get("bretter") or 8
    stark = staerken(d, bis_runde)
    mp0 = {t: 0 for t in teams}
    bp0 = {t: 0 for t in teams}       # in halben Punkten
    sg0 = {t: 0 for t in teams}
    offen = []
    for m in d["matches"]:
        h, g = m["h"], m["g"]
        if h not in mp0 or g not in mp0:
            continue                   # spielfrei o. ä.
        if m.get("gesp") and m["r"] <= bis_runde:
            bh, bg = round(2 * (m.get("bh") or 0)), round(2 * (m.get("bg") or 0))
            bp0[h] += bh
            bp0[g] += bg
            if bh > bg:
                mp0[h] += 2; sg0[h] += 1
            elif bg > bh:
                mp0[g] += 2; sg0[g] += 1
            else:
                mp0[h] += 1; mp0[g] += 1
        else:
            offen.append((h, g, _kampf_verteilung(stark[h], stark[g], bretter)))
    z = zonen(d, n)
    rng = random.Random(seed)
    platz = {t: [0] * (n + 1) for t in teams}
    punkte = {t: {} for t in teams}    # MP -> {zone: anzahl}
    for _ in range(anzahl):
        mp, bp, sg = dict(mp0), dict(bp0), dict(sg0)
        for h, g, kum in offen:
            bh = bisect.bisect_left(kum, rng.random())
            bg = 2 * bretter - bh
            bp[h] += bh
            bp[g] += bg
            if bh > bg:
                mp[h] += 2; sg[h] += 1
            elif bg > bh:
                mp[g] += 2; sg[g] += 1
            else:
                mp[h] += 1; mp[g] += 1
        reihe = sorted(teams, key=lambda t: (-mp[t], -bp[t], -sg[t], rng.random()))
        for p, t in enumerate(reihe, 1):
            platz[t][p] += 1
            zz = punkte[t].setdefault(mp[t], {})
            zz[z[p]] = zz.get(z[p], 0) + 1
    erg = {}
    for t in teams:
        pv = [100 * platz[t][p] / anzahl for p in range(1, n + 1)]
        summe = lambda art: sum(pv[p - 1] for p in range(1, n + 1) if z[p] == art)
        erg[t] = {
            "platz": [round(x, 1) for x in pv],
            "auf": round(summe("auf"), 1), "auf_evtl": round(summe("auf_evtl"), 1),
            "ab": round(summe("ab"), 1), "ab_evtl": round(summe("ab_evtl"), 1),
            "schnitt": round(sum(p * pv[p - 1] for p in range(1, n + 1)) / 100, 2),
            "punkte": {str(k): {a: round(100 * c / anzahl, 2) for a, c in v.items()} for k, v in sorted(punkte[t].items())},
            "staerke": round(stark[t]),
        }
    return erg


def berechnen(d):
    """-> {"aktuell": {...}, "verlauf": {tlnr: [(runde, auf, auf_evtl, ab, ab_evtl, schnitt), ...]}, "runde": r} oder None."""
    runde = d.get("aktuelle_runde") or 0
    if not d.get("teams") or not d.get("matches") or d.get("archiv"):
        return None
    if all(m.get("gesp") for m in d["matches"]):
        return None                    # Saison fertig: nichts mehr vorherzusagen
    seed = lambda r: f'{d.get("key")}-{d.get("saison")}-{r}-' + json.dumps(
        [(m["r"], m["h"], m["g"], m.get("bh"), m.get("bg")) for m in d["matches"] if m.get("gesp") and m["r"] <= r])
    aktuell = simulieren(d, runde, SIMULATIONEN, seed(runde))
    verlauf = {}
    for r in range(0, runde):
        e = simulieren(d, r, SIMULATIONEN_VERLAUF, seed(r))
        for t, w in e.items():
            verlauf.setdefault(t, []).append((r, w["auf"], w["auf_evtl"], w["ab"], w["ab_evtl"], w["schnitt"]))
    for t, w in aktuell.items():
        verlauf.setdefault(t, []).append((runde, w["auf"], w["auf_evtl"], w["ab"], w["ab_evtl"], w["schnitt"]))
    return {"aktuell": aktuell, "verlauf": verlauf, "runde": runde, "zonen": zonen(d, len(d["teams"]))}


# ------------------------------------------------------------
# Anzeige (Reiter "Prognose" auf der Mannschaftsseite)
# ------------------------------------------------------------
import html as _html

LIGAORAKEL = "https://www.schachklub-bad-homburg.de/LigaOrakel/LigaOrakel.php"
# Staffel beim LigaOrakel je Mannschaft (steht in dessen Adresse: ...LigaOrakel.php?staffel=BAY_MUN_A1).
# A-, B- und C-Klasse gibt es dort zweimal (A1/A2 …) – welche, sieht man nur auf deren Seite. Fehlt ein
# Eintrag, verlinkt die Seite auf die Münchner Ligen-Übersicht des LigaOrakels.
LIGAORAKEL_STAFFEL = {"Bezirksliga": "BAY_MUN_BL", "D-Klasse": "BAY_MUN_D", "E-Klasse": "BAY_MUN_E"}
LIGAORAKEL_STAFFEL_TEAM = {}       # z. B. {"mf2": "BAY_MUN_A1", "mf3": "BAY_MUN_B2", "mf4": "BAY_MUN_C1"}


def _e(x):
    return _html.escape(str(x), quote=True)


def _pz(x, nachkomma=1):
    return f"{x:.{nachkomma}f}".replace(".", ",")


def _ligaorakel_link(d):
    from urllib.parse import quote_plus
    staffel = LIGAORAKEL_STAFFEL_TEAM.get(d.get("key")) or LIGAORAKEL_STAFFEL.get(d.get("klasse") or "")
    if (d.get("quelle") or "Schachbezirk") != "Schachbezirk":
        return f'<a href="{LIGAORAKEL}" target="_blank" rel="noopener">Zum Vergleich: LigaOrakel ↗</a>'
    if not staffel:
        return f'<a href="{LIGAORAKEL}?staffel=BAY_MUN_BL" target="_blank" rel="noopener">Zum Vergleich: LigaOrakel (Münchner Ligen) ↗</a>'
    eigen = d.get("eigen_name") or d["teams"].get(str(d.get("eigen")), "")
    return (f'<a href="{LIGAORAKEL}?staffel={staffel}&amp;team={quote_plus(eigen)}" target="_blank" '
            f'rel="noopener">Zum Vergleich: LigaOrakel ↗</a>')


ZONE_FARBE = {"auf": "#3fae6c", "auf_evtl": "rgba(63,174,108,.5)", "": "#6b7a99",
              "ab_evtl": "rgba(224,90,79,.5)", "ab": "#e05a4f"}
ZONE_TEXT = {"auf": "Aufstieg", "auf_evtl": "evtl. Aufstieg", "": "Verbleib", "ab_evtl": "evtl. Abstieg", "ab": "Abstieg"}


def _wert_evtl(sicher, evtl, art):
    zusatz = f'<small>+{_pz(evtl)} evtl.</small>' if evtl >= 0.05 else ""
    return f'<td class="pr-{art}">{_pz(sicher)}{zusatz}</td>'


def _balken(werte, max_h=120):
    """werte: [(beschriftung, [(farbe, prozent), ...], titel)] -> Säulendiagramm (HTML)."""
    hoechst = max((sum(p for _, p in teile) for _, teile, _ in werte), default=1) or 1
    saeulen = "".join(
        f'<div class="pr-s" title="{_e(titel)}">' + "".join(
            f'<i style="height:{p / hoechst * max_h:.1f}px;background:{f}"></i>' for f, p in teile if p > 0) + "</div>"
        for _, teile, titel in werte)
    achse = "".join(f"<span>{_e(b)}</span>" for b, _, _ in werte)
    return f'<div class="pr-saeulen" style="height:{max_h}px">{saeulen}</div><div class="pr-achse">{achse}</div>'


def _verlauf_svg(punkte, runden):
    """punkte: [(runde, auf, auf_evtl, ab, ab_evtl, schnitt)] -> Linien Aufstieg/Abstieg in %."""
    if len(punkte) < 2:
        return '<p class="klein">Der Verlauf entsteht ab der 2. Runde.</p>'
    B, H, L, R, O, U = 640, 200, 36, 12, 12, 26
    x = lambda r: L + r * (B - L - R) / max(runden, 1)
    y = lambda p: O + (100 - p) * (H - O - U) / 100
    gitter = "".join(f'<line x1="{L}" x2="{B - R}" y1="{y(p):.1f}" y2="{y(p):.1f}" class="g"/>'
                     f'<text x="{L - 6}" y="{y(p) + 4:.1f}" text-anchor="end">{p}%</text>' for p in (0, 25, 50, 75, 100))
    achse = "".join(f'<text x="{x(r):.1f}" y="{H - 6}" text-anchor="middle">{"Start" if r == 0 else f"R{r}"}</text>'
                    for r in range(0, runden + 1))
    def linie(wert, kl, punkte_zeigen=True):
        pkt = [(q[0], wert(q)) for q in punkte]
        out = f'<polyline class="{kl}" points="' + " ".join(f"{x(r):.1f},{y(v):.1f}" for r, v in pkt) + '"/>'
        if punkte_zeigen:
            out += "".join(f'<circle class="{kl}" cx="{x(r):.1f}" cy="{y(v):.1f}" r="4"><title>'
                           f'{"Start" if r == 0 else f"nach Runde {r}"}: {_pz(v)} %</title></circle>' for r, v in pkt)
        return out
    mit_evtl_auf = any(q[2] >= 0.05 for q in punkte)
    mit_evtl_ab = any(q[4] >= 0.05 for q in punkte)
    linien = ((linie(lambda q: q[1] + q[2], "auf evtl", False) if mit_evtl_auf else "") +
              (linie(lambda q: q[3] + q[4], "ab evtl", False) if mit_evtl_ab else "") +
              linie(lambda q: q[1], "auf") + linie(lambda q: q[3], "ab"))
    legende = ('<span><i style="background:#3fae6c"></i>Aufstieg</span><span><i style="background:#e05a4f"></i>Abstieg</span>'
               + ('<span><i class="gestr"></i>gestrichelt: inkl. „evtl.“</span>' if mit_evtl_auf or mit_evtl_ab else ""))
    return (f'<svg class="pr-verlauf" viewBox="0 0 {B} {H}" role="img" aria-label="Verlauf der Auf- und Abstiegschance">'
            f'{gitter}{achse}{linien}</svg><div class="pr-legende">{legende}</div>')


def _detail(d, t, w, verlauf, z, n, offen):
    name = d["teams"][str(t)]
    verbleib = max(0.0, 100 - w["auf"] - w["auf_evtl"] - w["ab"] - w["ab_evtl"])
    kachel = lambda wert, evtl, text, kl: (f'<div class="pr-k {kl}"><b>{_pz(wert)} %</b><span>{text}</span>'
                                           + (f'<small>+ {_pz(evtl)} % evtl.</small>' if evtl >= 0.05 else "") + "</div>")
    plaetze = [(f"{p}.", [(ZONE_FARBE[z[p]], w["platz"][p - 1])], f"Platz {p}: {_pz(w['platz'][p - 1])} %") for p in range(1, n + 1)]
    pk = w["punkte"]
    if pk:
        lo, hi = min(int(k) for k in pk), max(int(k) for k in pk)
        punkte = [(str(m), [(ZONE_FARBE[a], pk.get(str(m), {}).get(a, 0)) for a in ("", "ab_evtl", "ab", "auf_evtl", "auf")],
                   f"{m} Punkte: {_pz(sum(pk.get(str(m), {}).values()))} %") for m in range(lo, hi + 1)]
    else:
        punkte = []
    return f"""<div class="pr-detail" data-pr="{t}"{"" if offen else " hidden"}>
  <h3>{_e(name)} <span class="klein">· DWZ-Schnitt ca. {w["staerke"]}</span></h3>
  <div class="pr-kacheln">{kachel(w["auf"], w["auf_evtl"], "Aufstieg", "auf")}{kachel(verbleib, 0, "Verbleib", "")}{kachel(w["ab"], w["ab_evtl"], "Abstieg", "ab")}</div>
  <div class="pr-grafiken">
    <div><h4>Wahrscheinlichkeit für Platzierung</h4>{_balken(plaetze)}</div>
    <div><h4>Wahrscheinlichkeit für Punkte am Saisonende</h4>{_balken(punkte)}
      <div class="pr-legende">{"".join(f'<span><i style="background:{ZONE_FARBE[a]}"></i>{ZONE_TEXT[a]}</span>' for a in ("auf", "auf_evtl", "", "ab_evtl", "ab") if any(a in v for v in pk.values()))}</div></div>
  </div>
  <h4>Saisonverlauf</h4>{_verlauf_svg(verlauf, d.get("runden") or n)}
</div>"""


def reiter_prognose(d):
    try:
        e = berechnen(d)
    except Exception as fehler:          # Prognose darf die Seite nie kaputt machen
        print(f"Prognose {d.get('kurz')}: {type(fehler).__name__}: {fehler}")
        return ""
    if not e:
        return ""
    akt, z, n, eigen = e["aktuell"], e["zonen"], len(d["teams"]), d.get("eigen")
    reihe = sorted(akt, key=lambda t: akt[t]["schnitt"])
    kopf = "".join(f'<th class="pr-z-{z[p] or "x"}">{p}.</th>' for p in range(1, n + 1))
    zeilen = ""
    for i, t in enumerate(reihe, 1):
        w = akt[t]
        zellen = "".join(f'<td style="background:rgba(63,174,108,{min(p / 35, 1) * .75:.2f})">{_pz(p)}</td>' for p in w["platz"])
        zeilen += (f'<tr data-pr="{t}"{" class=pr-ich" if t == eigen else ""} tabindex="0"><td class="pr-name"><span>{i}.</span>'
                   f'{_e(d["teams"][str(t)])}</td>{_wert_evtl(w["auf"], w["auf_evtl"], "auf")}{_wert_evtl(w["ab"], w["ab_evtl"], "ab")}{zellen}</tr>')
    runde = e["runde"]
    stand = f"nach Runde {runde} von {d.get('runden')}" if runde else "vor dem 1. Spieltag"
    details = "".join(_detail(d, t, akt[t], e["verlauf"].get(t, []), z, n, t == eigen) for t in reihe)
    return f"""{PROGNOSE_STYLE}
<p class="klein">{SIMULATIONEN:,} simulierte Saisons · Stand {stand} · Werte in % · Zeile antippen = Details</p>
<div class="tab-wrap"><table class="pr-tab">
  <thead><tr><th class="pr-name">Mannschaft (nach Prognose)</th><th>Auf&shy;stieg</th><th>Ab&shy;stieg</th>{kopf}</tr></thead>
  <tbody>{zeilen}</tbody></table></div>
<p class="klein">Je grüner, desto wahrscheinlicher. Linien im Tabellenkopf: Auf-/Abstiegsplätze laut Schachbezirk
  (gestrichelt = „evtl.“). Spielstärke aus den DWZ der gespielten Aufstellungen und der Meldeliste – eine Schätzung,
  keine Garantie. {_ligaorakel_link(d)}</p>
{details}
{PROGNOSE_JS}""".replace(f"{SIMULATIONEN:,}", f"{SIMULATIONEN:,}".replace(",", "."))


PROGNOSE_STYLE = """<style>
  .pr-tab { width: 100%; border-collapse: collapse; font-size: .88rem; font-variant-numeric: tabular-nums; }
  .pr-tab th { font-size: .76rem; color: var(--muted); padding: .45rem .3rem; border-bottom: 2px solid var(--line); font-weight: 600; text-align: center; }
  .pr-tab th.pr-z-auf { border-bottom-color: #3fae6c; } .pr-tab th.pr-z-auf_evtl { border-bottom: 2px dashed #3fae6c; }
  .pr-tab th.pr-z-ab { border-bottom-color: #e05a4f; } .pr-tab th.pr-z-ab_evtl { border-bottom: 2px dashed #e05a4f; }
  .pr-tab td { padding: .42rem .3rem; border-bottom: 1px solid var(--line); text-align: center; min-width: 2.6rem; }
  .pr-tab .pr-name { text-align: left; white-space: nowrap; }
  .pr-tab td.pr-name span { color: var(--muted); font-size: .8rem; margin-right: .35rem; }
  .pr-tab td.pr-auf { color: #3fae6c; font-weight: 700; } .pr-tab td.pr-ab { color: #e05a4f; font-weight: 700; }
  .pr-tab td small { display: block; font-size: .7rem; font-weight: 500; opacity: .85; }
  .pr-tab tbody tr { cursor: pointer; } .pr-tab tbody tr:hover td { filter: brightness(1.15); }
  .pr-tab tr.pr-ich td.pr-name { font-weight: 700; }
  .pr-tab tr.pr-ich td { box-shadow: inset 0 2px 0 #e8b931, inset 0 -2px 0 #e8b931; }
  .pr-tab tr.pr-aktiv td.pr-name { color: var(--link-c); }
  .pr-detail { border: 1px solid var(--line); background: var(--surface); border-radius: 12px; padding: 1.1rem 1.2rem; margin: 1.2rem 0; }
  .pr-detail h3 { margin: 0 0 .8rem; font-size: 1.05rem; } .pr-detail h4 { margin: 1.2rem 0 .5rem; font-size: .85rem; color: var(--muted); }
  .pr-kacheln { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem; }
  .pr-k { border-radius: 10px; padding: .65rem .9rem; background: var(--soft); }
  .pr-k b { display: block; font-size: 1.45rem; } .pr-k span { font-size: .82rem; color: var(--muted); }
  .pr-k small { display: block; font-size: .76rem; color: var(--muted); }
  .pr-k.auf b { color: #3fae6c; } .pr-k.ab b { color: #e05a4f; }
  .pr-grafiken { display: grid; grid-template-columns: 1fr 1.4fr; gap: 1.4rem; }
  .pr-saeulen { display: flex; align-items: flex-end; gap: 4px; border-bottom: 1px solid var(--line); }
  .pr-s { flex: 1; display: flex; flex-direction: column-reverse; border-radius: 3px 3px 0 0; overflow: hidden; min-width: 0; }
  .pr-s i { display: block; }
  .pr-achse { display: flex; gap: 4px; font-size: .7rem; color: var(--muted); margin-top: .25rem; }
  .pr-achse span { flex: 1; text-align: center; min-width: 0; }
  .pr-legende { display: flex; flex-wrap: wrap; gap: .4rem 1rem; font-size: .75rem; color: var(--muted); margin-top: .55rem; }
  .pr-legende i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: .3rem; vertical-align: -1px; }
  .pr-verlauf { width: 100%; height: auto; max-width: 720px; }
  .pr-verlauf text { font-size: 11px; fill: var(--muted); } .pr-verlauf .g { stroke: var(--line); }
  .pr-verlauf polyline { fill: none; stroke-width: 2.5; } .pr-verlauf polyline.auf { stroke: #3fae6c; } .pr-verlauf polyline.ab { stroke: #e05a4f; }
  .pr-verlauf circle.auf { fill: #3fae6c; } .pr-verlauf circle.ab { fill: #e05a4f; }
  .pr-verlauf polyline.evtl { stroke-width: 1.6; stroke-dasharray: 5 4; opacity: .6; }
  .pr-legende i.gestr { width: 16px; height: 0; border-top: 2px dashed var(--muted); border-radius: 0; vertical-align: 3px; }
  @media (max-width: 700px) { .pr-grafiken { grid-template-columns: 1fr; } .pr-k b { font-size: 1.2rem; } }
</style>"""

PROGNOSE_JS = """<script>
(function () {
  var zeilen = document.querySelectorAll(".pr-tab tbody tr[data-pr]"), det = document.querySelectorAll(".pr-detail");
  function zeige(t, scroll) {
    det.forEach(function (x) { x.hidden = x.dataset.pr !== t; });
    zeilen.forEach(function (z) { z.classList.toggle("pr-aktiv", z.dataset.pr === t); });
    var d = document.querySelector('.pr-detail[data-pr="' + t + '"]');
    if (scroll && d) d.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  zeilen.forEach(function (z) {
    z.addEventListener("click", function () { zeige(z.dataset.pr, true); });
    z.addEventListener("keydown", function (e) { if (e.key === "Enter") zeige(z.dataset.pr, true); });
  });
})();
</script>"""
