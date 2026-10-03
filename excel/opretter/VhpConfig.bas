Attribute VB_Name = "VhpConfig"
Option Explicit
'==============================================================================
' VhpConfig - alt, der beskriver SAP-skaermene og projektmappen, staar HER.
'
' Felt-ID'erne er IKKE pladsholdere. De er flyttet ordret fra de scripts, der
' har oprettet i jeres SAP:
'   VH-planer   det gamle regneark, excel/src/Modules/GUI_Script.bas
'               (CreateTLH, AddOperations, CreateItems, CreatePlans)
'   FL          SPOOL-arket, excel/vba/spool-gui/GUI_SCRIPT.bas
'               (FillMasterdataFields, GoToClassAssignment, FillCharacteristicsBatch,
'               SaveFLAndGetStatus)
' Aendrer SAP et skaermbillede, er det her, der rettes - ikke i VhpSteps eller
' VhpFlSteps.
'
' Ord i kommentarer og tekster skrives uden ae/oe/aa-bogstaver: VBA-editoren
' laeser .bas-filer i Windows' tegnsaet, og et UTF-8-bogstav bliver til to
' tegn. Det, brugeren SER, laves med VhpUtil.Dk("{ae}{oe}{aa}").
'==============================================================================

Public Const VHP_VERSION As String = "1.1"
Public Const VHP_APP_NAME As String = "SAP Opretter"

'--- Filer og mapper ----------------------------------------------------------
' Biblioteket i SharePoint hedder SAP-oprettelse og synkroniseres med OneDrive.
' Undermapperne oprettes af opretteren, hvis de mangler.
Public Const FOLDER_LIBRARY As String = "SAP-oprettelse"
Public Const FOLDER_ORDERS As String = "Til oprettelse"
Public Const FOLDER_RECEIPTS As String = "Kvitteringer"
Public Const FOLDER_DONE As String = "Oprettet"

Public Const ORDER_KIND As String = "vhplan-sap-order"
Public Const RECEIPT_KIND As String = "vhplan-sap-receipt"
Public Const FL_ORDER_KIND As String = "fl-sap-order"
Public Const FL_RECEIPT_KIND As String = "fl-sap-receipt"
' FL-kvitteringerne har deres egen mappe (Kvitteringer\FL) og deres eget flow,
' saa VH-planernes kvitteringsflow ikke ser dem.
Public Const FOLDER_FL_RECEIPTS As String = "FL"
Public Const SUFFIX_STATUS As String = ".status.json"
Public Const SUFFIX_RECEIPT As String = ".kvittering.json"

' En koersel, der ikke har skrevet i statusfilen i saa mange minutter, regnes
' for doed (Excel lukket, pc'en gik i dvale). Saa maa en anden tage over.
Public Const LOCK_STALE_MINUTES As Long = 120

' Mappen huskes pr. bruger i registreringsdatabasen (GetSetting), fordi
' OneDrive-stien indeholder brugernavnet og er forskellig paa hver pc. Navnet
' er det fra version 1.0, saa den valgte mappe huskes efter opdateringen.
Public Const REG_APP As String = "VH-plan Opretter"
Public Const REG_SECTION As String = "Indstillinger"
Public Const REG_FOLDER As String = "Mappe"

'--- Ark og tabeller ----------------------------------------------------------
Public Const SH_START As String = "Start"
Public Const SH_PREVIEW As String = "Detaljer"
' Arket hed "Vis plan" i version 1.0. Setup omdoeber det.
Public Const SH_PREVIEW_OLD As String = "Vis plan"
Public Const SH_LOOKUP As String = "Opslag"
Public Const SH_SETTINGS As String = "Indstillinger"
Public Const SH_LOG As String = "Log"

Public Const LO_ORDERS As String = "tblOrdrer"
Public Const LO_PLANTS As String = "tblVaerker"
Public Const LO_HORIZON As String = "tblKaldshorisont"
Public Const LO_SERVICES As String = "tblYdelser"
Public Const LO_FL_CHARS As String = "tblKarakteristikker"
Public Const LO_SETTINGS As String = "tblIndstillinger"
Public Const LO_LOG As String = "tblLog"

