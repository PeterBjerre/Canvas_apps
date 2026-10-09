# -*- coding: utf-8 -*-
"""Skriver ../App.pa.yaml for Measuring Point-appen.

Det hele staar i tools/domain_app.py - samlingsskemaet, tilstanden og de
navngivne formler er ens for de tre domaeneapps. Skal denne app have
noget andet, skrives det her (se SKILL.md "Hvem ejer hvad").
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import domain_config as cfg
import domain_app
import mp_parts as parts


def main():
    # Godkendelsens samlinger og tilstand (issue #210, fase 4) - kun naar
    # flaget er taendt, saa en app uden godkendelse ikke slaeber tomme
    # samlinger rundt. Uden flaget er App.pa.yaml uaendret.
    cols, state = [], ""
    if parts.APPROVAL_ON:
        cols = [(parts.APPROVERS, parts.APPR_SCHEMA), (parts.CREATORS, parts.CRE_SCHEMA)]
        state = parts.APPR_STATE
    domain_app.write_app(cfg, os.path.join(HERE, ".."),
                         extra_collections=cols, extra_state=state)


if __name__ == "__main__":
    main()
