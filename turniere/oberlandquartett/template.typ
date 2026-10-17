#let template(body) = {
  let fmt-numeric = "1."
  let fmt-alpha   = "a."
  let fmt-roman   = "I."

  let heading-config = (
    (
      active: true,
      format: fmt-numeric,
      size: 20pt,
      align-pos: center,
      weight: "bold",
      style: "normal",
      underlined: true,
    ),
    (
      active: true,
      format: fmt-numeric,
      size: 15pt,
      align-pos: left,
      weight: "bold",
      style: "normal",
      underlined: false,
    ),
    (
      active: false,
      format: fmt-alpha,
      size: 12pt,
      align-pos: left,
      weight: "bold",
      style: "italic",
      underlined: false,
    ),
  )

  set page(
    paper: "a4",         
    margin: (
      top:    2.5cm,
      bottom: 2.5cm,
      left:   3cm,
      right:  2.5cm,
    ),
    numbering: "1",
    number-align: right + bottom,

    header: align(right)[
      #emph[Korbinian Ruff]
    ],
    
    footer: align(center)[
      #context counter(page).display("1 / 1", both: false)
    ],
  )

  set text(
    font: "New Computer Modern", 
    size: 12pt,
    lang: "de",           
    region: "DE",
  )

  set par(
    justify: true,
    leading: 0.75em,
    spacing: 1.2em,
    first-line-indent: 0em,
  )

  show link: it => text(fill: orange)[#it]

  set heading(numbering: (..args) => {
    let depth = args.pos().len()
    if depth <= heading-config.len() {
      let cfg = heading-config.at(depth - 1)
      if cfg.active {
        numbering(cfg.format, ..args.pos())
      } else {
        none
      }
    } else {
      none
    }
  })

  show heading: it => {
    // Prüfen, ob für diese spezifische Überschrift numbering: none übergeben wurde
    let has-numbering = if "numbering" in it.fields() { it.numbering != none } else { true }
    
    let level-num = it.level
    if level-num <= heading-config.len() {
      let cfg = heading-config.at(level-num - 1)
      
      let styled-content = text(
        size: cfg.size, 
        weight: cfg.weight, 
        style: cfg.style
      )[
        #if cfg.active and has-numbering {
          counter(heading).display(cfg.format) + [ ] + it.body
        } else {
          it.body
        }
      ]

      let rendered = if cfg.underlined {
        underline(evade: true, extent: 3pt)[#styled-content]
      } else {
        styled-content
      }

      block(
        width: 100%,
        above: 1.5em, 
        below: 1em,
        align(cfg.align-pos, rendered)
      )
    } else {
      it
    }
  }

  show ref: it => {
    let eq = it.element
    if eq != none and eq.func() == heading {
      link(eq.location(), eq.body)
    } else {
      it
    }
  }

  body
}