'--- Indstillinger: noeglerne i tabellen tblIndstillinger ----------------------
' Kolonne 1 er noeglen (ASCII, laeses af koden), kolonne 3 er vaerdien.
Public Const SET_SAP_SYSTEM As String = "SapSystem"
Public Const SET_SAP_CLIENT As String = "SapClient"
Public Const SET_PROD_SYSTEMS As String = "ProdSystems"
Public Const SET_LOGON_TEST As String = "LogonTest"
Public Const SET_LOGON_PROD As String = "LogonProd"
Public Const SET_NEW_SESSION As String = "NewSession"
Public Const SET_CONFIRM_SAVE As String = "ConfirmSave"
Public Const SET_ITF_PATH As String = "ItfPath"
Public Const SET_KEY_DATE As String = "KeyDate"
Public Const SET_HORIZON_QUALIFIER As String = "HorizonQualifier"
Public Const SET_TASKLIST_TYPE As String = "TaskListType"
Public Const SET_PM02_MATGROUP As String = "Pm02MatGroup"
Public Const SET_DECIMAL_SEP As String = "DecimalSep"
Public Const SET_PLAN_CATEGORY As String = "PlanCategory"

'--- Fejlnumre ----------------------------------------------------------------
' SAP svarede med en fejl. Intet blev gemt i det trin.
Public Const ERR_SAP As Long = vbObjectError + 1001
' SAP svarede uklart efter et gem. En person skal se efter i SAP.
Public Const ERR_NEEDS_CHECK As Long = vbObjectError + 1002
' Brugeren sagde Nej til et gem: denne plan springes over.
Public Const ERR_SKIP_PLAN As Long = vbObjectError + 1003
' Brugeren sagde Annuller: hele koerslen stopper.
Public Const ERR_STOP_RUN As Long = vbObjectError + 1004
' Ordren kan ikke oprettes, som den er (validering, laas, miljoe).
Public Const ERR_ORDER As Long = vbObjectError + 1005

'==============================================================================
' SAP - transaktioner
'==============================================================================
Public Const TX_TASKLIST As String = "/nIA05"   ' opret generel arbejdsplan
Public Const TX_ITEM As String = "/nIP04"       ' opret vedligeholdsposition
Public Const TX_ITEM_CHANGE As String = "/nIP05" ' aendr position (langtekst)
Public Const TX_PLAN As String = "/nIP01"       ' opret vedligeholdsplan

'==============================================================================
' SAP - faelles
'==============================================================================
Public Const ID_OKCODE As String = "wnd[0]/tbar[0]/okcd"
Public Const ID_STATUSBAR As String = "wnd[0]/sbar"
Public Const ID_BTN_SAVE As String = "wnd[0]/tbar[0]/btn[11]"
Public Const ID_BTN_BACK As String = "wnd[0]/tbar[0]/btn[3]"
Public Const ID_BTN_EXECUTE As String = "wnd[0]/tbar[1]/btn[8]"

'==============================================================================
' IA05 - arbejdsplan (fra CreateTLH og AddOperations)
'==============================================================================
Public Const IA05_INIT_GROUP As String = "wnd[0]/usr/ctxtRC271-PLNNR"
Public Const IA05_INIT_PROFILE As String = "wnd[0]/usr/ctxtRC271-PROFIDNETZ"
Public Const IA05_INIT_KEYDATE As String = "wnd[0]/usr/ctxtRC271-STTAG"

Public Const IA05_HDR_GROUP As String = "wnd[0]/usr/ctxtPLKOD-PLNNR"
Public Const IA05_HDR_COUNTER As String = "wnd[0]/usr/txtPLKOD-PLNAL"
Public Const IA05_HDR_TEXT As String = "wnd[0]/usr/txtPLKOD-KTEXT"
Public Const IA05_HDR_PLANT As String = "wnd[0]/usr/ctxtPLKOD-WERKS"
Public Const IA05_HDR_WORKCENTER As String = "wnd[0]/usr/ctxtRCR01-ARBPL"
Public Const IA05_BTN_OPERATIONS As String = "wnd[0]/tbar[1]/btn[16]"

