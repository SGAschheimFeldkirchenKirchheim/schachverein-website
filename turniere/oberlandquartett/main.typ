#import "table.typ": render-table
#set page(width: 22cm, height: auto, margin: 1.5cm)
#set text(font: "Liberation Sans", size: 10pt)

#let navy = rgb("#0a1f44")
#let gold = rgb("#ffd54a")
#let navy-light = rgb("#eef1f8")

// Namensänderung im teams-Array für den Tabellenkopf:
#let teams = ("Aschheim-Feldkirchen-Kirchheim", "Deisenhofen", "Holzkirchen", "Höhenkirchen")

#let data = (
  ("21.07.1997", "Deisenhofen", (3, 1, 4, 2)),
  ("17.07.1998", "Aschheim-Feldkirchen", (1, 3, 4, 2)),
  ("1999", "Höhenkirchen", (1, 2, 4, 3)),
  ("30.06.2000", "Holzkirchen", (3, 1, 4, 2)),
  ("29.06.2001", "Deisenhofen", (3, 2, 1, 4)),
  ("24.07.2003", "Höhenkirchen", (4, 3, 2, 1)),
  ("18.06.2004", "Holzkirchen", (2, 3, 4, 1)),
  ("15.07.2005", "Deisenhofen", (3, 1, 4, 2)),
  ("28.06.2024", "Aschheim-Feldkirchen-Kirchheim", (1, 2, 3, "Aschheim II")),
  ("27.06.2025", "Höhenkirchen", (1, 2, 3, 4)),
  ("03.07.2026", "Holzkirchen", (1, 2, 3, 4)),
)

// Aufruf der Tabelle mit den Variablen
#render-table(
  teams: teams,
  data: data,
  navy: navy,
  gold: gold,
  navy-light: navy-light,
)
