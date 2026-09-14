# Prompt til VS Code (Sonnet 5) — deploy Masterdata Hub

Kopiér alt under linjen ind som din første besked i VS Code.

---

Du skal oprette og deploye en **ny** canvas app: landingssiden for SAP
masterdata-indmeldinger. Koden ligger i repoet — din opgave er at få listen
og appen på plads i Power Apps Studio og verificere.

## Kilde

Repo `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`, mappe `Masterdata Hub/`. Pull den
først og læs `Masterdata Hub/README.md`.

| | |
|---|---|
| Miljø | Bioenergy Solutions DEV |
| `environment_id` | `e0f8f822-d16a-e878-ba4e-fb42bc617e47` |
| Solution | BIO SAP (`43fe3e8a-adbe-4e49-996b-42e9b7081b2d`) |
| Ny app | Opret den — den findes ikke endnu |

## Trin 0 — listen skal findes først

Appen har **én** datakilde: SharePoint-listen `MD_RequestIndex`.
`compile_canvas` fejler på et ukendt navn, hvis den ikke er tilføjet appen.

1. Kør `sharepoint/provision/Provision-RequestIndex.ps1` mod SharePoint-sitet
   (bed brugeren om URL'en).
2. Bed brugeren oprette en tom canvas app i solution BIO SAP og tilføje
   `MD_RequestIndex` som datakilde.
3. Få `app_id` på den nye app.

Gå ikke videre, før begge dele er bekræftet.

## Trin 1 — testdata

Uden rækker kan intet verificeres. Opret 15–20 rækker i `MD_RequestIndex`
fordelt på alle fem `Domain`-værdier og på mindst fem forskellige
`Status`-værdier. Husk:

- `RequesterEmail` skal være **brugerens egen e-mail i småt** på cirka
  halvdelen, så "Mine indmeldinger" ikke er tom.
- `IsOpen` skal være `true` for alt undtagen `OprettetISAP`, `Afvist` og
  `Annulleret`.
- `StatusStep` skal matche status: Kladde 1, Indsendt 2, UnderBehandling og
  AfventerInfo 3, KlarTilSAP 4, OprettetISAP 5, Afvist og Annulleret 0.
- `AppUrl` på VH-plan-rækkerne sættes til
  `https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47/a/11fa8d90-868a-45a4-ba23-28f2cf0671a2`
- `LastActionOn` spredt over de seneste 30 dage.

## Trin 2 — byg og deploy

```bash
cd "Masterdata Hub/build"
python3 generate_hub_onstart.py
python3 assemble_hub.py
python3 ../../shared/canvas/check_layout.py ../ScreenMdHub.pa.yaml   # skal være grøn
```

Derefter, med `directoryPath` = den lokale sti til mappen `Masterdata Hub`:

```
canvas-authoring-connect   environment_id = <ovenfor>, app_id = <den nye app>
canvas-authoring-compile_canvas   directoryPath = <sti>
canvas-authoring-sync_canvas      directoryPath = <sti>
canvas-authoring-get_appchecker_errors
canvas-authoring-get_accessibility_errors
```

**Compile før sync.** Ret aldrig i YAML'en — den er genereret. Skal noget
laves om, så ret i `build/*.py`, kør de tre kommandoer igen, og synk.

## Trin 3 — appindstilling

Sæt appens **Data row limit til 2000** (Indstillinger → Generelt → Data row
limit). Standarden er 500, og det er for lavt til køen.

## Trin 4 — test manuelt

Ingen automatiserede browsertests. Kør listen og rapportér hvert punkt.

**Hastighed — det er hele pointen med appen**

1. Åbn appen med stopur. **Første skærm skal være klar på under 2 sekunder.**
   Er den ikke det, så stop og rapportér — der er noget galt, for
   `App.OnStart` henter ingen data og der er kun én datakilde.
2. Åbn App checker → Performance. Der må ikke være advarsler om
   `App.OnStart`.

**Delegation — afgør om siden skalerer**

3. Åbn `galMdRequests.Items` i formellinjen. Noter **hvor** Studio sætter
   delegationsadvarsler.
   → Den ydre `If` med to `Filter` er den vigtige: begge grene skal
   delegeres hver for sig. Rapportér præcis hvad advarslen siger.
4. Samme for `txtMdTileCountVHP.Text` (fliseantallet).

**Funktion**

5. Segmentet: "Mine indmeldinger" viser kun rækker med din e-mail.
   "Til behandling" viser alle åbne på tværs af indmeldere.
6. Klik en flise → listen filtreres til det domæne, flisens ramme farves, og
   knappen skifter til "Vis alle". Klik igen → filteret ryddes.
7. Statuschips: Åbne / Afsluttede / Alle ændrer listen korrekt.
8. Søgefeltet: skriv de første tegn af et nummer, en tekst og et værk —
   alle tre skal give hit.
9. Fliserne for FL, Udstyr, Målepunkt og Materiale skal vise **"Kommer snart"**
   og være deaktiverede. Kun VH-plan har "Opret ny".
10. "Opret ny" på VH-plan-flisen åbner VH-plan-appen i en **ny fane**.
11. Klik **Åbn** på en VH-plan-række → VH-plan-appen åbnes i en ny fane med
    `?reqid=<RequestGuid>` i URL'en. Tjek at hub-fanen stadig er indlæst.
12. Klik **Åbn** på en række uden `AppUrl` → venlig fejlbesked, ingen crash.
13. Filtrér til noget der ikke findes → "Ingen indmeldinger matcher filtrene."
14. Træk vinduet ned til ~900 px bredde → fliserne ombryder til to pr. række,
    og intet bliver klippet.

## Rapportér

- Opstartstid i sekunder.
- Præcis hvad delegationsadvarslerne siger på punkt 3 og 4.
- Punkt for punkt hvad der er grønt, og hvad der fejlede.
- `app_id` på den nye app, så den kan skrives ind i dokumentationen.

Commit og push kun til `claude/vh-plans-strategy-packages-lu8w70`. Opret ikke
en pull request.
