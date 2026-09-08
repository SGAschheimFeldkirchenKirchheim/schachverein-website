#import "template.typ": *
#show: template

#let navy = rgb("#0a1f44")
#let navy-light = rgb("#eef1f8")

// Hier einfach neue Einträge anhängen: (Spieler, Turnier, Jahr)
#let data = (
  ("Max Mustermann", "Weihnachtsblitz", "2020"),
  ("Erika Musterfrau", "Sommeropen", "2016"),
  ("Hans Beispiel", "Vereinsmeisterschaft", "2017"),
  ("Anna Test", "Blitzturnier", "2018"),
)

#align(center)[
  #table(
    columns: (2fr, 1fr, 2fr),
    stroke: 0.6pt + navy,
    fill: (col, row) => if row == 0 {
      navy
    } else if calc.even(row) {
      navy-light
    } else {
      white
    },
    inset: 8pt,
    align: (left, left, left),

    table.header(
      table.cell(text(fill: white, weight: "bold")[Turnier]),
      table.cell(text(fill: white, weight: "bold")[Jahr]),
      table.cell(text(fill: white, weight: "bold")[Spieler]),
    ),

    ..data.map(row => (
      table.cell(row.at(1)),
      table.cell(row.at(2)),
      table.cell(row.at(0)),
    )).flatten(),
  )
]
