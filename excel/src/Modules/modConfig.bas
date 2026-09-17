Option Explicit

'===========================
'   EAM ORDER EXTRACTOR (JSON)
'===========================
Public Const BASE_URL As String = _
    "https://sapap1yp2.de-prod.dk:44302/sap/opu/odata/sap/ZEAM_SMART_PLAN_SRV/"

Public Const INVENTORY_BASE_URL As String = _
    "https://sapap1yp2.de-prod.dk:44302/sap/opu/odata/sap/ZEAM_SMART_PLANT_INVENTORY_SRV/"
Public Const INVENTORY_MOVEMENTS_ENTITY_SET As String = "GoodsMovementSet"
Public Const MOVEMENT_TYPE_ISSUE As String = "261"
Public Const MOVEMENT_TYPE_RETURN As String = "262"

Public Const APP_TITLE As String = "EAM Tasklist Extractor"
Public Const TIMEOUT_MS As Long = 120000

' JSON som standard
Public Const USE_JSON As Boolean = True

