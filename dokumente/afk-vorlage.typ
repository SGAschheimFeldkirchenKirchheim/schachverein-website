// Gemeinsame Vorlage für Vereinsdokumente der SG AFK (Satzung, Historie, …)
// Einbinden:  #import "afk-vorlage.typ": *
//             #show: dokument.with(titel: "Satzung", untertitel: "…")

#let navy = rgb("#1c2d52")
#let hellblau = rgb("#6fa3dc")
#let grau = rgb("#5b6475")

#let dokument(
  titel: "",
  untertitel: none,
  verein: "Schachgemeinschaft Aschheim/Feldkirchen/Kirchheim e.V.",
  stand: none,                 // z. B. "11. Juli 2014"; erscheint in der Fußzeile
  schrift: "Libertinus Serif",
  groesse: 11pt,
  akzent: navy,
  body,
) = {
  set document(title: titel, author: verein)
  set page(
    paper: "a4",
    margin: (x: 2.4cm, top: 2.6cm, bottom: 2.4cm),
    header: context if counter(page).get().first() > 1 [
      #set text(8.5pt, fill: grau)
      #verein #h(1fr) #titel
      #v(-0.6em)
      #line(length: 100%, stroke: 0.4pt + grau.lighten(50%))
    ],
    footer: context [
      #set text(8.5pt, fill: grau)
      #if stand != none [Stand: #stand]
      #h(1fr)
      Seite #counter(page).display() von #counter(page).final().first()
    ],
  )
  set text(font: schrift, size: groesse, lang: "de", hyphenate: true)
  set par(justify: true, leading: 0.68em, spacing: 1.05em)

  // Kopf der ersten Seite
  block(width: 100%, inset: (bottom: 0.9em), stroke: (bottom: 2.5pt + hellblau))[
    #text(9.5pt, fill: grau, tracking: 0.04em, upper(verein))
    #v(0.35em)
    #text(26pt, weight: "bold", fill: akzent, titel)
    #if untertitel != none [
      #v(0.1em)
      #text(12pt, fill: grau, untertitel)
    ]
  ]
  v(0.8em)

  show heading.where(level: 1): it => block(above: 1.7em, below: 0.75em, sticky: true)[
    #text(13.5pt, weight: "bold", fill: akzent, it.body)
  ]
  show heading.where(level: 2): it => block(above: 1.2em, below: 0.55em, sticky: true)[
    #text(11.5pt, weight: "bold", fill: akzent, it.body)
  ]
  body
}

// Unterschriftenzeile: unterschriften(("H. Gundel", "1. Vorsitzender", "Helmut Gundel"), …)
#let unterschriften(..personen) = {
  v(2.2em)
  grid(
    columns: (1fr,) * personen.pos().len(),
    column-gutter: 1.2em,
    ..personen.pos().map(((gez, amt, name)) => [
      #text(fill: grau)[gez.:] #gez \
      #amt \
      #name
    ]),
  )
}
