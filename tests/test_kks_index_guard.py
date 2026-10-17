"""KKS Lookup: Index paa en tom tabel giver fejl-banneret "The 'Index'
function cannot be called with an empty table" i appen. Hvert Index-kald
paa KKS-skaermen skal derfor vaere pakket i IfError.

Undtagelse: FL-soegningens comboboks (cmbKksFl, issue #295) er den faelles
tools/fl_picker.py. Dens Items indekserer kun inden for
ForAll(Sequence(CountRows(..) + 1)) af den SAMME samling, regnet i samme
With - og kun naar raekken findes - saa den kan ikke ramme en tom tabel."""
import re
from pathlib import Path

SCREEN = Path(__file__).resolve().parents[1] / "BIO SAP App" / "ScreenKks.pa.yaml"


def _shared_fl_combo(text):
    start = text.index("- cmbKksFl:")
    m = re.compile(r"\n( *)- \w+:").search(text, start + 1)
    return start, (m.start() if m else len(text))


def test_every_index_on_the_kks_screen_is_guarded():
    text = SCREEN.read_text(encoding="utf-8")
    lo, hi = _shared_fl_combo(text)
    calls = [m.start() for m in re.finditer(r"\bIndex\(", text)
             if not lo <= m.start() < hi]
    assert calls, "forventede Index-kald paa KKS-skaermen"
    bare = [p for p in calls if not text[max(0, p - 8):p].endswith("IfError(")]
    assert not bare, f"{len(bare)} Index-kald uden IfError"


def test_only_the_shared_fl_combo_is_exempt():
    text = SCREEN.read_text(encoding="utf-8")
    lo, hi = _shared_fl_combo(text)
    combo = text[lo:hi]
    assert "Items: |-" in combo and "Sequence(n + 1)" in combo
    assert "\n      - " not in combo  # ikke ud over kontrollen
