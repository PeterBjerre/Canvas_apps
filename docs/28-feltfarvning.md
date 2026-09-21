# 28 – Feltfarvning: én regel, ikke fire

`docs/25-standardisering-plan.md` §2. Den var den mest synlige af alle
punkterne, og den eneste hvor fire forskellige regler sad i den samme
formular ved siden af hinanden.

---

## Hvad der var galt

| Kontrol | Hvad `BorderColor` faktisk blev |
|---|---|
| `text_input` **uden** `required` | **Ingen `BorderColor` overhovedet** → platformens standard, som ingen havde valgt |
| `text_input` **med** `required` | rød / neutral / **grøn** |
| `number_input`, `dropdown` | rød / neutral / **grøn** — også når feltet ikke var krævet |
| `ModernDatePicker` | **fast grå.** Aldrig rød, aldrig grøn — og bygget i hånden uden for `build_helpers` |
| `combobox` (ubrugt) | kun rød / neutral — **ingen grøn** |

I Equipments formular stod fire af dem side om side:

```
inpManufacturer    (tekst, ikke krævet)   ->  ingen farve, nogensinde
inpWarrantyStart   (dato)                 ->  altid grå, og HVID i visningstilstand
inpRequestType     (tekst, ikke krævet)   ->  ingen farve
inpDomText         (tekst, krævet)        ->  rød fra appen åbnede
```

Og datovælgeren havde **ingen `Fill`**: i visningstilstand så den
redigerbar ud — hvidt felt med kant, der ikke reagerer.

---

## Hvilken vej ensretningen gik

Argumentet stod allerede i koden, i `text_input`:

> *Kun på de krævede felter: en grøn kant om hvert eneste udfyldt felt gør
> farven meningsløs.*

Det er rigtigt. **Grøn skal betyde "dette krav er opfyldt", ikke "du har
tastet noget".** Derfor er der ensrettet på `text_input`s regel — ikke på
`number_input`s og `dropdown`s, selvom de var flertal.

Et felt, der ikke er krævet, får en almindelig kant, og den sættes
**eksplicit**. Gjorde den ikke det, arvede feltet platformens standard,
som ingen i projektet har valgt.

```
ikke krævet        ->  border-default
krævet + tom       ->  state-error-fg
krævet + udfyldt   ->  state-ok-fg
```

Alle fem inputtyper kalder nu `build_helpers.border_rule()`, og alle fem
kalder `input_fill()` for baggrunden. Datovælgeren er flyttet ind i
`build_helpers` som `date_picker()` og deler dermed begge.

### Efterprøvet: hvor mange mønstre er der tilbage?

| Antal | Mønster |
|---|---|
| 60 | `C.'border-default'` — feltet er ikke krævet |
| 18 | `If(<krav> && IsBlank(X), ROED, If(IsBlank(X), neutral, GROEN))` |

Variationerne inde i de 18 er forskellige **forretningsregler** (`numVhpCycle`
er kun krævet på en single cycle-plan), ikke forskellige stilregler. Det er
som det skal være.

Ingen `<INGEN>` tilbage. Hvert eneste input har nu både en `BorderColor` og
en `Fill`.

---

## Hvornår bliver kanten rød?

Det var det ene valg, der ikke var teknisk.

| App | Før |
|---|---|
| VH-plan | `varVhpPlanValidated && IsBlank(...)` — rød først når brugeren trykker **Validér** |
| Equipment, Material | `true && IsBlank(...)` — **rød fra appen åbnede**, før brugeren havde rørt noget |

To apps i samme familie sagde dermed to forskellige ting med den samme
farve. Og "rød fra første sekund" er den af de to, der **skader**: den lærer
brugeren at se bort fra rødt, og så er farven ingenting værd, når den
endelig betyder noget.

Equipment og Material er rettet til VH-plans model. De har ingen
Validér-knap, så udløseren er den, de har: **brugeren trykker Gem eller
Indsend.** Det er appens "jeg har tjekket".

```
domain_parts.REQUIRED = "varDomValidated"

Gem / Indsend   ->  Set(varDomValidated, true)     herfra må kanterne være røde
Ryd formular    ->  Set(varDomValidated, false)    ny formular, nyt blad
Hent en række   ->  Set(varDomValidated, false)
App.OnStart     ->  Set(varDomValidated, false)
```

**18 af Equipments 20 inputs har fået en anden kantregel.** Det er den
synlige del af hele standardiseringen — se på den, før den ruller videre.

---

## Hvad du vil lægge mærke til i appen

1. **Formularen er ikke længere rød, når du åbner den.** Krævede felter er
   neutrale, indtil du trykker Gem eller Indsend.
2. **Optionelle talfelter og dropdowns bliver ikke længere grønne**, når du
   skriver i dem. Kun de krævede.
3. **Garantidatoerne opfører sig som alle andre felter** — grå baggrund når
   rækken er indsendt og ikke kan redigeres.
4. **Tekstfelter, der ikke er krævet, har nu en synlig kant** i projektets
   egen farve i stedet for platformens.

---

## Det, der ikke blev ændret

`ValidationState` sidder stadig kun på `text_input`, `number_input` og
`dropdown`, og den bruger `required_formula` direkte. Den styrer Power
Apps' egen fejlmarkering og er ikke en farve, vi sætter — den er ladt
urørt med vilje, så ændringen her kun handler om det, `border_rule`
bestemmer.
