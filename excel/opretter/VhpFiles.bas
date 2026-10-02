Attribute VB_Name = "VhpFiles"
Option Explicit
'==============================================================================
' VhpFiles - mappen, ordrefilerne, statusfilerne og kvitteringerne.
'
' Alt gaar gennem Scripting.FileSystemObject og ADODB.Stream, ikke gennem
' VBA's egne Dir/Open/Name: OneDrive-stien indeholder "Oersted" med et
' bogstav, de gamle filfunktioner ikke altid kan haandtere, og JSON-filerne
' er UTF-8.
'
' Mappen, opretteren arbejder i, er det SharePoint-bibliotek, flowet skriver
' ordrerne i, synkroniseret til pc'en med OneDrive:
'
'   <...>\BioSAP - SAP-oprettelse\
'       Til oprettelse\   MP0133_20261002-084233.json         (flowet)
'                         MP0133_20261002-084233.status.json  (opretteren)
'       Kvitteringer\     MP0133_20261002-084233.kvittering.json -> flowet
'       Oprettet\         ordre + status, naar planen er oprettet
'==============================================================================

Private mFso As Object

Public Function Fso() As Object
    If mFso Is Nothing Then Set mFso = CreateObject("Scripting.FileSystemObject")
    Set Fso = mFso
End Function

'==============================================================================
' Mappen
'==============================================================================

' Mappen for den aktuelle bruger. Tom streng, hvis den ikke kendes endnu.
Public Function RootFolder() As String
    Dim saved As String

    saved = GetSetting(REG_APP, REG_SECTION, REG_FOLDER, vbNullString)
    If Len(saved) > 0 Then
        If Fso().FolderExists(saved) Then
            RootFolder = saved
            Exit Function
        End If
    End If

    saved = DetectFolder()
    If Len(saved) > 0 Then
        SaveRootFolder saved
        RootFolder = saved
    End If
End Function

Public Sub SaveRootFolder(ByVal path As String)
    SaveSetting REG_APP, REG_SECTION, REG_FOLDER, path
End Sub

' Valgte brugeren selve "Til oprettelse", er det foraeldremappen, der menes.
Public Function NormalizeRoot(ByVal path As String) As String
    Dim nm As String
    path = StripSlash(path)
    nm = Fso().GetFileName(path)
    If StrComp(nm, FOLDER_ORDERS, vbTextCompare) = 0 Or _
       StrComp(nm, FOLDER_RECEIPTS, vbTextCompare) = 0 Or _
       StrComp(nm, FOLDER_DONE, vbTextCompare) = 0 Then
        path = Fso().GetParentFolderName(path)
    End If
    NormalizeRoot = path
End Function

' Leder efter det synkroniserede bibliotek. OneDrive laegger et SharePoint-
' bibliotek i "%USERPROFILE%\<Organisation>\<Site> - <Bibliotek>", og en
' genvej ("Tilfoej genvej til Mine filer") direkte i OneDrive-mappen.
' Findes praecis EEN, bruges den. Findes flere (DEV og PROD), spoerges der.
Public Function DetectFolder() As String
    Dim found As New Collection
    Dim oneDrive As String
    Dim orgName As String

    oneDrive = Environ$("OneDriveCommercial")
    If Len(oneDrive) = 0 Then oneDrive = Environ$("OneDrive")
    If Len(oneDrive) = 0 Then Exit Function

    orgName = Fso().GetFileName(StripSlash(oneDrive))
    If LCase$(Left$(orgName, 11)) = "onedrive - " Then
        orgName = Mid$(orgName, 12)
        CollectLibraries Environ$("USERPROFILE") & "\" & orgName, found
    End If
    CollectLibraries oneDrive, found

    If found.Count = 1 Then DetectFolder = found(1)
End Function

