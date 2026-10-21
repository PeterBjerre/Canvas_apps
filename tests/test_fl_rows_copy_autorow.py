# -*- coding: utf-8 -*-
"""
Issue #467: Rows og Classes paa Functional Location.

  - En ny tom raekke af sig selv, naar den SIDSTE raekke bliver Ready -
    kun een tom raekke ad gangen, og Add row er der stadig.
  - Classes viser raekkens Room, Sort field, ABC indicator og ATEX - kun
    til visning.
  - StrIndicator og Class hedder det samme i Rows, Classes og panelet.
  - Copy i Actions: en ny, ugemt raekke uden FL, id og status.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_rows_copy_autorow.py
"""
import test_fl_spool_row as T


def test_new_empty_row_when_the_last_row_is_ready():
    verify = T._prop("btnFlVerify", "OnSelect")
    g2 = verify.split("// G2.")[1].split("// H.")[0]
    # Kun den sidste raekke (hoejeste RowNo), og kun Ready ("valid").
    assert 'Last(Sort(colFlRows, RowNo)).Status = "valid"' in g2
    # Kun naar der ikke allerede er en tom raekke.
    assert "IsEmpty(Filter(colFlRows, IsBlank(FL) && IsBlank(Description)))" in g2
    # Ikke i en laast anmodning, og ikke over raekkeloftet.
    assert '!varFlViewOnly && varFlStatus <> "Indsendt"' in g2
    assert "CountRows(colFlRows) < 400" in g2
    # Een raekke, tom og "draft", med sit nummer.
    assert g2.count("Collect(colFlRows") == 1
    assert 'FL: "", Description: "", ' in g2 and 'Status: "draft"' in g2
    assert "Pos: CountRows(colFlRows) + 1" in g2
    # Efter status (E) og foer panelet (H).
    assert verify.index("// E.") < verify.index("// G2.") < verify.index("// H.")
    # Add row er uaendret.
    assert "Collect(colFlRows" in T._prop("btnFlAddRow", "OnSelect")


def test_same_names_in_rows_classes_and_panel():
    rows = [T._prop(n, "Text").strip('"') for n in T._children("conFlRowsHead")]
    cls = [T._prop(n, "Text").strip('"') for n in T._children("conFlClsHead")]
    for lbl in ("StrIndicator", "Class"):
        assert lbl in rows and lbl in cls, lbl
    text = T._text()
    for old in ('"KKS type"', '"Assigned class"', "KKS type and assigned class"):
        assert old not in text, old
    assert "StrIndicator and class" in text
    # Kun etiketterne: bindingerne er de samme.
    assert "ThisItem.KksType" in T._prop("txtFlRowKks", "Text")
    assert "ThisItem.AssignedClass" in T._prop("txtFlRowCls", "Text")


def test_classes_show_row_values_read_only():
    heads = [T._prop(n, "Text").strip('"') for n in T._children("conFlClsHead")]
    i = heads.index("Class")
    assert heads[i + 1:i + 5] == ["Room", "Sort field", "ABC indicator", "ATEX"]
    for n, f in (("Room", "ROOM"), ("Sort", "SORT FIELD"), ("Abc", "ABC INDIC."), ("Atex", "ATEX")):
        c = T._ctrl(f"txtFlC{n}")
        assert c is not None and c["Control"] == "ModernText", n
        assert f'LookUp(colFlVals, RowGuid = ThisItem.RowGuid && Field = "{f}").Value' in \
            T._prop(f"txtFlC{n}", "Text"), n
        # Header og celle flugter.
        assert T._prop(f"txtFlClsHead{n}", "Width") == T._prop(f"txtFlC{n}", "Width"), n


def test_copy_makes_a_new_unsaved_row():
    on = T._prop("btnFlRowCopy", "OnSelect")
    # Ny id og nyt nummer - aldrig kildens.
    assert "ng: Text(GUID())" in on and "RowGuid: ng, RowNo: varFlNextRowNo, SpId: 0" in on
    # Ingen FL (unik), ingen status/beskeder; Description og felterne med.
    assert 'FL: "", Description: src.Description' in on
    assert 'Status: "draft", FirstIssue: "", FirstWarning: "", IssueCount: 0' in on
    assert "Filter(colFlVals, RowGuid = src.RowGuid)" in on
    assert "Collect(colFlVals, colFlCopyVals)" in on
    # Markeret som ny kopi, til den er gemt.
    assert "Collect(colFlCopies, { RowGuid: ng })" in on
    assert "colFlCopies" in T._prop("inpFlRowFl", "Placeholder")
    assert "Select(btnFlVerify)" in on and "CountRows(colFlRows) >= 400" in on
    # Delete er der stadig, efter Copy.
    assert "Collect(colFlDeleted" in T._prop("btnFlRowDelete", "OnSelect")
    kids = T._children("galFlRows")
    assert kids.index("btnFlRowCopy") + 1 == kids.index("btnFlRowDelete")
    # En tom raekke kan ikke kopieres.
    assert "IsBlank(ThisItem.FL) && IsBlank(ThisItem.Description)" in \
        T._prop("btnFlRowCopy", "DisplayMode")
    # Glemt, naar anmodningen er gemt, hentet eller ny.
    for c in ("colFlCopies", "colFlCopyVals"):
        assert f"If(false, ClearCollect({c}, " in T._text(), c
    assert T._text().count("Clear(colFlCopies)") >= 3
