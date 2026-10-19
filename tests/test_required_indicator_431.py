# -*- coding: utf-8 -*-
"""
Issue #431: "* Required" staar i sidepanelets overskrift (oeverst til
hoejre, foran pileknapperne) i Materials, Equipment og Measuring points -
ikke paa en egen raekke over formularens foerste sektion.

    python3 -m pytest tests/test_required_indicator_431.py
"""
import os
import re

import pytest

from conftest import ROOT

SCREENS = {
    "Mp": "ScreenMeasuringPoint.pa.yaml",
    "Eq": "ScreenEquipment.pa.yaml",
    "Mat": "ScreenMaterial.pa.yaml",
}


def _text(fname):
    return open(os.path.join(ROOT, "BIO SAP App", fname), encoding="utf-8").read()


def _block(text, name):
    """Kontrollen `name` og alt, der er indrykket under den."""
    m = re.search(r"^( *)- %s:\n" % re.escape(name), text, re.M)
    assert m, name + " mangler"
    ind = len(m.group(1))
    out = [m.group(0)]
    for line in text[m.end():].splitlines(True):
        if line.strip() and len(line) - len(line.lstrip()) <= ind:
            break
        out.append(line)
    return "".join(out)


@pytest.mark.parametrize("p", sorted(SCREENS))
def test_required_legend_in_panel_heading(p):
    text = _text(SCREENS[p])
    heading = _block(text, f"con{p}EditorHeading")
    legend = f"- con{p}FormReqLegend:"
    assert legend in heading, "* Required skal staa i panelets overskrift"
    # Efter titlen og foer pileknapperne - altsaa oeverst til hoejre.
    assert (heading.index(f"- txt{p}EditorPosition:") < heading.index(legend)
            < heading.index(f"- btn{p}EditorPrevious:"))
    leg = _block(text, f"con{p}FormReqLegend")
    assert '="*"' in leg and '="Required"' in leg
    # Sekundaer: lille tekst, ordet i den daempede farve.
    assert leg.count("=T.small") == 2
    assert "=C.'text-muted'" in leg
    # Kun een forklaring paa skaermen, og ingen egen raekke i formularen.
    assert text.count(f"- txt{p}FormReq:") == 1
    assert f"- con{p}FormTitle:" not in text


def test_material_editor_head_keeps_title_without_legend():
    text = _text(SCREENS["Mat"])
    head = _block(text, "conMatEditorHead")
    assert '="Row details"' in head
    assert "FormReq" not in head


@pytest.mark.parametrize("p", sorted(SCREENS))
def test_field_level_stars_kept(p):
    """Felternes egne stjerner er uroerte."""
    text = _text(SCREENS[p])
    assert len(re.findall(r"- txt%s\w*Star:" % p, text)) > 1
