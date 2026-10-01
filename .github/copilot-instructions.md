# Canvas_apps

## Læs dette før du retter noget

Repoet indeholder fem Power Apps canvas apps og én samlet test-app:

| App | Mappe | Skærm |
|---|---|---|
| Masterdata Hub (landingsside for alle domæner) | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` |
| VH-plan (vedligeholdsplaner til SAP PM) | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` |
| Equipments (udstyr) | `Equipment App/` | `ScreenEquipment.pa.yaml` |
| Materials (reservedele) | `Material App/` | `ScreenMaterial.pa.yaml` |
| Functional Location (SPOOL) | `Functional Location App/` | `ScreenFunctionalLocation.pa.yaml` |
| KKS-opslag (kun som skærm i BIO SAP) | `KKS App/` | `ScreenKks.pa.yaml` |
| BIO SAP (de seks som skærme i én app) | `BIO SAP App/` | alle seks |

**Alle `.pa.yaml`-filer er genereret** af Python-builderne i den enkelte
apps `build/`-mappe og af de fælles moduler i `tools/`. Retter du direkte i
YAML-filerne, er ændringen væk ved næste build.

Ret i `build/*.py` eller `tools/*.py` og kør:

```bash
pip install -r requirements.txt   # første gang
python3 tools/build_all.py        # alle apps + alle tjek
python3 tools/build_all.py --app equipment
```

Alt skal være grønt, før der synkroniseres til Power Apps Studio.

**De fælles moduler ligger i `tools/` i én udgave** – `gen_screen.py`,
`build_helpers.py`, `side_nav.py`, `domain_parts.py` (Equipment + Material),
`fl_picker.py`, `attflows.py`, `check_layout.py` m.fl. Der er ingen kopier i
app-mapperne; `*/build/check_layout.py` er kun en indgang.

**Equipments og Materials er to apps**, der deler byggeklodserne i
`tools/domain_parts.py`. Er en ændring kun rigtig for den ene, hører den i
appens egen `build/`-mappe.

**Farver og breakpoints må ikke skrives i en builder.** De står i
`tools/design_tokens.py` og `tools/layout_tokens.py`, og byggeriet stopper,
hvis nogen skriver et `RGBA(`, et `#rrggbb` eller en sammenligning mod
`App.Width` – også i `tools/`.

**Miljø- og app-id'er står ét sted:** `tools/canvas_apps.json`, læst af
`tools/env_config.py`. Skriv aldrig en play-URL eller et id i en builder.

**Hemmeligheder:** `tools/check_secrets.py` scanner hele repoet (også
Office-filer) ved fuld bygning. En trigger-URL med `sig=`, en client secret
eller en API-nøgle hører aldrig i git.

Hele arbejdsgangen, ejerskabet pr. builder, ydelseskravene til
landingssiden og de invarianter, der ikke må regressere, står i
`.github/skills/canvas-build/SKILL.md`. Følg den ved enhver ændring.
Status på kendte fund og den prioriterede plan står i `REVIEW.md`.
