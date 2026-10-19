# -*- coding: utf-8 -*-
"""
VEDHAEFTNINGSKONTRAKTEN - den eneste kilde (issue #300).

HVAD DER STOD FOER
------------------
Hver fil gik gennem tre Power Automate-flows til dokumentbiblioteket
TaskListDocuments (BioSap-TaskListAttachment, -GetSubmittedAttachments,
-DeleteSubmittedAttachments), og Issue Board sendte filerne gennem
BioSap-IssueBoard-Submit (handlingen attach). Knappen loeb
ForAll(<kontrol>.Attachments As F, ... F.Name ... F.Value) - og det
kompilerede ikke: kontrollen stod med Items = Blank(), saa dens
Attachments-output havde intet skema ("'Name' isn't recognized",
issue #300).

HVAD DER STAAR NU
-----------------
Peter (2026-10-17): "Jeg vil bevare modern attachments. Men ikke bruge
power automate til dokumenterne men direkte patch fra attachments
kontrollen."

Filerne er SharePoint-VEDHAEFTNINGER PAA LISTERAEKKEN - MS Learn,
"Attachments modern control", afsnittet "SharePoint attachments":

    Items     = <raekke>.Attachments
                Kontrollen viser selv de gemte filer, aabner/henter dem,
                og en fjernet fil er "markeret til fjernelse", til der
                gemmes. Raekken hentes med LookUp paa ID (delegerbart)
                og staar i en variabel (row_var).

    Gem       = Patch(<liste>, <raekke>, { Attachments: <kontrol>.Attachments })
                i EET kald - nye filer laegges paa, fjernede slettes.
                Svaret laegges i <row_var>Saved. Lykkes det, hentes raekken igen (saa Items viser det,
                der nu ligger i SharePoint), og kontrollen nulstilles.
                Fejler det, staar FirstError.Message i beskeden, og de
                valgte filer bliver staaende, saa man kan proeve igen.

Ingen flows, intet galleri over gemte filer, ingen Open/Remove pr.
raekke og ingen Refresh - kontrollen goer det selv.

    Equipment / Material   raekken i EquipmentItems / MaterialItems
    VH-plan                operationens raekke i TaskListMain
    Issue Board            sagens raekke i IB_Tickets (ib_parts.py)
    Measuring Point        ingen dokumenter (Peter, issue #300)

SharePoint er kun mellemlager: VH-planens filer skal senere videre til
blob storage/SAP DMS, FL-, materiale- og udstyrsfilerne til TekDoc.

RAEKKEN SKAL VAERE GEMT
-----------------------
En vedhaeftning boer paa en raekke, der findes i SharePoint. Er raekken
ikke gemt endnu, er row_var Blank, kontrollen er spaerret, og gem-knappen
siger det (not_saved) i stedet for at fejle.

DET GAMLE BIBLIOTEK
-------------------
Filer, der allerede ligger i TaskListDocuments, flyttes ikke og vises
ikke laengere i appen. LIBRARY staar her kun, fordi en ny domaeneraekke
stadig faar kolonnen AttachmentFolder skrevet (som foer).
"""

LIBRARY = "TaskListDocuments"


def save_fx(data_source, row, picker, busy_var, result_var, reload_fx, on_ok="",
            extra_fields="", not_saved=None):
    """Gem-knappens formel: EEN Patch af raekkens Attachments.

    row        raekken, der patches (en variabel eller et LookUp)
    result_var variablen, Patch'ens svar laegges i - None, naar svaret
               ikke bruges (App checker: UnusedVariables)
    reload_fx  hvad der skal ske bagefter - typisk at hente raekken igen,
               saa kontrollens Items viser det, der nu er gemt
    on_ok      det, appen ellers vil goere med svaret (fx taelle filerne)
    extra_fields  flere felter i SAMME Patch, fx ", FileCount: ..."

    Moensteret er MS Learns: IfError(Patch(...); true, Notify(fejl),
    succes). Svaret laegges i result_var, saa succes-grenen kan bruge
    raekkens ID. Fejler Patch, bliver de valgte filer staaende i
    kontrollen, saa man kan proeve igen."""
    patch = ("Patch(\n"
             f"    {data_source},\n"
             f"    {row},\n"
             f"    {{ Attachments: {picker}.Attachments{extra_fields} }}\n"
             ")")
    if result_var:
        patch = f"Set(\n    {result_var},\n" + "\n".join("    " + l for l in patch.split("\n")) + "\n)"
    body = (
        f"Set({busy_var}, true);\n"
        "IfError(\n"
        + "\n".join("    " + l for l in patch.split("\n")) + ";\n"
        "    true,\n"
        "    Notify(\n"
        "        \"The documents could not be saved. \" & FirstError.Message,\n"
        "        NotificationType.Error\n"
        "    ),\n"
        + "".join("    " + l + "\n" for l in reload_fx.split("\n") if l)
        + "".join("    " + l + "\n" for l in on_ok.split("\n") if l)
        + f"    Reset({picker});\n"
        "    Notify(\"Documents saved.\", NotificationType.Success)\n"
        ");\n"
        f"Set({busy_var}, false)"
    )
    if not not_saved:
        return body
    return ("If(\n"
            f"    IsBlank({row}),\n"
            f"    Notify(\"{not_saved}\", NotificationType.Warning),\n"
            + "\n".join("    " + l for l in body.split("\n")) + "\n)")


