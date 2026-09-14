# Canvas_apps

## Læs dette før du retter noget

Repoet indeholder to Power Apps canvas apps:

| App | Mappe | Skærm |
|---|---|---|
| VH-plan (indmelding af vedligeholdsplaner til SAP PM) | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` |
| Masterdata Hub (landingsside for alle fem domæner) | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` |

**Alle `.pa.yaml`-filer er genereret** af Python-builderne i den enkelte apps
`build/`-mappe. Retter du direkte i YAML-filerne, er ændringen væk ved næste
build.

Ret i `build/*.py` og kør:

```bash
python3 tools/build_all.py
```

Den bygger begge apps og kører begge layout-tjek. Alt skal være grønt, før
der synkroniseres til Power Apps Studio.

Hver build-mappe er selvbærende. Filerne `gen_screen.py`, `build_helpers.py`
og `check_layout.py` er kopieret ordret ind i begge — retter du i en af dem,
skal kopien opdateres i den anden app. `tools/build_all.py` stopper og siger
til, hvis de er gledet fra hinanden.

Hele arbejdsgangen, ejerskabet pr. builder, ydelseskravene til landingssiden
og de invarianter der ikke må regressere, står i
`.github/skills/canvas-build/SKILL.md`. Følg den ved enhver ændring.
