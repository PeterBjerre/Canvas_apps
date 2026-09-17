Attribute VB_Name = "modUiFieldMap"
Option Explicit

Public Function HeaderField_WorkOrderNumber() As String
    HeaderField_WorkOrderNumber = "Aufnr"
End Function

Public Function HeaderField_ShortText() As String
    HeaderField_ShortText = "Ktext"
End Function

Public Function HeaderField_FunctionalLocation() As String
    HeaderField_FunctionalLocation = "Tplnr"
End Function

Public Function HeaderField_MainWorkCenter() As String
    HeaderField_MainWorkCenter = "Vaplz"
End Function

Public Function HeaderField_PriorityKey() As String
    HeaderField_PriorityKey = "Priok"
End Function

Public Function HeaderField_PriorityText() As String
    HeaderField_PriorityText = "Priokx"
End Function

Public Function HeaderField_BasicStartUtc() As String
    HeaderField_BasicStartUtc = "GstrpUtc"
End Function

Public Function HeaderField_BasicFinishUtc() As String
    HeaderField_BasicFinishUtc = "GltrpUtc"
End Function

Public Function HeaderField_LongText() As String
    HeaderField_LongText = "Longtext"
End Function

Public Function HeaderField_PersonResponsibleInitials() As String
    HeaderField_PersonResponsibleInitials = "PersonResponsibleInitials"
End Function

Public Function Header_EquipmentField_FromObjects() As String
    Header_EquipmentField_FromObjects = "Equnr"
End Function

Public Function Header_EquipmentTextField_FromObjects() As String
    Header_EquipmentTextField_FromObjects = "Eqtxt"
End Function

Public Function FirstOperation_Field_OperationNumber() As String
    FirstOperation_Field_OperationNumber = "Vornr"
End Function

Public Function FirstOperation_Field_WorkCenter() As String
    FirstOperation_Field_WorkCenter = "Arbpl"
End Function

Public Function FirstOperation_Field_ControlKey() As String
    FirstOperation_Field_ControlKey = "Steus"
End Function

Public Function FirstOperation_Field_PersonnelNo() As String
    FirstOperation_Field_PersonnelNo = "Pernr"
End Function

Public Function GetColumns_Operations() As Variant
    GetColumns_Operations = MakeColumns(Array( _
        "Operation", "Vornr", _
        "Work center", "Arbpl", _
        "Control key", "Steus", _
        "Short text", "ShortText", _
        "Work", "Arbei", _
        "Unit", "Arbeh", _
        "No.", "Anzzl", _
        "Personnel no.", "Pernr", _
        "Vendor", "Lifnr", _
        "Actual work", "ActualHours" _
    ))
End Function

Public Function GetColumns_Permit() As Variant
    GetColumns_Permit = MakeColumns(Array( _
        "Permit ID", "PermitExtNo", _
        "Status", "PermitSystemStatus", _
        "Functional loc.", "PermitFunctionalLocation", _
        "Valid from", "ValidFromUtc", _
        "Valid to", "ValidToUtc", _
        "Requestor", "Requestor" _
    ))
End Function

Public Function GetColumns_Objects() As Variant
    GetColumns_Objects = MakeColumns(Array( _
        "Functional loc.", "Tplnr", _
        "FL description", "Pltxt", _
        "Equipment", "Equnr", _
        "Equipment text", "Eqtxt" _
    ))
End Function

Public Function GetColumns_Attachment() As Variant
    GetColumns_Attachment = MakeColumns(Array( _
        "Doc type", "DocumentType", _
        "Doc number", "DocumentNumber", _
        "Description", "Description", _
        "Original", "Url", _
        "Version", "DocumentVersion", _
        "Part", "DocumentPart" _
    ))
End Function

Public Function GetColumns_Planning() As Variant
    GetColumns_Planning = MakeColumns(Array( _
        "Task list type", "Plnty", _
        "Group", "Plnnr", _
        "Node", "Plnkn", _
        "Counter", "Zaehl", _
        "Work center", "Arbpl", _
        "Short text", "Ltxa1" _
    ))
End Function

Public Function CaptionForHeader_LongText() As String
    CaptionForHeader_LongText = "Langtekst"
End Function

Public Function CaptionForHeader_FunctionalLocation() As String
    CaptionForHeader_FunctionalLocation = "Funktionslokation"
End Function

Public Function CaptionForHeader_Equipment() As String
    CaptionForHeader_Equipment = "Equipment"
End Function

Public Function CaptionForHeader_MainWorkCenter() As String
    CaptionForHeader_MainWorkCenter = "Hoved work center"
End Function

Public Function CaptionForHeader_Priority() As String
    CaptionForHeader_Priority = "Prioritet"
End Function

Public Function CaptionForHeader_BasicStart() As String
    CaptionForHeader_BasicStart = "Basic start"
End Function

Public Function CaptionForHeader_BasicFinish() As String
    CaptionForHeader_BasicFinish = "Basic finish"
End Function

Public Function CaptionForHeader_PersonResponsible() As String
    CaptionForHeader_PersonResponsible = "Ansvarlig"
End Function

Private Function MakeColumns(ByVal flat As Variant) As Variant
    Dim n As Long
    n = (UBound(flat) - LBound(flat) + 1) \ 2
    Dim out() As Variant
    ReDim out(1 To n, 1 To 2)

    Dim i As Long, p As Long
    p = LBound(flat)
    For i = 1 To n
        out(i, 1) = CStr(flat(p)): p = p + 1
        out(i, 2) = CStr(flat(p)): p = p + 1
    Next i

    MakeColumns = out
End Function

