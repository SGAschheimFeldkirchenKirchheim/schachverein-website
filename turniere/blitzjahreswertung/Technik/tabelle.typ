#import "wertung.typ": berechne-jahreswertung, turnier-rangliste, ist-gespielt

// Farben an einer Stelle
#let farben = (
  blau: rgb("#1e3a8a"),
  kopf: rgb("#f1f5f9"),
  gewertet: rgb("#548b54"),
  gesamt: rgb("#e2e8f0"),
  offen: rgb("#e5e7eb"),
  grau: rgb("#9ca3af"),
)

#let _kopfzelle(inhalt, fill: farben.kopf) = table.cell(fill: fill)[#inhalt]

#let _titelzeile(titel, spalten) = table.cell(colspan: spalten, fill: farben.blau)[
  #set text(fill: white, weight: "bold", size: 1.1em)
  #pad(y: 4pt)[#titel]
]

#let _turnier-titel(t) = {
  let url = t.at("url", default: none)
  if url != none and url != "" { link(url)[#t.name] } else { t.name }
}

#let _punkt-zelle(p, gewertet) = {
  if p == none {
    text(fill: farben.grau)[–]
  } else if gewertet and p > 0 {
    table.cell(fill: farben.gewertet)[#text(fill: white, strong(str(p)))]
  } else if gewertet {
    str(p)
  } else {
    text(fill: farben.grau, strike(str(p)))
  }
}

// ==========================================
// Jahreswertung
// ==========================================
#let jahreswertung-tabelle(
  turniere-liste,
  mitglieder-db,
  titel: "SG AFK – Blitzjahreswertung",
  stand: none,
  beste: 3,
  sieg-punkte: 20,
  zeige-maximal: true,
  zeilenabstand: 6pt,
) = {
  let w = berechne-jahreswertung(turniere-liste, mitglieder-db, beste: beste, sieg-punkte: sieg-punkte)
  let mit-max = zeige-maximal and w.offen > 0

  // Kopf
  let headers = (_kopfzelle[*Pl.*], _kopfzelle[*Spieler*])
  let spalten = (auto, auto)
  for t in turniere-liste {
    if ist-gespielt(t) {
      headers.push(_kopfzelle[*#_turnier-titel(t)*])
    } else {
      headers.push(_kopfzelle(fill: farben.offen)[
        #set text(fill: farben.grau, size: 0.85em)
        *#t.name* \ #text(size: 0.85em)[ausstehend]
      ])
    }
    spalten.push(1fr)
  }
  headers.push(_kopfzelle[*Teiln.*])
  headers.push(_kopfzelle[*Gesamt*])
  spalten += (auto, auto)
  if mit-max {
    headers.push(_kopfzelle[*Max.*])
    spalten.push(auto)
  }

  // Zeilen
  let zellen = ()
  for s in w.spieler {
    zellen.push(str(s.rang))
    zellen.push(s.name)
    for (i, p) in s.einzel.enumerate() {
      if ist-gespielt(turniere-liste.at(i)) {
        zellen.push(_punkt-zelle(p, i in s.gewertet))
      } else {
        zellen.push(table.cell(fill: farben.offen)[])
      }
    }
    zellen.push(str(s.teilnahmen) + "/" + str(w.gespielt))
    zellen.push(table.cell(fill: farben.gesamt)[*#s.summe*])
    if mit-max {
      zellen.push(if s.titelchance [*#s.maximal*] else { text(fill: farben.grau, str(s.maximal)) })
    }
  }

  table(
    columns: spalten,
    inset: (x: 8pt, y: zeilenabstand),
    align: center + horizon,
    stroke: 1pt + farben.blau,
    table.header(repeat: false, _titelzeile(titel, spalten.len()), ..headers),
    ..zellen,
  )

  // Legende
  set text(size: 9pt)
  let stand-text = if stand != none [Stand: #stand · ] else []
  [
    #stand-text nach #w.gespielt von #w.gesamt Turnieren. \
    Gewertet werden die besten #beste Ergebnisse (#box(fill: farben.gewertet, inset: (x: 3pt), outset: (y: 2pt), text(fill: white, strong[grün]))),
    gestrichene Ergebnisse sind #text(fill: farben.grau, strike[durchgestrichen]).
    0 = teilgenommen ohne Punkte, – = nicht teilgenommen.
    #if mit-max [Max. = höchstmögliche Endpunktzahl mit #sieg-punkte Punkten in jedem offenen Turnier.]
  ]

  if mit-max {
    let kandidaten = w.spieler.filter(s => s.titelchance).sorted(key: s => -s.maximal)
    if kandidaten.len() > 0 {
      parbreak()
      [*Titel noch möglich:* #kandidaten.map(s => [#s.name (max. #s.maximal)]).join(", ")]
    }
  }
}

// ==========================================
// Einzelturnier
// ==========================================
#let einzelturnier-tabelle(turnier, mitglieder-db, titel-zusatz: "Endstand") = {
  heading(level: 1, _turnier-titel(turnier))

  let zellen = ()
  for s in turnier-rangliste(turnier.daten, mitglieder-db) {
    zellen.push(str(s.platz))
    zellen.push(s.name)
    zellen.push(_punkt-zelle(s.punkte, true))
  }

  table(
    columns: (auto, 1fr, auto),
    inset: (x: 8pt, y: 7pt),
    align: center + horizon,
    stroke: 1pt + farben.blau,
    table.header(
      repeat: false,
      _titelzeile([#turnier.name – #titel-zusatz], 3),
      _kopfzelle[*Pl.*], _kopfzelle[*Spieler*], _kopfzelle[*Punkte*],
    ),
    ..zellen,
  )
  pagebreak(weak: true)
}
