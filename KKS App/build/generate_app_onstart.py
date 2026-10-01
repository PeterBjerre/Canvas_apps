# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart.

App.Formulas   temaet (C), breakpoints og KKS-opslagets navigation og
               filtre (kks_parts.FORMULAS). Ingen data: de tre
               noegleomraader hentes fra SharePoint i skaermens OnVisible.
               Her stod de foer som 3.071 raekker Table(...) - se
               kks_config.py.

App.OnStart    temaet og skemaerne for samlingerne. Henter INGEN data.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import app_yaml
import design_tokens as tok
import layout_tokens as lay
import kks_config as cfg
import kks_parts as P

OUT_DIR = os.path.join(HERE, "..")


def formulas_block():
    return "\n\n".join([tok.formula(), lay.formula(), P.FORMULAS])


def collection_block():
    out = []
    name, schema = tok.prefs_schema()
    fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
    # Temaets samling (SaveData) fyldes af LoadData i selve OnStart, og BIO
    # SAP fjerner blokken som ordret tekst - derfor ClearCollect + Clear.
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
