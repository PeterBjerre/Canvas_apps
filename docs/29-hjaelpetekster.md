# 29 – Hjælpeteksterne flyttede til SharePoint

`MD_HelpText`. Teksten under et felt og afsnittene i `?`-panelet kan nu
rettes af dem, der kender fagligheden, uden at nogen skal bygge appen.

---

## Hvad der var problemet

Teksterne stod i `Maintenance Plan App/build/build_help.py` — 15 hints og
21 panelafsnit. Rigtige tekster, skrevet ud fra *"Den gode VH-plan"* og
*"Planlægning af en VH ordre"*, og de eneste, der kunne rette et komma i
dem, var dem der kunne køre `python3 tools/build_all.py` og deploye.

Spørgsmålet var, om appen bliver langsom af at hente dem. **Det gør den
ikke.** Det er én navngiven formel — doven og cachet:

```
colVhpHelp = ForAll(
    Filter(MD_HelpText, AppArea.Value = "MaintenancePlan") As R,
    { Key: R.HelpKey, Kind: R.Kind.Value, Heading: ..., Body: ..., Ord: ... }
);
```

Ét delegeret kald, første gang en hjælpetekst faktisk vises. Appen har 13
andre af samme slags. `App.OnStart` henter stadig ingenting.

---

## Det, der ikke kunne flytte

Syv af de 22 hints er **ikke tekst**. De er Power Fx:

```powerfx
If(
    !IsBlank(varVhpPlan.Plant) && !StartsWith(Upper(PlanText), Upper(Plant)),
    "Should start with the plant code " & varVhpPlan.Plant &
        " - so the plan can be found without searching by plant.",
    "Start with the plant code. The text must cover every task the plan calls."
)
```

Den fortæller **hvorfor feltet lyser lige nu**, og den sætter værkskoden
ind. *"Required: 2 item(s) have activity type 110 or 115"* er mere værd end
*"udfyldes ved lovpligtige eftersyn"*. Sådan en kan ikke være en række i
en liste.

| | antal | hvor |
|---|---|---|
| Hints, ren tekst | 15 | `MD_HelpText` |
| Hints, dynamiske | 7 | `build_help.HINTS` |
| Panelafsnit | 21 + 4 kildelinjer | `MD_HelpText` |

---

## En tom række betyder ingen tekst

Det var valget: **ingen fallback til koden.** Findes nøglen ikke, giver
`LookUp` blank, og feltet viser ingenting.

```powerfx
Coalesce(
    LookUp(colVhpHelp, Key = "PlanType" && Kind = "Hint").Body,
    ""
)
```

Alternativet — falde tilbage på en kopi i koden — ville betyde, at den der
sletter en række i SharePoint **ikke kan se forskel i appen**. Så er
listen ikke længere kilden; den er et lag oven på en kilde, ingen kan se.
Panelet siger det højt, når det er tomt:

> No help text for this section yet - it is maintained in the SharePoint
> list MD_HelpText.

---

## Panelet er blevet et galleri

Før kunne højden regnes: teksten stod i koden, og hvert afsnit fik
`18 * (1 + len(body) // 95)` — et gæt på antal linjer ud fra antal tegn.

Nu kendes længden ikke, når appen bygges. Panelet er derfor et **galleri**
med fast skabelonhøjde: overskrift 18 + fire linjer brødtekst à 16 + 6 px
luft = **88 px**.

Fire linjer dækker det længste af de 21 afsnit, seedet blev lavet af
(objektlisten, 312 tegn ≈ 3,3 linjer). **Et længere afsnit bliver
klippet.** Det er prisen for at teksten kan rettes uden en build, og den
står i `HELP_LINE_H` i `build_plan_header.py`, så den er til at se og til
at hæve.

---

## Én kilde pr. nøgle

Delingen er kun sund, så længe en nøgle står præcis ét sted. Står
`PlanText` begge steder, **vinder koden** — og den, der retter rækken i
SharePoint, ser ingen forskel. Det er den værste slags fejl: den ligner en
tilfældighed, og ingen melder den.

