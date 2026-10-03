# SPOOL-arkets GUI-script (reference)

Trukket ud af `excel/artifact/FL indberetninger udgave SPOOL V3.xlsm` med
oletools, uændret. De er **ikke** en del af nogen projektmappe her. De er
kilden til FL-oprettelsen i SAP Opretter:

| Fil | Brugt til |
|---|---|
| `GUI_SCRIPT.bas` | Felt-ID'erne i `excel/opretter/VhpConfig.bas` (FL-afsnittet) og skridtene i `VhpFlSteps.bas` |
| `GUI_RunCreate.bas` | Reglerne for klasser og karakteristikker i `VhpFl.bas` |
| `GUI_Session.bas` | Hvordan SPOOL finder SAP-sessionen |
| `Initial_Entry_Create_FL.bas` | SPOOL's korte vej (kun mærke og klasse), som opretteren ikke bruger |

`tests/test_sap_contract.py` tjekker, at hvert FL-felt-ID i `VhpConfig.bas`
står ordret i `GUI_SCRIPT.bas`. Ret derfor ikke i filerne her. Kommer der en
ny udgave af SPOOL-arket, så træk filerne ud igen og kør testene. Se
`docs/36-fl-sap-oprettelse.md`.
