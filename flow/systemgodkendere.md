# Systemgodkendere

Tabellen over systemgodkendere (systemnummer 1-16 -> 1. og 2. godkender)
staar ikke laengere her. Repoet er offentligt, og initialer + e-maildomaenet
er en medarbejders adresse (R2-025).

Kilden er SharePoint-listen `MD_Approver` (noegle = systemnummer, vaerkskode
eller `COST`). Kun sitets Owners og Master Data kan rette den
(`sharepoint/provision/Provision-AdminLists.ps1`, R2-024). Se
`docs/32-godkendelsesflow.md`, afsnit 6.

Til et nyt miljoe: laeg en CSV med de rigtige godkendere uden for git og
giv den til `Provision-VHPlanApproval.ps1 -SeedPath <fil>`.