' Operationsoversigten. Cellerne er "<prefix><synlig raekke>]".
Public Const IA05_OP_TABLE As String = "wnd[0]/usr/tblSAPLCPDITCTRL_3400"
Public Const IA05_COL_WORKCENTER As String = "ctxtPLPOD-ARBPL[2,"
Public Const IA05_COL_CONTROLKEY As String = "ctxtPLPOD-STEUS[4,"
Public Const IA05_COL_SHORTTEXT As String = "txtPLPOD-LTXA1[5,"
Public Const IA05_COL_LONGTEXT As String = "chkRC270-TXTKZ[6,"
Public Const IA05_COL_WORK As String = "txtPLPOD-ARBEI[8,"
Public Const IA05_COL_PERSONS As String = "txtPLPOD-ANZZL[10,"
Public Const IA05_COL_ORDERQTY As String = "txtPLPOD-BMVRG[30,"
Public Const IA05_COL_ORDERUNIT As String = "ctxtPLPOD-BMEIH[31,"
Public Const IA05_COL_PRICE As String = "txtPLPOD-PREIS[32,"
Public Const IA05_COL_PRICEUNIT As String = "txtPLPOD-PEINH[34,"
Public Const IA05_COL_MATGROUP As String = "ctxtPLPOD-MATKL[37,"
Public Const IA05_COL_VENDOR As String = "ctxtPLPOD-LIFNR[39,"

' PM03: ydelser fra modelydelsesspecifikationen
Public Const IA05_BTN_SERVICES As String = "wnd[0]/tbar[1]/btn[13]"
Public Const IA05_SRV_MODELSPEC As String = "wnd[1]/usr/ctxtRM11P-MUSTER_LV"
Public Const IA05_SRV_MODELSPEC_OK As String = "wnd[1]/tbar[0]/btn[0]"
Public Const IA05_SRV_TABLE As String = "wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW"
Public Const IA05_SRV_COL_SERVICE As String = "ctxtESLL-SRVPOS[2,"
Public Const IA05_SRV_ADOPT As String = "wnd[0]/tbar[1]/btn[9]"
Public Const IA05_SRV_QUANTITY As String = "wnd[0]/usr/subSERVICE:SAPLMLSP:0400/tblSAPLMLSPTC_VIEW/txtESLL-MENGE[4,0]"

'==============================================================================
' Langtekst - SAPscript-editoren (operation: AddOperations, item: CreateItems)
'==============================================================================
' Operationens tekst indeholder kortteksten i foerste linje, naar editoren
' aabnes. Den slettes foerst (Tekst > Slet + bekraeft), saa uploadet ikke
' kommer oven i. Itemets tekst uploades direkte.
Public Const LT_MENU_DELETE As String = "wnd[0]/mbar/menu[0]/menu[5]"
Public Const LT_DELETE_CONFIRM As String = "wnd[1]/usr/btnSPOP-OPTION1"
Public Const LT_MENU_UPLOAD As String = "wnd[0]/mbar/menu[0]/menu[3]"
Public Const LT_FORMAT_ITF As String = "wnd[1]/usr/radITCTK-TDITF"
Public Const LT_FORMAT_OK As String = "wnd[1]/tbar[0]/btn[0]"
Public Const LT_FILENAME As String = "wnd[2]/usr/ctxtITCTK-TDFILENAME"
Public Const LT_FILENAME_OK As String = "wnd[2]/tbar[0]/btn[0]"

'==============================================================================
' IP04 - vedligeholdsposition (fra CreateItems)
'==============================================================================
Public Const IP04_CATEGORY As String = "wnd[0]/usr/cmbRMIPM-MPTYP"
Public Const IP04_TEXT As String = "wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/txtRMIPM-PSTXT"

