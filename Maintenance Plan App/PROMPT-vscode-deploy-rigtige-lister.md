# Prompt til VS Code (Sonnet 5) — synk VH-plan appen

Kopiér alt under linjen ind som din første besked i VS Code.

**Denne prompt er bevidst kort.** Al verifikation sker uden for VS Code — du
skal kun bygge, oversætte og synkronisere. Lav ikke test, åbn ikke appen i
browseren, og udforsk ikke SharePoint.

---

Du skal synkronisere VH-plan appen til Power Apps Studio. Intet andet.

## Kilde

Repo `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`. **Pull først.**

| | |
|---|---|
| `environment_id` | `e0f8f822-d16a-e878-ba4e-fb42bc617e47` |
| `app_id` | `11fa8d90-868a-45a4-ba23-28f2cf0671a2` |

## Trin 1 — byg

```bash
python3 tools/build_all.py
```

Den skal være grøn. Linjen om at `MaintenancePlans.StrategyKey` "oprettes af
provisioneringen" er forventet og ikke en fejl.

Fejler den, så **rapportér udskriften ordret og stop**. Ret ikke i noget.

## Trin 2 — compile og synk

`directoryPath` er den lokale sti til mappen `Maintenance Plan App` (ikke
`build/`).

```
canvas-authoring-connect          environment_id = <ovenfor>, app_id = <ovenfor>
canvas-authoring-compile_canvas   directoryPath = <sti>
canvas-authoring-sync_canvas      directoryPath = <sti>
canvas-authoring-get_appchecker_errors
```

Nægter værktøjet at synke, fordi mappen indeholder andet end `.pa.yaml`
(`.md`-filer og `build/`), så brug samme løsning som sidst: kopiér de tre
`.pa.yaml` til en midlertidig undermappe, compile+sync derfra, og slet
undermappen bagefter. Rør ikke kildefilerne.

**Compile før sync.** Fejler compile, så stop og rapportér fejlen ordret.

## Rapportér

- Om `build_all.py` var grøn.
- Ordret hvad compile sagde.
- Ordret hvad app checker sagde.
- Intet andet.

## Det du ikke skal

- Ingen manuelle tests. Ingen browser. Ingen klik i appen.
- Du må ikke rette i `.pa.yaml` eller i `build/*.py`.
- Du må ikke røre SharePoint-lister eller køre PowerShell.
- Commit og push kun hvis du har ændret noget — hvilket du ikke skal have.
