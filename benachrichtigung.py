"""
Mail-Benachrichtigungen: Neuigkeiten erkennen und ans Apps Script schicken (Benachrichtigung.gs, n_ereignisse).

Läuft am Ende von build_site.py, aber nur im GitHub-Build (GITHUB_ACTIONS) und nur mit KONTO_SCHLUESSEL.
Vergleicht mit dem letzten Stand in benachrichtigung_stand.json (wird mit committet):
  termine         neuer Termin (je Spalte: Verein, AFK 1 … Jugend), nur Zukunft
  aenderungen     Termin geändert / weg; neuer Ausfall (ausfall.txt) -> Spalte "Verein"
  ergebnisse      Mannschaftskampf gespielt (mannschaften/*.json)
  berichte        neuer Bericht
  erwaehnt        neuer Bericht verlinkt ein Profil oder enthält eine Partie des Mitglieds
  ausschreibungen neue PDF in Ausschreibungen/
Beim allerersten Lauf (oder neuer Kategorie) wird nur der Stand gemerkt, nichts gemeldet.
Umfragen, Listen und Turnierkalender meldet das Apps Script selbst.
"""

import datetime
import json
import os
import re

STAND = "benachrichtigung_stand.json"
MAX_JE_SPALTE = 6          # mehr neue Termine in einer Spalte (z. B. neue Saison) -> eine Sammelzeile