Private Const IP04_TAB_ITEM As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/"
Public Const IP04_NO_RELEASE As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/chkMPOS-NO_AUFRELKZ"
Public Const IP04_FUNCLOC As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_1:SAPLIWO1:0100/ctxtRIWO1-TPLNR"
Public Const IP04_ORDERTYPE As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-AUART"
Public Const IP04_ACTIVITY As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-ILART"
Public Const IP04_WORKCENTER As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/ctxtRMIPM-GEWERK"
Public Const IP04_PRIORITY As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/cmbRMIPM-PRIOK"
Public Const IP04_TL_TYPE As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNTY"
Public Const IP04_TL_GROUP As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNNR"
Public Const IP04_TL_COUNTER As String = IP04_TAB_ITEM & "subSUBSCREEN_ITEM_2:SAPLIWP3:0500/txtRMIPM-PLNAL"

' Objektliste: een FL ad gangen gennem FL-udvaelgelsen.
Public Const IP04_TAB_OBJECTS As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12"
Public Const IP04_OBJ_ADD_FL As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\12/ssubSUBSCREEN_BODY2:SAPLIWP3:8023/subOBJECT:SAPLIWOL:0400/btnBTN_IFLO"
Public Const IP04_OBJ_MULTI As String = "wnd[0]/usr/btn%_STRNO_%_APP_%-VALU_PUSH"
Public Const IP04_OBJ_CLEAR As String = "wnd[1]/tbar[0]/btn[16]"
Public Const IP04_OBJ_VALUE As String = "wnd[1]/usr/tabsTAB_STRIP/tabpSIVA/ssubSCREEN_HEADER:SAPLALDB:3010/tblSAPLALDBSINGLE/ctxtRSCSEL_255-SLOW_I[1,0]"
Public Const IP04_OBJ_TAKE As String = "wnd[1]/tbar[0]/btn[8]"

' Kundefelter: status og revision
Public Const IP04_TAB_CUSTOM As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17"
Private Const IP04_CUSTOM As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\17/ssubSUBSCREEN_BODY2:SAPLIWP3:8027/subCUSSSCR1:SAPLXPRM:0100/"
Public Const IP04_USER_STATUS As String = IP04_CUSTOM & "ctxtGV_STATUS"
Public Const IP04_NONFLOW_STATUS As String = IP04_CUSTOM & "ctxtGV_NON_FLOW_USER_STAT"
Public Const IP04_REVISION As String = IP04_CUSTOM & "ctxtGV_REVNR"
Public Const IP04_REV_YEAR As String = IP04_CUSTOM & "txtCI_MPOS-ZZLREVY"
Public Const IP04_REV_BY As String = IP04_CUSTOM & "txtCI_MPOS-ZZREVBY"

'==============================================================================
' IP05 - itemets langtekst (fra CreateItems)
'==============================================================================
Public Const IP05_ITEM_NO As String = "wnd[0]/usr/ctxtRMIPM-WAPOS"
Public Const IP05_LONGTEXT As String = "wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6001/btnRMIPM-LTPOS_ICON"

'==============================================================================
' IP01 - vedligeholdsplan (fra CreatePlans)
'==============================================================================
Public Const IP01_CATEGORY As String = "wnd[0]/usr/cmbRMIPM-MPTYP"
Public Const IP01_STRATEGY As String = "wnd[0]/usr/ctxtRMIPM-WSTRA"
Public Const IP01_TEXT As String = "wnd[0]/usr/subSUBSCREEN_HEAD:SAPLIWP3:6000/txtRMIPM-WPTXT"

Private Const IP01_CYCLE_BASE As String = "wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\01/ssubSUBSCREEN_BODY1:SAPLIWP3:8011/subSUBSCREEN_CYCLE:SAPLIWP3:0205/"
Public Const IP01_CYCLE As String = IP01_CYCLE_BASE & "txtRMIPM-ZYKL1"
Public Const IP01_CYCLE_UNIT As String = IP01_CYCLE_BASE & "ctxtRMIPM-ZEIEH"

