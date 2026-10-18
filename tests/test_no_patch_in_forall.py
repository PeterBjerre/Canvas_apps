"""#342: Duplicate og Paste skriver samlet, ikke en Patch/Collect pr. raekke."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "BIO SAP App"


def _block(text, name):
    i = text.index(f"- {name}:")
    j = text.find("\n          - ", i + 1)
    return text[i:j if j > 0 else None]


def test_domain_duplicate_and_paste_patch_tables():
    for scr, pre in (("Equipment", "Eq"), ("Material", "Mat"), ("MeasuringPoint", "Mp")):
        y = (APP / f"Screen{scr}.pa.yaml").read_text(encoding="utf-8")
        for btn in (f"btn{pre}Duplicate", f"btn{pre}PasteAdd"):
            b = _block(y, btn)
            assert "{ created: Patch(" in b, btn
            assert "ForAll(created As n, { ID: n.ID })" in b, btn
            assert "{ n: Patch(" not in b, btn


def test_fl_paste_collects_once():
    y = (APP / "ScreenFunctionalLocation.pa.yaml").read_text(encoding="utf-8")
    b = _block(y, "btnFlPasteAdd")
    assert "ForAll(Sequence(CountRows(lines)), { RowGuid" in b
    assert "Collect(colFlRows, { RowGuid: Text(GUID()), RowNo: varFlNextRowNo + Value - 1" not in b


def test_build_has_no_rule15_warnings():
    for scr in ("Equipment", "Material", "MeasuringPoint", "FunctionalLocation"):
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "check_layout.py"),
                              str(APP / f"Screen{scr}.pa.yaml")],
                             capture_output=True, text=True, cwd=ROOT)
        assert "[15]" not in out.stdout + out.stderr, scr
