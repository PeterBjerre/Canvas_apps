# Arkiv

Indhold, der ikke længere bruges af apperne eller byggeriet, men som er
bevaret som historik. Intet her køres, bygges eller læses af `tools/`.
Git husker det også — mappen findes, så det er tydeligt, hvad der er
**ikke-levende**, uden at man skal grave i historikken.

| Sti | Hvad | Hvorfor arkiveret |
|---|---|---|
| `sharepoint/provision/Provision-VHPlanLists.ps1` | Første oplægs lister (`VHP_*`, `MD_ValueHelp`, `MD_Strategy*`) | Ingen app bruger `VHP_*`-modellen. Scriptet oprettede desuden `MD_Strategy`/`MD_StrategyPackage` med **andre kolonner** end `Provision-StrategyLists.ps1`, som apperne kører mod (REVIEW.md E7). Brug `Provision-StrategyLists.ps1`. |
| `sharepoint/seed/MD_ValueHelp.csv` | Seed til `MD_ValueHelp` | Listen bruges ikke. |
| `prompts/*.md` | Prompts fra VS Code-æraen | Deploy sker nu med `tools/canvas_mcp.py` (docs/21). Stierne i dem passer ikke længere. |
| `MaintenancePlan-steps.html` | Skitse af VH-planens trin | Pegede på en `steps.svg`, der ikke findes; trinene bygges af `build_hero.py`. |

Dokumenterne i `docs/` er ikke flyttet (links peger på dem), men de
historiske er markeret øverst med **Status: historisk**.
