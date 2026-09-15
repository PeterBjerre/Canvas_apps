Attribute VB_Name = "Verification_Cache"
Option Explicit

' Cache til kolonneindeks pr. ark og til vørdilister
Private mColIndexCache As Object   ' Dict: key=Sheet.CodeName -> Dict(header->col)
Private mListCache     As Object   ' Dict: key=ListObjectName  -> Variant() (1-based eller 0-based)

' Kald ved start af hver Verify-kørsel
Public Sub BeginRun(ByVal ClassName As String)
    If mColIndexCache Is Nothing Then
        Set mColIndexCache = CreateObject("Scripting.Dictionary")
        mColIndexCache.CompareMode = vbTextCompare
    End If
    If mListCache Is Nothing Then
        Set mListCache = CreateObject("Scripting.Dictionary")
        mListCache.CompareMode = vbTextCompare
    End If
End Sub

' Invalider kolonneindeks for et specifikt ark (brug hvis headers øndres)
Public Sub InvalidateColIndex(ByVal ws As Worksheet)
    If Not mColIndexCache Is Nothing Then
        Dim k As String: k = ws.CodeName
        If mColIndexCache.exists(k) Then mColIndexCache.Remove k
    End If
End Sub

' Hent / byg kolonneindeks for et ark (header-røkke = 3)
Public Function GetColIndex(ByVal ws As Worksheet) As Object
    Dim k As String: k = ws.CodeName

    If mColIndexCache Is Nothing Then
        Set mColIndexCache = CreateObject("Scripting.Dictionary")
        mColIndexCache.CompareMode = vbTextCompare
    End If

    If Not mColIndexCache.exists(k) Then
        Dim dict As Object: Set dict = CreateObject("Scripting.Dictionary")
        dict.CompareMode = vbTextCompare

        Dim lastCol As Long, c As Long, hdr As String
        lastCol = ws.Cells(3, ws.Columns.count).End(xlToLeft).Column

        For c = 1 To lastCol
            hdr = Trim$(CStr(ws.Cells(3, c).value))
            If Len(hdr) > 0 Then dict(hdr) = c
        Next c

        ' VIGTIGT: gem objekt i cache med Set
        Set mColIndexCache(k) = dict
    End If

    ' VIGTIGT: returnør objekt med Set
    Set GetColIndex = mColIndexCache(k)
End Function

' Slø kolonnenummer op via cachet indeks (returnerer 0 hvis ikke fundet)
Public Function LookupCol(ByVal colIndex As Object, ByVal header As String) As Long
    If Not colIndex Is Nothing Then
        If colIndex.exists(header) Then
            LookupCol = CLng(colIndex(header))
            Exit Function
        End If
    End If
    LookupCol = 0
End Function

' Hent (og cache) en vørdiliste fra en ListObject hvor 1. kolonne indeholder vørdier
Public Function GetList(ByVal listObjectName As String) As Variant
    If mListCache Is Nothing Then
        Set mListCache = CreateObject("Scripting.Dictionary")
        mListCache.CompareMode = vbTextCompare
    End If
    If mListCache.exists(listObjectName) Then
        GetList = mListCache(listObjectName)
        Exit Function
    End If

    Dim lo As ListObject, ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        Set lo = Nothing
        On Error Resume Next
        Set lo = ws.ListObjects(listObjectName)
        On Error GoTo 0
        If Not lo Is Nothing Then
            Dim rng As Range, arr As Variant, vals() As String, i As Long
            Set rng = lo.ListColumns(1).DataBodyRange
            If Not rng Is Nothing Then
                arr = rng.value
                ReDim vals(1 To rng.Rows.count)
                For i = 1 To rng.Rows.count
                    vals(i) = CStr(arr(i, 1))
                Next i
                ' Her gemmer vi en Variant() (ikke et objekt) ø Set er IKKE nødvendigt
                mListCache(listObjectName) = vals
                GetList = vals
                Exit Function
            End If
        End If
    Next ws

    ' Cache "ikke fundet" for at undgø gentagne scans i samme run.
    mListCache(listObjectName) = Array()
    GetList = mListCache(listObjectName)
End Function



