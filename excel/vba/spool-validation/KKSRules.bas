Attribute VB_Name = "KKSRules"
Option Explicit

' Single source of truth for KKS regex patterns used across validation flows.
Public Function GetKKSPatterns() As Variant
    GetKKSPatterns = Array( _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z]$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}$", _
        "^[A-Z]{3}\d{2}[\d\s]U[A-Z]{2}\d{2}UE\d{3}(FP|FD|FG|FH)$", _
        "^[A-Z]{3}\d{2}[\d\s]U[A-Z]{2}\d{2}UF\d{3}[DGH]$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z\s][-A-Z]{2}\d{2}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{5}[\w\s][-A-Z]{2}\d{2}$", _
        "^[A-Z]{3}\d{2,3}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{1,3}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{4}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{1}\d{4}$", _
        "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\s{3}\d{4}$" _
    )
End Function

Public Function IsLegacyHyphenFNumbering(ByVal functionalLocation As String) As Boolean
    Dim regex As Object

    Set regex = CreateObject("VBScript.RegExp")
    regex.IgnoreCase = False
    regex.Global = False
    regex.pattern = "^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z\s][-A-Z]{2}\d{1,3}$"

    IsLegacyHyphenFNumbering = regex.Test(UCase$(Trim$(functionalLocation)))
End Function

