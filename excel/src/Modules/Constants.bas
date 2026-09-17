Option Explicit

' SAP transactions
Public Const TX_IA05 As String = "/NIA05"
Public Const TX_IA07 As String = "/NIA07"
Public Const TX_IP01 As String = "/NIP01"
Public Const TX_IP03 As String = "/NIP03"
Public Const TX_IP04 As String = "/NIP04"
Public Const TX_IP05 As String = "/NIP05"
Public Const TX_IP06 As String = "/NIP06"
Public Const TX_IW33 As String = "/NIW33"

' Shared defaults
Public Const DEFAULT_SAP_DATE As String = "01.01.2020"
Public Const SAP_LONGTEXT_ITF_PATH As String = "C:\Users\Public\Documents\SAP_PM_Longtext.itf"

' Worksheet names
Public Const WS_CALL_HORIZON_TABLE As String = "Call_Horizon_Table"
Public Const WS_MAINTENANCE_TLH As String = "Maintenance_TLH"
Public Const WS_MAINTENANCE_TL As String = "Maintenance_TL"
Public Const WS_MAINTENANCE_ITEMS As String = "Maintenance_Items"
Public Const WS_MAINTENANCE_PLANS As String = "Maintenance_Plans"
Public Const WS_OBJECT_LIST As String = "Object_list"
Public Const WS_EXTRACT_DATA As String = "Extract Data"
Public Const WS_ITEM_EXTRACT As String = "Raw_Item_Header"
Public Const WS_TASKLIST_EXTRACT As String = "Raw_Tasklist_Operations"
Public Const WS_RAW_ORDRE_HEADER As String = "Raw_Ordre_Header"
Public Const WS_RAW_ORDRE_OPERATIONS As String = "Raw_Ordre_Operations"
Public Const WS_RAW_ORDRE_COMPONENTS As String = "Raw_Ordre_Components"
Public Const WS_RAW_ORDRE_OBJECTS As String = "Raw_Ordre_Objects"
Public Const WS_RAW_ORDRE_ATTACHMENTS As String = "Raw_Ordre_Attachments"
Public Const WS_RAW_ITEM_OBJECTS As String = "Raw_Item_Objects"
Public Const WS_RAW_TASKLIST_COMPONENTS As String = "Raw_Tasklist_Components"
Public Const WS_RAW_TASKLIST_ATTACHMENTS As String = "Raw_Tasklist_Attachments"
Public Const WS_COMPARE_MAP As String = "Compare_Map"
Public Const WS_COMPARE_RESULTS As String = "Compare_Results"
Public Const WS_COMPARE_DIFF As String = "Compare_Diff"
Public Const WS_COMPARE_SUMMARY As String = "Compare_Summary"
Public Const WS_COMPARE_COMPONENTS As String = "Compare_Components"
Public Const WS_COMPARE_ATTACHMENTS As String = "Compare_Attachments"
Public Const WS_COMPARE_LONGTEXT As String = "Compare_LongText"
Public Const WS_COCKPIT_HOME As String = "Cockpit_Home"
Public Const WS_COCKPIT_ORDER As String = "Cockpit_Order"
Public Const WS_COCKPIT_DIFFS As String = "Cockpit_Diffs"
Public Const WS_COCKPIT_LONGTEXT_EDITOR As String = "Cockpit_LongText_Editor"
Public Const WS_COCKPIT_DECISIONS As String = "Cockpit_Decisions"
Public Const WS_DATA_DIFF_FACTS As String = "Data_Diff_Facts"
Public Const WS_DATA_EDIT_BUFFER As String = "Data_Edit_Buffer"
Public Const WS_DATA_DECISION_FACTS As String = "Data_Decision_Facts"
Public Const WS_SETUP As String = "Setup"

