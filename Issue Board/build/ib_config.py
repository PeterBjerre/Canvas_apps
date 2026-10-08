# -*- coding: utf-8 -*-
"""
Alt, der er Issue Boards eget (issue #114): navne, lister, kolonner og
ordforraadet. EET sted - skaermen (ib_parts.py), provisioneringen
(sharepoint/provision/Provision-IssueBoard.ps1) og flowet
(BioSap-IssueBoard-Submit) bruger de samme navne, og
tests/test_issue_board.py holder dem i trit.

ARKITEKTUREN (issue #193 - foer: trin 1 og 2 i issue #114)
-----------------------------------------------------------
    app ──Patch──► IB_Tickets            brugerens egen forbindelse
        ny sag     opretter raekken (Defaults); Created By er brugeren
        edit       retter raekken; bagefter Run("edit", prev) - se under

    IB_Tickets ──"When an item is created"──► BioSap-IssueBoard-OnCreated
                                            (servicekontoens forbindelser)
        1. TicketNo = ISS-000000 ud fra ID, ReporterEmail/-Name ud fra
           Created By, Status New, Priority Normal - ogsaa hvis en
           bruger har oprettet raekken direkte i SharePoint
        2. mail til admins og til rapportoeren (afsender: servicekontoen)

    app ──Run(handling, JSON)──► BioSap-IssueBoard-Submit
        comment  skriver kommentaren i IB_TicketComments og giver KUN
                 rapportoeren Read (ikke ved Internal) og admins
                 (UserAndGroups, Title = Admin) Contribute paa raekken.
        edit     appen har rettet sagen; flowet sammenligner raekken med
                 vaerdierne foer (prev) og skriver een haendelse pr.
                 aendring, stempler ResolvedOn/ClosedOn og sender mailen
                 ved Ready for retest/Closed.
        reopen   rapportoeren (eller en admin) genaabner en lukket sag
                 eller en sag, der er klar til gentest.
        archive  kun admin: arkiver eller gendan.
        delete   kun admin, og kun med sagsnummeret som bekraeftelse:
                 sletter haendelserne og sagen med dens vedhaeftninger.
        attach   en fil paa sagens raekke (SharePoint-vedhaeftning) og en
                 Attachment-haendelse i Activity. Kun rapportoeren og
                 admins. Appen kalder den fra fanen Attachments - og
                 papirclipsen paa flisen aabner sagen paa den fane.

RETTIGHEDER (sharepoint/provision/Provision-IssueBoard.ps1)
-----------------------------------------------------------
    IB_Tickets          Members Contribute, Read all items, Edit own items;
                        admins Design (retter alle). Ingen anonymisering:
                        alle ser alle sager med rapportoerens navn, og
                        vedhaeftningerne arver listen.
    IB_TicketComments   privat liste; rettigheder paa hver raekke (flowet):
                        kun sagens rapportoer og admins kan laese en sags
                        kommentarer - det haandhaever SharePoint.

    SharePoint haandhaever HVEM der retter en sag, ikke HVILKE felter: at
    kun admins flytter status, prioritet og tildeling, og at rapportoeren
    kun retter, mens sagen er New, er appens regel (knapperne IbCan* og
    SAVE_EDIT, der laeser raekken igen foer Patch). Nummeret og
    rapportoeren rettes af OnCreated-flowet paa serveren.

Mail (Outlook, samme forbindelse som de andre BIO SAP-flows): ny sag til
admins og rapportoeren (OnCreated); til rapportoeren, naar en admin
svarer synligt, og naar sagen er klar til gentest eller lukket (Submit).

FEATURE-FLAGET
--------------
tools/canvas_apps.json, environments.<miljoe>.features.issue_board. Er det
ikke slaaet til, bygges skaermen slet ikke (tools/env_config.py).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# --- appen ------------------------------------------------------------
APP_KEY = "issueboard"
SCREEN = "ScreenIssueBoard"
TITLE = "Issue Board"
FEATURE = "issue_board"

# --- listerne (Provision-IssueBoard.ps1) --------------------------------
L_TICKETS = "IB_Tickets"
L_COMMENTS = "IB_TicketComments"
L_SECTIONS = "IB_AppSections"

# Kolonnerne, appen LAESER, pr. liste. Power Fx binder paa visningsnavnet;
# provisioneringen giver alle kolonner samme interne navn og visningsnavn,
# og Title beholder navnet Title. Testen tjekker, at hver kolonne her
# oprettes af provisioneringen.
COLS = {
    L_TICKETS: ["ID", "Title", "TicketNo", "Description", "ReproSteps", "ExpectedResult",
                "ActualResult", "Application", "Section", "OtherContext", "RelatedRequestNo",
                "Severity", "Priority", "Status", "Resolution", "AssignedToName",
                "ReporterEmail", "ReporterName", "AssignedToEmail", "Created", "LastActivityOn",
                "IsArchived", "Attachments"],
    L_COMMENTS: ["TicketId", "AuthorEmail", "AuthorRole", "EventType", "Visibility",
                 "Content", "PreviousStatus", "NewStatus", "EventOn", "FileName", "FileSizeKb",
                 "AtSubmission"],
    L_SECTIONS: ["Application", "Section", "AppOrder", "SectionOrder", "ScreenKey",
                 "IsActive"],
}

# --- flowet ----------------------------------------------------------------
FLOW = "'BioSap-IssueBoard-Submit'"
# Nummer og mail ved en ny sag - udloeses af SharePoint, kaldes ikke af appen.
FLOW_ON_CREATED = "BioSap-IssueBoard-OnCreated"
ACT_COMMENT = "comment"
ACT_EDIT = "edit"
ACT_REOPEN = "reopen"
ACT_ARCHIVE = "archive"
ACT_DELETE = "delete"
ACT_ATTACH = "attach"

# --- ordforraadet (valgene i SharePoint) ---------------------------------
# Livsforloebet: New -> Triaged -> In progress -> Ready for retest -> Closed,
# og Reopened, naar en lukket sag ikke er loest. Status kan gaa baglaens,
# saa skaermen viser et maerke, ikke en fremdriftsbjaelke. Flowet saetter
# New (OnCreated-flowet); admin flytter status i Edit; rapportoeren genaabner med Reopen.
#
# (vaerdi, farvetoken-par, rang til sortering)
STATUS = [
    ("New", "info", 1),
    ("Reopened", "rose", 2),
    ("Triaged", "violet", 3),
    ("In progress", "warn", 4),
    ("Ready for retest", "lime", 5),
    ("Closed", "ok", 6),
]
STATUS_NEW = "New"
STATUS_CLOSED = "Closed"
STATUS_RETEST = "Ready for retest"
STATUS_REOPENED = "Reopened"
# Rapportoeren maa rette sin sag, saa laenge den har denne status.
STATUS_EDITABLE = STATUS_NEW
# Herfra kan sagen genaabnes.
REOPENABLE = [STATUS_CLOSED, STATUS_RETEST]
SEVERITY = ["Blocker", "Major", "Minor", "Cosmetic"]
SEVERITY_DEFAULT = "Minor"
# Prioriteten saetter admin i Edit. Alle starter paa Normal.
PRIORITY = [("Urgent", 1), ("High", 2), ("Normal", 3), ("Low", 4)]
PRIORITY_DEFAULT = "Normal"
EVENT_TYPES = ["Comment", "StatusChange", "Assignment", "PriorityChange", "Attachment",
               "Reopened", "Closed", "Archived", "System"]
AUTHOR_ROLES = ["Reporter", "Admin", "System"]
# Reporter = rapportoeren og admins kan se den. Internal = kun admins.
VISIBILITY = ["Reporter", "Internal"]

# "Other" i Application eller Section kraever en beskrivelse.
OTHER = "Other"

# Konfigurationen seedes herfra.
SEED_CSV = os.path.join(ROOT, "sharepoint", "seed", "IB_AppSections.csv")

# Hoejst saa mange raekker hentes pr. liste - appens datagraense (Studio:
# Settings -> Data row limit). Sorteret nyeste foerst, saa det er de
# aeldste, der falder ud.
ROW_LIMIT = 500

# Vedhaeftninger: samme loft som dokumentruden (tools/domain_parts.py) - og
# flowet afviser over 10 MB.
MAX_FILE_MB = 10
MAX_FILES = 5
IMAGE_EXT = ["png", "jpg", "jpeg", "gif", "bmp", "webp"]
