# 33 — Udfasning af de fem enkeltapps

**Beslutning (2026-09-30):** BIO SAP App er den app, der skal bruges. At
skifte mellem fem apps var for klodset. De fem enkeltapps — Masterdata Hub,
VH-plan, Equipments, Materials og Functional Location — udfases, når den
samlede app har bestået testplanen i
[`BIO SAP App/README.md`](../BIO%20SAP%20App/README.md#testplan).

Repoet er gjort klar: udfasningen er **ét flag** og nogle få git-kommandoer.
Byggerne bliver stående. BIO SAP bygges af de fem appers egne byggere.

## 1. Forudsætninger

- [ ] Testplanen i `BIO SAP App/README.md` er kørt i DEV og bestået,
      inklusive Functional Location (trin 7).
- [ ] Målingerne (trin 8) er noteret: tid til hubben og første besøg på
      hvert domæne.
- [ ] BIO SAP App er delt med alle, der bruger de fem apps i dag.
- [ ] Mailflowet `BioSap-EmailNotification-NewPlanCreated` er rettet.
      Det læser `AppUrl` fra `AppSettings`, ikke fra indekset (se
      BIO SAP-README'en, "Dyblinks").
- [ ] Kladder, der er åbne i en enkeltapp, er gemt. Indeksets `AppUrl`
      peger allerede på den samlede app, så de kan åbnes dér.

## 2. I repoet

```bash
# 1. Slå udfasningen til
#    tools/canvas_apps.json:   "single_apps": "retired"

# 2. Enkeltappernes .pa.yaml er nu mellemprodukter - ud af git
git rm --cached \
  "Masterdata Hub/App.pa.yaml"          "Masterdata Hub/ScreenMdHub.pa.yaml" \
  "Maintenance Plan App/App.pa.yaml"    "Maintenance Plan App/ScreenVhPlan.pa.yaml" \
  "Equipment App/App.pa.yaml"           "Equipment App/ScreenEquipment.pa.yaml" \
  "Material App/App.pa.yaml"            "Material App/ScreenMaterial.pa.yaml" \
  "Functional Location App/App.pa.yaml" "Functional Location App/ScreenFunctionalLocation.pa.yaml"

# 3. ...og ind i .gitignore
cat >> .gitignore <<'EOF'
# Udfasede enkeltapps (docs/33): mellemprodukter for BIO SAP App
/Masterdata Hub/*.pa.yaml
/Maintenance Plan App/*.pa.yaml
/Equipment App/*.pa.yaml
/Material App/*.pa.yaml
/Functional Location App/*.pa.yaml
EOF

# 4. Byg og test
python3 tools/build_all.py
python3 -m pytest -q tests
```

Det gør flaget (`tools/env_config.py`, `RETIRED`):

| Hvor | `active` (nu) | `retired` |
|---|---|---|
| `build_all.py` / `build.py` | Alle seks apps | Kun BIO SAP. Den kører selv de fem generatorer |
| `build_all.py --app equipment` | Bygger Equipment | Afvises med en besked |
| `canvas_mcp.py deploy --app vhplan` | Deployer VH-plan | Afvises. Kun `--app biosap` |
| FL-regeltjek og docs/31-tjek | FL-appen og BIO SAP | BIO SAP's FL-skærm |
| `tests/` | BIO SAP's skærme | Uændret |
| `MD_RequestIndex.AppUrl` | Den samlede app | Uændret |

**Efterprøvet 2026-09-30.** Med `CANVAS_SINGLE_APPS=retired` og de ti
filer slettet: byggeriet er grønt, BIO SAP's skærme er byte-identiske, og
alle tests består. Enkeltappernes `App.pa.yaml` bliver genskabt identisk af
BIO SAP's `generate_app.py`. Deploy og byg af en enkeltapp bliver afvist.

Du kan prøve den udfasede tilstand uden at ændre noget:

```bash
CANVAS_SINGLE_APPS=retired python3 tools/build_all.py
```

`_EditorState.pa.yaml` i Masterdata Hub og VH-plan er Studio-filer. De kan
slettes med resten.

## 3. I Power Platform

- [ ] Fjern de fem apps fra brugernes Teams-faner, SharePoint-links og
      bogmærker. Læg BIO SAP i stedet.
- [ ] **Overvej en overgangsperiode:** lad hver enkeltapp starte BIO SAP
      på sin skærm (`Launch(<BIO SAP>?domain=<domæne>)` i `OnStart`), så
      gamle links virker. Det er ikke bygget. Sig til, hvis det skal.
- [ ] Når ingen bruger dem længere: fjern apperne fra solution *BIO SAP* og
      slet dem. **Kan ikke fortrydes** — eksportér solution'en først.
- [ ] `AppSettings`-rækkerne, der peger på den gamle VH-app, opdateres
      eller slettes, når mailflowet er rettet.

## 4. Tilbage

Sæt `"single_apps": "active"`, fjern linjerne i `.gitignore`, og byg igen.
Så bygges og kan deployes de fem apps som før. Apperne i Power Platform
står, til de slettes.
