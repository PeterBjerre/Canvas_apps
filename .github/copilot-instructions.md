# Canvas_apps

## VH-plan canvas appen — læs dette før du retter noget

`Maintenance Plan App/ScreenVhPlan.pa.yaml` og `App.pa.yaml` er **genereret**
af Python-builderne i `Maintenance Plan App/build/`. Retter du direkte i
YAML-filerne, er ændringen væk ved næste build.

Ret i `build/*.py`, kør derefter:

```bash
cd "Maintenance Plan App/build"
python3 generate_app_onstart.py
python3 assemble_screen.py
python3 check_layout.py          # skal være grøn før sync til Studio
```

Hele arbejdsgangen, ejerskabet pr. builder og de invarianter der ikke må
regressere, står i `.github/skills/vhplan-canvas-build/SKILL.md`. Følg den
ved enhver ændring af appen.
