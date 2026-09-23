# 30 – Responsivt layout: rammen, den forsigtige bredde og to tilstande

Bjælker, der forsvandt, og knapper, der ikke kunne ses. Det så tilfældigt
ud – hel skærm på én maskine, klippet på en anden – og hver rettelse
flyttede fejlen et andet sted hen. Her er, hvorfor det skete, og den
metode, alle fire apps nu er bygget efter, så det ikke kan ske igen uden at
byggeriet stopper.

---

## Hvorfor det var "hit and miss"

Canvas-containere kan ikke måle deres indhold. Hver højde og hver bredde
regnes derfor ud i Python og skrives som en formel. Det er rigtigt nok —
men regnestykket byggede på tre antagelser, og alle tre holdt kun nogle
gange.

### 1. `SHELL_W` lovede mere plads, end der var

Alle bredder i alle fire apps er regnet af ét udtryk:
`SHELL_W = App.Width - 64`. Det var oprindeligt 24 + 24 px padding **plus
16 px til den lodrette scrollbar**.

I commit `863c168` blev paddingen sat op til 32 + 32 "så tallet passer".
Dermed var scrollbarens plads væk. Og scrollbaren er altid der, for
indholdet er altid højere end skærmen:

| Maskine | Scrollbar | Plads til indholdet | `SHELL_W` lover |
|---|---|---|---|
| Mac, overlay-scrollbar | ligger oven på indholdet | `App.Width - 64` | `App.Width - 64` ✔ |
| Windows, klassisk scrollbar | tager ~17 px | `App.Width - 81` | `App.Width - 64` ✘ |

Hver række, der var regnet til at fylde `SHELL_W` på pixlen — topbjælken,
fem hub-fliser, fire felter i en formularrække — var 17 px for bred på
Windows. **Derfor "hit and miss":** den samme skærm var hel på én maskine og
klippet på en anden.

### 2. En række med `LayoutWrap` kan få flere linjer, end højden har plads til

Er en wrap-række for bred, ombryder platformen det sidste barn til en ny
linje. Men højden er regnet i Python og ved ikke, at det skete. Den nye
linje ligger under containerens kant — **klippet væk**.

Det er præcis sådan topbjælkens højreside forsvandt: *To the hub*,
temaknappen, rækkenummeret. `wrap_row_height()` gjorde det ikke bedre: den
regnede med højst **to** linjer, men på en smal skærm blev det tre, fire
eller fem.

### 3. Hele skærmen hang på én sum

```
conDomShell.Height = 60 + bjælke + 16 + formular + 16 + liste/dokumenter + 16 + indsend
```

Én forkert term hvor som helst, og skallen blev for lav. Det nederste —
indsend-knapperne — blev klippet. Hubbens skal indeholdt endda en hel
forespørgsel mod SharePoint i sin højde. Fejler den formel, bliver hele
skallen til ingenting, **bjælken med**.

Og summen kunne ikke efterprøves: `check_layout` kunne kun regne på
`varVhp*`. Alt med `varDom*` eller `gbl*` blev sprunget over med et tavst
"kan ikke". Det skjulte, at `conDomSplit` i Equipment og Material kun havde
højde til **én** linje, mens listen og dokumentruden stod under hinanden på
alle skærme under 1600 px — **hele dokumentruden var klippet væk**.

### Hvad det nye tjek fandt på den gamle kode

Regel 4c (nedenfor) spiller layoutet igennem, som platformen gør det. Kørt
mod koden før denne ændring:

| App | Klippet | Hvornår |
|---|---|---|
| Equipment, Material | `conDomBar` — hele højresiden af bjælken | ≥ 1024 px, Windows |
| Equipment, Material | `conDomRow*` — sidste felt i hver formularrække | ≥ 1024 px, Windows |
| Equipment, Material | `conDomSplit` — hele dokumentruden | < 1600 px, overalt |
| VH-plan | `conVhpPlanRow0–2` — sidste felt i planhovedet | ≥ 1024 px, Windows |
| VH-plan | `conVhpItemsSplit` — item editoren | ≥ 1024 px, Windows |
| VH-plan | `conVhpProcessStrip`, `conVhpOpsTabBar` | smal skærm |
| Hub | `conMdBar`, `conMdTiles`, `conMdFilters` | smal skærm (+ Windows) |

---

## Metoden: tre regler

### Regel A — Rammen: bjælken står uden for det, der scroller

Microsofts eget mønster for responsive canvas apps, og nu det samme i alle
fire apps (`build_helpers.app_frame`):

```
con<X>Root      lodret, Parent.Width × Parent.Height, scroller IKKE
  con<X>Header    fast højde — kun afhængig af App.Width. Bjælken står her
  con<X>Body      FillPortions = 1, LayoutOverflowY = Scroll
    kort
    kort
    ...
```

- **Bjælken kan ikke scrolle væk**, og den kan ikke klippes af et andet kort.
- **Der er ingen sum.** En scrollende container skal ikke være høj nok til
  sit indhold — den scroller. Hvert kort regner stadig sin egen højde ud,
  men en fejl dér rammer kun det kort, ikke alt nedenunder.
- **Headerens højde afhænger kun af skærmbredden** — aldrig af data. Den kan
  ikke fejle på netværket.
- Handlingerne, man skal kunne nå hele tiden — *Validate*, *Export JSON*,
  *To the hub*, temaet — står i bjælken. I VH-plan stod de før i hero-kortet
  og scrollede væk.

### Regel B — Den forsigtige bredde: `SHELL_W` er en nedre grænse

