# Excel

| Sti | Hvad |
|---|---|
| [`opretter/`](opretter) | **SAP Opretter**: opretter VH-planer og FL-anmodninger i SAP. Se [`opretter/README.md`](opretter/README.md), [`../docs/34-sap-oprettelse.md`](../docs/34-sap-oprettelse.md) og [`../docs/36-fl-sap-oprettelse.md`](../docs/36-fl-sap-oprettelse.md) |
| `artifact/FL indberetninger udgave SPOOL V3.xlsm` | SPOOL-arket. `tests/test_sap_contract.py` tjekker opretterens FL-felt-ID'er mod det |
| `vba/spool-gui/GUI_SCRIPT.bas` | SPOOL-arkets GUI-script, som opretterens FL-felt-ID'er (`VhpConfig.bas`) er taget fra og tjekkes mod |
| `vba/vhplan-lister/mod*.bas` | Hentningen af en SAP-ordre fra `BIO SAP VH-plan lister.xlsm` (OData `WorkOrderHeaderSet` med relationer, materialbevægelser, IW33). Forbilledet for flowet `BioSap-Integration-WoeOrder` ([`../docs/45-woe-ordre-flow.md`](../docs/45-woe-ordre-flow.md)); køres ikke og tjekkes ikke af `tools/check_vba.py` |
| `vba/spool-validation/` | SPOOL-arkets validering. `tools/extract_spool_rules.py` laver seedet til `MD_FLClass` og `MD_FLCharacteristic` af den |

Oplæggets første skabelon (`VHPlan-SAP-skabelon.xlsx`, `vba/*.bas`,
`powerquery/`) blev aldrig taget i brug og er fjernet; den findes i
git-historikken.
