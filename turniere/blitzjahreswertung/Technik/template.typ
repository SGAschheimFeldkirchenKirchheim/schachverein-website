#let LightSlateBlue = rgb("#8470ff")
#let hellrot = red.lighten(25%)
#let rot = red.lighten(5%)
#let gruen = green.lighten(10%)
#let gelb = yellow.lighten(10%)
#let orange = orange.lighten(10%)
#let weiss = white
#let schwarz = black.lighten(30%)
#let CornflowerBlue = rgb("#6495ed")
#let dunkelblau = rgb("#4b1480")
#let LightSlateBlue = rgb("#8470ff")

#let template(body) = [
  #set page(
    paper: "a4",           
    flipped: true,
    margin: (x: 1.5cm, top: 2cm, bottom: 2cm),
    
    footer: [
    #set text(size: 9pt, fill:black)
    
    #grid(
      columns: (auto,1fr,auto),
      [#align(center)[
      Falls euch bei den Ergebnissen ein Fehler auffällt, wendet euch bitte umgehend an #link("mailto:pierre.tassell@gmail.com")[Pierre] oder #link("mailto:Korbinian.ruff@t-online.de")[Korbinian].
    ]],[],[#link("https://typst.app/")[Made with Typst]]
    )
  ],
  )
  
  #set document(title: "MMM 2026/2027", author: "Pierre Tassell")
  
  #set text(
    font: "New Computer Modern", 
    size: 12pt,                
    lang: "de",                
    region: "DE",
  )

  // DEINE NEUE REGEL FÜR HEADING LEVEL 1
  #show heading.where(level: 1): it => {
    set align(center)
    set text(size: 24pt, weight: "bold")
    block[#underline(it.body)]
    v(2em)
  }

  #show link: it => text(fill: dunkelblau)[#it]
  #show ref: it => text(fill:  LightSlateBlue)[#it]





  #body
]






