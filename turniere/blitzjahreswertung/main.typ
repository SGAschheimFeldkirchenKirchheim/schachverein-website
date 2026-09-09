#import "Technik/template.typ": *
#show: template
#import "database.typ": *

#import "Turniere/Neujahrsblitz.typ": *
#import "Turniere/Osterblitz.typ": *
#import "Turniere/Sommerblitz.typ": *
#import "Turniere/Herbstblitz.typ": * 
#import "Turniere/Weihnachtsblitz.typ": * 

#import "Technik/wertung.typ": * 
#import "Technik/tabelle.typ": * 

#let alle-turniere = (
  (name: "Neujahrsblitz", daten: neujahrsblitz),
  (name: "Osterblitz", daten: osterblitz),
  (name: "Sommerblitz", daten: sommerblitz),
  // (name: "Herbstblitz", daten: herbstblitz),
  // (name: "Weihnachtsblitz", daten: weihnachtsblitz),

)

= Gesamttabelle
#jahreswertung-tabelle(alle-turniere, mitglieder)

= Neujahrsblitz
#einzelturnier-tabelle(neujahrsblitz, "Neujahrsblitz", mitglieder)

= Osterblitz
#einzelturnier-tabelle(neujahrsblitz, "Osterblitz", mitglieder)

= Sommerblitz
#einzelturnier-tabelle(neujahrsblitz, "Sommerblitz", mitglieder)

//= Herbstblitz
//#einzelturnier-tabelle(neujahrsblitz, "Herbstblitz", mitglieder)

//= Weihnachtsblitz
//#einzelturnier-tabelle(neujahrsblitz, "Weihnachtsblitz", mitglieder)


