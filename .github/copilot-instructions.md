# Canvas_apps

## Læs dette før du retter noget

Repoet indeholder fire Power Apps canvas apps:

| App | Mappe | Skærm |
|---|---|---|
| VH-plan (vedligeholdsplaner til SAP PM) | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` |
| Masterdata Hub (landingsside for alle fem domæner) | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` |
| Equipments (udstyr) | `Equipment App/` | `ScreenEquipment.pa.yaml` |
| Materials (reservedele) | `Material App/` | `ScreenMaterial.pa.yaml` |

**Equipments og Materials er den samme app** med hver sin
`build/domain_config.py`. Resten af deres builderfiler er ordret ens.

**Alle `.pa.yaml`-filer er genereret** af Python-builderne i den enkelte apps
`build/`-mappe. Retter du direkte i YAML-filerne, er ændringen væk ved næste
build.

Ret i `build/*.py` og kør:

```bash
python3 tools/build_all.py
```

Den bygger alle fire apps og kører alle fire layout-tjek. Alt skal være grønt, før
der synkroniseres til Power Apps Studio.

Hver build-mappe er selvbærende. `gen_screen.py`, `build_helpers.py` og
`check_layout.py` er kopieret ordret ind i **alle fire** — retter du i en af
dem, skal kopien opdateres i de tre andre. `tools/build_all.py` stopper og
siger til, hvis de er gledet fra hinanden.

**Farver og breakpoints må ikke skrives i en builder.** De står i
`tools/design_tokens.py` og `tools/layout_tokens.py`, og byggeriet stopper,
hvis nogen skriver et `RGBA(`, et `#rrggbb` eller en sammenligning mod
`App.Width`.

Hele arbejdsgangen, ejerskabet pr. builder, ydelseskravene til landingssiden
og de invarianter der ikke må regressere, står i
`.github/skills/canvas-build/SKILL.md`. Følg den ved enhver ændring.
