# 26 – Designtokens og mørk tilstand

Farverne i de fire apps står nu **ét sted**: `tools/design_tokens.py`.
Ingen builder må indeholde en farve, og `tools/build_all.py` nægter at
bygge, hvis nogen skriver en.

Mørk tilstand er ikke en funktion oven på det. Den er den anden gren af
den samme `If`.

---

## Det korte

```
tools/design_tokens.py          31 tokens x 2 temaer
        |
        | ref("bg-card")  ->  "C.'bg-card'"
        v
builderne                       skriver ALDRIG en RGBA-vaerdi
        |
        v
ScreenX.pa.yaml                 Fill: =C.'bg-card'
        ^
        | C = If(!darkModeEnabled, { ...lys... }, { ...moerk... });
        |
App.pa.yaml (Formulas)          den navngivne formel
```

Skifter `darkModeEnabled`, genberegner Power Fx den navngivne formel, og
hver eneste kontrol, der læser `C.'et-eller-andet'`, skifter med.
**Ingen kontrol ved, at mørk tilstand findes.**

| Fil | Ejer |
|---|---|
| `tools/design_tokens.py` | **Alle farver.** Begge temaer, temaformlen, `OnStart`-blokken og knappens handling |
| `*/build/gen_screen.py` | De gamle `C_*`-navne, som nu peger på tokens |
| `*/build/build_helpers.py` | `theme_button()` — den ene temaknap, alle fire apps bruger |
| `tools/build_all.py` | Vagten: ingen `RGBA(` og ingen `#rrggbb` i en builder |
| `*/build/check_layout.py` | Regel 8b: enhver token, skærmen bruger, findes i temaformlen |

---

## Hvorfor ikke miljøvariabler

Det var det oprindelige spørgsmål, og svaret blev nej. Efterprøvet på
Microsoft Learn:

- Miljøvariabler af typen **Data source** kan en canvas app bruge direkte.
  Det er dem, solutionen allerede bruger til SharePoint-listerne
  (`orsted_BioSapSiteUrl` + 20 listevariabler), og **det er rigtigt brugt.**
- Miljøvariabler af typen **Text** eller **JSON** kan en canvas app
  **ikke** læse fra Power Fx. De to eneste veje er Dataverse-tabellerne
  `Environment Variable Definition`/`Value` som datakilde, eller et cloud
  flow, der kalder `RetrieveEnvironmentVariableValue`. Begge er et
  **opslag ved opstart**.
- Oven i det: *"It may take up to an hour to fully publish updated
  environment variables"*.

Et opslag ved opstart for at vide, hvilken grøn en kant skal have, bryder
med appernes egen vigtigste ydelsesregel (*ingen datahentning i
`App.OnStart`*), og indtil svaret er der, har felterne ingen farve.

Og farver er ikke det, miljøvariabler er til: de er til det, der **er
forskelligt mellem DEV og PROD**. Den grønne er den samme begge steder.

**Den ALM-gevinst, spørgsmålet egentlig var ude efter** — at kunne bygge
mod et andet miljø uden at rette i koden — hører til miljø- og app-id'erne,
ikke til farverne. Den står som §3 i `docs/25-standardisering-plan.md` og
er ikke lavet endnu.

---

## Tokenerne

31 navne, samme sæt i begge temaer. `design_tokens._check()` stopper
byggeriet, hvis et navn kun står det ene sted — for en token, der mangler,
giver **blank**, og blank er gennemsigtig. Kontrollen ville forsvinde, men
kun for de brugere der har slået mørk tilstand til.

| Gruppe | Navne |
|---|---|
| Brand | `color-brand-primary`, `-hover`, `-soft` |
| Baggrunde | `bg-app`, `bg-surface`, `bg-card`, `bg-muted`, `bg-modal` |
| Tekst | `text-primary`, `text-muted`, `text-on-primary` |
| Kanter | `border-default`, `border-subtle` |
| Inputfelter | `input-bg`, `input-bg-disabled` |
| Tilstande | `state-{ok,warn,error,info,neutral}-{fg,bg}` |
| Øvrigt | `overlay` |
| Domæner | `domain-{fl,eq,mp,mat,vhp}` |