class Pane(object):
    """En dokumentrude paa EEN listeraekke.

    Underklassen leverer navnene og listen. Alt andet - Items, hentning,
    gem og luk - staar her og er ens i alle apper."""

    picker = None        # navnet paa Attachments-kontrollen (moderne)
    row_var = None       # variablen med listeraekken (LookUp paa ID)
    busy_var = None      # sand, mens Patch koerer (dobbelt-tryk)
    not_saved = None     # beskeden, naar raekken ikke er gemt endnu

    @property
    def data_source(self):
        raise NotImplementedError

    def extra_fields(self):
        """Flere felter i samme Patch (", Felt: vaerdi")."""
        return ""

    def on_ok(self):
        """Hvad appen ellers goer med svaret (row_var + "Saved")."""
        return ""

    # -- afledte udtryk ---------------------------------------------------
    @property
    def items(self):
        """Kontrollens Items: raekkens gemte vedhaeftninger."""
        return f"{self.row_var}.Attachments"

    @property
    def busy(self):
        """Laeses ogsaa, foer variablen er sat - saa er den Blank."""
        return "IfError(Coalesce(%s, false), false)" % self.busy_var

    @property
    def saved(self):
        """Findes raekken i SharePoint?"""
        return f"!IsBlank({self.row_var})"

    # -- formlerne --------------------------------------------------------
    def load_fx(self, id_expr):
        """Hent raekken paa ID - delegerbart. 0 eller Blank = ikke gemt."""
        return (
            "With(\n"
            f"    {{ docRowId: Coalesce({id_expr}, 0) }},\n"
            f"    Set({self.row_var}, If(docRowId = 0, Blank(), LookUp({self.data_source}, ID = docRowId)))\n"
            ")"
        )

    def save_fx(self):
        res = self.row_var + "Saved"
        return save_fx(
            self.data_source, self.row_var, self.picker, self.busy_var, res,
            f"Set({self.row_var}, LookUp({self.data_source}, ID = {res}.ID));",
            on_ok=self.on_ok(), extra_fields=self.extra_fields(),
            not_saved=self.not_saved)

    def close_fx(self):
        """Luk: glem de valgte, ikke gemte aendringer og raekken."""
        return f"Reset({self.picker});\nSet({self.row_var}, Blank())"


class DomainPane(Pane):
    """Equipment og Material. Ruden haenger paa den raekke, POPUPPEN er
    aabnet for (varDomDocsId) - ikke paa den, der ligger i formularen."""

    picker = "attDomPicker"
    row_var = "varDomAttRow"
    busy_var = "varDomAttBusy"
    not_saved = "Save the row first - documents are attached to the saved row."

    @property
    def data_source(self):
        # domain_config findes kun i domaeneapperne.
        import domain_config as cfg
        return cfg.L_ROWS

    def extra_fields(self):
        # Antallet staar ogsaa paa raekken, saa raekkeoversigten kan vise
        # det uden et opslag pr. raekke.
        return f", FileCount: {self.picker}.AttachmentsCount"

    def on_ok(self):
        res = self.row_var + "Saved"
        return (f"UpdateIf(colDomRows, RowId = {res}.ID, "
                f"{{ FileCount: Coalesce({res}.FileCount, 0) }});")
