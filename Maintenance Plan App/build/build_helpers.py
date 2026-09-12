# -*- coding: utf-8 -*-
"""
Genbrugelige kontrol-byggere. Styling er uaendret fra den oprindelige app
(samme farver, radier, skriftstoerrelser og polstring som powerapp-materialer).

Det eneste der er lavet om, er hoejdemodellen: group() regner selv sin hoejde
ud af boernenes hoejder plus gaps og padding, i stedet for at en formel i
YAML'en refererer andre kontrollers .Height. Se gen_screen.stack_height.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (
    Ctrl, render, render_screen, stack_height, row_height,
    C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
    C_PRIMARY, C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_DISABLED_BG,
    C_DIVIDER, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT,
    SHELL_W, EDITOR_W, RAIL_W, SPLIT_GAP, OUT_DIR,
)

# Braekpunkt hvor et to-kolonne-felt stables lodret.
TWO_COL_MIN = 640


def text_ctrl(name, text, size=14, color=C_TITLE, weight=None, wrap="false",
              align=None, height=20, width=None, fill=C_TRANSPARENT,
              accessible=None, visible=None, layout_min_width=None, extra=None):
    props = {
        "AccessibleLabel": accessible if accessible else text,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Color": color,
        "Fill": fill,
        "Font": FONT,
        "Height": str(height),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Size": str(size),
        "Text": text,
        "Wrap": wrap,
    }
    if weight:
        props["FontWeight"] = f"FontWeight.{weight}"
    if align:
        props["Align"] = f"Align.{align}"
    if width is not None:
        props["Width"] = str(width)
    if visible is not None:
        props["Visible"] = visible
    if layout_min_width is not None:
        props["LayoutMinWidth"] = str(layout_min_width)
    if extra:
        props.update(extra)
    return Ctrl(name, "ModernText", props=props, h=height, vis=visible)


def group(name, children, direction="Vertical", gap=8, height=None, width="Parent.Width",
          align_items="Stretch", fill=None, border_color=None, border_thickness=None,
          radius=None, pad=None, fill_portions=None, wrap=None, justify=None,
          overflow_y=None, overflow_x=None, visible=None, drop_shadow="None", align_in_container=None,
          layout_min_width=None, wrap_rows=1):
    """height=None betyder: regn hoejden ud af boernene (anbefalet).

    Angiv kun height eksplicit, naar containeren bevidst skal have en fast
    hoejde og selv klippe/scrolle sit indhold.
    """
    if pad is not None:
        if isinstance(pad, tuple):
            pt, pr, pb, pl = pad
        else:
            pt = pr = pb = pl = pad
    else:
        pt = pr = pb = pl = 0

    if height is None:
        if direction == "Vertical":
            height = stack_height(children, gap, pt, pb)
        else:
            height = row_height(children, pt, pb, rows=wrap_rows, gap=gap)

    props = {
        "BorderStyle": "BorderStyle.None" if not border_color else None,
        "BorderColor": border_color,
        "BorderThickness": str(border_thickness) if border_thickness is not None else ("1" if border_color else None),
        "DropShadow": f"DropShadow.{drop_shadow}",
        "LayoutAlignItems": f"LayoutAlignItems.{align_items}",
        "LayoutDirection": f"LayoutDirection.{direction}",
        "LayoutGap": str(gap),
        "LayoutMinWidth": str(layout_min_width) if layout_min_width is not None else "0",
        # Referenceappen (powerapp-materialer) saetter altid FillPortions
        # eksplicit paa GroupContainer/Gallery. 0 = voks ikke.
        "FillPortions": str(fill_portions) if fill_portions is not None else "0",
        "Height": str(height),
    }
    if fill is not None:
        props["Fill"] = fill
    if width is not None:
        props["Width"] = str(width)
    if radius is not None:
        props["RadiusBottomLeft"] = str(radius)
        props["RadiusBottomRight"] = str(radius)
        props["RadiusTopLeft"] = str(radius)
        props["RadiusTopRight"] = str(radius)
    if pad is not None:
        props["PaddingTop"] = str(pt)
        props["PaddingRight"] = str(pr)
        props["PaddingBottom"] = str(pb)
        props["PaddingLeft"] = str(pl)
    if wrap is not None:
        props["LayoutWrap"] = wrap
    if justify is not None:
        props["LayoutJustifyContent"] = f"LayoutJustifyContent.{justify}"
    if overflow_y is not None:
        props["LayoutOverflowY"] = f"LayoutOverflow.{overflow_y}"
    if overflow_x is not None:
        props["LayoutOverflowX"] = f"LayoutOverflow.{overflow_x}"
    if visible is not None:
        props["Visible"] = visible
    if align_in_container is not None:
        props["AlignInContainer"] = f"AlignInContainer.{align_in_container}"
    props = {k: v for k, v in props.items() if v is not None}
    return Ctrl(name, "GroupContainer", variant="AutoLayout", props=props, children=children,
                h=height, vis=visible)


def button(name, text, onselect, primary=False, danger=False, width=140, height=36,
           display_mode=None, base_color=None, layout_min_width=None, visible=None,
           accessible=None):
    props = {
        "AccessibleLabel": accessible if accessible else text,
        "Align": "Align.Center",
        "AlignInContainer": "AlignInContainer.Center",
        "Font": FONT,
        "FontWeight": "FontWeight.Semibold",
        "Height": str(height),
        "Layout": "ButtonLayout.TextOnly",
        "OnSelect": onselect,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "Text": text,
        "VerticalAlign": "VerticalAlign.Middle",
        "Width": str(width),
    }
    if danger:
        props["Appearance"] = "ButtonAppearance.Secondary"
        props["BorderColor"] = C_INVALID_FG
        props["BorderThickness"] = "1"
        props["Color"] = C_INVALID_FG
    elif primary:
        props["BasePaletteColor"] = base_color or C_PRIMARY
        props["Color"] = C_WHITE
    else:
        props["Appearance"] = "ButtonAppearance.Secondary"
        props["BorderColor"] = C_CARD_BORDER
        props["BorderThickness"] = "1"
        props["Color"] = C_TITLE
    if display_mode:
        props["DisplayMode"] = display_mode
    if layout_min_width is not None:
        props["LayoutMinWidth"] = str(layout_min_width)
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "ModernButton", props=props, h=height, vis=visible)


def button_row(name, buttons, container_w, gap=8, height=36, align_items="Center"):
    """Knapraekke der ALDRIG ombryder.

    Den oprindelige raekke havde faste knapbredder (104 + 104 + 112 + gaps =
    336 px) i et kort med 324 px indhold. Den ombroed derfor til to linjer,
    mens raekkens hoejde stod fast paa 36 - og den sidste knap blev klippet.
    Her deler knapperne bredden ligeligt, saa de altid passer.
    """
    n = len(buttons)
    w = f"({container_w} - {gap * (n - 1)}) / {n}"
    for b in buttons:
        b.props["Width"] = w
        b.props["LayoutMinWidth"] = "0"
    return group(name, buttons, direction="Horizontal", gap=gap, height=height,
                 align_items=align_items)


def text_input(name, default, placeholder="\"\"", max_length=None, required_formula="false",
               width="Parent.Width", height=36, display_mode=None, ttype=None,
               onchange=None):
    props = {
        "AccessibleLabel": f"\"{name}\"",
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": C_INPUT_BG if not display_mode else f"If({display_mode} = DisplayMode.Disabled, {C_DISABLED_BG}, {C_INPUT_BG})",
        "Font": FONT,
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Placeholder": placeholder,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Trim(Self.Text)), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }
    if max_length is not None:
        props["MaxLength"] = str(max_length)
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    if ttype is not None:
        props["Type"] = f"TextInputType.{ttype}"
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernTextInput", props=props, h=height)


def number_input(name, default, min_v=None, max_v=None, required_formula="false",
                 width="Parent.Width", height=36, display_mode=None):
    props = {
        "AccessibleLabel": f"\"{name}\"",
        "Appearance": "Appearance.Outline",
        "BorderColor": f"If({required_formula} && IsBlank(Self.Value), {C_REQUIRED}, {C_CARD_BORDER})",
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": C_INPUT_BG,
        "Font": FONT,
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Precision": "DecimalPrecision.'0'",
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Self.Value), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }
    if min_v is not None:
        props["Min"] = str(min_v)
    if max_v is not None:
        props["Max"] = str(max_v)
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    return Ctrl(name, "ModernNumberInput", props=props, h=height)


def dropdown(name, items, default, item_display="ThisItem.Value", required_formula="false",
             width="Parent.Width", height=36, display_mode=None, value_field="Value"):
    props = {
        "AccessibleLabel": f"\"{name}\"",
        "Appearance": "Appearance.Outline",
        "BorderColor": f"If({required_formula} && IsBlank(Self.Selected.{value_field}), {C_REQUIRED}, {C_CARD_BORDER})",
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": C_INPUT_BG,
        "Font": FONT,
        "Height": str(height),
        "ItemDisplayText": item_display,
        "Items": items,
        "LayoutMinWidth": "0",
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Self.Selected.{value_field}), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    return Ctrl(name, "ModernDropdown", props=props, h=height)


def label_row(name, label_text, required=False, width="Parent.Width"):
    kids = [text_ctrl(f"{name}Lbl", f"\"{label_text}\"", size=13, weight="Semibold", height=20, wrap="false")]
    if required:
        kids.append(text_ctrl(f"{name}Star", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                              height=20, width=10, wrap="false", accessible="\"Skal udfyldes\""))
    return group(f"{name}Row", kids, direction="Horizontal", gap=3, height=20, align_items="Center", width=width)


def field_cell(name, label_text, input_ctrl, required=False, hint_text=None, width=None,
               container_w=SHELL_W, fill_portions_formula="If(App.Width < 1024, 0, 1)"):
    """Et felt med label over. Hoejden regnes af indholdet - den er ikke laengere
    et magisk tal, saa et hoejere input (fx multiline) giver automatisk et
    hoejere felt."""
    kids = [label_row(name, label_text, required=required), input_ctrl]
    if hint_text is not None:
        kids.append(text_ctrl(f"{name}Hint", hint_text, size=12, color=C_MUTED, height=16, wrap="false"))
    w = width or f"If({container_w} < {TWO_COL_MIN}, {container_w}, ({container_w} - 20) / 2)"
    return group(name, kids, direction="Vertical", gap=6, width=w,
                 align_items="Stretch", fill_portions=fill_portions_formula,
                 align_in_container="Start")


def two_col_row(name, cell_a, cell_b, container_w=SHELL_W):
    """To felter side om side - stablet under braekpunktet.

    Hoejden foelger nu cellernes faktiske hoejde i stedet for et fast tal,
    og braekpunktet maales paa containerens egen bredde i stedet for
    App.Width. Item Editor-kortet er ca. 380 px smallere end skaermen, saa
    App.Width som maalestok fik felterne til at staa side om side laenge
    efter at der reelt var plads."""
    ha, hb = cell_a.h, cell_b.h
    tall = f"Max(({ha}), ({hb}))" if ha != hb else f"({ha})"
    h = f"If({container_w} < {TWO_COL_MIN}, ({ha}) + 20 + ({hb}), {tall})"
    return group(name, [cell_a, cell_b], direction="Horizontal", gap=20, height=h, wrap="true")


def badge(name, text, size=11, width=64):
    return text_ctrl(name, text, size=size, color=C_MUTED, weight="Semibold", height=22,
                     width=width, wrap="false",
                     extra={"Fill": C_NEUTRAL_BG, "Align": "Align.Center",
                            "AlignInContainer": "AlignInContainer.Center",
                            "PaddingLeft": "10", "PaddingRight": "10",
                            "RadiusBottomLeft": "12", "RadiusBottomRight": "12",
                            "RadiusTopLeft": "12", "RadiusTopRight": "12"})


def card(name, children, gap=14, visible=None):
    """Sektionskort i appens standardstil. Padding taelles automatisk med i
    hoejden - det var den fejl der gjorde hvert eneste kort 36 px for lavt."""
    return group(name, children, direction="Vertical", gap=gap,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14,
                 pad=(18, 18, 18, 18), visible=visible)
