Attribute VB_Name = "modConfig"
Option Explicit
'==============================================================================
' modConfig - alt der skal tilpasses jeres system staar HER og kun her.
'
' Feltet-ID'er i SAP afhaenger af release, skaermvariant, brugerparametre og
' aktive faneblade. Ingen kan skrive dem korrekt udefra. Fremgangsmaade:
'
'   1. Aabn transaktionen manuelt i SAP.
'   2. Kald modSapInspect.DumpScreen paa hver skaerm undervejs.
'   3. Kopier ID'erne herned.
'   4. Koer paa EEN raekke foer du koerer en batch.
'
' Vaerdierne nedenfor er pladsholdere fra en typisk ECC-installation. Gaa ud
' fra at de er forkerte hos jer, indtil DumpScreen har bekraeftet dem.
'==============================================================================

'--- Arknavne og tabeller (ListObjects) ---------------------------------------
Public Const SH_PLAN        As String = "T_Plan"
Public Const SH_ITEM        As String = "T_Item"
Public Const SH_TASKLIST    As String = "T_TaskList"
Public Const SH_OPERATION   As String = "T_Operation"
Public Const SH_PACKAGE     As String = "T_Package"
Public Const SH_PACKAGEDEF  As String = "T_PackageDef"
Public Const SH_LOG         As String = "Log"
Public Const SH_INSPECT     As String = "Inspect"

'--- Koerselsopsaetning -------------------------------------------------------
' Saet til True foerste gang: alt logges, men intet gemmes i SAP.
Public Const DRY_RUN        As Boolean = True

' Sekunder der ventes paa at en skaerm er klar. GUI scripting er synkront,
' men enkelte transaktioner returnerer foer skaermen er tegnet faerdig.
Public Const SCREEN_WAIT    As Double = 0.2

' Datoformatet SKAL matche det format, SAP-brugeren er sat op med
' (System > Brugerprofil > Egne data > Standardvaerdier).
Public Const SAP_DATE_FMT   As String = "dd.mm.yyyy"

' HTTP-trigget Power Automate-flow, der skriver status tilbage paa
' SharePoint-listen.
' ADVARSEL: URL'en indeholder en signatur og ER adgangen. Alle med URL'en kan
' kalde flowet. Del ikke projektmappen bredt med denne vaerdi udfyldt, og lad
' flowet kun acceptere kendte RequestGuid-vaerdier og kun skrive de tre felter.
Public Const FLOW_URL       As String = ""

'==============================================================================
' TRANSAKTIONSKODER
'==============================================================================
Public Const TCODE_TASKLIST As String = "/nIA01"   ' udstyrsarbejdsplan
Public Const TCODE_PLAN     As String = "/nIP42"   ' strategiplan
Public Const TCODE_PLAN_SC  As String = "/nIP41"   ' single cycle-plan

'==============================================================================
' FELT-ID'er - IA01 (arbejdsplan)
'==============================================================================
Public Const IA01_EQUIPMENT  As String = "wnd[0]/usr/ctxtRC271-EQUNR"
Public Const IA01_PLANT      As String = "wnd[0]/usr/ctxtRC271-WERKS"
Public Const IA01_GROUP      As String = "wnd[0]/usr/ctxtRC271-PLNNR"
Public Const IA01_PROFILE    As String = "wnd[0]/usr/ctxtRC271-PROFIDNETZ"

' Hovedskaerm
Public Const IA01_DESCRIPTION As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/txtPLKOD-KTEXT"
Public Const IA01_USAGE       As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/ctxtPLKOD-VERWE"
Public Const IA01_STATUS      As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/ctxtPLKOD-STATU"
Public Const IA01_PLANNERGRP  As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/ctxtPLKOD-VAGRP"
Public Const IA01_WORKCENTER  As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/ctxtPLKOD-ARBPL"
Public Const IA01_STRATEGY    As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_KOPF:SAPLCPDI:1200/ctxtPLKOD-STRAT"

' Operationsoversigt (table control)
Public Const IA01_TC_OPER     As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_LIST:SAPLCPDO:0220/tblSAPLCPDOCONTROL_0220"
Public Const IA01_COL_OPNO    As String = "PLPOD-VORNR"
Public Const IA01_COL_WORKCTR As String = "PLPOD-ARBPL"
Public Const IA01_COL_CTRLKEY As String = "PLPOD-STEUS"
Public Const IA01_COL_TEXT    As String = "PLPOD-LTXA1"
Public Const IA01_COL_WORK    As String = "PLPOD-ARBEI"
Public Const IA01_COL_NUMPER  As String = "PLPOD-ANZZL"
Public Const IA01_COL_DURAT   As String = "PLPOD-DAUNO"

' Vedligeholdelsespakker (table control). Kolonnerne er EN pr. pakke.
Public Const IA01_TC_PKG      As String = "wnd[0]/usr/subSUB_ALL:SAPLCPDI:3010/ssubSUB_LIST:SAPLCPDO:0400/tblSAPLCPDOCONTROL_0400"
' Indeks paa den FOERSTE pakkekolonne i table controlet (0-baseret).
' Bruges kun, hvis kolonnenavnene ikke kan matches - se modSapTaskList.
Public Const IA01_PKG_COL0    As Long = 2
' Menuvej til pakkeskaermen. Alternativt en knap-ID.
Public Const IA01_MENU_PKG    As String = "wnd[0]/mbar/menu[3]/menu[4]"

'==============================================================================
' FELT-ID'er - IP42 (strategiplan)
'==============================================================================
Public Const IP42_PLANCAT     As String = "wnd[0]/usr/ctxtRMIPM-MPTYP"
Public Const IP42_STRATEGY    As String = "wnd[0]/usr/ctxtRMIPM-STRAT"

Public Const IP42_DESCRIPTION As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1200/txtRMIPM-WPTXT"
Public Const IP42_SORTFIELD   As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1200/ctxtRMIPM-WPGRP"
Public Const IP42_CYCLESTART  As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1200/ctxtRMIPM-STADT"

' Positionsdata
Public Const IP42_ITEM_TEXT   As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/txtRMIPM-PSTXT"
Public Const IP42_ITEM_EQUNR  As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-EQUNR"
Public Const IP42_ITEM_TPLNR  As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-TPLNR"
Public Const IP42_ITEM_PLNGRP As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-INGRP"
Public Const IP42_ITEM_ORDTYP As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-AUART"
Public Const IP42_ITEM_WORKCT As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-GEWRK"
Public Const IP42_ITEM_PLANT  As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-IWERK"

' Arbejdsplantilknytning
Public Const IP42_TL_TYPE     As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-PLNTY"
Public Const IP42_TL_GROUP    As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-PLNNR"
Public Const IP42_TL_COUNTER  As String = "wnd[0]/usr/subSUB_ALL:SAPLIWP3:1300/ctxtRMIPM-PLNAL"

'==============================================================================
' FAELLES ID'er - de eneste der er stabile paa tvaers af releases
'==============================================================================
Public Const ID_OKCODE        As String = "wnd[0]/tbar[0]/okcd"
Public Const ID_STATUSBAR     As String = "wnd[0]/sbar"
Public Const ID_BTN_SAVE      As String = "wnd[0]/tbar[0]/btn[11]"
Public Const ID_BTN_ENTER     As String = "wnd[0]/tbar[0]/btn[0]"
Public Const ID_BTN_BACK      As String = "wnd[0]/tbar[0]/btn[3]"
