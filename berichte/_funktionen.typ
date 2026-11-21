// Gemeinsame Funktionen für alle Berichte.
// Nur für die VS-Code-Vorschau, die Website ignoriert diese Datei.
#let date(body) = block(text(fill: gray, body))
#let author(body) = block(text(fill: gray, body))
#let entwurf(body) = block(text(fill: red, weight: "bold")[ENTWURF])
#let kategorie(body) = block(text(fill: gray)[Kategorie: #body])
// Partie (PGN-Datei im selben Ordner) und chess-results-Tabelle: auf der Website interaktiv, hier nur ein Platzhalter
#let partie(datei, ab: 0, sicht: "w", ergebnis: "") = block(fill: luma(240), inset: 8pt, radius: 4pt, width: 100%)[Partie: #datei]
#let partien(datei, ergebnis: "") = block(fill: luma(240), inset: 8pt, radius: 4pt, width: 100%)[Partien: #datei]
#let tabelle(url) = block(fill: luma(240), inset: 8pt, radius: 4pt, width: 100%)[Tabelle: #link(url)]
