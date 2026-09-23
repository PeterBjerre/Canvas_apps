# 27 – Layouttokens: ét sted hvor layoutet skifter

> **Opdateret af [`30-responsivt-layout.md`](30-responsivt-layout.md):** `SHELL_W`
> står nu i `tools/layout_tokens.py` sammen med rammen, den er regnet af, og
> `wrap_row_height()` er erstattet af `build_helpers.flow_row()`.
> `HERO_BTNS`/`BAR_RIGHT` og deres vagter er væk — `top_bar()` regner
> bredderne af knapperne selv.

Samme greb som `docs/26-designtokens.md`, bare målt i pixels. Farven stod
ét sted; nu gør breakpointet det også.

---

## Hvad der var galt

Ni breakpoints, ni steder, målt mod **tre forskellige baser**
(`App.Width`, `SHELL_W = App.Width - 64`, `HERO_CW = App.Width - 96`).
Omregnet til `App.Width` lå de sådan her:

```
 704   SHELL_W < 640          to kolonner -> en
 718   HERO_CW < 622          procesindikatoren ombryder
 740   (SHELL_W - 36) < 640   felterne -> en kolonne
 900   App.Width < 900        topbjælken ombryder
 996   HERO_CW < 900          heroen stables
1000   App.Width < 1000       item-skinnen stables
1004   SHELL_W < 940          fem fliser -> to
1024   App.Width < 1024       FillPortions slås fra
1600   App.Width < 1600       listen ved siden af formularen
```

**Fire breakpoints inden for 28 pixels.** Trækker en bruger vinduet fra 990
til 1030, sker der fire ting på fire forskellige tidspunkter. Det ligner
ikke et layout, der skifter tilstand — det ligner et, der sætter sig.

Ingen af de fire tal var valgt i forhold til de tre andre. De var valgt
hver for sig, i hver sin måned, mod hver sin base. At `SHELL_W < 940` og
`App.Width < 1000` er 4 pixels fra hinanden, kunne man ikke se uden at
regne.

---

## De to slags grænser

Det var ikke kun et talproblem. De ni grænser er **to forskellige
spørgsmål**, som var skrevet ens:

### 1. Viewport-tier — "hvor stor er skærmen?"

Fem fliser eller to. Hero ved siden af eller ovenpå. Det er en beslutning
om enhedsklasse, og den skal træffes **det samme sted for hele appen**.

```
LayoutContext = "Mobile" | "Tablet" | "Desktop" | "Wide"
LayoutRank    =    1     |    2     |     3     |   4
```

To navngivne formler i `App.Formulas`, skrevet af `tools/layout_tokens.py`.
`LayoutContext` er den, man kan **læse** i Studio. `LayoutRank` er den, man
kan **sammenligne** med: *"desktop eller bredere"* bliver `LayoutRank >= 3`
i stedet for en kæde af eller'er over strenge.

| Tier | Fra `App.Width` | Hvorfor lige det tal |
|---|---|---|
| Mobile | 0 | |
| Tablet | 720 | Samme tal som i oplægget, og det falder midt i appernes egen klynge (704–740) |
| Desktop | **1024** | Stod allerede i `build_helpers.py`, er den klassiske tablet-landskabsbredde, og ligger øverst i den anden klynge (996–1024) |
| Wide | 1600 | Ikke pyntetal: Equipment-listen har syv kolonner og knap 540 px faste bredder, så den kan først stå ved siden af formularen her |

Builderne skriver aldrig et tal:

```python
from layout_tokens import below, if_below, at_least

TILE_W = if_below("Desktop", f"({SHELL_W} - 10) / 2", f"({SHELL_W} - 40) / 5")
```

### 2. Container-grænse — "er der plads til indholdet i DENNE kasse?"

Et kort på 600 px skal stable sine to kolonner, uanset om vinduet er 1920
bredt. Det er ikke en enhedsklasse; det er aritmetik på indholdet.

De bliver **lokale** — men de skal **regnes ud af det, de beskytter**, ikke
skrives som et tal:

```python
from layout_tokens import fits, TWO_COL_MIN

# fem chips a 118 px + fire gaps a 8
CHIPS_W = CHIP_W * N_CHIPS + CHIP_GAP * (N_CHIPS - 1)
height = fits(HERO_CW, CHIPS_W, "26 + 8 + 26", "26")
```

**Forskellen er ikke akademisk.** Topbjælken havde `900` skrevet i sig,
mens højresiden fyldte 440. Da temaknappen gjorde højresiden 542 bred,
fulgte de 900 ikke med — og bjælken ville have ombrudt til to rader på
enhver skærmbredde. Det var ikke et uheld under kodning; det var en
grænse, der ikke vidste hvad den beskyttede.

---

## De koblede par, der ikke var koblet

Det her var den egentlige gevinst. Fire steder skulle **to eller tre tal
være ens**, og intet i koden sagde det:

| Hvor | Skulle passe sammen | Hvad der ellers sker |
|---|---|---|
| `build_items.py` | Splittets højde, skinnens bredde, `EDITOR_W` | Skinnen tror den står under editoren, editoren tror den står ved siden af — højden passer til ingen af delene |
| `build_hub.py` | `TILE_W` og fliseholderens højde | Holderen har plads til én række fliser, mens fliserne står i tre. De to nederste bliver klippet |
| `build_hero.py` | Knapperækkens bredde og venstresidens reservation | Rækken bliver bredere end pladsen; hele heroen ombryder |
| `build_domain.py` | Højresidens bredde, venstresidens reservation, breakpointet | Bjælken ombryder på enhver skærmbredde |

