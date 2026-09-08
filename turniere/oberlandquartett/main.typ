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
  // 1997
  ("21.07.1997", "Deisenhofen", (1, 3, 4, 2)),
  // 1998
  ("17.07.1998", "Aschheim", (1, 3, 4, 2)),
  // 1999
  ("?", "Höhenkirchen", (1, 2, 4, 3)),
  // 2000
  ("30.06.2000", "Holzkirchen", (3, 1, 4, 2)),
  // 2001
  ("29.06.2001", "Deisenhofen", (3, 2, 1, 4)),
  // 2002
  ("?", "Aschheim", ("-", "-", "-", "-")),
  // 2003
  ("24.07.2003", "Höhenkirchen", (4, 3, 2, 1)),
  // 2004
  ("18.06.2004", "Holzkirchen", (2, 3, 4, 1)),
  // 2005
  ("15.07.2005", "Deisenhofen", (3, 1, 4, 2)),
  // 2006
  ("07.07.2006", "Aschheim", (1, 2, 3, 4)),
  // 2007
  ("29.06.2007", "Höhenkirchen", (1, 2, 4, 3)),
  // 2008
  ("04.07.2008", "Holzkirchen", (1, 2, 3, 4)),
  // 2009
  ("26.06.2009", "Deisenhofen", (3, 1, 4, 2)),
  // 2010
  ("11.06.2010", "Aschheim", (2, 1, 4, 3)),
  // 2011
  ("24.06.2011", "Höhenkirchen", (3, 1, 4, 2)),
  // 2012
  ("29.06.2012", "Holzkirchen", (3, 1, 2, 4)),
  // 2013
  ("28.06.2013", "Deisenhofen", (4, 1, 2, 3)),
  // 2014
  ("13.06.2014", "Aschheim", (3, 2, 4, 1)),
  // 2015
  ("17.07.2015", "Höhenkirchen", (1, 2, 4, 3)),
  // 2016
  ("08.07.2016", "Holzkirchen", (4, 1, 2, 3)),
  // 2017
  ("30.06.2017", "Deisenhofen", (4, 3, 1, 2)),
  // 2018
  ("29.06.2018", "Aschheim", (2, 1, 3, 4)),
  // 2019
  ("28.06.2019", "Höhenkirchen", (3, 1, 2, 4)),
  // 2020 (Ausfall Corona)
  ("-", "-", ("-", "-", "-", "-")),
  // 2021 (Ausfall Corona)
  ("-", "-", ("-", "-", "-", "-")),
  // 2022
  ("01.07.2022", "Holzkirchen", (1, 4, 2, 3)),
  // 2023
  ("23.06.2023", "Deisenhofen", (1, 2, 4, 3)),
  // 2024
  ("28.06.2024", "Aschheim", (1, 2, "-", 3)),
  // 2025
  ("27.06.2025", "Höhenkirchen", (1, 2, 4, 3)),
  // 2026
  ("03.07.2026", "Holzkirchen", (1, 2, 4, 3)),
)

// Aufruf der Tabelle mit den Variablen
#render-table(
  teams: teams,
  data: data,
  navy: navy,
  gold: gold,
  navy-light: navy-light,
)
