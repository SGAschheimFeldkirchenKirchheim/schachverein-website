"""
Mitgliederbereich: Login, eigenes Profil, Verwaltung.

Das Backend ist das Apps Script (AppsScript/Mitglieder.gs, gleiche Web-App wie einreichen.SKRIPT_URL).
Dieser Teil des Builds
  1. schickt die Mitgliederliste (Name, Geburtsdatum, Slug der Spielerseite) ans Script  -> Registrierung prüfen, Austritte erkennen
  2. holt die öffentlichen Profildaten und Fotos der registrierten Mitglieder ab          -> spieler/konten.json, spieler/fotos_konto/
  3. baut die Seiten mein-profil.html und verwaltung.html (Inhalt kommt per konto.js)

Ohne Schlüssel (oder offline) wird der letzte Stand aus spieler/konten.json benutzt.

Schlüssel: im Apps-Script-Editor syncSchluesselZeigen() ausführen, dann
  - GitHub: Settings -> Secrets and variables -> Actions -> New secret  KONTO_SCHLUESSEL
  - lokal:  Datei konto_schluessel.txt in C:\\Python\\Schach (eine Zeile, NICHT ins Website-Repo)
"""
import os
import json
import base64
import datetime

import einreichen

# ---------------- Einstellungen ----------------
AN = True                                    # Mitgliederbereich (Login-Knopf, Seiten) einschalten
SKRIPT_URL = einreichen.SKRIPT_URL           # Web-App-URL des Apps Scripts
DATEN = os.path.join("spieler", "konten.json")          # öffentliche Profildaten (wird mit committet)
FOTO_ORDNER = os.path.join("spieler", "fotos_konto")    # hochgeladene Profilfotos (wird mit committet)
SCHLUESSEL_DATEIEN = [os.path.join("..", "konto_schluessel.txt"), os.path.join("..", "..", "konto_schluessel.txt")]
NUR_OEFFENTLICHE_GEBURTSTAGE = True          # Startseite & Co.: nur Geburtstage, die das Mitglied selbst öffentlich gestellt hat
TIMEOUT = 60
# ------------------------------------------------

PROFILE = {}          # slug -> Profil (nach laden())


def script_tag(css_path, nav_path):
    if not AN or not SKRIPT_URL:
        return ""
    return f'<script src="{css_path}konto.js" data-skript="{SKRIPT_URL}" data-pfad="{nav_path}" defer></script>'


def _schluessel():
    s = os.environ.get("KONTO_SCHLUESSEL", "").strip()
    if s:
        return s
    for p in SCHLUESSEL_DATEIEN:
        try:
            with open(p, encoding="utf-8") as f:
                s = f.read().strip()
            if s:
                return s
        except OSError:
            pass
    return ""


def _post(daten):
    import requests
    r = requests.post(SKRIPT_URL, data=json.dumps(daten), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def synchronisieren(mitglieder, slug):
    """Mitgliederliste ans Script schicken. mitglieder = [{'vorname','nachname','geburtstag' (TT.MM.JJJJ)}]."""
    s = _schluessel()
    if not AN or not s or not mitglieder:
        return
    liste = [{"vorname": m.get("vorname", ""), "nachname": m.get("nachname", ""), "geburtstag": m.get("geburtstag", ""),
              "slug": slug(f"{m.get('vorname', '')} {m.get('nachname', '')}")} for m in mitglieder]
    try:
        a = _post({"typ": "m_sync", "s": s, "mitglieder": liste})
        print(f"Mitgliederbereich: {a.get('anzahl', '?')} Mitglieder abgeglichen" if a.get("ok")
              else f"Mitgliederbereich: Abgleich abgelehnt ({a.get('fehler')})")
    except Exception as e:
        print(f"Mitgliederbereich: Abgleich nicht möglich ({type(e).__name__})")


def _alt_laden():
    try:
        with open(DATEN, encoding="utf-8") as f:
            return {p["slug"]: p for p in json.load(f)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def laden():
    """Öffentliche Profile holen (sonst letzter Stand). Fotos nur neu laden, wenn sie sich geändert haben."""
    global PROFILE
    alt = _alt_laden()
    s = _schluessel()
    if not AN or not s:
        PROFILE = alt
        return PROFILE
    try:
        a = _post({"typ": "m_export", "s": s})
        if not a.get("ok"):
            raise ValueError(a.get("fehler"))
        neu = {p["slug"]: p for p in a.get("profile", [])}
    except Exception as e:
        print(f"Mitgliederbereich: Profile nicht abrufbar ({type(e).__name__}: {e}) – letzter Stand")
        PROFILE = alt
        return PROFILE
    os.makedirs(FOTO_ORDNER, exist_ok=True)
    for slug, p in neu.items():
        pfad = os.path.join(FOTO_ORDNER, slug + ".jpg")
        if not p.get("foto"):
            if os.path.exists(pfad):
                os.remove(pfad)
            continue
        if alt.get(slug, {}).get("foto") == p["foto"] and os.path.exists(pfad):
            continue
        try:
            f = _post({"typ": "m_foto_export", "s": s, "benutzer": p["benutzer"]})
            if f.get("ok"):
                with open(pfad, "wb") as out:
                    out.write(base64.b64decode(f["bild"]))
        except Exception as e:
            print(f"Mitgliederbereich: Foto von {p['name']} nicht geladen ({type(e).__name__})")
            p["foto"] = alt.get(slug, {}).get("foto", 0) if os.path.exists(pfad) else 0
    for slug in set(alt) - set(neu):                      # gelöscht/ausgeblendet/ausgetreten -> Foto weg
        pfad = os.path.join(FOTO_ORDNER, slug + ".jpg")
        if os.path.exists(pfad):
            os.remove(pfad)
    os.makedirs(os.path.dirname(DATEN), exist_ok=True)
    with open(DATEN, "w", encoding="utf-8") as f:
        json.dump(sorted(neu.values(), key=lambda p: p["slug"]), f, ensure_ascii=False, indent=1)
    PROFILE = neu
    print(f"Mitgliederbereich: {len(neu)} registrierte Profile")
    return PROFILE


def foto(slug):
    pfad = os.path.join(FOTO_ORDNER, slug + ".jpg")
    return pfad.replace(os.sep, "/") if slug in PROFILE and os.path.exists(pfad) else ""


def geburtstag_oeffentlich(slug):
    """Darf der Geburtstag dieses Mitglieds öffentlich (Startseite) gezeigt werden?"""
    if not NUR_OEFFENTLICHE_GEBURTSTAGE:
        return True
    return PROFILE.get(slug, {}).get("gb") == "oeffentlich"


def seiten_bauen(render_page):
    """mein-profil.html, verwaltung.html, listen.html und umfrage.html (Inhalt baut konto.js im Browser)."""
    if not AN or not SKRIPT_URL:
        return
    for datei, titel, art in (("mein-profil.html", "Mein Profil", "profil"), ("verwaltung.html", "Verwaltung", "verwaltung"),
                             ("listen.html", "Listen", "listen"), ("umfrage.html", "Umfrage", "umfrage"),
                             ("mitmachen.html", "Mitmachen", "mitmachen")):
        content = (f'<h1>{titel}</h1><div id="kt-seite" data-seite="{art}">'
                   '<noscript><p>Für diese Seite wird JavaScript benötigt.</p></noscript></div>')
        render_page(titel, content, datei, description=f"{titel} – Mitgliederbereich der SG AFK.")
