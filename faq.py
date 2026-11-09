"""
FAQ-Seite (faq.html): häufige Fragen, aufklappbar und nach Themen gruppiert.

Fragen hier unter FRAGEN pflegen: (Thema, [(Frage, Antwort-HTML), ...]).
Platzhalter in Antworten:
  {beitraege}  Liste der Jahresbeiträge (aus build_site.BEITRAEGE)
  {spielort}   Adresse des Spielorts (aus build_site.SPIELORT, ohne Gebäudenamen)
build_site.py ruft seite() auf.
"""

import html

# ==========================================
# FRAGEN
# ==========================================
FRAGEN = [
    ("Vorbeikommen", [
        ("Muss ich mich anmelden?",
         'Nein. Komm einfach freitags vorbei. Wer mag, meldet sich vorher über das '
         '<a href="kontakt.html">Kontaktformular</a>.'),
        ("Brauche ich Vorkenntnisse?",
         "Nein. Einsteiger sind genauso willkommen wie Turnierspieler. Die Regeln bringen wir dir gern bei."),
        ("Kostet das Schnuppern etwas?",
         "Nein, Schnuppern ist kostenlos und unverbindlich, so oft du willst."),
        ("Was muss ich mitbringen?",
         "Nichts. Bretter, Figuren und Uhren sind vor Ort."),
        ("Wann und wo spielt ihr?",
         "Jeden Freitag im Gymnasium Kirchheim (GyKi), {spielort}. Die Jugend trainiert von 18:00 bis 19:30 Uhr, "
         "Erwachsene spielen ab 19:30 Uhr mit Open End. Das GyKi ist eine Schachschule und unser Spielort. "
         '<a href="neu-hier.html">So kommst du vorbei →</a>'),
        ("Findet der Spielabend auch in den Ferien statt?",
         'Meistens ja. Fällt ein Abend aus, steht das auf der <a href="index.html">Startseite</a> und im '
         '<a href="termine.html">Spielplan</a>.'),
    ]),
    ("Mitgliedschaft", [
        ("Was kostet die Mitgliedschaft?",
         "Der Jahresbeitrag beträgt: {beitraege}"),
        ("Wie werde ich Mitglied?",
         'Mitgliedsantrag <a href="mitgliederantrag.pdf" download>als PDF herunterladen</a>, ausfüllen und am Spielabend '
         'abgeben oder an <a href="mailto:info@sg-afk.de">info@sg-afk.de</a> schicken.'),
    ]),
    ("Spielbetrieb", [
        ("Muss ich Mannschaft spielen?",
         "Nein, das ist freiwillig. Wer Lust hat, kann in einer unserer "
         '<a href="mannschaften.html">Mannschaften</a> mitspielen, bei den '
         '<a href="senioren.html">Senioren</a> oder in der <a href="jugend.html">Jugend</a>.'),
        ("Was bedeuten MMM und MSMM?",
         "MMM ist die Münchner Mannschaftsmeisterschaft, MSMM die Münchner Senioren-Mannschaftsmeisterschaft. "
         "In diesen Ligen spielen unsere Mannschaften."),
        ("Was ist die DWZ?",
         "Die Deutsche Wertungszahl misst die Spielstärke. Sie entsteht automatisch, sobald du gewertete "
         'Turnier- oder Mannschaftspartien spielst. <a href="https://www.schachbund.de/dwz.html" target="_blank" '
         'rel="noopener">Mehr beim Deutschen Schachbund ↗</a>'),
        ("Gibt es Turniere im Verein?",
         'Ja, z. B. die Blitzjahreswertung, die Vereinsmeisterschaft und das Oberlandquartett. '
         '<a href="turniere.html">Zu den Turnieren →</a>'),
    ]),
    ("Kinder & Jugendliche", [
        ("Gibt es ein Jugendtraining?",
         'Ja, jeden Freitag von 18:00 bis 19:30 Uhr. Alles für Eltern steht auf der '
         '<a href="jugend.html">Jugendseite</a>.'),
    ]),
]


# ==========================================
# SEITE
# ==========================================
def esc(x):
    return html.escape(str(x if x is not None else ""))


def seite(beitraege=(), spielort=""):
    """faq.html. beitraege: [(wer, preis), ...]. Rückgabe (content, styles)."""
    b_html = "<ul>" + "".join(f"<li>{wer}: <strong>{preis}</strong></li>" for wer, preis in beitraege) + "</ul>"
    gruppen = []
    for thema, fragen in FRAGEN:
        eintraege = "".join(
            f'<details class="faq-eintrag"><summary>{esc(f)}</summary>'
            f'<div class="faq-antwort">{a.format(beitraege=b_html, spielort=esc(spielort))}</div></details>'
            for f, a in fragen)
        gruppen.append(f'<section class="faq-gruppe"><h2>{esc(thema)}</h2>{eintraege}</section>')

    content = f"""
    <h1>Häufige Fragen</h1>
    <p>Deine Frage ist nicht dabei? <a href="kontakt.html">Schreib uns</a> oder komm einfach freitags vorbei.</p>
    {"".join(gruppen)}
    """
    return content, ""
