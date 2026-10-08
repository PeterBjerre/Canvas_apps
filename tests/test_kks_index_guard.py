"""KKS Lookup: Index paa en tom tabel giver fejl-banneret "The 'Index'
function cannot be called with an empty table" i appen. Hvert Index-kald
paa KKS-skaermen skal derfor vaere pakket i IfError."""
import re
from pathlib import Path

SCREEN = Path(__file__).resolve().parents[1] / "BIO SAP App" / "ScreenKks.pa.yaml"


def test_every_index_on_the_kks_screen_is_guarded():
    text = SCREEN.read_text(encoding="utf-8")
    calls = [m.start() for m in re.finditer(r"\bIndex\(", text)]
    assert calls, "forventede Index-kald paa KKS-skaermen"
    bare = [p for p in calls if not text[max(0, p - 8):p].endswith("IfError(")]
    assert not bare, f"{len(bare)} Index-kald uden IfError"
