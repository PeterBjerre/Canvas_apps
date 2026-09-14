# Prompt til VS Code (Sonnet 5) — udtræk SharePoint-strukturen

Kopiér alt under linjen ind som din første besked i VS Code.

---

Du skal udtrække den komplette struktur af SharePoint-listerne bag VH-plan
appen og committe resultatet. Scriptet findes allerede — **skriv det ikke om,
og opfind ikke dit eget.**

## Kilde

Repo `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`. Pull den først.

Scriptet er `sharepoint/inspect/Export-ListSchema.ps1`. Læs
`docs/08-datamapning.md` først — den forklarer hvad udtrækket skal bruges til,
og hvilke seks spørgsmål det skal besvare.

## Trin 1 — spørg brugeren om to ting

Gå ikke videre, før du har svar:

1. **Site-URL'en** til det site, listerne ligger på.
2. **Må rigtige data komme med i repoet?** Scriptet tager som standard de
   første 8 rækker pr. liste med, så værdiernes *form* kan ses. Er der noget i
   listerne, der ikke må forlade sitet, skal du køre med `-NoData`.

## Trin 2 — kør scriptet

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser    # kun hvis den mangler
cd sharepoint\inspect
.\Export-ListSchema.ps1 -SiteUrl "<url fra trin 1>"
```

Det åbner et browservindue til login. Bed brugeren logge ind, og vent.

**Hvis det fejler med noget om `ClientId`:** PnP.PowerShell 2.x har ikke
længere en fælles app-registrering. Så skal der enten sættes en miljøvariabel
`PNP_CLIENT_ID`, gives `-ClientId <app id>`, eller registreres en app:

```powershell
Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP Masterdata" -Tenant <tenant>.onmicrosoft.com -Interactive
```

Det kræver rettigheder i Entra. Kan brugeren ikke det, så stop og rapportér —
find ikke på en anden vej rundt om det.

**Scriptet må ikke ændres for at komme videre.** Fejler det på noget andet, så
rapportér fejlen ordret og stop.

## Trin 3 — kontrollér før du committer

Et halvt udtræk, der bliver committet i stilhed, er værre end ingenting.
Tjek alle fire:

1. `sharepoint/inspect/out/schema.md` findes og er over 100 linjer.
2. Antallet af `##`-overskrifter i `schema.md` svarer til antallet af lister,
   scriptet skrev ud i konsollen.
3. Disse lister **skal** være med, ellers er noget gået galt:
   `MaintenancePlans`, `MaintenanceItems`, `TaskListMain`, `MainWorkCenters`,
   `PlantList`, `StandardStrategyList`, `CallHorizonMatrix`,
   `MaintenanceActivityTypeList`, `SortFieldList`, `MD_RequestIndex`.
4. Kørte du **uden** `-NoData`: der findes `sample-*.json`-filer, og de er
   ikke tomme arrays.

Mangler noget, så rapportér præcis hvad — lap ikke filerne i hånden.

## Trin 4 — commit og push

```bash
git add sharepoint/inspect/out sharepoint/inspect/Export-ListSchema.ps1
git commit -m "Udtræk af SharePoint-listestrukturen"
git push -u origin claude/vh-plans-strategy-packages-lu8w70
```

Opret **ikke** en pull request.

## Trin 5 — læs schema.md og svar på det du kan

Du har nu strukturen foran dig. Besvar så mange af de seks spørgsmål i
`docs/08-datamapning.md` §5 som filerne faktisk kan svare på. Skriv svarene i
din rapport — **ret ikke i dokumentet**, og gæt ikke. Står der intet om det i
listerne, så skriv "kan ikke afgøres af strukturen".

Særligt disse fire, hvor jeg har en formodning der skal be- eller afkræftes:

1. **Har de seks `<VÆRK> Standard Tasklist`-lister identiske kolonner?**
   Sammenlign kolonnesættene for `ASV`, `AVV`, `HEV`, `KYV`, `SKV` og `SSV`
   Standard Tasklist. Er de ens, så skriv det — så kan de seks lister slås
   sammen til én med en `Plant`-kolonne.
2. **Hvor ligger operationerne?** Find den liste, der har kolonner i retning
   af operationsnummer, kort tekst, timer, varighed og arbejdscenter. Hvilken
   kolonne binder en operation til et maintenance item?
3. **Hvordan hænger `MaintenancePlans` og `MaintenanceItems` sammen?** Hvilken
   kolonne er nøglen — et opslag, et tal, en tekst?
4. **Findes strategipakkerne nogen steder?** Led efter kolonner som
   `PackageNo`, `ShortCode`, `CycleLength`, `Hierarchy` — i
   `StandardStrategyList` eller andetsteds. Findes de ikke, så sig det
   ligeud: så skal de oprettes.

## Rapportér

- Antal lister og samlet antal kolonner.
- Om du kørte med eller uden `-NoData`.
- Dine svar på de fire spørgsmål ovenfor, med den liste og kolonne du støtter
  svaret på.
- Alt der så mærkeligt ud: kolonner med samme visningsnavn i samme liste,
  beregnede felter, opslag på tværs af lister, eller lister med 0 rækker.

## Det du ikke skal

- Du må **ikke ændre, oprette eller slette** noget i SharePoint. Scriptet
  læser kun — hold det sådan.
- Du må ikke ændre datamodellen eller oprette nye lister. Det kommer bagefter,
  når spørgsmålene er besvaret.
- Du må ikke rette i `docs/08-datamapning.md`.
- Du må ikke røre `Maintenance Plan App/` eller `Masterdata Hub/`.
