# -*- coding: utf-8 -*-
"""
FLOWKONTRAKTEN FOR DOKUMENTER - den eneste kilde.

HVORFOR DEN HER FIL FINDES
--------------------------
Kontrakten stod TO steder: her og i "Maintenance Plan App/build/
build_attflows.py". De to filer havde de samme fjorten navne, de samme
tre flowkald og de samme fire knapformler - men de var IKKE ordrette ens,
saa ingen vagt kunne se dem som kopier.

Det er praecis den fejlklasse, der ramte build_flsearch.py: to udgaver af
den samme kontrakt mod de samme tre flows. Rettes et flow i Azure - et
felt skifter navn, et svar skifter form - skal begge filer med. Den ene
bliver glemt, og den app fejler foerst, naar en bruger trykker paa
knappen.

Nu staar flowkaldene her. Hver app leverer kun det, DENS egen samling
hedder og gemmer - og netop det er reelt forskelligt (se PANE nedenfor).

MAALT, IKKE GAETTET
-------------------
De tre flows er laest i solution-eksporten
(solution/BIOSAP/src/Workflows/), og kaldene er kopieret fra den app, der
allerede brugte dem - "BioSap Maintenance Plans", skaermen
TaskListAndItemsForm. Hver konstruktion her er altsaa bevist i netop
dette miljoe, mod netop disse flows.

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
   staar `folder` og `folder_path` hver for sig nedenfor.

2. Get svarer med en STRENG, ikke en tabel. Den skal gennem ParseJSON -
   samme moenster som FL-soegningen.

ET BIBLIOTEK, FIRE APPS
-----------------------
De tre flows er HAARDKODEDE til biblioteket TaskListDocuments. Et
bibliotek pr. domaene ville kraeve tre nye flows pr. domaene - ni i alt -
for at goere praecis det samme. Apperne deler i stedet biblioteket og
holdes fra hinanden paa MAPPENAVNET, som er postens noegle: MI0007,
EQ-000912-010, MAT-001233-020. Navnet er unikt paa tvaers af domaener,
fordi praefikset er det.

Prisen er, at biblioteket hedder TaskListDocuments, selv om det nu ogsaa
rummer udstyr og materialer. Det er et navn, ikke en fejl.

MAPPEN ER RAEKKENS
------------------
Noeglen findes foerst, naar raekken er skrevet i SharePoint - den er lavet
af raekkens eget ID. Derfor kan der ikke laegges dokumenter op paa en
raekke, der kun staar i formularen. Knappen siger det selv i stedet for at
fejle.

Filnavnet er noeglen paa raekken. SharePoint tillader ikke to filer med
samme navn i samme mappe, saa navnet er unikt, stabilt og kendt af begge
sider - i modsaetning til et loebenummer, appen selv skulle finde paa.
"""

FLOW_UPLOAD = "'BioSap-TaskListAttachment'"
FLOW_LIST = "'BioSap-GetSubmittedAttachments'"
FLOW_DELETE = "'BioSap-DeleteSubmittedAttachments'"

LIBRARY = "TaskListDocuments"