Plus to **afledte** hex-værdier, `hex-text-primary` og `hex-text-muted`.
VH-plans tabeloverskrifter er `HtmlViewer`-kontroller, og HTML kender ikke
`RGBA()`. Farven stod derfor som `#59667A` midt i en stylestreng — det
rigtige tal, men uden nogen forbindelse til `text-muted`. Hex-værdierne
**regnes nu ud** af de samme tokens og kan derfor ikke glide.

`RGBA(0, 0, 0, 0)` er ikke en token. Gennemsigtig er gennemsigtig i begge
temaer, og der er ingen beslutning at træffe om den.

---

## Det lyse tema er uændret

Det var kravet: omlægningen flytter farverne et andet sted hen, den laver
dem ikke om.

Efterprøvet kontrol for kontrol — hver tokenreference substitueret tilbage
til sin lyse værdi og sammenlignet med skærmen, som den så ud før:

| App | Farveegenskaber efterprøvet | Ændret | Nye kontroller |
|---|---|---|---|
| Masterdata Hub | 129 | **0** | `btnMdTheme` |
| Maintenance Plan App | 576 | **0** | `btnVhpTheme` |
| Equipment App | 188 | **0** | `btnDomTheme` |
| Material App | 191 | **0** | `btnDomTheme` |

1.084 farveegenskaber, ingen ændret, ingen kontrol fjernet.

**Én kendt afvigelse, som ikke blev rettet:** `state-ok-fg` på
`state-ok-bg` giver 4,44:1 og rammer dermed lige under WCAG AA's 4,5 for
brødtekst. Det er en fejl, appen har i dag, og den står uændret, netop for
at lys tilstand ser ud præcis som før. Rettelsen er én værdi —
`RGBA(19, 120, 87, 1)` giver 4,86 og kan ikke ses med det blotte øje.

---

## Det mørke tema er efterregnet, ikke gættet

Ikke "det lyse tema med omvendt lysstyrke". Kontrastforhold:

| Par | Lys | Mørk | Krav |
|---|---|---|---|
| Brødtekst på app-baggrund | 14,07 | 15,47 | 4,5 |
| Brødtekst på kort | 15,40 | 14,42 | 4,5 |
| Dæmpet tekst på kort | 5,62 | 6,96 | 4,5 |
| Knaptekst på brandfarve | 5,91 | **5,17** | 4,5 |
| Status grøn | **4,44** | 7,66 | 4,5 |
| Status gul | 5,39 | 8,58 | 4,5 |
| Status rød | 5,35 | 5,58 | 4,5 |
| Status blå | 6,87 | 5,94 | 4,5 |
| Status neutral | 4,78 | 5,71 | 4,5 |
| Tekst i inputfelt | 15,94 | 16,29 | 4,5 |
| Kant mod inputfelt | — | 4,24 | 3,0 |

**Tre valg var ikke frie:**

1. `color-brand-primary` er blue-600, ikke blue-500. Hvid tekst på
   blue-500 giver **3,68:1** og falder dermed under AA for de 14 px
   halvfede knaptekster, apperne bruger. Blue-600 giver 5,17 og står
   stadig 3,45 fra kortet bagved.
2. `color-brand-primary-hover` er **mørkere** end grundfarven — ikke
   lysere, som man ellers gør på mørk baggrund. Samme grund: en lysere
   hover ville tage knaptekstens kontrast med sig ned. Knappen er allerede
   afgrænset af sin hvilefarve.
3. `border-default` er slate-500, ikke slate-700. Kanten er det, der
   afgrænser et **inputfelt**, og skal derfor selv kunne ses: slate-700
   giver 1,95 mod feltets baggrund, slate-500 giver 4,24. `border-subtle`
   — de rene skillelinjer — må godt være svagere.

---

## Sådan huskes valget

Tre kilder, i den rækkefølge:

```
Coalesce(
    If(Lower(Param("theme")) = "dark",  true,
       Lower(Param("theme")) = "light", false),   1. kom fra hubben
    First(colAppPrefs).Dark,                      2. eget gemte valg
    false                                         3. foerste gang
)
```

> **Forudsætning:** appens *Formula-level error management* skal være slået
> **til** (Settings → Updates → Retired: *"Disable formula-level management"*
> skal stå OFF). Den er til som standard i nye apps. Er den slået fra,
> virker `IfError` ikke efter hensigten — og så fejler `App.OnStart` i
> Studio i stedet for at blive fanget.

