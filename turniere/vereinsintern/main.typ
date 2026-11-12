#import "template.typ": *
#show: template

#let navy = rgb("#0a1f44")
#let navy-light = rgb("#eef1f8")

// Hier neue Einträge oben anhängen: (Spieler, Turnier, Jahr)
// Mehrere Sieger: "Name A und Name B".
// Blitzmeister: Seit Einführung der Blitzjahreswertung ist ihr Sieger der Blitzmeister.
// Der Osterblitz gehört nicht in die Hall of Fame (Absprache mit Pierre und Frederik).
#let data = (
  ("Alexander Wittko", "Vereinsmeister", "2026"),
  ("Alexander Wittko", "Pokalsieger", "2026"),
  ("Dominik Dax", "Schnellschachmeister", "2026"),
  ("Konrad Keblat", "Jugend-Schnellschachmeister", "2026"),
  ("Fabian Müller", "Blitzschachmeister", "2025"),
  ("Pierre Tassell", "Blitzserienmeister", "2025"),
  ("Stefans Kasims", "Schnellschachmeister", "2025"),
  ("Pierre Tassell", "Vereinsmeister", "2025"),
  ("Alexander Wittko", "Pokalsieger", "2025"),
  ("Alexander Wittko", "Jugendmeister", "2025"),
  ("Pierre Tassell", "Blitzschachmeister", "2024"),
  ("Stefans Kasims", "Weihnachtsblitz", "2024"),
  ("Pierre Tassell", "Vereinsmeister", "2024"),
  ("Pierre Tassell", "Pokalsieger", "2024"),
  ("Ronny Damaske und Pierre Tassell", "Blitzschachmeister", "2023"),
  ("Ronny Damaske", "Weihnachtsblitz", "2023"),
  ("Armin Tobisch", "Schnellschachmeister", "2023"),
  ("Armin Tobisch", "Kirchheimer Stadtmeister", "2023"),
  ("Pierre Tassell", "Vereinsmeister", "2023"),
  ("Pierre Tassell", "Blitzschachmeister", "2022"),
  ("Lars Goldbeck", "Weihnachtsblitz", "2022"),
  ("David Mehlhorn", "Schnellschachmeister", "2022"),
  ("Pierre Tassell", "Vereinsmeister", "2022"),
  ("David Mehlhorn", "Weihnachtsblitz", "2021"),
  ("Arthur Krumm", "Kirchheimer Stadtmeister", "2021"),
  ("Pierre Tassell", "Schnellschachmeister", "2021"),
  ("Pierre Tassell", "Weihnachtsblitz", "2020"),
  ("Frederik Prause", "Blitzschachmeister", "2020"),
  ("Dieter Vischer", "Blitzschachmeister", "2019"),
  ("Pierre Tassell", "Weihnachtsblitz", "2019"),
  ("Pierre Tassell", "Pokalsieger", "2019"),
  ("Arthur Krumm", "Vereinsmeister", "2019"),
  ("Rudolf Oster", "Weihnachtsblitz", "2018"),
  ("Frederik Prause", "Blitzschachmeister", "2018"),
  ("Pierre Tassell", "Pokalsieger", "2018"),
  ("Armin Tobisch", "Weihnachtsblitz", "2017"),
  ("Dieter Vischer", "Vereinsmeister", "2017"),
  ("Dieter Vischer", "Pokalsieger", "2017"),
  ("Ronny Damaske", "Weihnachtsblitz", "2016"),
  ("Frederik Prause", "Vereinsmeister", "2016"),
  ("Frederik Prause", "Blitzschachmeister", "2016"),
  ("Armin Tobisch", "Pokalsieger", "2016"),
  ("Ronny Damaske", "Weihnachtsblitz", "2015"),
  ("Hanspeter Hecht", "Vereinsmeister", "2015"),
  ("Frederik Prause", "Blitzschachmeister", "2015"),
  ("Hanspeter Hecht", "Vereinsmeister", "2014"),
  ("Armin Tobisch", "Weihnachtsblitz", "2014"),
  ("Frederik Prause", "Schnellschachmeister", "2014"),
  ("Ronny Damaske", "Vereinsmeister", "2013"),
  ("Frederik Prause", "Blitzschachmeister", "2013"),
  ("Frederik Prause", "Weihnachtsblitz", "2013"),
  ("Dieter Vischer", "Pokalsieger", "2012"),
  ("Ronny Damaske", "Weihnachtsblitz", "2012"),
  ("Armin Tobisch und Dieter Vischer", "Vereinsmeister", "2012"),
  ("Ronny Damaske", "Blitzschachmeister", "2012"),
  ("Ronny Damaske", "Vereinsmeister", "2011"),
  ("Armin Tobisch", "Weihnachtsblitz", "2011"),
  ("Ronny Damaske", "Blitzschachmeister", "2011"),
  ("Armin Tobisch", "Pokalsieger", "2011"),
  ("Dieter Vischer", "Vereinsmeister", "2010"),
  ("Frederik Prause", "Weihnachtsblitz", "2010"),
  ("Frederik Prause", "Blitzschachmeister", "2010"),
  ("Ronny Damaske", "Pokalsieger", "2010"),
  ("Dieter Vischer", "Vereinsmeister", "2009"),
  ("Dieter Vischer", "Blitzschachmeister", "2009"),
  ("Armin Tobisch", "Weihnachtsblitz", "2009"),
  ("Ronny Damaske", "Vereinsmeister", "2008"),
  ("Frederik Prause", "Blitzschachmeister", "2008"),
  ("Frederik Prause", "Weihnachtsblitz", "2008"),
  ("Dieter Vischer", "Vereinsmeister", "2007"),
  ("Ronny Damaske", "Blitzschachmeister", "2007"),
  ("Frederik Prause", "Weihnachtsblitz", "2007"),
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
