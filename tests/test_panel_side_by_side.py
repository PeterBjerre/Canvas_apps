import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIO = os.path.join(ROOT, "BIO SAP App")


def _read(name):
    with open(os.path.join(BIO, name), encoding="utf-8") as f:
        return f.read()


def test_panel_inset_covers_the_three_row_panel_domains():
    app = _read("App.pa.yaml")
    line = re.search(r"PanelInset = .*", app).group(0)
    for var in ("varEqEditorOpen", "varMatEditorOpen", "varMpEditorOpen",
                "varFlPanelOpen", "varIbDetailOn"):
        assert var in line
    assert "App.Width >= 1280" in line


def test_frame_and_scrim_follow_the_panel():
    for screen, tag in (("ScreenEquipment", "Eq"), ("ScreenMaterial", "Mat"),
                        ("ScreenMeasuringPoint", "Mp")):
        y = _read(screen + ".pa.yaml")
        assert "PanelInset" in y
        assert "- PanelInset" in y
        assert "PanelInset = 0" in y  # backdrop only when the panel overlays
        assert "OnHidden" in y