Public Const IP01_ITEM_LINK As String = "wnd[0]/usr/subSUBSCREEN_MITEM:SAPLIWP3:8002/tabsTABSTRIP_ITEM/tabpT\11/ssubSUBSCREEN_BODY2:SAPLIWP3:8022/subSUBSCREEN_MAINT_ITEM_TEXT:SAPLIWP3:6005/btnITEM_LINK"
Public Const IP01_ITEM_NO As String = "wnd[0]/usr/txtWAPOS-LOW"
Public Const IP01_ITEM_GRID As String = "wnd[0]/usr/cntlGRID1/shellcont/shell"
Public Const IP01_ITEM_CHOOSE As String = "wnd[0]/tbar[1]/btn[42]"

Public Const IP01_TAB_SCHEDULING As String = "wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02"
Private Const IP01_SCHED_BASE As String = "wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\02/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0115/"
Public Const IP01_HORIZON As String = IP01_SCHED_BASE & "txtRMIPM-HORIZ"
Public Const IP01_HORIZON_QUALIFIER As String = IP01_SCHED_BASE & "ctxtRMIPM-HORIZ_QUALIFIER"
Public Const IP01_SCHED_PERIOD As String = IP01_SCHED_BASE & "txtRMIPM-ABRHO"
Public Const IP01_SCHED_UNIT As String = IP01_SCHED_BASE & "ctxtRMIPM-HUNIT"
Public Const IP01_START_DATE As String = IP01_SCHED_BASE & "ctxtRMIPM-STADT"
Public Const IP01_KEY_DATE As String = IP01_SCHED_BASE & "radRMIPM-STICH"

Public Const IP01_TAB_SORT As String = "wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\03"
Public Const IP01_SORT_FIELD As String = "wnd[0]/usr/subSUBSCREEN_MPLAN:SAPLIWP3:8001/tabsTABSTRIP_HEAD/tabpT\03/ssubSUBSCREEN_BODY1:SAPLIWP3:8012/subSUBSCREEN_PARAMETER:SAPLIWP3:0113/cmbRMIPM-PLAN_SORT"


'==============================================================================
' FUNCTIONAL LOCATIONS - fra SPOOL-arket (excel/vba/spool-gui/GUI_SCRIPT.bas)
'==============================================================================

'--- Felterne i ordren --------------------------------------------------------
' Appens feltnavne: SPOOL-arkets kolonneoverskrifter med versaler. Karakteris-
' tikkerne staar ikke her - de staar i tabellen Karakteristikker i Opslag.
Public Const FLF_MANUFACTURER As String = "MANUFACTURER"
Public Const FLF_MODEL As String = "MODEL NUMBER"
Public Const FLF_PARTNO As String = "MANUFACTURER PART NUMBER"
Public Const FLF_SERIAL As String = "MANUFACTURER SERIAL NUMBER"
Public Const FLF_ROOM As String = "ROOM"
Public Const FLF_ABC As String = "ABC INDIC."
Public Const FLF_SORTFIELD As String = "SORT FIELD"
Public Const FLF_WARRANTY_START As String = "WARRANTY START"
Public Const FLF_WARRANTY_END As String = "WARRANTY END"
Public Const FLF_ATEX As String = "ATEX"
Public Const FLF_RISIKO As String = "RISIKO"
Public Const FLF_ASBESTOS As String = "ASBESTOS"
Public Const FLF_PTW As String = "PTW"
Public Const FLF_SUPERIOR As String = "SUPERIOR FL"
Public Const FLF_TRM As String = "TRM ASSIGNMENT"
Public Const FLF_GIVEXT As String = "GIV_EXT ASSIGNMENT"

' Klasser uden klassetildeling (SPOOL: Class <> "NO CLASS" And <> "SIGNAL").
Public Const FL_CLASS_NONE As String = "NO CLASS"
Public Const FL_CLASS_SIGNAL As String = "SIGNAL"

