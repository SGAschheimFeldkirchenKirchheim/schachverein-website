// Gemeinsame Funktionen für alle Berichte.
// Nur für die VS-Code-Vorschau, die Website ignoriert diese Datei.
#let date(body) = block(text(fill: gray, body))
#let author(body) = block(text(fill: gray, body))
#let entwurf(body) = block(text(fill: red, weight: "bold")[ENTWURF])