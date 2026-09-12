# -*- coding: utf-8 -*-
"""
Generator for ScreenVhPlan.pa.yaml (Power Apps canvas app, VH-plan).
Builds a nested control tree and serializes it to the .pa.yaml source format
used by the canvas-authoring coauthoring session, matching the visual style
of the existing powerapp-materialer app (ScreenMaterialer / ScreenDetails).
"""
import json

OUT_DIR = r"c:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\SAP\SAP Site\html\powerapp-vhplan"

# ---------------------------------------------------------------------------
# Style constants (matched to ScreenMaterialer.pa.yaml / ScreenDetails.pa.yaml)
# ---------------------------------------------------------------------------
C_APP_BG = "RGBA(237, 241, 247, 1)"
C_CARD_BG = "RGBA(250, 251, 253, 1)"
C_CARD_BORDER = "RGBA(215, 222, 232, 1)"
C_TITLE = "RGBA(26, 34, 49, 1)"
C_MUTED = "RGBA(89, 102, 122, 1)"
C_REQUIRED = "RGBA(179, 50, 60, 1)"
C_PRIMARY = "RGBA(0, 103, 174, 1)"
C_PRIMARY2 = "RGBA(0, 122, 204, 1)"
C_WHITE = "RGBA(255, 255, 255, 1)"
C_TRANSPARENT = "RGBA(0, 0, 0, 0)"
C_INPUT_BG = "RGBA(255, 255, 255, 1)"
C_DISABLED_BG = "RGBA(240, 243, 248, 1)"
C_DIVIDER = "RGBA(228, 233, 241, 1)"

C_VALID_FG = "RGBA(21, 127, 92, 1)"
C_VALID_BG = "RGBA(232, 245, 238, 1)"
C_INVALID_FG = "RGBA(179, 50, 60, 1)"
C_INVALID_BG = "RGBA(253, 236, 236, 1)"
C_INFO_FG = "RGBA(0, 83, 140, 1)"
C_INFO_BG = "RGBA(222, 240, 252, 1)"
C_NEUTRAL_FG = "RGBA(89, 102, 122, 1)"
C_NEUTRAL_BG = "RGBA(228, 233, 241, 1)"

FONT = "Font.'Segoe UI'"

# ---------------------------------------------------------------------------
# Tiny control-tree DSL
# ---------------------------------------------------------------------------
class Ctrl:
    __slots__ = ("name", "control", "variant", "props", "children")

    def __init__(self, name, control, variant=None, props=None, children=None):
        self.name = name
        self.control = control
        self.variant = variant
        self.props = props or {}
        self.children = children or []


def render(node, item_indent):
    pad = " " * item_indent
    lines = [f"{pad}- {node.name}:"]
    body_indent = item_indent + 4
    bpad = " " * body_indent
    lines.append(f"{bpad}Control: {node.control}")
    if node.variant:
        lines.append(f"{bpad}Variant: {node.variant}")
    if node.props:
        lines.append(f"{bpad}Properties:")
        prop_indent = body_indent + 2
        ppad = " " * prop_indent
        content_indent = prop_indent + 4
        cpad = " " * content_indent
        for key in sorted(node.props.keys()):
            val = node.props[key]
            if val is None:
                continue
            val = str(val)
            lines.append(f"{ppad}{key}: |-")
            first = True
            for raw_line in val.split("\n"):
                if first:
                    lines.append(f"{cpad}={raw_line}")
                    first = False
                else:
                    lines.append(f"{cpad}{raw_line}")
    if node.children:
        lines.append(f"{bpad}Children:")
        child_indent = body_indent + 2
        for child in node.children:
            lines.extend(render(child, child_indent))
    return lines


def render_screen(screen_name, screen_props, children):
    lines = ["Screens:", f"  {screen_name}:", "    Properties:"]
    ppad = " " * 6
    cpad = " " * 10
    for key in sorted(screen_props.keys()):
        val = str(screen_props[key])
        lines.append(f"{ppad}{key}: |-")
        first = True
        for raw_line in val.split("\n"):
            if first:
                lines.append(f"{cpad}={raw_line}")
                first = False
            else:
                lines.append(f"{cpad}{raw_line}")
    lines.append("    Children:")
    for child in children:
        lines.extend(render(child, 6))
    return "\n".join(lines) + "\n"


print("Helper module loaded OK")