'--- Transaktioner ------------------------------------------------------------
Public Const TX_FL_CREATE As String = "/nIL01"
Public Const TX_FL_CHANGE As String = "/nIL02"
Public Const TX_FL_DISPLAY As String = "/nIL03"

' Statuslinjen i IL01, naar maerket findes: "Functional location <FL> already
' exists" (SPOOL sammenligner hele teksten). Engelsk logon som i dag.
Public Const FL_MSG_EXISTS As String = "already exists"

'--- Indgangsbilledet (FillMasterdataFields) ----------------------------------
Public Const IL01_FL As String = "wnd[0]/usr/txtIFLOS-STRNO"
Public Const IL01_STRIND As String = "wnd[0]/usr/ctxtRILO0-TPLKZ"
Public Const IL02_FL As String = "wnd[0]/usr/ctxtIFLO-TPLNR"
Public Const IL02_STRIND As String = "wnd[0]/usr/ctxtRILO0-TPLKZ"
' IL03 bruges kun til at se efter, om en FL findes (SPOOL: ExtractMasterdataFields).
Public Const IL03_FL As String = "wnd[0]/usr/ctxtIFLO-TPLNR"

'--- Hovedbilledet -----------------------------------------------------------
Public Const FL_DESCRIPTION As String = "wnd[0]/usr/txtIFLO-PLTXT"
Private Const FL_TABS As String = "wnd[0]/usr/tabsTABSTRIP/"

' Fanen General
Private Const FL_GEN As String = FL_TABS & "tabpT\01/ssubSUB_DATA:SAPLITO0:0102/"
Public Const FL_CLASS_SHOWN As String = FL_GEN & "subSUB_0102A:SAPLITO0:1020/txtITOBATTR-KLASSE"
Public Const FL_OBJECT_TYPE As String = FL_GEN & "subSUB_0102A:SAPLITO0:1020/subSUB_1020A:SAPLITO0:1025/ctxtITOB-EQART"
Public Const FL_MANUFACTURER As String = FL_GEN & "subSUB_0102C:SAPLITO0:1022/txtITOB-HERST"
Public Const FL_MODEL As String = FL_GEN & "subSUB_0102C:SAPLITO0:1022/txtITOB-TYPBZ"
Public Const FL_PARTNO As String = FL_GEN & "subSUB_0102C:SAPLITO0:1022/txtITOB-MAPAR"
Public Const FL_SERIAL As String = FL_GEN & "subSUB_0102C:SAPLITO0:1022/txtITOB-SERGE"
' SPOOL skriver altid "s" i objekttypen.
Public Const FL_OBJECT_TYPE_VALUE As String = "s"

' Fanen Location
Public Const FL_TAB_LOCATION As String = FL_TABS & "tabpT\02"
Private Const FL_LOC As String = FL_TABS & "tabpT\02/ssubSUB_DATA:SAPLITO0:0102/"
Public Const FL_ROOM As String = FL_LOC & "subSUB_0102A:SAPLITO0:1050/txtITOB-MSGRP"
Public Const FL_ABC As String = FL_LOC & "subSUB_0102A:SAPLITO0:1050/ctxtITOB-ABCKZ"
Public Const FL_SORTFIELD As String = FL_LOC & "subSUB_0102A:SAPLITO0:1050/txtITOB-EQFNR"
Private Const FL_WARRANTY As String = FL_LOC & "subSUB_0102B:SAPLITO0:1098/subSUB_1098A:SAPLBG00:3400/"
Public Const FL_WARRANTY_START As String = FL_WARRANTY & "ctxtWCHECK_V_H-GWLDT_I"
Public Const FL_WARRANTY_END As String = FL_WARRANTY & "ctxtWCHECK_V_H-GWLEN_I"
Public Const FL_WARRANTY_INHERIT As String = FL_WARRANTY & "chkWCHECK_V_H-WAGET_I"
Public Const FL_WARRANTY_PASSON As String = FL_WARRANTY & "chkWCHECK_V_H-GAERB_I"

