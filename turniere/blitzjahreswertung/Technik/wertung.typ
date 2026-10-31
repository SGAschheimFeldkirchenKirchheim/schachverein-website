// Turnierdateien dürfen beide Formate enthalten:
//   alt: "AntonM": 20
//   neu: "AntonM": (punkte: 20, platz: 2)   <- schreibt main.py
#let eintrag-punkte(e) = if type(e) == dictionary { e.punkte } else { e }

#let ist-gespielt(t) = t.at("gespielt", default: true)

#let spieler-name(id, mitglieder-db) = {
  let m = mitglieder-db.at(id, default: none)
  if m == none { id } else { m.Vorname + " " + m.Nachname }
}

// Rangliste eines Turniers, sortiert nach chess-results-Platz.
// Ohne explizites "platz" gilt die Reihenfolge in der Datei.
#let turnier-rangliste(daten, mitglieder-db) = {
  let liste = ()
  for (i, (id, e)) in daten.pairs().enumerate() {
    let platz = if type(e) == dictionary and "platz" in e { e.platz } else { i + 1 }
    liste.push((id: id, name: spieler-name(id, mitglieder-db), punkte: eintrag-punkte(e), platz: platz))
  }
  liste.sorted(key: x => x.platz)
}

// Jahreswertung: beste `beste` Ergebnisse zählen, punktgleich = gleicher Platz.
// `sieg-punkte` wird für die Maximal-Berechnung bei offenen Turnieren genutzt.
#let berechne-jahreswertung(turniere-liste, mitglieder-db, beste: 3, sieg-punkte: 20) = {
  let gespielt = turniere-liste.filter(ist-gespielt)
  let offen = turniere-liste.len() - gespielt.len()

  let alle-ids = ()
  for t in gespielt {
    for id in t.daten.keys() {
      if id not in alle-ids { alle-ids.push(id) }
    }
  }

  let spieler = ()
  for id in alle-ids {
    // none = nicht teilgenommen bzw. Turnier noch offen
    let einzel = turniere-liste.map(t =>
      if ist-gespielt(t) and id in t.daten { eintrag-punkte(t.daten.at(id)) } else { none }
    )
    let teilgenommen = einzel.enumerate().filter(x => x.at(1) != none)
    // stabil sortiert: bei gleichem Wert zählt das frühere Turnier
    let sortiert = teilgenommen.sorted(key: x => -x.at(1))
    let gewertet = sortiert.slice(0, calc.min(beste, sortiert.len())).map(x => x.at(0))
    let summe = gewertet.map(i => einzel.at(i)).sum(default: 0)

    let moeglich = teilgenommen.map(x => x.at(1)) + (sieg-punkte,) * offen
    let maximal = moeglich.sorted(key: x => -x).slice(0, calc.min(beste, moeglich.len())).sum(default: 0)

    spieler.push((
      id: id,
      name: spieler-name(id, mitglieder-db),
      einzel: einzel,
      gewertet: gewertet,
      teilnahmen: teilgenommen.len(),
      summe: summe,
      maximal: maximal,
    ))
  }

  // erst nach Name, dann (stabil) nach Punkten -> Gleichstände alphabetisch
  spieler = spieler.sorted(key: x => x.name).sorted(key: x => -x.summe)

  // Plätze (punktgleich = gleicher Platz) und Titelchance
  let ergebnis = ()
  let rang = 1
  for (i, s) in spieler.enumerate() {
    if i > 0 and s.summe < spieler.at(i - 1).summe { rang = i + 1 }
    let beste-andere = spieler.enumerate().filter(x => x.at(0) != i).map(x => x.at(1).summe)
    let titelchance = offen > 0 and s.maximal >= beste-andere.fold(0, calc.max)
    ergebnis.push(s + (rang: rang, titelchance: titelchance))
  }

  (spieler: ergebnis, gespielt: gespielt.len(), gesamt: turniere-liste.len(), offen: offen)
}
