# Release til PROD — fra din PC

Solution BIO SAP flyttes fra DEV til PROD som **managed** med
`tools/release_solution.ps1`. Scriptet kører på din PC med dit eget login,
så solutionen behøver ingen kobling til GitHub og ingen service principal.
Der er ikke noget TEST-miljø: du tester i DEV, og det, der er testet, er
det, der eksporteres.

```powershell
# Første gang: lav settings-filen og udfyld den med PROD-værdier
.\tools\release_solution.ps1 -NewSettings -SettingsFile "$HOME\BioSap\settings.prod.json"

# Hver release: tør-kørsel, så den rigtige
.\tools\release_solution.ps1 -SettingsFile "$HOME\BioSap\settings.prod.json" -Version 1.2.0.0 -WhatIfOnly
.\tools\release_solution.ps1 -SettingsFile "$HOME\BioSap\settings.prod.json" -Version 1.2.0.0
```

## Hvad scriptet gør

| Trin | pac-kommando | Stopper, hvis |
|---|---|---|
| Sætter versionen i DEV (kun med `-Version`) | `solution online-version` | versionen ikke er et tal som 1.2.0.0 |
| Publicerer alt i DEV | `solution publish` | |
| Eksporterer managed til `releases\<version>\` | `solution export --managed` | |
| Tjekker settings-filen mod en ny skabelon fra zip'en | `solution create-settings` | en værdi er tom, eller solutionen har fået en variabel eller forbindelse, filen ikke kender |
| Læser versionen i PROD | `solution list --json` | DEV's version ikke er højere end PROD's |
| Spørger | | du skriver andet end `PROD` |
| Importerer i PROD | `solution import --settings-file … --activate-plugins --publish-changes` (+ `--stage-and-upgrade`, når solutionen findes i PROD) | importen fejler |

`-WhatIfOnly` gør alt undtagen importen. `-Check` kører desuden solution
checker på zip'en. `-SkipAuth` springer `pac auth create` over, når du
allerede er logget ind.

Miljø-id'erne læses fra `tools/canvas_apps.json` (`environments.dev` og
`environments.prod`). PROD's `environment_id` skal udfyldes dér, før den
første release; ellers kan det gives med `-TargetEnvironment`.

## Settings-filen

Filen bærer miljøvariablernes værdier (site-URL, e-mailadresser, Power BI
workspace og resten) og forbindelsesreferencernes forbindelser i PROD.
Den indeholder e-mails og URL'er og må **aldrig** i repoet. Scriptet nægter
at bruge en fil i repoet, som git ikke ignorerer. Læg den fx i
`$HOME\BioSap\`.

- `Value` udfyldes for hver miljøvariabel. `orsted_BioSapWOCClientSecret`
  hører hjemme i Azure Key Vault, ikke som tekst i filen.
- `ConnectionId` er id'et på en forbindelse i PROD. Opret forbindelserne én
  gang i PROD med servicekontoen (Power Automate → Forbindelser), og kopiér
  id'et fra forbindelsens URL.

## Før første release

1. Bind appens SharePoint-datakilder om til miljøvariabler i DEV (se
   planen "Plan: Deployment pipeline til PROD"). Ellers peger appen i PROD
   stadig på DEV-sitet.
2. Ryd solutionen op, så udfasede apps og flows ikke følger med.
3. Kør provisioning-scripts mod PROD-sitet, først med `-WhatIfOnly`.
4. Opret forbindelserne i PROD og lav settings-filen.

## Hver release

1. Har releasen nye kolonner eller lister: kør de relevante
   `Provision-*.ps1` mod PROD-sitet, først med `-WhatIfOnly`.
2. Kør scriptet med `-WhatIfOnly`, så uden.
3. Åbn appen i PROD, tjek at flows er slået til, og at appen er delt med
   brugerne.

## Rul tilbage

`releases\<version>\` gemmer zip'en og `RELEASE.md` (dato, versioner,
git-commit). Mappen er i `.gitignore`, fordi zip'en bærer DEV's
værdier for miljøvariablerne — gem den selv. For at rulle tilbage
importeres den forrige zip i PROD med samme settings-fil. Skemaer og data i
SharePoint rulles ikke tilbage.

## Godt at vide

- En managed solution kan ikke rettes i PROD. Rettelser laves i DEV og
  udrulles som en ny version.
- Med `--stage-and-upgrade` slettes komponenter, der er fjernet fra
  solutionen i DEV, også i PROD.
- `-Version` sættes i DEV, før du bekræfter. Afbryder du, står den nye
  version stadig i DEV; det skader ikke.
