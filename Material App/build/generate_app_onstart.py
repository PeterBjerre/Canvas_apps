# -*- coding: utf-8 -*-
"""Skriver ../App.pa.yaml for Material-appen.

Det hele staar i tools/domain_app.py - samlingsskemaet, tilstanden og de
navngivne formler er ens for Equipments og Materials. Skal denne app have
noget andet, skrives det her (se SKILL.md "Hvem ejer hvad").
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import domain_config as cfg
import domain_app
import material_parts as parts


def main():
    # Materials' eget (issue #204): objektlisten paa den raekke,
    # formularen staar paa, og raekken med de valgfrie oplysninger, der er
    # foldet ind ved opstart.
    domain_app.write_app(cfg, os.path.join(HERE, ".."),
                         extra_collections=[(parts.OBJECTS, parts.OBJ_SCHEMA)],
                         extra_state=parts.EXTRA_STATE)


if __name__ == "__main__":
    main()
