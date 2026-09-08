// ---------- POKAL-LOGIK (nichts anfassen) ----------
// Ermittelt alle Zellen, in denen der Pokal endgueltig gewonnen wurde:
// entweder 3x hintereinander die 1, oder 5x insgesamt seit dem letzten Reset.
#let compute-pokal-wins(teams, data) = {
  let streak = teams.map(t => 0)
  let total = teams.map(t => 0)
  let wins = ()

  for (i, entry) in data.enumerate() {
    let results = entry.at(2)
    for (j, val) in results.enumerate() {
      if type(val) == int and val == 1 {
        streak.at(j) = streak.at(j) + 1
        total.at(j) = total.at(j) + 1
      } else {
        streak.at(j) = 0
      }
    }
    for (j, t) in teams.enumerate() {
      if streak.at(j) >= 3 or total.at(j) >= 5 {
        wins.push((i, j))
        streak = teams.map(t => 0)
        total = teams.map(t => 0)
      }
    }
  }
  wins
}

// ---------- HAUPTFUNKTION ----------
#let render-table(
  teams: (),
  data: (),
  navy: rgb("#0a1f44"),
  gold: rgb("#ffd54a"),
  navy-light: rgb("#eef1f8"),
) = {
  let pokal-wins = compute-pokal-wins(teams, data)
  let is-pokal-cell(i, j) = pokal-wins.any(w => w.at(0) == i and w.at(1) == j)

  align(center)[
    #text(size: 16pt, weight: "bold")[Oberland Quartett]
    #v(0.8em)

    #table(
      columns: (auto, auto) + teams.map(t => 1fr),
      stroke: 0.6pt + navy,
      inset: 7pt,
      align: (left, left) + teams.map(t => center),
      fill: (col, row) => {
        if row == 0 { navy }
        else if col >= 2 {
          let j = col - 2
          let i = row - 1
          let val = data.at(i).at(2).at(j)
          if is-pokal-cell(i, j) { navy }
          else if type(val) == int and val == 1 { gold }
          else if calc.even(row) { navy-light }
          else { white }
        } else if calc.even(row) { navy-light }
        else { white }
      },

      table.header(
        table.cell(text(fill: white, weight: "bold")[Datum]),
        table.cell(text(fill: white, weight: "bold")[Ausrichter]),
        ..teams.map(t => table.cell(text(fill: white, weight: "bold")[#t])),
      ),

      ..data.enumerate().map(((i, entry)) => {
        let (datum, ausrichter, results) = entry
        let cells = (table.cell(datum), table.cell(ausrichter))
        for (j, val) in results.enumerate() {
          let shown = if type(val) == str { val } else { str(val) }
          let win = is-pokal-cell(i, j)
          cells.push(table.cell(
            if win { text(fill: white, weight: "bold")[#shown] } else { [#shown] }
          ))
        }
        cells
      }).flatten(),
    )
  ]

  v(1em)
  text(size: 9pt, style: "italic")[
    Den Pokal gewinnt die Mannschaft, die entweder 3x hintereinander gewinnt oder insgesamt 5x.
    
    Nach dem Pokalgewinn beginnt die Zählung von vorne! Der Gewinner spendiert den neuen Pokal.
  ]
}
