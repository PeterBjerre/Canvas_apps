# -*- coding: utf-8 -*-
"""Issue #423: CLAUDE kan vaelges i "Assigned to" og vises med et lille
ikon i oversigtens kolonne Assigned to - ikke i dropdown'en.

CLAUDE er ingen M365-bruger. AssignedToEmail faar en fast markoer uden @,
AssignedToName bliver "CLAUDE", og intet sender mail til markoeren."""
import glob
import json
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ib_config as cfg  # noqa: E402

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
YAML = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")


def _walk(nodes):
    for n in nodes if isinstance(nodes, (list, tuple)) else [nodes]:
        yield n
        yield from _walk(n.children)


def _ctrls(root):
    return {c.name: c for c in _walk(root)}


def test_marker_is_never_a_mail_address_and_gives_the_name():
    assert "@" not in cfg.CLAUDE_EMAIL and cfg.CLAUDE_EMAIL == cfg.CLAUDE_EMAIL.lower()
    # Gem-logikken regner navnet ud af markoeren (delen foer @, store
    # bogstaver) - det skal give CLAUDE uden en saerregel.
    assert cfg.CLAUDE_EMAIL.split("@")[0].upper() == cfg.CLAUDE_NAME == "CLAUDE"
    import ib_parts as P
    assert "AssignedToName: If(" in P.SAVE_EDIT and P._initials(P.ASG_EMAIL) in P.SAVE_EDIT


def test_dropdown_offers_claude_after_not_assigned_without_icon():
    import ib_parts as P
    asg = _ctrls(P.build_form())["drpIbAssignee"]
    items = asg.props["Items"]
    na, cl = items.index('Name: "Not assigned"'), items.index('Name: "CLAUDE"')
    assert na < cl < items.index("colIbAdmins")
    assert f'Email: "{cfg.CLAUDE_EMAIL}"' in items
    # Genaabnet sag tildelt CLAUDE viser CLAUDE som valgt.
    assert f'.AssignedEmail = "{cfg.CLAUDE_EMAIL}", "CLAUDE"' in asg.props["DefaultSelectedItems"]
    # Intet ikon i dropdown'en.
    assert not any("svg" in str(v) for v in asg.props.values())
    assert asg.props["ItemDisplayText"] == "ThisItem.Name"


def test_row_shows_icon_only_for_claude_and_stays_aligned():
    import ib_parts as P
    ctrls = _ctrls([P.build_list()])
    head, row = ctrls["conIbListHead"], ctrls["conIbRow"]
    assert len(head.children) == len(row.children)
    for h, r in zip(head.children, row.children):
        assert h.props["Width"] == r.props["Width"]
    cell = ctrls["conIbRowAssigned"]
    assert cell.props["Width"] == P.COL_W["ASG"] and cell.props["Visible"] == P.WIDE
    icon, name = cell.children
    assert icon.name == "imgIbRowClaude" and name.name == "txtIbRowAssigned"
    assert icon.props["Visible"] == f'ThisItem.AssignedEmail = "{cfg.CLAUDE_EMAIL}"'
    assert int(icon.props["Width"]) == int(icon.props["Height"]) <= 16
    assert icon.props["TabIndex"] == "0" and icon.props["AccessibleLabel"] == '"Claude"'
    assert "data:image/svg+xml" in icon.props["Image"] and "hex-domain-mat" in icon.props["Image"]
    # Teksten giver plads til ikonet kun paa CLAUDE-raekker.
    assert "If(ThisItem.AssignedEmail" in name.props["Width"]
    # Det kompakte kort og popuppen har intet ikon.
    assert "imgIbRowClaude" not in {c.name for c in _walk(ctrls["conIbRowC"])}


def test_generated_yaml_has_the_icon_once():
    y = open(YAML, encoding="utf-8").read()
    assert y.count("- imgIbRowClaude:") == 1
    assert '{ Email: "claude", Name: "CLAUDE" }' in y


def test_icon_is_a_simple_stroke_glyph():
    import icons
    assert icons.CLAUDE_TOKEN in __import__("design_tokens").HTML_TOKENS
    svg = icons.svg(icons.CLAUDE, "#000", size=14, width=icons.CLAUDE_STROKE)
    assert svg.startswith("<svg") and '"' not in svg


def test_flow_never_mails_the_assignee():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-Submit-*.json"))
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, dict) and "emailMessage/To" in json.dumps(v.get("inputs", {})):
                    found.append(json.dumps(v["inputs"]["parameters"]["emailMessage/To"]))
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(json.load(open(path, encoding="utf-8-sig")))
    assert found and not any("AssignedTo" in t or "assignee" in t.lower() for t in found)


def test_assigned_to_me_never_matches_claude():
    import ib_parts as P
    # varIbMe er brugerens mail (med @); markoeren har intet @.
    assert 'Filter(colIbAll, AssignedEmail = varIbMe)' in P.collections() or \
        "AssignedEmail = varIbMe" in open(YAML, encoding="utf-8").read()