' Setup cells (1-based row/column)
Public Const SETUP_SYSTEM_ROW As Long = 3
Public Const SETUP_SYSTEM_COL As Long = 4
Public Const SETUP_FLOW_URL_ROW As Long = 5
Public Const SETUP_FLOW_URL_COL As Long = 4
Public Const SETUP_SHAREPOINT_PLANS_URL_ROW As Long = 6
Public Const SETUP_SHAREPOINT_PLANS_URL_COL As Long = 4
Public Const SETUP_SHAREPOINT_ITEMS_URL_ROW As Long = 7
Public Const SETUP_SHAREPOINT_ITEMS_URL_COL As Long = 4
Public Const SETUP_SHAREPOINT_TLH_URL_ROW As Long = 8
Public Const SETUP_SHAREPOINT_TLH_URL_COL As Long = 4
Public Const SETUP_SHAREPOINT_TL_URL_ROW As Long = 9
Public Const SETUP_SHAREPOINT_TL_URL_COL As Long = 4
Public Const SETUP_SHAREPOINT_CRED_TARGET_ROW As Long = 10
Public Const SETUP_SHAREPOINT_CRED_TARGET_COL As Long = 4
Public Const SETUP_SHAREPOINT_TOKEN_FALLBACK_ROW As Long = 11
Public Const SETUP_SHAREPOINT_TOKEN_FALLBACK_COL As Long = 4
Public Const SETUP_SHAREPOINT_TLH_FILTER_ROW As Long = 12
Public Const SETUP_SHAREPOINT_TLH_FILTER_COL As Long = 4
Public Const SETUP_SHAREPOINT_TL_FILTER_ROW As Long = 13
Public Const SETUP_SHAREPOINT_TL_FILTER_COL As Long = 4

' OData entity sets
Public Const ES_HDR As String = "WorkOrderHeaderSet"

' SAP GUI login defaults
Public Const SAP_LOGON_EXE_PATH As String = "C:\Program Files\SAP\FrontEnd\SAPGUI\saplogon.exe"
Public Const SAP_SYSTEM_GP1 As String = "SAP  DECS GP1  Production"
Public Const SAP_SYSTEM_GQ1 As String = "SAP  DECS GQ1  Quality"
Public Const SAP_CLIENT_SUFFIX As String = "450"
Public Const SAP_WAIT_SECONDS As String = "0:00:05"

' Tables
Public Const LO_CALL_HORIZON As String = "Call_Horizon"
Public Const LO_DIFF_FACTS As String = "tbDiffFacts"
Public Const LO_DECISION_QUEUE As String = "tbDecisionQueue"
Public Const LO_LONGTEXT_QUEUE As String = "tbLongTextQueue"
Public Const LO_DECISION_FACTS As String = "tbDecisionFacts"

' Compare engine
Public Const USE_PYTHON_COMPARE As Boolean = False   ' True = PY()-based (requires M365), False = pure VBA

' Integrations
Public Const POWER_AUTOMATE_URL As String = "https://default100b3c99f3e24da09c8ab9d345742c.36.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/353df9ba00c44de69aac2c0e826043f8/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=1Tjx-wgJvL_EFkb8hZvx7wvoWC3BWv_tApbhsmGMBnQ"
Public Const SHAREPOINT_DEFAULT_PAGE_SIZE As Long = 500
Public Const SHAREPOINT_MAINTENANCE_PLANS_URL As String = "https://orsted.sharepoint.com/teams/BioSAP/_api/web/lists/getbytitle('MaintenancePlans')/items"
Public Const SHAREPOINT_MAINTENANCE_ITEMS_URL As String = "https://orsted.sharepoint.com/teams/BioSAP/_api/web/lists/getbytitle('MaintenanceItems')/items"
Public Const SHAREPOINT_MAINTENANCE_TLH_URL As String = "https://orsted.sharepoint.com/teams/BioSAP/_api/web/lists/getbytitle('TaskListMain')/items"
Public Const SHAREPOINT_MAINTENANCE_TL_URL As String = "https://orsted.sharepoint.com/teams/BioSAP/_api/web/lists/getbytitle('TaskListMain')/items"
