Attribute VB_Name = "modExtractWorkOrder"
Option Explicit

Public Function FetchWorkOrderAll(ByVal aufnr As String, Optional ByRef errText As String) As Boolean
    On Error GoTo EH

    Dim orderNo As String
    orderNo = NormalizeAufnr(aufnr)
    If Len(orderNo) = 0 Then
        errText = "AUFNR mangler."
        FetchWorkOrderAll = False
        Exit Function
    End If

    modUtil.BindOutputWorkbook ThisWorkbook

    PrepareAllSheets

    Dim url As String
    url = BASE_URL & "WorkOrderHeaderSet('" & EscapeODataKey(orderNo) & "')?$format=json"

    Dim root As Object
    Set root = modHttpOData.HttpGetJson(url)

    modOrderParserJson.ParseOrderJSON root

    FetchWorkOrderAll = True
    Exit Function

EH:
    errText = "FetchWorkOrderAll fejl: " & Err.Number & " - " & Err.Description
    FetchWorkOrderAll = False
End Function

Private Sub PrepareAllSheets()
    Dim arr As Variant
    Dim i As Long
    arr = modODataCatalog.WorkOrderCoreSheets()
    For i = LBound(arr) To UBound(arr)
        modUtil.PrepareSheet CStr(arr(i))
    Next i
End Sub

Private Function NormalizeAufnr(ByVal v As String) As String
    NormalizeAufnr = Replace(Trim$(CStr(v)), " ", "")
End Function

Private Function EscapeODataKey(ByVal v As String) As String
    EscapeODataKey = Replace(CStr(v), "'", "''")
End Function