`tools/check_helptext.py` læser `HINTS`-nøglerne ud af `build_help.py` og
holder dem op mod seedet. Kører sidst i `build_all`.

```
Hjaelpetekst: 1 noegle(r) staar BAADE i koden og i listen.
  PlanText

Koden vinder, saa den, der retter raekken i SharePoint, ser
ingen forskel i appen. Vaelg eet sted:
  dynamisk (Power Fx) -> bliv i build_help.HINTS, slet raekken
  ren tekst           -> slet den fra HINTS, behold raekken
```

**Det den ikke kan:** seedet er det, listen blev *fyldt* med — ikke det,
den indeholder nu. Opretter nogen en `PlanText`-række direkte i
SharePoint, opdager tjekket det ikke. Det ville kræve et opslag mod
listen, og byggeriet læser ikke SharePoint.

---

## En fejl fundet undervejs

`check_datasources` fyldte kun `used` fra `Patch()`. **En liste, appen kun
læser, blev aldrig tjekket** — hverken navnet eller kolonnerne. Den
kunne hedde hvad som helst.

`MD_HelpText` var præcis sådan en: læst af en navngiven formel, skrevet af
ingen. Tre ting rettet:

1. `Filter`/`LookUp`/`Sort` tæller nu også som brug.
2. `ForAll(Filter(Liste, ...) As R, ...)` — kilden må være et **kald**, ikke
   kun et navn. Mønstret krævede `ForAll(Liste As R`, så de fem kolonner i
   den nye formel blev ikke efterprøvet.
3. `New-PnPList -Title $LIST_NAME` — navnet i en variabel bliver nu slået
   op, og ethvert `New-*Field` genkendes som en kolonne.

Med det kommer `MD_HelpText` frem som *"oprettes af provisioneringen, men
findes ikke i udtrækket endnu"*, hvilket er den rigtige tilstand.

To falske fund fulgte med: `ops` og `sel` er **With-scope-navne**, ikke
lister. Tjekket samler nu `With({ navn: ... })` og `As NAVN` og springer
dem over.

---

## Sådan tager du det i brug

```powershell
# 1. Opret listen og fyld den. Seedet ligger allerede i repoet.
sharepoint\provision\Provision-HelpText.ps1 -SiteUrl "https://..." -Seed

# 2. Eksportér skemaet, så check_datasources kender kolonnerne
sharepoint\inspect\Export-ListSchema.ps1 -SiteUrl "https://..."

# 3. Byg og deploy
python3 tools\build_all.py
python  tools\canvas_mcp.py deploy --app vhplan
```

**`tools/gen_helptext_seed.py` skal du ikke køre.** Den er et
flytteværktøj, og den er kørt. Da teksterne var flyttet, havde
`build_help.py` ikke længere en kopi at læse — så den ville skrive en
**tom** csv oven i de 36 rækker. Den siger fra i stedet:

```
STOPPER: build_help.py har ingen statiske hjaelpetekster tilbage,
men sharepoint/seed/MD_HelpText.csv har 36 raekke(r).
...
Skal seedet laves om, er kilden LISTEN - eksporter den fra SharePoint.
```

`-Seed` **overskriver ikke** rækker, der findes i forvejen — de er
SharePoints nu. Skal listen sættes tilbage til det, koden havde, er der
`-Force`.

Indtil trin 2 er kørt, står der i hvert build:

```
1 liste(r) oprettes af provisioneringen, men findes ikke i udtraekket endnu:
  MD_HelpText
```

Det er den rigtige tilstand — kolonnerne er ikke efterprøvet endnu.

---

## Det, der stadig står

- **Kun VH-plan læser listen.** `AppArea` er der allerede, så Equipment og
  Material kan flytte deres hjælpetekster ind uden en skemaændring — men
  de har ingen endnu.
- **88 px pr. panelafsnit.** Et længere afsnit klippes. Hæv `HELP_LINE_H`,
  hvis det bliver et problem.