`SHELL_W` er ikke længere et gæt på den præcise bredde. Den er det
**mindste**, platformen kan give, og der er lagt luft oveni:

```
krop:    24 (venstre) + 16 (højre) + 18 (scrollbar) + 6 (luft) = 64
header:  24 (venstre) + 34 (højre = 16 + scrollbar) + 6 (luft) = 64
```

Det står ét sted — `RAMMEN` i `tools/layout_tokens.py` — og
`SHELL_W = App.Width - 64` er uændret. Alle breakpoints står derfor stille.
Headeren får scrollbarens bredde som højre-padding, så dens højre kant
flugter med kortenes.

**Den faktiske bredde er altid ≥ `SHELL_W` + 6.** En række, der er regnet til
at passe, passer — på Mac og på Windows.

### Regel C — To tilstande, aldrig noget midt imellem

`build_helpers.flow_row()` erstatter `wrap_row_height()`. En række står
**enten** på én linje **eller** som et gitter med et fast antal kolonner:

| Tilstand | Bredder | Linjer | Højde |
|---|---|---|---|
| passer | børnenes egne | 1 | det højeste barn |
| passer ikke | `(Parent.Width − gaps) / kolonner − 1` | `ceil(n / kolonner)` | summen af linjerne |

Platformen får aldrig lov at bestemme, hvor mange linjer det bliver.
Antallet er et tal, Python kender — derfor kan højden ikke være forkert.

Grænsen regnes af børnenes egne bredder mod den forsigtige bredde, så den
flytter sig selv, når nogen tilføjer en knap. `flex=` lader ét barn
(typisk titlen) tage resten af linjen.

`build_helpers.top_bar()` er bjælken i alle fire apps: titel og undertitel
til venstre, handlinger til højre. På en smal skærm står titlen over
knapperne, og knapperne står to og to. Der er ingen håndskreven tabel over
knapbredderne og ingen vagt, der skal holde den i trit — `BAR_RIGHT`,
`HERO_BTNS`, `ACTIONS_W` og deres vagter er væk.

---

## Tjekket: layoutet spilles, ikke kun formlerne

| Regel | Fanger |
|---|---|
| **4c** | Hver wrap-række pakkes ved hver testbredde, som autolayout gør det — fra venstre, ny linje når næste barn ikke kan være der — i den bredde, containeren **faktisk** får: padding trukket fra, **scrollbaren trukket fra**, og `Stretch` i en lodret forælder respekteret. Højden skal kunne rumme de linjer, der kommer ud af det |
| **23** | Rammen: første barn er `con<X>Root` (Parent.Width × Parent.Height, scroller ikke), præcis én krop med `Scroll` og `FillPortions > 0` |
| **23b** | Headerens højde må ikke nævne `CountRows`, `Filter`, `LookUp`, `IsEmpty`, `col*`, `var*`, `gbl*` — og skal kunne regnes ud ved alle testbredder |
| **23c** | Padding + scrollbar + luft ≥ `SHELL_INSET`. Sætter nogen paddingen op igen, som i `863c168`, stopper byggeriet |

`evaluate()` kan nu også regne på `varDom*`, `gbl*`, `!`, `<>`, tekst i
anførselstegn og `IsEmpty(…)` — ugunstigste tilfælde: det, der kun vises for
en valgt række, **er** vist. Højder, der ikke kunne efterregnes, gik fra 36
til 26 af 918; de 26 tilbageværende er næsten alle `Parent.*` i gallerier og
rammens egen `Parent.Height`.

### Efterprøvet mod plantede fejl

| Plantet | Fyrer |
|---|---|
| Kroppens højre-padding 32 (den gamle fejl) | 23c + 4c på fire rækker |
| `CountRows` i headerens højde | 23b |
| Rammen selv scroller | 23a + 4c |
| `conDomSplit` tilbage til højde til én linje | 3 + 4c |
| Bjælkens højreside 20 px bredere end grænsen | 4c |
| Uændret | tavs |

---

## Sådan bygger du noget nyt

- **En ny sektion** → læg kortet i listen til `app_frame(...)`. Regn ikke en
  skal ud.
- **En ny knap i bjælken** → tilføj den til listen, `top_bar()` får. Intet
  andet.
- **En række, der skal kunne ombryde** → `flow_row()`. Skriv aldrig
  `wrap="true"` med en håndregnet højde.
- **En bredde** → regn af `SHELL_W` (eller en container-bredde afledt af
  den), aldrig af `App.Width` direkte. `Parent.Width` er også sikkert: den
  er den faktiske bredde.
- **En højde** → må afhænge af konstanter, `App.Width`/`LayoutRank` og
  samlinger (`CountRows(col…)`). Aldrig af en datakilde, og aldrig af en
  anden kontrols `.Height`.

## Det, der stadig står

- **Modalerne i VH-plan** har faste bredder (680 og 620 px). De ligger
  uden for rammen og passer fra Tablet (720 px) og op. Apperne er tablet-
  og desktoplayouts; en telefonudgave af modalerne er ikke bygget.
- **Tekst, der ombryder**, kan platformen ikke måle for os. Beskrivelsen i
  VH-heroen har nu to højder (40/60 px) efter bredden; andre tekster er
  sat til `wrap="false"` eller har fast plads.
- **Kortenes indre højder** er stadig regnet i Python — det kan canvas ikke
  gøre anderledes. Men en fejl dér rammer nu kun det kort, og regel 2–4c
  efterregner dem ved hver bygning.
