# -*- coding: utf-8 -*-
"""
Flow-kontrakten for dokumenter. Navne og former staar KUN her.

MAALT, IKKE GAETTET
-------------------
De tre flows er laest i solution-eksporten
(solution/BIOSAP/src/Workflows/), og kaldene er kopieret fra den app, der
allerede bruger dem - "BioSap Maintenance Plans", skaermen
TaskListAndItemsForm. Hver konstruktion her er altsaa bevist i netop dette
miljoe, mod netop disse flows.

    BioSap-TaskListAttachment        text + file{name, contentBytes}
                                     -> CreateFile i
                                        /TaskListDocuments/<text>/<name>
                                     -> flowrunsuccess

    BioSap-GetSubmittedAttachments   text = MAPPESTI
                                     -> files: en STRENG med et JSON-array
                                        af { Name, Link, Identifier }

    BioSap-DeleteSubmittedAttachments  text = Identifier -> DeleteFile

TO FAELDER
----------
1. `text` betyder ikke det samme i de to foerste. Upload laegger selv
   "/TaskListDocuments/" foran; Get bruger vaerdien, som den er. Derfor
   FOLDER og FOLDER_PATH hver for sig nedenfor.

2. Get svarer med en STRENG, ikke en tabel. Den skal gennem ParseJSON -
   samme moenster som FL-soegningen.

MAPPEN ER ITEMETS
-----------------
Eet dokument hoerer til eet item, saa mappen hedder itemets noegle
(MI0007). Noeglen findes foerst, naar planen er gemt - derfor kan der ikke
laegges dokumenter op paa en plan, der kun staar i appen. Knappen siger det
selv i stedet for at fejle.

Filnavnet er noeglen paa raekken. SharePoint tillader ikke to filer med
samme navn i samme mappe, saa navnet er unikt, stabilt og kendt af begge
sider - i modsaetning til et lobenummer, appen selv skulle finde paa og
holde styr paa hen over en opdatering.
"""

FLOW_UPLOAD = "'BioSap-TaskListAttachment'"
FLOW_LIST = "'BioSap-GetSubmittedAttachments'"
FLOW_DELETE = "'BioSap-DeleteSubmittedAttachments'"

LIBRARY = "TaskListDocuments"

PICKER = "attVhpAttPicker"

# Itemets noegle - tom, indtil planen er gemt.
FOLDER = 'LookUp(colVhpSavedItems, LocalId = varVhpActiveItemId).ItemKey'
FOLDER_PATH = f'"{LIBRARY}/" & {FOLDER}'

NOT_SAVED = ('Save the plan before attaching documents - the folder is '
             'named after the item.')


def refresh_fx(indent=0):
    """Hent mappens indhold og laeg det i colVhpAttachments.

    Operationskoblingen (OperationsKey) findes kun i appen, ikke i
    biblioteket. Den reddes derfor over i colVhpAttKeep FOER raekkerne
    skiftes ud, og saettes tilbage paa de filer, der stadig er der."""
    pad = " " * indent
    return "\n".join(pad + l for l in (
        "ClearCollect(",
        "    colVhpAttKeep,",
        "    ForAll(",
        "        Filter(colVhpAttachments, ItemId = varVhpActiveItemId) As A,",
        "        { FileName: A.FileName, OperationsKey: A.OperationsKey }",
        "    )",
        ");",
        "Set(",
        "    varVhpAttJson,",
        f"    {FLOW_LIST}.Run({FOLDER_PATH}).files",
        ");",
        "ClearCollect(",
        "    colVhpAttFiles,",
        "    ForAll(",
        "        ParseJSON(varVhpAttJson),",
        "        {",
        "            Name: Text(ThisRecord.Name),",
        "            Link: Text(ThisRecord.Link),",
        "            Identifier: Text(ThisRecord.Identifier)",
        "        }",
        "    )",
        ");",
        "RemoveIf(colVhpAttachments, ItemId = varVhpActiveItemId);",
        "Collect(",
        "    colVhpAttachments,",
        "    ForAll(",
        "        colVhpAttFiles As F,",
        "        {",
        "            ItemId: varVhpActiveItemId,",
        "            FileName: F.Name,",
        "            FileUrl: F.Link,",
        "            Identifier: F.Identifier,",
        "            FileSize: 0,",
        "            OperationsKey: Coalesce(",
        "                LookUp(colVhpAttKeep, FileName = F.Name).OperationsKey,",
        "                \";\"",
        "            ),",
        "            Status: \"Uploaded\",",
        "            Selected: false",
        "        }",
        "    )",
        ");",
        "Clear(colVhpAttKeep)",
    ))


def upload_fx():
    """Send hver valgt fil gennem flowet, og hent listen forfra bagefter.

    ForAll over kontrollens Attachments - Name og Value er kolonnerne, og
    Value ER indholdet. Det er kaldet fra den gamle app, ordret."""
    return (
        "If(\n"
        f"    IsBlank({FOLDER}),\n"
        f"    Notify(\"{NOT_SAVED}\", NotificationType.Warning),\n"
        "\n"
        f"    If(\n"
        f"        CountRows({PICKER}.Attachments) = 0,\n"
        "        Notify(\"Choose one or more files first.\", NotificationType.Warning),\n"
        "\n"
        "        ForAll(\n"
        f"            {PICKER}.Attachments,\n"
        f"            {FLOW_UPLOAD}.Run(\n"
        f"                {FOLDER},\n"
        "                { file: { contentBytes: Value, name: Name } }\n"
        "            )\n"
        "        );\n"
        f"        Reset({PICKER});\n"
        "\n"
        + refresh_fx(8) + ";\n"
        "\n"
        "        Notify(\"Document(s) uploaded.\", NotificationType.Success)\n"
        "    )\n"
        ")"
    )


def refresh_button_fx():
    return (
        "If(\n"
        f"    IsBlank({FOLDER}),\n"
        f"    Notify(\"{NOT_SAVED}\", NotificationType.Warning),\n"
        "\n"
        + refresh_fx(4) + "\n"
        ")"
    )


def delete_fx():
    """Slet de markerede - i biblioteket, ikke kun i appen.

    Identifier kommer fra Get-flowet. Er den tom, findes filen ikke i
    biblioteket endnu, og saa er der kun appens egen raekke at fjerne."""
    return (
        "If(\n"
        "    CountRows(Filter(colVhpAttachments, ItemId = varVhpActiveItemId, "
        "Selected = true)) = 0,\n"
        "    Notify(\"Select one or more documents first.\", NotificationType.Warning),\n"
        "\n"
        "    ForAll(\n"
        "        Filter(colVhpAttachments, ItemId = varVhpActiveItemId, "
        "Selected = true) As D,\n"
        "        If(\n"
        "            !IsBlank(D.Identifier),\n"
        f"            {FLOW_DELETE}.Run(D.Identifier)\n"
        "        )\n"
        "    );\n"
        "    RemoveIf(colVhpAttachments, ItemId = varVhpActiveItemId, Selected = true);\n"
        "    Notify(\"Document(s) removed.\", NotificationType.Success)\n"
        ")"
    )
