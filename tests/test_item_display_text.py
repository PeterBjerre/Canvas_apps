"""Issue #300: ItemDisplayText paa en ModernDropdown maa kun bruge
dropdownens egen post (ThisItem.<kolonne>). LookUp, samlinger og
variabler afvises af compile ("cannot be accessed in expressions on
this property")."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "BIO SAP App"
ALLOWED = re.compile(r"^=ThisItem\.[A-Za-z_][A-Za-z0-9_]*$")


def _item_display_texts():
    for f in sorted(APP.glob("*.pa.yaml")):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "ItemDisplayText: |-":
                yield f.name, lines[i + 1].strip()


def test_item_display_text_only_uses_this_item():
    found = list(_item_display_texts())
    assert found, "ingen ItemDisplayText fundet"
    bad = [(f, v) for f, v in found if not ALLOWED.match(v)]
    assert not bad, bad


def test_fl_panel_dropdowns_show_own_value():
    texts = [v for f, v in _item_display_texts()
             if f == "ScreenFunctionalLocation.pa.yaml"]
    assert texts and all(v == "=ThisItem.Value" for v in texts)
