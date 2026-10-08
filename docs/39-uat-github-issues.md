# UAT: fra Issue Board til GitHub-issue

Under UAT melder testerne fejl og ønsker i **Issue Board** i BIO SAP-appen. En admin vurderer hver sag. Når en ændring skal laves, sætter admin sagen til status **Triaged**, og scriptet `sharepoint/github/Send-IssueBoardToGitHub.ps1` opretter et GitHub-issue for den. Issue-rutinen tager issuet op ved næste kørsel og laver en PR mod `main`.

## Livsforløbet

| Status i Issue Board | Hvem | Hvad sker der |
| --- | --- | --- |
| New | Testeren | Sagen er meldt ind via **New issue** |
| Triaged | Admin | Ændringen er godkendt og skal laves |
| (GitHub-issue) | Admin kører scriptet | Ét issue pr. sag, titel `[ISS-000123] <titel>`, label `uat` |
| In progress | Admin | Sat i Issue Board, gerne med GitHub-linket som kommentar |
| Ready for retest | Admin | Rettelsen er merget og deployet; testeren får en mail |
| Closed / Reopened | Testeren eller admin | Testeren genåbner med **Reopen**, hvis det ikke virker |

Et fund, der ikke skal laves, lukkes af admin med en forklaring i **Resolution**. Det bliver aldrig til et GitHub-issue.

## Kør scriptet

Kræver PnP.PowerShell (samme login som provisioneringen) og et GitHub-token med **Issues: Read and write** på repoet (fine-grained personal access token). Tokenet gemmes aldrig i repoet.

```powershell
cd sharepoint\github
# Tørløb: vis hvad der ville blive oprettet
.\Send-IssueBoardToGitHub.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV" -WhatIfOnly

# Opret (spørger for hver sag; -Yes spørger ikke)
$env:GITHUB_TOKEN = '<dit token>'
.\Send-IssueBoardToGitHub.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"
```

Parametre: `-Status` (standard `Triaged`), `-TicketNo ISS-000123,ISS-000130` (kun de sager), `-Label` (standard `uat`), `-Repo` (standard `PeterBjerre/Canvas_apps`).

## Det, scriptet sender og ikke sender

Repoet er **offentligt**. Scriptet sender sagsnummer, titel, Application, Section, alvor, prioritet, relateret anmodning, What happened, Steps to reproduce, Expected result, Actual result og navnene på vedhæftningerne. Det sender aldrig rapportørens navn eller e-mail, kommentarerne eller selve filerne. Hver sag vises, før den sendes, og scriptet advarer, hvis teksten indeholder en e-mailadresse.

Scriptet kan køres igen og igen: en sag, der allerede har et issue med label `uat`, springes over. Scriptet ændrer intet i SharePoint, så status og kommentarer i Issue Board går stadig gennem flowet og kommer med i sagens Activity.
