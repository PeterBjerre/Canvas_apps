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
import invoice_parts


def main():
    # Fakturaimporten er Materials' egen (invoice_parts.py, docs/34).
    domain_app.write_app(cfg, os.path.join(HERE, ".."),
                         extra_collections=invoice_parts.collections(),
                         extra_state=invoice_parts.STATE)


if __name__ == "__main__":
    main()