class Pane(object):
    """En dokumentrude.

    Flowkaldene staar her. Underklassen leverer de seks navne, der er
    forskellige fra app til app, og sin EGEN refresh_fx() - den er den
    ene, hvor de to apper faktisk goer noget forskelligt:

        VH-plan   redder OperationsKey over, foer raekkerne skiftes ud;
                  koblingen findes kun i appen, ikke i biblioteket.
        Domaene   skriver antallet tilbage i BAADE SharePoint-listen og
                  colDomRows, saa raekkeoversigten kan vise det uden et
                  opslag pr. raekke.

    Det er forretningsforskelle, ikke stilforskelle, og de skal blive ved
    at vaere synlige hver for sig. Alt det, der ER ens, staar her."""

    picker = None          # navnet paa Attachments-kontrollen
    folder = None          # udtryk: mappenavnet = raekkens noegle
    key_pred = None        # udtryk: "RowId = varDomDocsId"
    collection = None      # samlingen med rudens filer
    up_collection = None   # arbejdssamling til uploadsvarene
    not_saved = None       # beskeden, naar raekken ikke er gemt endnu
    empty_pre = None       # teksten foer stien, naar mappen er tom
    empty_post = None      # og efter

    # -- afledte udtryk ---------------------------------------------------
    @property
    def folder_path(self):
        return '"%s/" & %s' % (LIBRARY, self.folder)

    @property
    def scope(self):
        """Raekkens egne filer i samlingen."""
        return "Filter(%s, %s)" % (self.collection, self.key_pred)

    @property
    def selected(self):
        return "Filter(%s, %s, Selected = true)" % (self.collection,
                                                    self.key_pred)

    def refresh_fx(self, indent=0):
        raise NotImplementedError

    # -- de fire knapformler ----------------------------------------------
    def upload_fx(self):
        """Send hver valgt fil gennem flowet, og hent listen forfra bagefter.

        ForAll over kontrollens Attachments - Name og Value er kolonnerne,
        og Value ER indholdet. Det er kaldet fra den gamle app, ordret.

        ForAll returnerer en TABEL, og ClearCollect tager den i EET kald.
        Her stod foer et Collect INDE i ForAll - een mutation pr. fil, som
        App checker melder som ForAllWithMutation. Flowet koerer stadig een
        gang pr. fil; det er kun skrivningen, der er samlet.

        Svaret bliver LAEST. Der stod foer et fast "Document(s) uploaded."
        lige efter ForAll, uanset hvad flowet svarede - en kvittering,
        appen selv fandt paa. flowrunsuccess samles nu pr. fil, og de
        filer, der ikke kom igennem, staar med navn i beskeden."""
        return (
            "If(\n"
            f"    IsBlank({self.folder}),\n"
            f"    Notify(\"{self.not_saved}\", NotificationType.Warning),\n"
            "\n"
            "    If(\n"
            f"        CountRows({self.picker}.Attachments) = 0,\n"
            "        Notify(\"Choose one or more files first.\", "
            "NotificationType.Warning),\n"
            "\n"
            "        ClearCollect(\n"
            f"            {self.up_collection},\n"
            "            ForAll(\n"
            f"                {self.picker}.Attachments As F,\n"
            "                {\n"
            "                    Name: F.Name,\n"
            "                    Ok: IfError(\n"
            "                        Lower(\n"
            "                            Text(\n"
            f"                                {FLOW_UPLOAD}.Run(\n"
            f"                                    {self.folder},\n"
            "                                    { file: { contentBytes: F.Value, "
            "name: F.Name } }\n"
            "                                ).flowrunsuccess\n"
            "                            )\n"
            "                        ) = \"true\",\n"
            "                        false\n"
            "                    )\n"
            "                }\n"
            "            )\n"
            "        );\n"
            f"        Reset({self.picker});\n"
            "\n"
            + self.refresh_fx(8) + ";\n"
            "\n"
            "        If(\n"
            f"            CountRows(Filter({self.up_collection}, Ok = false)) > 0,\n"
            "            Notify(\n"
            "                \"SharePoint refused: \" &\n"
            f"                Concat(Filter({self.up_collection}, Ok = false), "
            "Name, \", \"),\n"
            "                NotificationType.Error\n"
            "            ),\n"
            "            Notify(\"Document(s) uploaded.\", NotificationType.Success)\n"
            "        )\n"
            "    )\n"
            ")"
        )

    def refresh_button_fx(self):
        return (
            "If(\n"
            f"    IsBlank({self.folder}),\n"
            f"    Notify(\"{self.not_saved}\", NotificationType.Warning),\n"
            "\n"
            + self.refresh_fx(4) + "\n"
            ")"
        )

    def delete_fx(self):
        """Slet de markerede - i biblioteket, ikke kun i appen.

        Identifier kommer fra Get-flowet. Er den tom, findes filen ikke i
        biblioteket, og saa er der kun appens egen raekke at fjerne."""
        return (
            "If(\n"
            f"    CountRows({self.selected}) = 0,\n"
            "    Notify(\"Select one or more documents first.\", "
            "NotificationType.Warning),\n"
            "\n"
            "    ForAll(\n"
            f"        {self.selected} As D,\n"
            "        If(\n"
            "            !IsBlank(D.Identifier),\n"
            f"            {FLOW_DELETE}.Run(D.Identifier)\n"
            "        )\n"
            "    );\n"
            f"    RemoveIf({self.collection}, {self.key_pred}, Selected = true);\n"
            "    Notify(\"Document(s) removed.\", NotificationType.Success)\n"
            ")"
        )

    def empty_text_fx(self):
        """Teksten, naar der ingen raekker er.

        Get-flowet svarer files: "[]" BAADE naar mappen ikke findes og naar
        den er tom - de to kan ikke skelnes fra appen. Derfor staar stien i
        beskeden, saa den kan holdes op mod, hvad der rent faktisk ligger i
        biblioteket."""
        return (
            "If(\n"
            f"    IsBlank({self.folder}),\n"
            f"    \"{self.not_saved}\",\n"
            f"    \"{self.empty_pre}\" & {self.folder_path} & \"{self.empty_post}\"\n"
            ")"
        )


