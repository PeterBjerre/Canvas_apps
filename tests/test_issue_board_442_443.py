# -*- coding: utf-8 -*-
"""Issue #442 og #443: antallet af vedhaeftninger i Issue Board.

#443: papirclipsen stod paa alle raekker. Den laeste connectorens
{HasAttachments} ('Has attachments'), som ikke er en kolonne i listen.
Nu laeser den raekkens eget tal, kolonnen FileCount paa IB_Tickets.

#442: fanen viste "Attachments (0)", til filerne var hentet. Tallet kom
fra Activity's Attachment-haendelser, som ingen har skrevet siden #300.
Nu kommer det fra FileCount, som oversigten allerede har hentet. Er
tallet ukendt (blankt), staar der "Attachments" uden tal.

Appen skriver FileCount i samme Patch som filerne, og LOAD_FILES retter
tallet, naar de rigtige filer er hentet. Provisioneringen opretter
kolonnen og taeller de gamle sager op."""
import json
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ib_config as cfg  # noqa: E402
import ib_parts as P  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
PS1 = os.path.join(ROOT, "sharepoint", "provision", "Provision-IssueBoard.ps1")
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")


def _read(path, enc="utf-8"):
    with open(path, encoding=enc) as f:
        return f.read()


def test_file_count_is_a_provisioned_number_column():
    ps1 = _read(PS1, "utf-8-sig")
    assert "New-MdField 'IB_Tickets' 'FileCount' Number" in ps1
    # De gamle sager taelles op uden at roere Modified.
    assert "Set-TicketFileCounts $TICKETS" in ps1
    assert "AttachmentFiles" in ps1 and "-UpdateType SystemUpdate" in ps1
    lists = json.loads(_read(SCHEMA, "utf-8-sig"))["lists"]
    tickets = next(l for l in lists if l["title"] == cfg.L_TICKETS)
    field = next(f for f in tickets["fields"] if f["internalName"] == "FileCount")
    assert field["displayName"] == "FileCount" and field["type"] == "Number"


def test_overview_reads_the_rows_own_count_not_the_connector_flag():
    # Een hentning ($select) - FileCount er en almindelig kolonne.
    assert "FileCount" in P.OVERVIEW_COLS
    assert "FileCount: r.FileCount" in P.FETCH_ALL
    text = _read(SCREEN)
    assert "Has attachments" not in text and "HasFiles" not in text
    # Papirclipsen pr. raekke: kun naar DENNE sag har mindst een fil.
    assert P.ROW_HAS_FILES == "Coalesce(ThisItem.FileCount, 0) > 0"
    # 2 synligheder + 2 i telefonens kortplacering (issue #508: taleboblen
    # og metadata giver plads til papirclipsen, naar den staar).
    assert text.count("Coalesce(ThisItem.FileCount, 0) > 0") == 4


def test_upload_saves_the_count_in_the_same_patch():
    assert "{ Attachments: attIbFiles.Attachments, LastActivityOn: Now(), " \
           "FileCount: attIbFiles.AttachmentsCount }" in P.UPLOAD_FILES
    # En ny sag har ingen filer.
    assert "FileCount: 0," in P.SUBMIT
    assert "FileCount: 0" in P.ADD_NEW


def test_loaded_files_correct_the_count_everywhere():
    fx = P.LOAD_FILES
    assert "With({ fileN: CountRows(varIbFiles) }" in fx
    assert "Patch(varIbSel, { FileCount: fileN })" in fx
    assert "UpdateIf(colIbAll, Id = varIbSelId, { FileCount: fileN })" in fx
    # SharePoint rettes kun, naar tallet er forkert, og kun af dem, der
    # maa rette sagen.
    assert ("If(fileN <> Coalesce(varIbSel.FileCount, -1) && IbSeeActivity,\n"
            f"            IfError(Patch({cfg.L_TICKETS}, LookUp({cfg.L_TICKETS}, ID = varIbSelId), "
            "{ FileCount: fileN }); true, false));") in fx
    # Efter en aendring (RELOAD_SEL) staar listens tal i varIbSel, saa
    # LOAD_FILES sammenligner med det, der faktisk er gemt.
    assert "FileCount: r.FileCount" in P.RELOAD_SEL
    # Naar sagen aabnes fra papirclipsen, er filerne hentet foer raekken -
    # deres antal vinder.
    assert "FileCount: If(varIbFilesFor = varIbSelRow.ID, CountRows(varIbFiles), varIbSelRow.FileCount)" \
        in P.LOAD_OPEN


def test_tab_count_is_known_at_open_and_never_a_guessed_zero():
    formulas = _read(APP)
    assert ("IbFileCount = If(varIbFilesFor = varIbSelId, CountRows(varIbFiles), "
            "varIbSel.FileCount);") in formulas
    # Ikke laengere Activity's Attachment-haendelser (de skrives ikke siden #300).
    assert 'CountRows(Filter(colIbActivity, Kind = "Attachment"))' not in formulas
    # Blank = ukendt -> "Attachments" uden tal.
    # Paa en telefon hedder fanen "Files" (issue #508).
    assert ('If(LayoutRank < 2, "Files", "Attachments") & If(IsBlank(IbFileCount), "", '
            '" (" & IbFileCount & ")")') in _read(SCREEN)
    # Filerne hentes stadig foerst, naar fanen vaelges.
    assert P.LOAD_FILES not in P.LOAD_OPEN
