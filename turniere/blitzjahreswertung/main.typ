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
#import "Technik/links.typ": turnier-links

#let alle-turniere = (
  (name: "Neujahrsblitz", daten: neujahrsblitz),
  (name: "Osterblitz", daten: osterblitz),
  (name: "Sommerblitz", daten: sommerblitz),
  (name: "Herbstblitz", daten: herbstblitz),
  // (name: "Weihnachtsblitz", daten: weihnachtsblitz),
)
// Weniger Turniere ==> besserer Platz
#jahreswertung-tabelle(alle-turniere, mitglieder)

#set page(flipped: false)
#einzelturnier-tabelle(neujahrsblitz, "Neujahrsblitz", mitglieder, turnier-url: turnier-links.neujahrsblitz)

#einzelturnier-tabelle(osterblitz, "Osterblitz", mitglieder, turnier-url: turnier-links.osterblitz)

#einzelturnier-tabelle(sommerblitz, "Sommerblitz", mitglieder, turnier-url: turnier-links.sommerblitz)

#einzelturnier-tabelle(herbstblitz, "Herbstblitz", mitglieder, turnier-url: turnier-links.herbstblitz)

// #einzelturnier-tabelle(weihnachtsblitz, "Weihnachtsblitz", mitglieder, turnier-url: turnier-links.weihnachtsblitz)