' Fanen Structure - overordnet FL (kun KAB, som i SPOOL)
Public Const FL_TAB_STRUCTURE As String = FL_TABS & "tabpT\04"
Private Const FL_STRUCT As String = FL_TABS & "tabpT\04/ssubSUB_DATA:SAPLITO0:0102/subSUB_0102A:SAPLITO0:1060/subSUB_1060A:SAPLITO0:1066/"
Public Const FL_SUPERIOR As String = FL_STRUCT & "txtITOB-TPLMA"
Public Const FL_SUPERIOR_CHANGE As String = FL_STRUCT & "btnFCODE_CHM"
Public Const FL_SUPERIOR_POPUP As String = "wnd[1]/usr/ctxtIFLO-TPLMA"

' Tilladelser (Permits): menuen og tabellen i dialogen
Public Const FL_MENU_PERMITS As String = "wnd[0]/mbar/menu[2]/menu[6]"
Public Const FL_PERMIT_BTN_8 As String = "wnd[1]/tbar[0]/btn[8]"
Public Const FL_PERMIT_BTN_14 As String = "wnd[1]/tbar[0]/btn[14]"
Public Const FL_PERMIT_CELL As String = "wnd[1]/usr/tblSAPLIMSPTCTRL_1000/ctxtRM63S-PMSOG[0,"
Public Const FL_PERMIT_DONE As String = "wnd[1]/tbar[0]/btn[11]"

' Klassetildeling. Ekstra klasser (TRM, WCM, GIV_EXT) skrives i linje 1 efter
' et tryk paa knappen, der giver en ny linje - som i SPOOL.
Public Const FL_BTN_CLASSES As String = "wnd[0]/tbar[1]/btn[20]"
Public Const FL_CLASS_CELL As String = "wnd[0]/usr/subSUBSCR_ZUORD:SAPLCLFM:1600/tblSAPLCLFMTC_OBJ_CLASS/ctxtRMCLF-CLASS[0,"
Public Const FL_CLASS_NEWLINE As String = "wnd[0]/usr/btn%#AUTOTEXT003"
Public Const FL_CLASS_MARKALL As String = "wnd[0]/usr/btnICON_MARKALL"
Public Const FL_CLASS_DELETE As String = "wnd[0]/usr/btnICON_DELETE"

' Fanen med karakteristikkerne
Public Const FL_TAB_CHARS As String = FL_TABS & "tabpT\06"
Public Const FL_CHAR_CONTAINER As String = FL_TABS & "tabpT\06/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1090/subSUB_1090A:SAPLCTMS:5110/sub:SAPLCTMS:5110"
Public Const FL_CHAR_NEXT_PAGE As String = FL_TABS & "tabpT\06/ssubSUB_DATA:SAPLITO0:0109/subSUB_0109A:SAPLITO0:1090/subSUB_1090A:SAPLCTMS:5110/btnOES_PDOWN"
' Vaerdidialogen (F4) til Remarks, Supply from og Safety Critical Equipment
' med flere vaerdier
Public Const FL_VALUE_CELL As String = "wnd[1]/usr/tblSAPLCTMSVALUE_S/txtRCTMS-ATWRT[1,0]"
Public Const FL_VALUE_TABLE As String = "wnd[1]/usr/tblSAPLCTMSVALUE_S"
Public Const FL_VALUE_TEXT As String = "wnd[1]/usr/tblSAPLCTMSVALUE_S/txtRCTMS-ATWTB[3,"
Public Const FL_VALUE_CHECK As String = "wnd[1]/usr/tblSAPLCTMSVALUE_S/chkRCTMS-SEL01[0,"
Public Const FL_VALUE_OK As String = "wnd[1]/tbar[0]/btn[8]"

