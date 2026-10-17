# -*- coding: utf-8 -*-
"""
Gem- og upload-sloeret med den moderne Progress bar (issue #305, del af #161).

Foer var "Saving"/"Sending"/"Uploading" det samme drejende SVG-hjul som
indlaesningen (build_helpers.loading_overlay). En gemning eller upload er en
igangvaerende handling, hvis fremskridt ikke kan maales - Learns
"indeterminate" Progress bar. Indlaesning ("Loading", "Opening",
"Searching") er stadig hjul (issue #302) og bygges ikke her.

    [sloer, bjaelke, (tekst)]

  sloer    det samme Image som foer, i sloerets farve, over hele skaermen
           og uden billede - saa ingen naar at trykke paa noget imens
  bjaelke  ModernProgressBar@1.0.0, Indeterminate, midt paa skaermen
  tekst    billedteksten (fx "Uploading files..."), som foer stod under
           hjulet i SVG'en; nu en ModernText under bjaelken. Learn: "The
           control doesn't display a label".

Alle tre har PRAECIS den Visible, sloeret havde foer: IfError(busy_var,
false). Ingen logik er aendret - kun det, der tegnes.

Kun egenskaber, Microsoft Learn dokumenterer for den opdaterede Progress
bar (check_layout regel 16f): ingen farve ud over ProgressColor.Brand
(appens brandfarve), ingen TabIndex, ingen Label.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_TITLE  # noqa: E402
from build_helpers import stable_scrim, text_ctrl  # noqa: E402

# Versionen er den, Microsoft Learns YAML-eksempel skriver. check_layout
# regel 16f afviser enhver anden.
PROGRESS_CONTROL = "ModernProgressBar@1.0.0"
BAR_W = "Min(320, App.Width - 32)"


def progress_bar(name, visible, accessible, *, width=BAR_W):
    """Den ubestemte bjaelke - EEN kontrol for hele repoet (issue #305)."""
    return Ctrl(name, PROGRESS_CONTROL, props={
        "AccessibleLabel": accessible,
        "Height": "8",
        "Indeterminate": "true",
        "ProgressColor": "ProgressColor.Brand",
        "Shape": "ProgressShape.Rounded",
        "Thickness": "ProgressThickness.Large",
        "Visible": visible,
        "Width": str(width),
    }, h=8, vis=visible)


def progress_overlay(name, busy_var, label, caption=None):
    """Sloeret mens der gemmes eller uploades - [sloer, bjaelke, (tekst)].

    name er sloerets navn som foer (img<App>Saving osv.); bjaelken hedder
    det samme med "prg", teksten med "txt" og "Caption". Staar SIDST i
    skaermens boern: det, der staar senere, ligger oeverst."""
    assert name.startswith("img"), name
    vis = f"IfError({busy_var}, false)"
    scrim = Ctrl(name, "Image", props={
        "AccessibleLabel": f'"{label}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(),
        "Height": "App.Height",
        "Image": '""',
        "TabIndex": "0",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)
    bar = progress_bar("prg" + name[3:], vis, f'"{label}"')
    bar.props["X"] = "(App.Width - Self.Width) / 2"
    bar.props["Y"] = "(App.Height - Self.Height) / 2"
    out = [scrim, bar]
    if caption:
        txt = text_ctrl("txt" + name[3:] + "Caption", f'"{caption}"', size=14, color=C_TITLE,
                        weight="Semibold", align="Center", height=24, width=BAR_W,
                        visible=vis)
        txt.props["X"] = "(App.Width - Self.Width) / 2"
        txt.props["Y"] = "App.Height / 2 + 16"
        out.append(txt)
    return out
