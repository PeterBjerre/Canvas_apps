"""
Issue #161/#300: filvaelgerne er den moderne Attachments-kontrol i netop
den version, Peters Studio skriver (ModernAttachments@1.3.0). Siden
issue #300 er hver kontrol bundet til en listeraekkes vedhaeftninger
(Items = <raekke>.Attachments, aldrig Blank()), og gem-knappen Patch'er
raekkens Attachments direkte - uden flows. Measuring Point har ingen
dokumenter.

    python3 -m pytest tests/test_modern_attachments.py
"""
import importlib.util
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

from conftest import ROOT, TOOLS

APP = os.path.join(ROOT, "BIO SAP App")
VERSION = "ModernAttachments@1.3.0"

# Skaerm -> (kontrol, gem-knap, liste, Items).
PICKERS = {
    "ScreenEquipment.pa.yaml": ("attEqPicker", "btnEqAttUpload", "EquipmentItems",
                                "varEqAttRow.Attachments"),
    "ScreenMaterial.pa.yaml": ("attMatPicker", "btnMatAttUpload", "MaterialItems",
                               "varMatAttRow.Attachments"),
    "ScreenVhPlan.pa.yaml": ("attVhpAttPicker", "btnVhpAttUpload", "TaskListMain",
                             "varVhpAttRow.Attachments"),
    "ScreenIssueBoard.pa.yaml": ("attIbFiles", "btnIbUpload", "IB_Tickets",
                                 "If(varIbFilesFor = varIbSelId, varIbFiles, FirstN(varIbFiles, 0))"),
}
CLASSIC_ONLY = ("NoAttachmentsText", "BorderColor", "BorderThickness", "PaddingLeft")
OLD_FLOWS = ("'BioSap-TaskListAttachment'", "'BioSap-GetSubmittedAttachments'",
             "'BioSap-DeleteSubmittedAttachments'")


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    """Kontrollens egen YAML-blok - til naeste soeskende paa samme niveau."""
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, prop):
    """En egenskabs formel (efter "=") - en- eller flerlinjet."""
    m = re.search(r"^( +)%s: \|-\n((?:\1 +.*\n?)+)" % prop, block, re.M)
    assert m, prop
    return "\n".join(l.strip() for l in m.group(2).splitlines()).lstrip("=")


def test_every_picker_is_modern_attachments_1_3_0():
    for screen, (name, _btn, _lst, _items) in PICKERS.items():
        text = _read(screen)
        assert "Attachments@2.3.0" not in text, screen
        assert text.count("Control: ModernAttachments@") == 1, screen
        block = _block(text, name)
        assert f"Control: {VERSION}" in block, screen
        for prop in ("AccessibleLabel:", "MaxAttachments:", "MaxAttachmentSize:", "OnError:"):
            assert prop in block, (screen, prop)
        for prop in CLASSIC_ONLY:
            assert prop + ":" not in block, (screen, prop)


def test_every_picker_is_bound_to_a_rows_attachments():
    """Issue #300: Items er raekkens vedhaeftninger - aldrig Blank(), for
    saa har Attachments-outputtet intet skema og kompilerer ikke."""
    for screen in os.listdir(APP):
        if not screen.endswith(".pa.yaml"):
            continue
        text = _read(screen)
        for m in re.finditer(r"^ *- (\w+):\n *Control: ModernAttachments@", text, re.M):
            items = _prop(_block(text, m.group(1)), "Items")
            assert items != "Blank()", (screen, m.group(1))
            assert ".Attachments" in items or "varIbFiles" in items, (screen, items)
    for screen, (name, _btn, _lst, items) in PICKERS.items():
        assert _prop(_block(_read(screen), name), "Items") == items, screen


def test_save_buttons_patch_the_rows_attachments_without_flows():
    for screen, (name, btn, lst, _items) in PICKERS.items():
        text = _read(screen)
        on_select = _prop(_block(text, btn), "OnSelect")
        assert re.search(r"Patch\(\s*%s," % lst, on_select), screen
        assert f"Attachments: {name}.Attachments" in on_select, screen
        assert "IfError(" in on_select and "FirstError.Message" in on_select, screen
        assert f"Reset({name})" in on_select, screen
        # Ingen ForAll over filerne og intet flowkald.
        assert ".Attachments As " not in text, screen
        assert ".Run(" not in on_select, screen
        # Dobbelt-tryk: spaerret mens kontrollen laeser filer ind og mens der gemmes.
        mode = _prop(_block(text, btn), "DisplayMode")
        assert f"{name}.IsUploading" in mode, screen
    for screen in os.listdir(APP):
        if screen.endswith(".pa.yaml"):
            text = _read(screen)
            for flow in OLD_FLOWS:
                assert flow not in text, (screen, flow)


def test_domain_and_vhplan_save_tells_when_the_row_is_not_saved():
    for screen in ("ScreenEquipment.pa.yaml", "ScreenMaterial.pa.yaml", "ScreenVhPlan.pa.yaml"):
        _name, btn, _lst, items = PICKERS[screen]
        row = items.split(".")[0]
        on_select = _prop(_block(_read(screen), btn), "OnSelect")
        assert on_select.startswith(f"If(\nIsBlank({row}),"), screen


def test_measuring_point_has_no_documents():
    text = _read("ScreenMeasuringPoint.pa.yaml")
    for bad in ("ModernAttachments", "varMpDocsId", "varMpAttRow", "btnMpRowDocs",
                "conMpDocs", "btnMpDocs", "conMpAttModal"):
        assert bad not in text, bad
    assert "varMpDocsId" not in _read("App.pa.yaml")


def _check_layout():
    """tools/check_layout.py ved stien - "Issue Board/build" har sin egen
    check_layout.py, som kan ligge foerst paa sys.path."""
    spec = importlib.util.spec_from_file_location("tools_check_layout_161",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rule_16b_rejects_classic_and_other_versions(tmp_path):
    cl = _check_layout()
    screen = "ScreenEquipment.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    for bad in (None, "Attachments@2.3.0", "ModernAttachments@1.2.0", "ModernAttachments"):
        new = text if bad is None else text.replace(f"Control: {VERSION}", f"Control: {bad}", 1)
        assert bad is None or new != text
        (tmp_path / screen).write_text(new, encoding="utf-8")
        old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = cl.main()
        finally:
            sys.argv = old_argv
        if bad is None:
            assert rc == 0 and "[16b]" not in buf.getvalue(), buf.getvalue()
        else:
            assert rc == 1 and "[16b]" in buf.getvalue(), (bad, buf.getvalue())


def test_picker_height_fills_parent_without_needless_scroll():
    """Issue #344: kontrollen har plads til tom-tilstanden (mindst
    PICKER_H), vokser med filerne og kappes foerst af foraelderens plads
    (Parent.Height minus de andre boern) - ikke af et fast loft paa fire
    filer. Den naevner ikke sig selv ved navn i sin egen hoejde."""
    sys.path.insert(0, TOOLS)
    import doc_upload as du
    assert du.PICKER_H > 112
    for screen, (name, _btn, _lst, items) in PICKERS.items():
        h = _prop(_block(_read(screen), name), "Height")
        assert h.startswith(f"Min({du.PICKER_H} + Max(Self.AttachmentsCount, "
                            f"CountRows({items})) * {du.PICKER_FILE_H}, "
                            f"Max({du.PICKER_H}, Parent.Height - ("), (screen, h)
        assert f"{name}." not in h, (screen, h)
        assert "Min(Self.AttachmentsCount, 4)" not in h, screen
