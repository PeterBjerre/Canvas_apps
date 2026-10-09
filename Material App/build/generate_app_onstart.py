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
    # Materials' eget (issue #204, #228): objekterne en kopi tager med, og
    # objektlisten i popuppen paa den gemte raekke.
    cols = [(parts.OBJECTS, parts.OBJ_SCHEMA), (parts.POP, parts.OBJ_SCHEMA)]
    state = parts.EXTRA_STATE
    # Systemgodkendelsens svar - kun naar flaget er taendt, saa en app
    # uden godkendelse ikke slaebber en tom samling rundt.
    if parts.APPROVAL_ON:
        cols.append((parts.APPROVERS, parts.APPR_SCHEMA))
        state += ";\n" + parts.APPR_STATE
    domain_app.write_app(cfg, os.path.join(HERE, ".."),
                         extra_collections=cols, extra_state=state)


if __name__ == "__main__":
    main()
