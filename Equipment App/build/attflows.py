# -*- coding: utf-8 -*-
"""
Dokumentruden. Samme tre flows som VH-plan-appen - intet nyt bygges.

HVORFOR DE SAMME FLOWS OG DET SAMME BIBLIOTEK
---------------------------------------------
De tre flows er laest i solution-eksporten
(solution/BIOSAP/src/Workflows/), og de er HAARDKODEDE til biblioteket
TaskListDocuments:

    BioSap-TaskListAttachment        CreateFile i /TaskListDocuments/<text>/
                                     text = MAPPENAVN
                                     -> flowrunsuccess

    BioSap-GetSubmittedAttachments   text = MAPPESTI ("TaskListDocuments/...")
                                     -> files: en STRENG med et JSON-array
                                        af { Name, Link, Identifier }

    BioSap-DeleteSubmittedAttachments  text = Identifier -> DeleteFile

Upload-flowet skriver "/TaskListDocuments/" foran selv; get-flowet bruger
vaerdien, som den er. Derfor FOLDER og FOLDER_PATH hver for sig.

Et nyt bibliotek pr. domaene ville kraeve tre nye flows pr. domaene - ni i
alt - for at goere praecis det samme. De tre apps deler i stedet
biblioteket og holdes fra hinanden paa MAPPENAVNET, som er postens
noegle: MI0007, EQ-000912-010, MAT-001233-020. Navnet er unikt paa tvaers
af domaener, fordi praefikset er det.

Prisen er, at biblioteket hedder TaskListDocuments, selv om det nu ogsaa
rummer udstyr og materialer. Det er et navn, ikke en fejl.

MAPPEN ER POSTENS
-----------------
Noeglen findes foerst, naar indmeldingen er gemt - derfor kan der ikke
laegges dokumenter op paa en post, der kun staar i appen. Knappen siger
det selv i stedet for at fejle.

Filnavnet er noeglen paa raekken. SharePoint tillader ikke to filer med
samme navn i samme mappe, saa navnet er unikt, stabilt og kendt af begge
sider - i modsaetning til et loebenummer, appen selv skulle finde paa.
"""

FLOW_UPLOAD = "'BioSap-TaskListAttachment'"
FLOW_LIST = "'BioSap-GetSubmittedAttachments'"
FLOW_DELETE = "'BioSap-DeleteSubmittedAttachments'"

LIBRARY = "TaskListDocuments"

PICKER = "attDomPicker"

# Postens noegle - tom, indtil indmeldingen er gemt.
FOLDER = 'LookUp(colDomItems, LocalId = varDomActiveItemId).ItemKey'
FOLDER_PATH = f'"{LIBRARY}/" & {FOLDER}'

ACTIVE = "Filter(colDomAttachments, LocalId = varDomActiveItemId)"

NOT_SAVED = ('Save the request before attaching documents - the folder is '
             'named after the item.')


def refresh_fx(indent=0):
    """Hent mappens indhold og laeg det i colDomAttachments.

    ParseJSON faar Coalesce(..., "[]"): svarer flowet ingenting, skal
    resten af kaeden stadig koere. Uden den river en tom vaerdi hele
    knappen med sig, og brugeren ser ingenting - hverken filer eller fejl.
    """
    pad = " " * indent
    return "\n".join(pad + l for l in (
        "Set(",
        "    varDomAttJson,",
        f"    {FLOW_LIST}.Run({FOLDER_PATH}).files",
        ");",
        "RemoveIf(colDomAttachments, LocalId = varDomActiveItemId);",
        "Collect(",
        "    colDomAttachments,",
        "    ForAll(",
        "        ParseJSON(Coalesce(varDomAttJson, \"[]\")) As J,",
        "        {",
        "            LocalId: varDomActiveItemId,",
        "            FileName: Text(J.Name),",
        "            FileUrl: Text(J.Link),",
        "            Identifier: Text(J.Identifier),",
        "            Selected: false",
        "        }",
        "    )",
        ")",
    ))


def upload_fx():
    """Send hver valgt fil gennem flowet, og hent listen forfra bagefter.

    Svaret bliver LAEST. VH-plan-appen kvitterede foerst med et fast
    "Document(s) uploaded." lige efter ForAll, uanset hvad flowet sagde -
    en kvittering, appen selv fandt paa. Den fejl gentages ikke her:
    flowrunsuccess samles pr. fil, og de filer, der ikke kom igennem,
    staar med navn i beskeden."""
    return (
        "If(\n"
        f"    IsBlank({FOLDER}),\n"
        f"    Notify(\"{NOT_SAVED}\", NotificationType.Warning),\n"
        "\n"
        f"    If(\n"
        f"        CountRows({PICKER}.Attachments) = 0,\n"
        "        Notify(\"Choose one or more files first.\", NotificationType.Warning),\n"
        "\n"
        "        Clear(colDomAttUp);\n"
        "        ForAll(\n"
        f"            {PICKER}.Attachments As F,\n"
        "            Collect(\n"
        "                colDomAttUp,\n"
        "                {\n"
        "                    Name: F.Name,\n"
        "                    Ok: IfError(\n"
        "                        Lower(\n"
        "                            Text(\n"
        f"                                {FLOW_UPLOAD}.Run(\n"
        f"                                    {FOLDER},\n"
        "                                    { file: { contentBytes: F.Value, name: F.Name } }\n"
        "                                ).flowrunsuccess\n"
        "                            )\n"
        "                        ) = \"true\",\n"
        "                        false\n"
        "                    )\n"
        "                }\n"
        "            )\n"
        "        );\n"
        f"        Reset({PICKER});\n"
        "\n"
        + refresh_fx(8) + ";\n"
        "\n"
        "        If(\n"
        "            CountRows(Filter(colDomAttUp, Ok = false)) > 0,\n"
        "            Notify(\n"
        "                \"SharePoint refused: \" &\n"
        "                Concat(Filter(colDomAttUp, Ok = false), Name, \", \"),\n"
        "                NotificationType.Error\n"
        "            ),\n"
        "            Notify(\"Document(s) uploaded.\", NotificationType.Success)\n"
        "        )\n"
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
    biblioteket, og saa er der kun appens egen raekke at fjerne."""
    return (
        "If(\n"
        f"    CountRows(Filter(colDomAttachments, LocalId = varDomActiveItemId, "
        "Selected = true)) = 0,\n"
        "    Notify(\"Select one or more documents first.\", NotificationType.Warning),\n"
        "\n"
        "    ForAll(\n"
        "        Filter(colDomAttachments, LocalId = varDomActiveItemId, "
        "Selected = true) As D,\n"
        "        If(\n"
        "            !IsBlank(D.Identifier),\n"
        f"            {FLOW_DELETE}.Run(D.Identifier)\n"
        "        )\n"
        "    );\n"
        "    RemoveIf(colDomAttachments, LocalId = varDomActiveItemId, Selected = true);\n"
        "    Notify(\"Document(s) removed.\", NotificationType.Success)\n"
        ")"
    )


def empty_text_fx():
    """Teksten, naar der ingen raekker er.

    Get-flowet svarer files: "[]" BAADE naar mappen ikke findes og naar
    den er tom - de to kan ikke skelnes fra appen. Derfor staar stien i
    beskeden, saa den kan holdes op mod biblioteket."""
    return (
        "If(\n"
        f"    IsBlank({FOLDER}),\n"
        f"    \"{NOT_SAVED}\",\n"
        f"    \"No documents in \" & {FOLDER_PATH} & \" yet.\"\n"
        ")"
    )