def _lade():
    try:
        with open(STAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _zahl(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x or "")
    return (f"{x:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def _datum_de(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d.weekday()]} {d.day:02d}.{d.month:02d}."


def ereignisse_bauen(alt, neu, site_url):
    """Reiner Vergleich (testbar): alt/neu = Stand-Dicts -> Liste von Ereignissen."""
    ev = []
    if not alt:
        return ev
    heute = datetime.date.today().isoformat()

    # --- Termine ---
    if "termine" in alt:
        at, nt = alt["termine"], neu["termine"]
        neue = {}
        for k, t in nt.items():
            if t["datum"] < heute:
                continue
            if k not in at:
                neue.setdefault(t["spalte"], []).append(t)
            elif (at[k]["text"], at[k]["zeit"]) != (t["text"], t["zeit"]):
                vorher = " ".join(x for x in (at[k]["zeit"], at[k]["text"]) if x)
                jetzt = " ".join(x for x in (t["zeit"], t["text"]) if x)
                ev.append({"thema": "aenderungen", "spalte": t["spalte"], "schluessel": f"t-{k}-{jetzt}",
                           "titel": f"{t['spalte']}: {_datum_de(t['datum'])}",
                           "text": f"jetzt: {jetzt} (vorher: {vorher})", "link": site_url + "termine.html"})
        for k, t in at.items():
            if t["datum"] >= heute and k not in nt:
                ev.append({"thema": "aenderungen", "spalte": t["spalte"], "schluessel": f"t-weg-{k}",
                           "titel": f"{t['spalte']}: {_datum_de(t['datum'])}{(' ' + t['zeit']) if t['zeit'] else ''}",
                           "text": f"„{t['text']}“ steht nicht mehr im Kalender (verschoben oder abgesagt?)", "link": site_url + "termine.html"})
        for spalte, liste in neue.items():
            liste.sort(key=lambda t: t["datum"])
            if len(liste) > MAX_JE_SPALTE:
                ev.append({"thema": "termine", "spalte": spalte, "schluessel": f"t-sammel-{spalte}-{liste[0]['datum']}-{len(liste)}",
                           "titel": f"{spalte}: {len(liste)} neue Termine",
                           "text": f"ab {_datum_de(liste[0]['datum'])}", "link": site_url + "termine.html"})
                continue
            for t in liste:
                ev.append({"thema": "termine", "spalte": spalte, "schluessel": f"t-neu-{t['datum']}-{spalte}-{t['text']}",
                           "titel": f"{_datum_de(t['datum'])}{(', ' + t['zeit']) if t['zeit'] else ''}",
                           "text": f"{spalte}: {t['text']}", "link": site_url + "termine.html"})

    # --- Ausfall (Spielabende) ---
    if "ausfall" in alt:
        for a in neu["ausfall"]:
            if a not in alt["ausfall"] and a.split("|")[1] >= heute:
                start, ende, grund = a.split("|", 2)
                wann = _datum_de(start) + ("" if start == ende else " – " + _datum_de(ende))
                ev.append({"thema": "aenderungen", "spalte": "Verein", "schluessel": "a-" + a,
                           "titel": "Spielabend fällt aus", "text": f"{wann}{(' – ' + grund) if grund else ''}",
                           "link": site_url + "termine.html"})

    # --- Ergebnisse ---
    if "ergebnisse" in alt:
        for k, e in neu["ergebnisse"].items():
            if k not in alt["ergebnisse"]:
                ev.append({"thema": "ergebnisse", "mannschaft": e["mannschaft"], "schluessel": "e-" + k,
                           "titel": f"{e['mannschaft']}: {e['ergebnis']}", "text": e["text"], "link": e["link"]})

    # --- Berichte + Erwähnungen ---
    if "berichte" in alt:
        for k, b in neu["berichte"].items():
            if k in alt["berichte"]:
                continue
            ev.append({"thema": "berichte", "schluessel": "b-" + k, "titel": b["titel"], "text": b.get("meta", ""), "link": b["link"]})
            if b.get("slugs"):
                ev.append({"thema": "erwaehnt", "slugs": b["slugs"], "schluessel": "m-" + k, "titel": b["titel"],
                           "text": "In diesem Bericht kommst du vor", "link": b["link"]})

    # --- Ausschreibungen ---
    if "ausschreibungen" in alt:
        for k, a in neu["ausschreibungen"].items():
            if k not in alt["ausschreibungen"]:
                ev.append({"thema": "ausschreibungen", "schluessel": "s-" + k, "titel": a["titel"],
                           "text": "Neue Ausschreibung", "link": a["link"]})
    return ev


def bericht_slugs(r, slug_fn):
    """Wer kommt in diesem Bericht vor? Profil-Links + Spieler aus den Partien (ohne den Autor)."""
    body = r.get("body", "")
    slugs = set(re.findall(r'spieler/([a-z0-9-]+)\.html', body))
    for name in re.findall(r'\[(?:White|Black) (?:"|&quot;)([^"&]+)(?:"|&quot;)\]', body):
        if "," in name:
            nach, vor = [x.strip() for x in name.split(",", 1)]
            slugs.add(slug_fn(f"{vor} {nach}"))
    slugs.discard(r.get("autor_slug", ""))
    return {s for s in slugs if s}


def meine_json(termine, berichte, teams, site_url, slug_fn, tage=120):
    """spieler/meine.json für "Meine nächsten Termine" / "Meine Berichte" im Profil (nur öffentliche Daten)."""
    bis = datetime.date.today() + datetime.timedelta(days=tage)
    kader = {}
    for d in teams:
        spalte = "Jugend" if str(d.get("kurz", "")).startswith("U") else d.get("kurz", "")
        for k in d.get("kader") or []:
            name = str(k.get("name", "")).strip()
            if "," in name:
                nach, vor = [x.strip() for x in name.split(",", 1)]
                name = f"{vor} {nach}"
            s = slug_fn(name) if name else ""
            if s and spalte and spalte not in kader.setdefault(s, []):
                kader[s].append(spalte)
    erw = {}
    for r in berichte:
        for s in bericht_slugs(r, slug_fn):
            erw.setdefault(s, []).append({"titel": re.sub(r"<[^>]+>", "", r.get("title", "")), "link": "berichte/" + r["filename"],
                                          "datum": r["when"].isoformat() if hasattr(r.get("when"), "isoformat") and r["when"].year > 1 else ""})
    for s in erw:
        erw[s].sort(key=lambda x: x["datum"], reverse=True)
        erw[s] = erw[s][:20]
    return {"stand": datetime.date.today().isoformat(),
            "termine": [{"datum": t["datum"].isoformat(), "zeit": t["zeit"], "spalte": t["spalte"], "text": t["text"]}
                        for t in termine if t["datum"] <= bis],
            "kader": kader, "berichte": erw}


def stand_bauen(termine, ausfaelle, berichte, ausschreibungen, teams, site_url, slug_fn, seite_fn):
    """Aktuellen Stand aus den Build-Daten zusammenstellen."""
    st = {"stand": datetime.datetime.now().isoformat(timespec="minutes"), "termine": {}, "ausfall": [],
          "ergebnisse": {}, "berichte": {}, "ausschreibungen": {}}
    for t in termine:          # {"datum": date, "zeit", "spalte", "text"}
        k = f"{t['datum'].isoformat()}|{t['spalte']}"
        st["termine"][k] = {"datum": t["datum"].isoformat(), "zeit": t["zeit"], "spalte": t["spalte"], "text": t["text"]}
    st["ausfall"] = sorted(f"{a['start']}|{a['end']}|{a.get('reason') or ''}" for a in ausfaelle)
    for d in teams:
        teamnamen, eigen = d.get("teams") or {}, d.get("eigen")
        for m in d.get("matches") or []:
            if not m.get("gesp") or eigen is None or eigen not in (m.get("h"), m.get("g")):
                continue
            heim = m.get("h") == eigen
            gegner = teamnamen.get(str(m.get("g") if heim else m.get("h")), "?")
            wir, sie = (m.get("bh"), m.get("bg")) if heim else (m.get("bg"), m.get("bh"))
            k = f"{d.get('kurz')}|{d.get('saison')}|{m.get('r')}"
            st["ergebnisse"][k] = {"mannschaft": d.get("kurz", ""), "ergebnis": f"{_zahl(wir)} : {_zahl(sie)}",
                                   "text": f"Runde {m.get('r')} {'gegen' if heim else 'bei'} {gegner}", "link": site_url + seite_fn(d)}
    for r in berichte:
        slugs = bericht_slugs(r, slug_fn)
        st["berichte"][r["stem"]] = {"titel": re.sub(r"<[^>]+>", "", r.get("title", "")), "meta": re.sub(r"<[^>]+>", "", r.get("meta", "")),
                                    "link": site_url + "berichte/" + r["filename"], "slugs": sorted(s for s in slugs if s)}
    for a in ausschreibungen:
        st["ausschreibungen"][a["name"]] = {"titel": a["label"], "link": site_url + a["url"]}
    return st


def melden(termine, ausfaelle, berichte, ausschreibungen, teams, site_url, slug_fn, seite_fn, senden):
    """senden(ereignisse) -> Antwort-Dict. Stand wird nur gespeichert, wenn das Melden geklappt hat (oder nichts zu melden war)."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        neu = stand_bauen(termine, ausfaelle, berichte, ausschreibungen, teams, site_url, slug_fn, seite_fn)
        alt = _lade()
        ev = ereignisse_bauen(alt, neu, site_url)
        if ev:
            a = senden(ev)
            if not a or not a.get("ok"):
                print(f"Benachrichtigungen: nicht gemeldet ({(a or {}).get('fehler', 'keine Antwort')}) – nächster Build versucht es nochmal.")
                return
            print(f"Benachrichtigungen: {len(ev)} Neuigkeiten gemeldet, {a.get('eingereiht', 0)} Mails vorgemerkt.")
        with open(STAND, "w", encoding="utf-8") as f:
            json.dump(neu, f, ensure_ascii=False, indent=0, sort_keys=True)
    except Exception as e:
        print(f"Benachrichtigungen: übersprungen ({type(e).__name__}: {e})")
