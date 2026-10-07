# -*- coding: utf-8 -*-
"""
Alt, der er Issue Boards eget (issue #114): navne, lister, kolonner og
ordforraadet. EET sted - skaermen (ib_parts.py), provisioneringen
(sharepoint/provision/Provision-IssueBoard.ps1) og flowet
(BioSap-IssueBoard-Submit) bruger de samme navne, og
tests/test_issue_board.py holder dem i trit.

ARKITEKTUREN (trin 1)
---------------------
    app ──Run("create"|"comment", JSON)──► BioSap-IssueBoard-Submit
                                            (flowejerens forbindelse)
        1. opretter raekken i IB_Tickets / IB_TicketComments
        2. bryder nedarvningen paa raekken og giver KUN
           rapportoeren Read og admins (UserAndGroups, Title = Admin) Contribute
        3. spejler en saneret kopi til IB_SharedIssues
        4. svarer appen - foerst nu kan rapportoeren se sagen

    IB_Tickets og IB_TicketComments har brudt nedarvning paa LISTEN, uden
    Members og Visitors. En raekke er derfor usynlig for alle andre end
    ejerne og flowets konto, fra den oprettes, til flowet har givet
    rapportoeren adgang - der er intet hul.

    Appen LAESER med brugerens egen forbindelse. Rettighederne paa raekken
    er sikringen; filtrene i appen er kun UX.

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
L_SHARED = "IB_SharedIssues"

# Kolonnerne, appen LAESER, pr. liste. Power Fx binder paa visningsnavnet;
# provisioneringen giver alle kolonner samme interne navn og visningsnavn,
# og Title beholder navnet Title. Testen tjekker, at hver kolonne her
# oprettes af provisioneringen.
COLS = {
    L_TICKETS: ["ID", "Title", "TicketNo", "Description", "ReproSteps", "ExpectedResult",
                "ActualResult", "Application", "Section", "OtherContext", "RelatedRequestNo",
                "Severity", "Priority", "Status", "Resolution", "AssignedToName",
                "ReporterEmail", "Created", "LastActivityOn", "IsArchived"],
    L_COMMENTS: ["TicketId", "AuthorEmail", "AuthorRole", "EventType", "Visibility",
                 "Content", "PreviousStatus", "NewStatus", "EventOn"],
    L_SECTIONS: ["Application", "Section", "AppOrder", "SectionOrder", "ScreenKey",
                 "IsActive"],
    L_SHARED: ["ID", "Title", "TicketNo", "Summary", "Application", "Section", "Status",
               "Severity", "Priority", "Resolution", "ReportedOn", "LastActivityOn",
               "IsArchived"],
}

# --- flowet ----------------------------------------------------------------
FLOW = "'BioSap-IssueBoard-Submit'"
ACT_CREATE = "create"
ACT_COMMENT = "comment"

# --- ordforraadet (valgene i SharePoint) ---------------------------------
# Livsforloebet: New -> Triaged -> In progress -> Ready for retest -> Closed,
# og Reopened, naar en lukket sag ikke er loest. Status kan gaa baglaens,
# saa skaermen viser et maerke, ikke en fremdriftsbjaelke. (Trin 2:
# admin-boardet flytter status; i trin 1 saetter flowet New.)
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
SEVERITY = ["Blocker", "Major", "Minor", "Cosmetic"]
SEVERITY_DEFAULT = "Minor"
# Prioriteten saetter admin (trin 2). Flowet starter alle paa Normal.
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
