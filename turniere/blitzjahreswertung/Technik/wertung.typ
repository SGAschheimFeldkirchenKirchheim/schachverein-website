#import "../database.typ": * 

#let berechne-jahreswertung(turniere-liste, mitglieder-db) = {
  
  // 1. Alle Spieler-IDs sammeln, die in mindestens einem Turnier vorkommen
  let alle-ids = ()
  for t in turniere-liste {
    for id in t.daten.keys() {
      if not alle-ids.contains(id) {
        alle-ids.push(id)
      }
    }
  }

  // 2. Für jeden Spieler die Punkte sammeln und die Top-3 addieren
  let gesamt-liste = ()
  for id in alle-ids {
    // Vor- und Nachname aus der Mitglieder-Datenbank holen
    let m = mitglieder-db.at(id, default: (Vorname: id, Nachname: ""))
    let voller-name = m.Vorname + " " + m.Nachname

    // Punkte für jedes Turnier einsammeln
    let spieler-punkte = ()
    for t in turniere-liste {
      // Nutzt deine bestehende punkte()-Funktion
      spieler-punkte.push(punkte(id, t.daten))
    }

    // Top-3 Regel: Absteigend sortieren, max. 3 nehmen und summieren
    let sorted-p = spieler-punkte.sorted(key: x => -x)
    let top3 = sorted-p.slice(0, calc.min(3, sorted-p.len()))
    let summe = top3.fold(0, (acc, val) => acc + val)

    gesamt-liste.push((
      id: id,
      name: voller-name,
      einzel: spieler-punkte,
      summe: summe
    ))
  }

  // 3. Nach Gesamtpunkten absteigend sortieren
  return gesamt-liste.sorted(key: x => -x.summe)
}
