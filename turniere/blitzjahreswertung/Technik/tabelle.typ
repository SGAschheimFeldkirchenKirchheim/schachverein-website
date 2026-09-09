#import "wertung.typ": berechne-jahreswertung

// 1. Funktion für die Gesamtwertung (mehrere Turniere)
#let jahreswertung-tabelle(turniere-liste, mitglieder-db) = {
  let auswertung = berechne-jahreswertung(turniere-liste, mitglieder-db)

  let headers = ([*Pl.*], [*Spieler*])
  let col-widths = (30fr, auto)

  for t in turniere-liste {
    headers.push([*#t.name*])
    col-widths.push(60fr)
  }
  headers.push([*Gesamt*])
  col-widths.push(60fr)

  // WICHTIG: Hier starten wir mit einem leeren Array, 
  // damit die Header nicht doppelt gerendert werden!
  let table-cells = ()
  
  // Variablen für die korrekte Rang-Vergabe bei Punktgleichheit
  let aktueller-rang = 1
  let letzter-score = none

  for (index, item) in auswertung.enumerate() {
    if letzter-score == none or item.summe < letzter-score {
      aktueller-rang = index + 1
    }
    letzter-score = item.summe

    table-cells.push(str(aktueller-rang))
    table-cells.push(item.name)
    
    // Top-3 Indizes ermitteln
    let indexed-einzel = item.einzel.enumerate()
    let sorted-by-val = indexed-einzel.sorted(key: x => x.at(1))
    let top-indices = ()
    
    if sorted-by-val.len() <= 3 {
      top-indices = sorted-by-val.map(x => x.at(0))
    } else {
      let top-n = sorted-by-val.slice(sorted-by-val.len() - 3)
      top-indices = top-n.map(x => x.at(0))
    }
    
    for (col-idx, p) in item.einzel.enumerate() {
      // WERTUNG BLEIBT INTAKT (rechnet mit p), aber Anzeige wird angepasst:
      // Wenn p == 0, zeigen wir "-", ansonsten den echten Wert p
      let anzeige = if p == 0 [–] else [#p]

      // Ein Spieler mit 0 Punkten soll natürlich nicht in die Top-3-Markierung rutschen
      if top-indices.contains(col-idx) and p > 0 {
        table-cells.push(table.cell(fill: rgb("#548b54"))[#text(fill: white, strong(str(p)))])
      } else {
        table-cells.push(align(center)[#anzeige])
      }
    }
    
    table-cells.push(table.cell(fill: rgb("#e2e8f0"))[#align(center)[*#item.summe*]])
  }

  let vereins-blau = rgb("#1e3a8a")

  table(
    columns: col-widths,
    inset: (x: 8pt, y: 7pt),
    align: center,
    stroke: 1pt + vereins-blau,
    table.header(
      // Haupttitel über die gesamte Breite
      table.cell(
        colspan: col-widths.len(), 
        fill: vereins-blau
      )[
        #set text(fill: white, weight: "bold", size: 1.1em)
        #pad(y: 4pt)[SG AFK – Blitzjahreswertung 2026]
      ],
      // Spalten-Header einmalig sauber einfügen
      ..headers.map(h => table.cell(fill: rgb("#f1f5f9"))[#h])
    ),
    fill: (col, row) => none,
    ..table-cells
  )
  pagebreak()
}

// 2. Funktion für ein einzelnes Turnier
#let einzelturnier-tabelle(turnier-daten, turnier-name, mitglieder-db) = {
  let liste = ((name: turnier-name, daten: turnier-daten),)
  jahreswertung-tabelle(liste, mitglieder-db)
}