Private Sub CollectLibraries(ByVal parent As String, ByVal found As Collection)
    Dim f As Object
    Dim nm As String

    If Not Fso().FolderExists(parent) Then Exit Sub
    On Error Resume Next
    For Each f In Fso().GetFolder(parent).SubFolders
        nm = f.Name
        If StrComp(nm, FOLDER_LIBRARY, vbTextCompare) = 0 Or _
           LCase$(Right$(nm, Len(FOLDER_LIBRARY) + 3)) = LCase$(" - " & FOLDER_LIBRARY) Then
            found.Add f.Path
        End If
    Next f
    On Error GoTo 0
End Sub

' Undermapperne oprettes, hvis de mangler. I en synkroniseret mappe bliver
' de saa ogsaa oprettet i SharePoint.
Public Sub EnsureSubfolders(ByVal root As String)
    EnsureFolder OrdersFolder(root)
    EnsureFolder ReceiptsFolder(root)
    EnsureFolder DoneFolder(root)
End Sub

Public Function OrdersFolder(ByVal root As String) As String
    OrdersFolder = StripSlash(root) & "\" & FOLDER_ORDERS
End Function

Public Function ReceiptsFolder(ByVal root As String) As String
    ReceiptsFolder = StripSlash(root) & "\" & FOLDER_RECEIPTS
End Function

Public Function DoneFolder(ByVal root As String) As String
    DoneFolder = StripSlash(root) & "\" & FOLDER_DONE
End Function

Private Sub EnsureFolder(ByVal path As String)
    If Not Fso().FolderExists(path) Then Fso().CreateFolder path
End Sub

