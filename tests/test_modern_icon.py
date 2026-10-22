# -*- coding: utf-8 -*-
"""
Issue #306 (del af #161): pynt- og statusikoner med et Fluent-sidestykke
er den moderne Icon-kontrol (ModernIcon@1.1.0) i de samme tokenfarver.
Stoerrelse, placering og synlighed er uaendrede. Domaeneikonerne og de
klikbare ikoner er stadig billeder.

    python3 -m pytest tests/test_modern_icon.py
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
VERSION = "ModernIcon@1.1.0"
TOAST_ICON = ('Switch(IfError(gblToast.Kind, ""), "Success", "CheckmarkCircle", "Warning", '
              '"ErrorCircle", "Error", "DismissCircle", "Info")')
TOAST_COLOR = ('Switch(IfError(gblToast.Kind, ""), "Success", C.\'state-ok-fg\', "Warning", '
               'C.\'state-warn-fg\', "Error", C.\'state-error-fg\', C.\'state-info-fg\')')
# Issue #448: kortet er "Valid", naar itemet ingen blokeringer har
# (build_items.ITEM_BLOCKERS) - ikke af den gemte Status.
ITEM_OK = "IsEmpty(With("

# Skaerm -> {ikon: (Icon, IconColor, Height/Width, Visible)}.
ICONS = {
    "ScreenIssueBoard.pa.yaml": {
        "icoIbSearchIcon": ('"Search"', "C.'text-muted'", "20", None),
        # Issue #422's Activity-ikoner er siden #469 en klikbar knap
        # (btnIbRowAct*, tests/test_issue_board_469.py).
    },
    "ScreenKks.pa.yaml": {
        "icoKksFindIcon": ('"Search"', "C.'text-muted'", "20", None),
    },
    "ScreenVhPlan.pa.yaml": {
        "icoVhpPlanFoldStatus": ('If(VhpPlanValid, "CheckmarkCircle", "ErrorCircle")',
                                 "If(VhpPlanValid, C.'state-ok-fg', C.'state-error-fg')",
                                 "20", None),
        "icoVhpItemCardStatus": (None, None, "20", None),
        # Task list and operations: fluebenet foran titlen, kun naar
        # sektionen er gyldig (issue #522 - afloeser Valid-maerket).
        "icoVhpOpsHeadStatus": ('If(VhpOpsValid, "CheckmarkCircle", "ErrorCircle")',
                                "If(VhpOpsValid, C.'state-ok-fg', C.'state-error-fg')",
                                "20", "IfError(VhpOpsValid, false)"),
    },
    "ScreenMdHub.pa.yaml": {
        "icoMdAprPerson": ('"Person"', "C.'text-muted'", "16",
                           'ThisItem.Kind = "D" && ThisItem.Human'),
    },
}
TAGS = {"ScreenEquipment.pa.yaml": "Eq", "ScreenFunctionalLocation.pa.yaml": "Fl",
        "ScreenIssueBoard.pa.yaml": "Ib", "ScreenKks.pa.yaml": "Kks",
        "ScreenMaterial.pa.yaml": "Mat", "ScreenMdHub.pa.yaml": "Md",
        "ScreenMeasuringPoint.pa.yaml": "Mp", "ScreenVhPlan.pa.yaml": "Vhp"}
for _screen, _tag in TAGS.items():
    ICONS.setdefault(_screen, {})[f"ico{_tag}ToastIcon"] = (TOAST_ICON, TOAST_COLOR, "20", None)


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    """Kontrollens egen YAML-blok - til naeste soeskende paa samme niveau."""
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    m = re.search(r"^ +%s: \|-\n +=(.*)$" % key, block, re.M)
    return m.group(1).strip() if m else None


def test_every_icon_is_modern_icon_in_the_token_color():
    total = 0
    for screen, icons in ICONS.items():
        text = _read(screen)
        assert text.count("Control: ModernIcon") == len(icons), screen
        assert "Control: ModernIcon@" in text and text.count(f"Control: {VERSION}") == len(icons)
        for name, (icon, color, size, vis) in icons.items():
            block = _block(text, name)
            assert f"Control: {VERSION}" in block, name
            if icon:
                assert _prop(block, "Icon") == icon, name
            if color:
                assert _prop(block, "IconColor") == color, name
            assert _prop(block, "IconStyle") == "IconStyle.Outline", name
            assert _prop(block, "Width") == size and _prop(block, "Height") == size, name
            if vis:
                assert _prop(block, "Visible") == vis, name
            acc = _prop(block, "AccessibleLabel")
            assert acc and acc != '""', name
            for bad in ("Image", "TabIndex", "OnSelect", "Style", "ImagePosition"):
                assert _prop(block, bad) is None, (name, bad)
            # Det gamle billede er vaek.
            assert f"- img{name[3:]}:" not in text, name
            total += 1
    # 15 foer issue #469 (Activity-ikonerne blev en knap); + 1 issue #522.
    assert total == 14


def test_item_card_status_follows_the_same_rule_as_its_text():
    block = _block(_read("ScreenVhPlan.pa.yaml"), "icoVhpItemCardStatus")
    # Formlerne fylder flere linjer (issue #448) - hele vaerdien laeses.
    def full(key):
        m = re.search(r"^( +)%s: \|-\n +=(.*(?:\n\1 .*)*)" % key, block, re.M)
        return " ".join(m.group(2).split())
    icon = full("Icon")
    assert icon.startswith("If(" + ITEM_OK), icon
    assert icon.endswith(', "CheckmarkCircle", "ErrorCircle")'), icon
    assert full("IconColor").endswith(", C.'state-ok-fg', C.'state-error-fg')")


def test_person_keeps_its_place():
    block = _block(_read("ScreenMdHub.pa.yaml"), "icoMdAprPerson")
    assert _prop(block, "X") == "48"
    assert _prop(block, "Y").endswith("+ 2")


def test_domain_icons_stay_images():
    """Domaeneikonerne (tools/icons.py) har intet Fluent-sidestykke og skal
    vaere ens med sidebaren - de bliver billeder."""
    for screen, tag in TAGS.items():
        text = _read(screen)
        block = _block(text, f"img{tag}TitleIcon")
        assert "Control: Image" in block, screen


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_306",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_rule(cl, tmp_path, screen, text):
    (tmp_path / screen).write_text(text, encoding="utf-8")
    old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = cl.main()
    finally:
        sys.argv = old_argv
    return rc, buf.getvalue()


def test_rule_16i_rejects_other_versions_and_unknown_properties(tmp_path):
    cl = _check_layout()
    screen = "ScreenKks.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    rc, out = _run_rule(cl, tmp_path, screen, text)
    assert rc == 0 and "[16i]" not in out, out

    for bad in ("ModernIcon@1.0.0", "ModernIcon"):
        new = text.replace(f"Control: {VERSION}", f"Control: {bad}", 1)
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16i]" in out, (bad, out)

    block = _block(text, "icoKksFindIcon")
    pad = re.search(r"^( +)Height: \|-", block, re.M).group(1)
    for key in ("TabIndex", "Style", "OnSelect"):
        val = "true" if key == "OnSelect" else "0"
        new = text.replace(block, block.replace(f"{pad}Height: |-",
                                                f"{pad}{key}: |-\n"
                                                f"{pad}    ={val}\n"
                                                f"{pad}Height: |-", 1), 1)
        assert new != text, key
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16i] icoKksFindIcon" in out, (key, out)
