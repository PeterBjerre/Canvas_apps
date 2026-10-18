"""Issue #336: Attachments kan ikke laeses i en ForAll over listen.

Compile afviste CountRows(OP.Attachments) i btnVhpOpen ("The specified
column is not accessible in this context"). Antallet hentes i stedet,
naar Docs-popuppen aabner raekken, og knappen viser "Docs" indtil da."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    with open(os.path.join(ROOT, "BIO SAP App", name), encoding="utf-8") as f:
        return f.read()


def test_load_does_not_read_attachments_in_forall():
    assert "OP.Attachments" not in _read("ScreenVhPlan.pa.yaml")


def test_docs_button_shows_count_only_when_known():
    text = _read("ScreenVhPlan.pa.yaml")
    assert 'If(IsBlank(n), "Docs", "Docs (" & Text(n) & ")")' in text
    assert "UpdateIf(colVhpOperations, SpId = varVhpAttRow.ID, { FileCount: CountRows(varVhpAttRow.Attachments) })" in text
