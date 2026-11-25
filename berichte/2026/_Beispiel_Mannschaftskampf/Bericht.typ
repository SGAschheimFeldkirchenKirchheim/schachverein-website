#import "../../_funktionen.typ": *

#title[Beispiel: Mannschaftskampf mit 8 Partien]
#date[21.11.2026]
#author[Korbinian Ruff]
#kategorie[afk 2]

// Beispielbericht für die Partien-Sammlung – kann über die Verwaltung wieder weg.
// Testweise 8-mal dieselbe Partie mit erfundenen Namen und Ergebnissen.

So sieht ein Mannschaftskampf mit allen Partien aus: oben die Paarungen mit Ergebnissen, darunter ein Brett. Ein Klick auf eine Zeile zeigt die Partie, unser Spieler steht immer unten.

#partien("partie1.pgn")

Mit dem Zusatz ergebnis: "ende" in der Partien-Zeile bleiben alle Ergebnisse und der Endstand verdeckt, bis man die jeweilige Partie durchgeklickt hat.
