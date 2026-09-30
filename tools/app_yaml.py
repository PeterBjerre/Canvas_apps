# -*- coding: utf-8 -*-
"""
App.pa.yaml - EEN skriver for alle apps.

Her stod fem skrivere (Hub, VH-plan, Equipment, Material, FL) og en sjette
i BIO SAP, hver med sin egen loekke over linjerne (REVIEW.md C5). De gjorde
det samme med smaa forskelle, og ingen af dem satte App.OnError.

    import app_yaml
    app_yaml.write(out_dir, formulas=..., onstart=..., start_screen="ScreenX")
"""
import os

# APP.OnError - DEN SAMME I ALLE APPS
#
# OnError koerer kun for fejl, ingen formel har fanget med IfError. Uden den
# viser Power Apps sin egen standardbanner, og fejlen findes ingen andre
# steder. Her logges den til Monitor/Application Insights (Trace) og vises
# med vores egen tekst (REVIEW.md D26).
ON_ERROR = """Trace(
    "Unhandled error",
    TraceSeverity.Error,
    { Message: FirstError.Message, Source: FirstError.Source, Observed: FirstError.Observed }
);
Notify("Something went wrong: " & FirstError.Message, NotificationType.Error)"""


def block(prop, text):
    """En egenskab som YAML-blok med '=' foran foerste ikke-tomme linje."""
    out = [f"    {prop}: |"]
    first = True
    for line in text.split("\n"):
        if not line.strip():
            out.append("")
        elif first:
            out.append("      =" + line)
            first = False
        else:
            out.append("      " + line)
    return out


def render(formulas, onstart, start_screen, on_error=ON_ERROR):
    """Hele App.pa.yaml som tekst. start_screen er et skaermnavn eller en
    formel (BIO SAP vaelger skaerm efter dyblinket)."""
    out = ["App:", "  Properties:"]
    out += block("Formulas", formulas)
    out += block("OnError", on_error)
    out += block("OnStart", onstart)
    if "\n" in start_screen:
        out += block("StartScreen", start_screen)
    else:
        out += ["    StartScreen: |-", f"        ={start_screen}"]
    out += ["    Theme: |-", "        =PowerAppsTheme"]
    return "\n".join(out) + "\n"


def write(out_dir, formulas, onstart, start_screen, on_error=ON_ERROR):
    """Skriv App.pa.yaml i out_dir. Returnerer teksten."""
    content = render(formulas, onstart, start_screen, on_error)
    with open(os.path.join(out_dir, "App.pa.yaml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(content)
    return content