Private Function StripSlash(ByVal path As String) As String
    Do While Len(path) > 3 And (Right$(path, 1) = "\" Or Right$(path, 1) = "/")
        path = Left$(path, Len(path) - 1)
    Loop
    StripSlash = path
End Function

'==============================================================================
' Filerne
'==============================================================================

' Ordrefilerne i "Til oprettelse", sorteret efter navn. Status- og
' kvitteringsfiler og halvt skrevne .tmp-filer er ikke ordrer.
Public Function ListOrderFiles(ByVal root As String) As Collection
    Dim result As New Collection
    Dim names As New Collection
    Dim f As Object
    Dim nm As String
    Dim folder As String

    Set ListOrderFiles = result
    folder = OrdersFolder(root)
    If Not Fso().FolderExists(folder) Then Exit Function

    For Each f In Fso().GetFolder(folder).Files
        nm = f.Name
        If LCase$(Right$(nm, 5)) = ".json" Then
            If Not IsSidecar(nm) Then InsertSorted names, nm
        End If
    Next f

    Dim v As Variant
    For Each v In names
        result.Add folder & "\" & CStr(v)
    Next v
End Function

Private Function IsSidecar(ByVal nm As String) As Boolean
    nm = LCase$(nm)
    IsSidecar = (Right$(nm, Len(SUFFIX_STATUS)) = LCase$(SUFFIX_STATUS)) Or _
                (Right$(nm, Len(SUFFIX_RECEIPT)) = LCase$(SUFFIX_RECEIPT))
End Function

Private Sub InsertSorted(ByVal c As Collection, ByVal value As String)
    Dim i As Long
    For i = 1 To c.Count
        If StrComp(value, CStr(c(i)), vbTextCompare) < 0 Then
            c.Add value, Before:=i
            Exit Sub
        End If
    Next i
    c.Add value
End Sub

Public Function FileNameOf(ByVal path As String) As String
    FileNameOf = Fso().GetFileName(path)
End Function

' MP0133_20261002-084233.json -> MP0133_20261002-084233
Public Function BaseNameOf(ByVal path As String) As String
    Dim nm As String
    nm = FileNameOf(path)
    If LCase$(Right$(nm, 5)) = ".json" Then nm = Left$(nm, Len(nm) - 5)
    BaseNameOf = nm
End Function

Public Function StatusPathFor(ByVal orderPath As String) As String
    StatusPathFor = Fso().GetParentFolderName(orderPath) & "\" & BaseNameOf(orderPath) & SUFFIX_STATUS
End Function

Public Function ReceiptPathFor(ByVal root As String, ByVal orderPath As String) As String
    ReceiptPathFor = ReceiptsFolder(root) & "\" & BaseNameOf(orderPath) & SUFFIX_RECEIPT
End Function

Public Function FileExists(ByVal path As String) As Boolean
    FileExists = Fso().FileExists(path)
End Function

' Flyt ordren og dens statusfil til "Oprettet". Findes et navn i forvejen,
' faar den nye et tidsstempel bag paa - der slettes aldrig noget her.
Public Sub MoveToDone(ByVal root As String, ByVal orderPath As String)
    Dim statusPath As String
    statusPath = StatusPathFor(orderPath)
    MoveUnique orderPath, DoneFolder(root)
    If Fso().FileExists(statusPath) Then MoveUnique statusPath, DoneFolder(root)
End Sub

Private Sub MoveUnique(ByVal src As String, ByVal destFolder As String)
    Dim target As String
    target = destFolder & "\" & FileNameOf(src)
    If Fso().FileExists(target) Then
        target = destFolder & "\" & Format$(Now, "yyyymmdd-hhnnss") & "_" & FileNameOf(src)
    End If
    Fso().MoveFile src, target
End Sub

' Kopier en ordrefil (fx gemt fra mailen) ind i "Til oprettelse".
Public Function CopyIntoOrders(ByVal root As String, ByVal src As String) As String
    Dim target As String
    EnsureSubfolders root
    target = OrdersFolder(root) & "\" & FileNameOf(src)
    If StrComp(Fso().GetAbsolutePathName(src), Fso().GetAbsolutePathName(target), vbTextCompare) <> 0 Then
        Fso().CopyFile src, target, True
    End If
    CopyIntoOrders = target
End Function

'==============================================================================
' UTF-8
'==============================================================================

Public Function ReadUtf8(ByVal path As String) As String
    Dim st As Object
    Dim s As String

    Set st = CreateObject("ADODB.Stream")
    st.Type = 2                 ' tekst
    st.Charset = "utf-8"
    st.Open
    st.LoadFromFile path
    s = st.ReadText(-1)         ' alt
    st.Close

    If Len(s) > 0 Then
        If AscW(Left$(s, 1)) = &HFEFF Then s = Mid$(s, 2)
    End If
    ReadUtf8 = s
End Function

' UTF-8 UDEN byte order mark. Power Automates json() fejler paa et BOM i
' starten af teksten, og kvitteringen laeses af et flow.
'
' Der skrives til en .tmp-fil, som derefter flyttes paa plads. OneDrive
' synkroniserer saa aldrig en halvt skrevet fil.
Public Sub WriteUtf8(ByVal path As String, ByVal text As String)
    Dim st As Object
    Dim bin As Object
    Dim tmp As String

    tmp = path & ".tmp"

    Set st = CreateObject("ADODB.Stream")
    st.Type = 2
    st.Charset = "utf-8"
    st.Open
    st.WriteText text
    st.Position = 3             ' spring BOM'en over (3 bytes)

    Set bin = CreateObject("ADODB.Stream")
    bin.Type = 1                ' binaer
    bin.Open
    st.CopyTo bin
    bin.SaveToFile tmp, 2       ' overskriv
    bin.Close
    st.Close

    If Fso().FileExists(path) Then Fso().DeleteFile path, True
    Fso().MoveFile tmp, path
End Sub

'==============================================================================
' JSON
'==============================================================================

Public Function ReadJson(ByVal path As String) As Object
    Set ReadJson = JsonConverter.ParseJson(ReadUtf8(path))
End Function

Public Sub WriteJson(ByVal path As String, ByVal value As Object)
    WriteUtf8 path, JsonConverter.ConvertToJson(value, 2)
End Sub