'--- Gem (SaveFLAndGetStatus) og dialoger -------------------------------------
' En dialog efter Gem betyder, at FL'en IKKE blev gemt. SPOOL lukker den med
' OK, gaar ud med Exit og svarer Nej til at gemme.
Public Const FL_BTN_EXIT As String = "wnd[0]/tbar[0]/btn[15]"
Public Const POPUP_WINDOW As String = "wnd[1]"
Public Const POPUP_W1_BTN0 As String = "wnd[1]/tbar[0]/btn[0]"
Public Const POPUP_W1_BTN1 As String = "wnd[1]/tbar[0]/btn[1]"
Public Const POPUP_W2_BTN0 As String = "wnd[2]/tbar[0]/btn[0]"
Public Const POPUP_OPTION1 As String = "wnd[1]/usr/btnSPOP-OPTION1"
Public Const POPUP_OPTION2 As String = "wnd[1]/usr/btnSPOP-OPTION2"

'==============================================================================
' Indstillinger
'==============================================================================

' Vaerdien for en noegle i tblIndstillinger. Mangler raekken eller tabellen,
' bruges standardvaerdien - saa en ny indstilling ikke stopper en gammel
' projektmappe.
Public Function Setting(ByVal key As String) As String
    Dim lo As ListObject
    Dim r As Long

    Setting = DefaultSetting(key)

    On Error Resume Next
    Set lo = ThisWorkbook.Worksheets(SH_SETTINGS).ListObjects(LO_SETTINGS)
    On Error GoTo 0
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function

    For r = 1 To lo.ListRows.Count
        If StrComp(Trim$(CStr(lo.DataBodyRange.Cells(r, 1).Value)), key, vbTextCompare) = 0 Then
            Setting = Trim$(CStr(lo.DataBodyRange.Cells(r, 3).Value))
            Exit Function
        End If
    Next r
End Function

Public Function SettingIsYes(ByVal key As String) As Boolean
    Select Case UCase$(Setting(key))
        Case "JA", "YES", "TRUE", "1", "X", "SAND"
            SettingIsYes = True
    End Select
End Function

' Standardvaerdierne. Setup skriver dem i tblIndstillinger; herfra bruges de
' kun, naar en raekke mangler.
Public Function DefaultSetting(ByVal key As String) As String
    Select Case key
        Case SET_SAP_SYSTEM: DefaultSetting = "GQ1"
        Case SET_SAP_CLIENT: DefaultSetting = "450"
        Case SET_PROD_SYSTEMS: DefaultSetting = "GP1"
        Case SET_LOGON_TEST: DefaultSetting = "SAP  DECS GQ1  Quality"
        Case SET_LOGON_PROD: DefaultSetting = "SAP  DECS GP1  Production"
        Case SET_NEW_SESSION: DefaultSetting = "Ja"
        Case SET_CONFIRM_SAVE: DefaultSetting = "Ja"
        Case SET_ITF_PATH: DefaultSetting = "C:\Users\Public\Documents\SAP_PM_Longtext.itf"
        Case SET_KEY_DATE: DefaultSetting = "01.01.2020"
        Case SET_HORIZON_QUALIFIER: DefaultSetting = "FCD"
        Case SET_TASKLIST_TYPE: DefaultSetting = "A"
        Case SET_PM02_MATGROUP: DefaultSetting = "B08.06"
        Case SET_DECIMAL_SEP: DefaultSetting = ","
        Case SET_PLAN_CATEGORY: DefaultSetting = "PM"
        Case Else: DefaultSetting = vbNullString
    End Select
End Function

' Er systemet et produktionssystem? Listen staar i indstillingen ProdSystems,
' kommasepareret. Et ukendt system regnes IKKE for produktion - men DEV- og
' TEST-data maa kun gaa til et system, der ikke staar paa listen.
Public Function IsProductionSystem(ByVal systemName As String) As Boolean
    Dim parts() As String
    Dim i As Long

    parts = Split(Setting(SET_PROD_SYSTEMS), ",")
    For i = LBound(parts) To UBound(parts)
        If StrComp(Trim$(parts(i)), Trim$(systemName), vbTextCompare) = 0 Then
            IsProductionSystem = True
            Exit Function
        End If
    Next i
End Function