**`SaveData`/`LoadData` virker i den publicerede web-afspiller** (1 MB), men
**ikke i Studio**. Derfor er begge kald pakket i `IfError`. Uden den ville
hele `App.OnStart` stoppe, hver gang nogen trykker Preview — og fejlen
ville se ud til at handle om noget helt andet, fordi resten af `OnStart` så
ikke nåede at køre.

**Lageret er isoleret pr. app-id.** Det er derfor led 1 findes: uden det
ville et klik fra en mørk hub over i Equipment lande i en lys app, og
brugeren ville se appen skifte farve som følge af sit eget klik. Hubben
hænger `?theme=dark` på play-URL'en, og satellitterne hænger den på igen på
vejen tilbage.

Skifter brugeren tema **inde i** en satellit, er det dét valg, der gemmes
lokalt og gælder næste gang, appen åbnes direkte.

> **Det følger ikke brugeren på tværs af maskiner.** Vælger nogen mørk
> tilstand på kontoren, er browseren derhjemme stadig lys. Skal det følge
> brugeren, er svaret en lille SharePoint-liste `MD_UserPrefs`, og den
> koster ét rækkeopslag ved opstart plus en datakilde i alle fire apps.
> Det er fravalgt her.

---

## Knappen

`build_helpers.theme_button()` — **samme kontrol i alle fire apps**. En
knap, der ser forskellig ud fra app til app, er præcis den slags drift, der
har gjort de fire apps forskellige indtil nu.

| App | Kontrol | Placering | Tekst |
|---|---|---|---|
| Masterdata Hub | `btnMdTheme` | Toplinjen, yderst til højre | `Dark` / `Light` |
| Maintenance Plan | `btnVhpTheme` | Hero, før "Til hubben" | `Moerk` / `Lys` |
| Equipment | `btnDomTheme` | Topbjælken, før "Til hubben" | `Moerk` / `Lys` |
| Material | `btnDomTheme` | Topbjælken, før "Til hubben" | `Moerk` / `Lys` |

Teksten siger **hvad der sker**, ikke hvad der er: står appen lyst, står
der "Mørk" på knappen. Samme konvention som Windows og browsere — en knap
er en handling. `AccessibleLabel` siger det udførligt ("Skift til mørkt
tema"), fordi ét ord uden knappens udseende ikke er nok for en skærmlæser.

**Bredderegnskabet skal følge med.** En knap mere i en række med fast
bredde gør rækken bredere, og gør man ikke plads til den i den anden side,
ombryder hele bjælken på enhver skærmbredde. `conDomBarRight` gik fra 440
til 542, og `conDomBarLeft` fra `SHELL_W - 500` til `SHELL_W - 602`. De to
tal hører sammen.

---

## Sådan retter du en farve

```bash
# 1. ret vaerdien i BEGGE temaer
$EDITOR tools/design_tokens.py

# 2. byg. Fire apps skifter sammen.
python3 tools/build_all.py

# 3. deploy den, der skal se anderledes ud
python tools/canvas_mcp.py deploy --app equipment
```

Der er ingen anden vej. Skriver du en farve i en builder, stopper
byggeriet:

```
Der staar farver i builderne:

  Equipment App/build/domain_config.py:132: RGBA(...) i en builder - brug design_tokens.ref()
  Equipment App/build/domain_config.py:133: hex-farve i en builder - brug design_tokens.ref_hex()
```

Vagten læser **syntakstræet**, ikke linjerne. Første udgave klippede
kommentarer af ved et `#` og gav to falske fund med det samme — begge var
en kommentar, der forklarede, at farven ikke måtte stå der. En vagt, der
melder om sin egen dokumentation, bliver slået fra.

---

## Det, der stadig mangler

- **Feltfarvningen er ikke lavet om endnu.** `docs/25-standardisering-plan.md`
  §2 står stadig: fire forskellige regler for hvornår en feltkant bliver
  rød eller grøn, og en datovælger der altid er grå. Tokenerne er
  forudsætningen for den rettelse, ikke rettelsen selv.
- **`AccessibleLabel` er stadig kontrolnavnet** på 75 felter (§6). Den nye
  temaknap gør det rigtigt; de andre gør ikke.
- **Miljø- og app-id'erne står stadig fire steder** (§3).