class DomainPane(Pane):
    """Equipment og Material. Ruden haenger paa den raekke, POPUPPEN er
    aabnet for - ikke paa den, der ligger i formularen.

    Det var varDomActiveRowId indtil dokumentruden blev en popup. De to er
    ikke det samme: man skal kunne se dokumenterne paa en raekke uden
    foerst at laese den ind i formularen og dermed smide det, man var i
    gang med at skrive. Blank betyder "popuppen er lukket"."""

    picker = "attDomPicker"
    folder = 'LookUp(colDomRows, RowId = varDomDocsId).ItemKey'
    key_pred = "RowId = varDomDocsId"
    collection = "colDomAttachments"
    up_collection = "colDomAttUp"
    not_saved = "Save the row first - the folder is named after the row key."
    empty_pre = "No documents in "
    empty_post = " yet."

    def refresh_fx(self, indent=0):
        """Hent mappens indhold og laeg det i colDomAttachments.

        ParseJSON faar Coalesce(..., "[]"): svarer flowet ingenting, skal
        resten af kaeden stadig koere. Uden den river en tom vaerdi hele
        knappen med sig, og brugeren ser ingenting - hverken filer eller
        fejl.

        Importen ligger inde i metoden med vilje: domain_config findes kun
        i de to domaeneapper, og VH-plan importerer den samme modul."""
        import domain_config as cfg
        pad = " " * indent
        return "\n".join(pad + l for l in (
            "Set(",
            "    varDomAttJson,",
            f"    {FLOW_LIST}.Run({self.folder_path}).files",
            ");",
            f"RemoveIf({self.collection}, {self.key_pred});",
            "Collect(",
            f"    {self.collection},",
            "    ForAll(",
            "        ParseJSON(Coalesce(varDomAttJson, \"[]\")) As J,",
            "        {",
            "            RowId: varDomDocsId,",
            "            FileName: Text(J.Name),",
            "            FileUrl: Text(J.Link),",
            "            Identifier: Text(J.Identifier),",
            "            Selected: false",
            "        }",
            "    )",
            ");",
            # Antallet skrives tilbage BEGGE steder: i listen, saa den kan
            # laeses i browseren, og i samlingen, saa raekkeoversigten viser
            # det uden et opslag pr. raekke.
            "With(",
            f"    {{ n: CountRows({self.scope}) }},",
            "    Patch(",
            f"        {cfg.L_ROWS},",
            f"        LookUp({cfg.L_ROWS}, ID = varDomDocsId),",
            "        { FileCount: n }",
            "    );",
            "    UpdateIf(",
            "        colDomRows,",
            "        RowId = varDomDocsId,",
            "        { FileCount: n }",
            "    )",
            ")",
        ))
