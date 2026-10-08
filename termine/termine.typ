#import "package.typ": *  

#let template(body) = [
  #set page(
    paper: "a3",           
    flipped: true,
    width: auto, 
    height: auto, 
    margin: 1cm,
  )

  #set document(title: "MMM 2026/2027", author: "Korbinian Ruff")
  
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
    v(0.2em)
  }

  // Standard: überall außerhalb von Tabellen
#show link: set text(fill: LightSlateBlue)

#show table.cell: it => {
  let c = if it.fill == green {
    black
  } else if it.fill == none {
    black
  } else if it.fill == orange {
    black
  } else if it.fill == yellow {
    dunkelblau
  } else {
    LightSlateBlue
  }
  show link: set text(fill: c)
  it
}

  #body
]
