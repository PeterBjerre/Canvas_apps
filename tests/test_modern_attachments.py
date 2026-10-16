# -*- coding: utf-8 -*-
"""
Issue #161: de fem filvaelgere er den moderne Attachments-kontrol i
netop den version, Peters Studio skriver (ModernAttachments@1.3.0) - og
uploaden gaar uaendret gennem de samme flows med Name og Value.

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

# Skaerm -> (kontrol, flow). EQ/MAT/MP/VHP laegger i TaskListDocuments,
# Issue Board i IB_Tickets' listevedhaeftninger - begge via flow.
PICKERS = {
    "ScreenEquipment.pa.yaml": ("attEqPicker", "'BioSap-TaskListAttachment'"),
    "ScreenMaterial.pa.yaml": ("attMatPicker", "'BioSap-TaskListAttachment'"),
    "ScreenMeasuringPoint.pa.yaml": ("attMpPicker", "'BioSap-TaskListAttachment'"),
    "ScreenVhPlan.pa.yaml": ("attVhpAttPicker", "'BioSap-TaskListAttachment'"),
    "ScreenIssueBoard.pa.yaml": ("attIbFiles", "'BioSap-IssueBoard-Submit'"),
}
CLASSIC_ONLY = ("NoAttachmentsText", "BorderColor", "BorderThickness", "PaddingLeft")


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    """Kontrollens egen YAML-blok - til naeste soeskende paa samme niveau."""
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def test_every_picker_is_modern_attachments_1_3_0():
    for screen, (name, _flow) in PICKERS.items():
        text = _read(screen)
        assert "Attachments@2.3.0" not in text, screen
        assert text.count("Control: ModernAttachments@") == 1, screen
        block = _block(text, name)
        assert f"Control: {VERSION}" in block, screen
        assert "=Blank()" in block.split("Items:")[1].split("\n")[1], screen
        for prop in ("AccessibleLabel:", "MaxAttachments:", "MaxAttachmentSize:", "OnError:"):
            assert prop in block, (screen, prop)
        for prop in CLASSIC_ONLY:
            assert prop + ":" not in block, (screen, prop)


def test_upload_still_goes_through_the_same_flows_with_name_and_value():
    for screen, (name, flow) in PICKERS.items():
        text = _read(screen)
        assert f"{name}.Attachments As " in text, screen
        assert flow + ".Run(" in text, screen
        assert "{ file: { contentBytes: F.Value, name: F.Name } }" in text, screen
        # Upload er laast, mens kontrollen laeser filer ind.
        assert f"{name}.IsUploading" in text, screen
    ib = _read("ScreenIssueBoard.pa.yaml")
    assert "Patch(IB_Tickets" not in ib
    assert "Patch(TaskListDocuments" not in "".join(_read(s) for s in PICKERS)


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