De to sidste er nu **regnet ud af knapperne selv**, og builderen
efterprøver sig selv:

```python
HERO_BTNS = [("btnVhpTheme", 92), ("btnVhpBackToHub", 120),
             ("btnVhpValidate", 110), ("btnVhpExport", 130)]
ACTIONS_W = sum(w for _, w in HERO_BTNS) + HERO_BTN_GAP * (len(HERO_BTNS) - 1)
...
got = [(c.name, int(c.props["Width"])) for c in row]
if got != HERO_BTNS:
    raise SystemExit("HERO_BTNS passer ikke paa handlingsraekken: ...")
```

Tilføjer nogen en femte knap uden at skrive den i tabellen, stopper
byggeriet. Efterprøvet: både en manglende knap og en knap med sin egen
bredde uden om tabellen bliver fanget.

---

## Hvor meget flytter det sig?

| Hvad | Før | Efter | Flytning |
|---|---|---|---|
| Item-skinnen stables | 1000 | 1024 | +24 |
| Fem fliser → to | 1004 | 1024 | +20 |
| Heroen stables | 996 | 1024 | **+28** |
| FillPortions slås fra | 1024 | 1024 | 0 |
| Listen ved siden af formularen | 1600 | 1600 | 0 |
| Topbjælken ombryder | 900 | 856 | −44 (regnes nu af indholdet) |
| Procesindikatoren ombryder | 718 | 718 | 0 |
| To kolonner → en | 704 | 704 | 0 |
| Felter → en kolonne | 740 | 740 | 0 |

**Intet viewport-breakpoint flytter sig mere end 28 px**, og klyngen
996/1000/1004/1024 er nu ét tal. Container-grænserne står helt stille —
de var allerede regnet af deres indhold.

Bjælkens −44 er den ene, der er en rigtig ændring: den er ikke længere et
tal, men `højresiden + gap + 240 px læselig titel`. Efterregnet:

```
App.Width  855   ombryder
App.Width  856   titlen faar 240 px   i alt 792 af 792
App.Width  900   titlen faar 284 px
App.Width 1920   titlen faar 1304 px
```

---

## Layout-tjekket prøver nu dér hvor det skifter

Før stod der en håndplukket liste:

```python
WIDTHS = [420, 640, 900, 1024, 1366, 1920]
```

Den sprang henover **1023** — altså pixlen lige før layoutet skifter — og
det er præcis dér, layoutfejl bor. En container, der er høj nok på 1024 og
tolv pixels for lav på 1023, var usynlig for tjekket.

Nu kommer bredderne fra breakpointene selv, hver grænse **og pixlen under
den**:

```
[420, 719, 720, 1023, 1024, 1366, 1599, 1600, 1920]
```

Og `evaluate()` kender de to navngivne formler. Uden det kunne tjekket ikke
regne på en eneste højde, der afhænger af et breakpoint — altså netop dem,
der skifter. Alle 15 blev sprunget over med et tavst *"kan ikke"*.

> Efterprøvet mod den gamle udgave: **363 af 405 højder kan efterregnes,
> før og efter — ingen blev uevaluerbar af omlægningen.** De 42, der ikke
> kan, er blokeret af `Coalesce(` og `Parent.` og var det også før. Det er
> §5 i `docs/25-standardisering-plan.md`.

---

## Regel 8c: ingen skærm må sammenligne `App.Width` med et tal

```
[8c] FillPortions: sammenligner App.Width med et tal - braekpunkter hoerer
     i tools/layout_tokens.py (below()/if_below()/fits())
```

**Hvorfor det håndhæves på skærmen og ikke i builderne:** tallet bliver
som regel interpoleret ind i en f-streng, så en vagt, der læser
Python-kildens strengkonstanter, ser hverken bredden eller tallet. I den
byggede YAML står begge dele.

Aritmetik er i orden — `SHELL_W` *er* `(App.Width - 64)`. Det er kun
**sammenligningen**, der er en beslutning om enhedsklasse.

Efterprøvet mod en indsat overtrædelse: reglen fyrer.

---

## En fejl fundet undervejs

`tools/build_all.py` kørte videre, når en builder fejlede. Fejlede
`assemble_hub.py`, lå den **forrige** skærm stadig på disken, og
`check_layout.py` svarede *"Layout-tjek OK"* på den. Beskeden var sand om
filen og løgn om byggeriet — og den stod **nedenfor** fejlen, så den var
det sidste, man så.

Det skete under netop dette arbejde: `TILE_MIN` blev fjernet ét sted, men
brugt to. Byggeriet sagde OK.

Nu springer den resten af den app over og siger hvorfor.

---

## Sådan retter du et breakpoint

```bash
$EDITOR tools/layout_tokens.py      # BREAKPOINTS
python3 tools/build_all.py          # fire apps skifter sammen
```

Skal en **container** skifte ved en anden bredde, er svaret ikke et nyt
breakpoint — det er at regne grænsen ud af det, containeren skal holde, og
bruge `fits()`.

---

## Det, der stadig mangler

- `LayoutContext` bruges kun som læsbar formel; alle beslutninger går
  gennem `LayoutRank`. Der er endnu ingen *Mobile*-specifik adfærd — 720
  er sat, men ingen builder spørger på den endnu. Apperne er tablet- og
  desktoplayouts.
- 42 højder kan stadig ikke efterregnes pga. `Coalesce(` og `Parent.`
  (§5 i plan 25).
- Feltfarvningen (§2) står stadig.
