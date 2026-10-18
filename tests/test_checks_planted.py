# -*- coding: utf-8 -*-
"""
Flere plantede fejl (R2-068): de layoutregler, der ikke havde en, og
datakilde-tjekket (R2-069).

Samme moenster som tests/test_checks.py: en KOPI af den byggede
Equipment-skaerm, een fejl plantet, og tjekket skal naevne reglen.
"""
import os
import re
import shutil

from test_checks import APP, SCREEN, _layout

# Kolonneoverskriftens foerste celle og dens Width-linje.
HEAD_CELL_W = r"(- txtEqHeadStatus:\n(?:.*\n)*?\s+Width: \|-\n\s+)=[^\n]+"


def test_layout_rule_24_parent_width_arithmetic(tmp_path):
    rc, out = _layout(tmp_path, lambda t: re.sub(HEAD_CELL_W, r"\1=Parent.Width - 20", t, count=1))
    assert rc == 1 and "[24] txtEqHeadStatus" in out, out[-2000:]


def test_layout_rule_25_button_too_low(tmp_path):
    def plant(t):
        return re.sub(r"(Control: ModernButton\n(?:(?!\n\s+- ).*\n)*?\s+Height: \|-\n\s+)=[^\n]+",
                      r"\1=24", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[25]" in out, out[-2000:]


def test_layout_rule_26c_container_in_gallery(tmp_path):
    def plant(t):
        return re.sub(r"(- galEqRows:\n(?:.*\n)*?\s+Children:\n\s+- \w+:\n\s+Control: )\w+",
                      r"\1GroupContainer", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[26c] galEqRows" in out, out[-2000:]


def test_layout_rule_28_fillportions_in_non_wrapping_row(tmp_path):
    def plant(t):
        return re.sub(r"(- txtEqHeadStatus:\n\s+Control: ModernText\n(\s+)Properties:\n)",
                      r"\1\2  FillPortions: |-\n\2      =1\n", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[28] txtEqHeadStatus" in out, out[-2000:]


# Regel 29 parrer en overskrift med galleriets RAEKKECONTAINER. De byggede
# gallerier er foldet ud (gen_screen.flatten_galleries, regel 26c), saa
# reglen har intet at maale paa i dag - den proeves derfor paa en lille
# skaerm med den form, den er skrevet til.
MINI_29 = """Screens:
  ScreenT:
    Children:
      - conTCard:
          Control: GroupContainer
          Variant: AutoLayout
          Properties:
            LayoutDirection: =LayoutDirection.Vertical
            Width: =900
            Height: =400
          Children:
            - conTHead:
                Control: GroupContainer
                Variant: AutoLayout
                Properties:
                  LayoutDirection: =LayoutDirection.Horizontal
                  Width: =900
                  Height: =30
                Children:
                  - txtTHeadA:
                      Control: ModernText
                      Properties:
                        Text: ="A"
                        Width: =%s
                        Height: =20
                  - txtTHeadB:
                      Control: ModernText
                      Properties:
                        Text: ="B"
                        Width: =300
                        Height: =20
            - galT:
                Control: Gallery
                Variant: Vertical
                Properties:
                  Items: =colT
                  Width: =900
                  Height: =300
                Children:
                  - conTRow:
                      Control: GroupContainer
                      Variant: AutoLayout
                      Properties:
                        Width: =900
                        Height: =40
                      Children:
                        - txtTRowA:
                            Control: ModernText
                            Properties:
                              Text: =ThisItem.A
                              Width: =200
                              Height: =20
                        - txtTRowB:
                            Control: ModernText
                            Properties:
                              Text: =ThisItem.B
                              Width: =300
                              Height: =20
"""


def _mini_29(tmp_path, head_w):
    import io
    import sys
    from contextlib import redirect_stdout
    import check_layout
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    (tmp_path / "ScreenT.pa.yaml").write_text(MINI_29 % head_w, encoding="utf-8")
    old_argv, buf = sys.argv, io.StringIO()
    sys.argv = ["check_layout.py", str(tmp_path / "ScreenT.pa.yaml")]
    try:
        with redirect_stdout(buf):
            check_layout.main()
    finally:
        sys.argv = old_argv
    return buf.getvalue()


def test_layout_rule_29_header_and_row_columns_differ(tmp_path):
    assert "[29]" not in _mini_29(tmp_path, 200)
    out = _mini_29(tmp_path, 260)
    assert "[29] conTHead og conTRow flugter ikke" in out, out[-2000:]


def test_layout_rule_39_notify(tmp_path):
    def plant(t):
        return t.replace("=Set(varEqActiveRowId, ThisItem.RowId);",
                         "=Notify(\"x\"); Set(varEqActiveRowId, ThisItem.RowId);", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[39]" in out and "Notify" in out, out[-2000:]


# ---------------------------------------------------------- check_datasources

def _datasources(tmp_path, old, new):
    import check_datasources as cds
    src = os.path.join(APP, SCREEN)
    text = open(src, encoding="utf-8").read()
    assert old in text, "mutationen ramte ikke noget - testen er forkert"
    p = tmp_path / SCREEN
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    schema = cds.load_schema()
    problems, stats = [], {"checked": 0}
    cds.check(str(p), schema, problems, stats, set())
    return cds.classify(problems, cds.provisioned_columns(), cds.provisioned_column_choices())


def test_datasources_unknown_column(tmp_path):
    uniq, pending = _datasources(tmp_path, "StatusStep: 2,", "Kolonne_der_ikke_findes: 2,")
    assert any(x.startswith("MD_RequestIndex:") and "Kolonne_der_ikke_findes" in x
               for x in uniq), uniq


def test_datasources_choice_from_other_column_is_not_pending(tmp_path):
    # "draft" er en provisioneret valgvaerdi - men paa RowStatus, ikke paa
    # MD_RequestIndex.Status. Foer blev den godkendt som "venter" (R2-069).
    uniq, pending = _datasources(tmp_path, 'Status: { Value: "Indsendt" },',
                                 'Status: { Value: "draft" },')
    assert any("MD_RequestIndex" in x and '"draft"' in x for x in uniq), uniq
    assert not any(x.startswith("MD_RequestIndex") for x in pending), pending


def test_datasources_provisioned_choice_is_pending():
    import check_datasources as cds
    uniq, pending = cds.classify(
        [("EquipmentItems", 'RowStatus: valgvaerdien "draft" findes ikke. Gyldige: valid')],
        set(), cds.provisioned_column_choices())
    assert uniq == [] and pending == ['EquipmentItems.RowStatus (valgvaerdi "draft")']


def test_datasources_summary_mentions_waiting(capsys):
    import check_datasources as cds
    assert cds.main() == 0
    out = capsys.readouterr().out
    # "Alle ... findes" maa ikke staa oven paa en liste af mangler (R2-069).
    waiting = "oprettes af provisioneringen" in out
    assert waiting == ("venter paa provisionering" in out)
    assert waiting != ("Alle kolonner og valgvaerdier findes." in out)
