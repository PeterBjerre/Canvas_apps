"""Review 2026-10: R2-002, R2-003 og R2-014 i den genererede BIO SAP-app.

R2-002: en raekke, ejeren gemmer i en aaben anmodning, faar anmodningens
GUID (ikke kun en admins), Paste-raekker ogsaa, og kladderaekkerne foelger
anmodningen ved Submit.
R2-003: FL-skaermens klargoering rydder den forrige anmodnings samlinger.
R2-014: ejeren maa rette en FL-anmodning, der er sendt retur.
"""
import os

import pytest

from conftest import ROOT

SCREENS = {"Eq": "ScreenEquipment", "Mat": "ScreenMaterial", "Mp": "ScreenMeasuringPoint"}


def _control(screen, name):
    """Kontrollens tekst i YAML'en: fra '- name:' til naeste kontrol paa
    samme eller lavere indrykning."""
    lines = open(os.path.join(ROOT, "BIO SAP App", screen + ".pa.yaml"),
                 encoding="utf-8").read().split("\n")
    for i, l in enumerate(lines):
        if l.strip() == f"- {name}:":
            ind = len(l) - len(l.lstrip())
            out = [l]
            for m in lines[i + 1:]:
                if m.strip().startswith("- ") and len(m) - len(m.lstrip()) <= ind:
                    break
                out.append(m)
            return "\n".join(out)
    raise AssertionError(f"{name} findes ikke i {screen}")


@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_owner_row_gets_request_guid(tag):
    save = _control(SCREENS[tag], f"btn{tag}Save")
    assert (f"!IsBlank(var{tag}RequestGuid) && IsBlank(Coalesce(var{tag}SpRow.RequestGuid, \"\"))"
            in save)
    assert f"RequestNo: Coalesce(var{tag}RequestNo, \"\")" in save


@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_paste_rows_get_request_guid(tag):
    paste = _control(SCREENS[tag], f"btn{tag}PasteAdd")
    assert f'RequestGuid: Coalesce(var{tag}RequestGuid, "")' in paste
    assert "RequestGuid: If(" not in paste


@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_drafts_follow_the_request_on_submit(tag):
    sub = _control(SCREENS[tag], f"btn{tag}SubmitConfirm")
    drafts = f'Filter(col{tag}Rows, Status = "draft")'
    assert f"ForAll({drafts} As X, {{ ID: X.RowId }})" in sub
    assert f"ForAll({drafts}, {{ RequestNo: var{tag}RequestNo, RequestGuid: var{tag}RequestGuid }})" in sub


def test_fl_open_clears_rows_before_new_request():
    text = _control("ScreenFunctionalLocation", "btnFlOpen")
    clear = text.find("Clear(colFlRows);")
    reset = text.find('Set(varFlRequestGuid, "")')
    assert clear != -1 and reset != -1 and clear < reset


def test_fl_new_request_and_open_share_one_reset():
    """New request og klargoeringen rydder den samme liste (fl_parts.RESET_FX)."""
    build = os.path.join(ROOT, "Functional Location App", "build")
    parts = open(os.path.join(build, "fl_parts.py"), encoding="utf-8").read()
    asm = open(os.path.join(build, "assemble_screen.py"), encoding="utf-8").read()
    assert 'NEW_FX = RESET_FX + """;' in parts
    assert "return P.RESET_FX" in asm


def test_fl_owner_may_edit_returned_request():
    text = _control("ScreenFunctionalLocation", "btnFlOpen")
    assert ('Lower(Coalesce(varFlReq.RequesterEmail, "")) = varFlMe && '
            '(varFlStatus = "Kladde" || varFlStatus = "AfventerInfo")') in text
