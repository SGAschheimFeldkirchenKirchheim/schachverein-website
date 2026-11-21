#import "../_funktionen.typ": *
// =====================================================================
// VORLAGE für einen Bericht – alles, was die Website versteht.
// Benutzen: Ordner kopieren nach berichte/<Jahr>/<Kurzname>/ (ohne "_" vorne!)
// und hier "../_funktionen.typ" durch "../../_funktionen.typ" ersetzen.
// Ordner mit "_" vorne (wie dieser) werden NICHT auf die Website gebaut.
// Einfacher geht es auf der Website unter Berichte -> Bericht schreiben.
// =====================================================================

// ---------- Kopf ----------
#title[Titel des Berichts]
#date[21.11.2026]                       // TT.MM.JJJJ – bestimmt die Reihenfolge
#author[Vor- und Nachname]              // wird zum Profil verlinkt, wenn es eins gibt
#kategorie[turnier, afk 2]              // turnier, jugend, senioren, afk 1 … afk 6, verein (mehrere mit Komma)

// ---------- Steuerzeilen (optional) ----------
// Diese Zeilen stehen allein in einer Zeile und beginnen mit "//" – sie erscheinen nicht im Text.
// Zum Benutzen die passende Zeile ohne das führende "x" übernehmen:
//x // titelbild: foto2.jpg      -> Vorschaubild in der Übersicht (sonst das erste Bild)
//x // entwurf                   -> Bericht wird nicht gebaut (Alternative: Ordnername mit "_" beginnen)
//x // gast                      -> Autor nicht bestätigt, Name wird nicht verlinkt
//x // konto: benutzername       -> setzt die Website selbst (wer es geschrieben hat)

// ---------- Text ----------
Der erste Absatz erscheint auch als Vorschautext in der Übersicht. Leere Zeile = neuer Absatz.

Im Text gehen *fett*, _kursiv_ und Links wie #link("https://www.schachbund-bayern.de")[Bayerischer Schachbund]. \
Ein Backslash am Zeilenende macht einen Zeilenumbruch ohne neuen Absatz.

= Zwischenüberschrift
== Kleinere Überschrift

- Aufzählung mit Strich
- noch ein Punkt

+ nummerierte Liste
+ zweiter Punkt

// ---------- Bilder (Datei im selben Ordner; alt = Bildunterschrift) ----------
#image("foto1.jpg", alt: "Bildunterschrift zum ersten Foto")

// ---------- Partie zum Nachspielen (PGN-Datei im selben Ordner) ----------
//   ab:       Halbzug, bei dem das Brett startet: 0 = Grundstellung, -1 = Schlussstellung,
//             z. B. 18 = vor dem 10. Zug von Weiß, 19 = vor dem 10. Zug von Schwarz
//   sicht:    "w" oder "b" – diese Farbe steht unten
//   ergebnis: "ende" – Ergebnis erst nach dem letzten Zug verraten (weglassen = oben neben den Namen)
// Namen und Ergebnis kommen aus der PGN ([White "…"], [Black "…"], [Result "…"]).
#partie("partie1.pgn", ab: 0, sicht: "w", ergebnis: "ende")

// ---------- Tabelle von chess-results (Endstand bzw. aktueller Stand) ----------
// Wird beim Build geholt; in den ersten 30 Tagen nach dem Datum jede Nacht neu.
#tabelle("https://chess-results.com/tnr1171232.aspx")
