# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart (issue #114).

App.Formulas   temaet (C), breakpoints, IsAdmin (tools/permissions.py,
               ordret som i de andre apps) og Issue Boards formler
               (ib_parts.FORMULAS). Ingen data.
App.OnStart    temaet og skemaerne for samlingerne. Henter INGEN data -
               skaermens OnVisible goer det.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import app_yaml
import design_tokens as tok
import layout_tokens as lay
import permissions as perm
import ib_config as cfg
import ib_parts as P

OUT_DIR = os.path.join(HERE, "..")


def formulas_block():
    return "\n\n".join([tok.formula(), lay.formula(), perm.formula(), P.FORMULAS])


def collection_block():
    out = []
    name, schema = tok.prefs_schema()
    fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
    # Temaets samling fyldes af LoadData i OnStart; BIO SAP fjerner blokken
    # som ordret tekst - derfor ClearCollect + Clear (som KKS).
    out.append(f"ClearCollect({name}, {{ {fields} }});\nClear({name});")
    for name, schema in P.collections():
        fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
        # If(false, ...): kun skemaet (check_layout regel 34).
        out.append(f"If(false, ClearCollect({name}, {{ {fields} }}));")
    return "\n".join(out)


def main():
    onstart = collection_block() + "\n\n" + tok.onstart_block()
    content = app_yaml.write(OUT_DIR, formulas_block(), onstart, cfg.SCREEN)
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer,",
          len(P.collections()), "samlinger, 0 datahentninger i OnStart.")


if __name__ == "__main__":
    main()
