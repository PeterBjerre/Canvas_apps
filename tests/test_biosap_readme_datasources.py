# -*- coding: utf-8 -*-
"""R2-078: README'ens liste over BIO SAP App's SharePoint-datakilder er
den samme som appens DataSources.json i solution/. README'en sagde, at
UserAndGroups kun hoerte til Issue Board - en, der slog flaget fra, ville
fjerne den, og saa fejlede IsAdmin i hub, VH, Equipment, Material og MP."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "BIO SAP App", "README.md")
DS = os.path.join(ROOT, "solution", "BIOSAP", "src", "CanvasApps", "orsted_biosap_af21f.src",
                  "References", "DataSources.json")


def _section(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


def _names(text):
    return set(re.findall(r"`([A-Za-z_]+)`", text))


def test_readme_lists_the_apps_sharepoint_lists():
    with open(DS, encoding="utf-8-sig") as f:
        data = json.load(f)
    rows = data.get("DataSources", data) if isinstance(data, dict) else data
    lists = {r["Name"] for r in rows if r.get("Type") == "ConnectedDataSourceInfo"}
    text = open(README, encoding="utf-8").read()
    always = _names(_section(text, "*SharePoint-lister (", "`UserAndGroups` (admins"))
    mp = _names(_section(text, "*Kun med Measuring Point", "*Kun med Issue Board"))
    ib = _names(_section(text, "*Kun med Issue Board", "3. **"))
    ib = {n for n in ib if n.startswith("IB_")}
    assert always | mp | ib == lists, sorted((always | mp | ib) ^ lists)
    n = int(re.search(r"\*SharePoint-lister \((\d+)\):\*", text).group(1))
    assert n == len(always)
    # De faste lister staar ikke under et flag.
    for name in ("UserAndGroups", "MD_Approver", "MD_ApprovalLog", "VHP_NoteToSelf"):
        assert name in always and name not in ib | mp, name
