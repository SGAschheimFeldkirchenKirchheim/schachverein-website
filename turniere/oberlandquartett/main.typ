#set page(width: 22cm, height: auto, margin: 1.5cm)
#set text(size: 10pt)

#let navy = rgb("#0a1f44")
#let gold = rgb("#ffd54a")
#let navy-light = rgb("#eef1f8")

// ============ HIER TRAGT IHR EURE DATEN EIN ============

// Reihenfolge der Teams = Reihenfolge der Ergebnis-Spalten in der Tabelle
#let teams = ("AFK", "Deisenhofen", "Holzkirchen", "Höhenkirchen")

// Jede Zeile: (Datum, Ausrichter, (Platz Team1, Platz Team2, Platz Team3, Platz Team4))
// Platz kann sein:
//   - eine Zahl 1-4  -> normale Platzierung (die 1 wird automatisch gelb)
//   - "-"            -> Team ist nicht angetreten
//   - beliebiger Text -> z.B. Name einer Ersatzmannschaft (siehe letzte Zeile)
#let data = (
  ("21.07.1997", "Deisenhofen", (3, 1, 4, 2)),
  ("17.07.1998", "Aschheim-Feldkirchen", (1, 3, 4, 2)),
  ("1999", "Höhenkirchen", (1, 2, 4, 3)),
  ("30.06.2000", "Holzkirchen", (3, 1, 4, 2)),
  ("29.06.2001", "Deisenhofen", (3, 2, 1, 4)),
  ("24.07.2003", "Höhenkirchen", (4, 3, 2, 1)),
  ("18.06.2004", "Holzkirchen", (2, 3, 4, 1)),
  ("15.07.2005", "Deisenhofen", (3, 1, 4, 2)),
  ("28.06.2024", "AFK", (2, "SG ASK – Revolution!", 3, 1)),
  ("06.06.2027", "Deisenhofen", (3, 4, 1, "-")),
)

// Aufruf der Tabelle mit den Variablen
#render-table(
  teams: teams,
  data: data,
  navy: navy,
  gold: gold,
  navy-light: navy-light,
)
