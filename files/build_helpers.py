# -*- coding: utf-8 -*-
"""
Builds ScreenVhPlan.pa.yaml content using gen_screen.py helpers.
"""
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import (
    Ctrl, render, render_screen,
    C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
    C_PRIMARY, C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_DISABLED_BG,
    C_DIVIDER, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT,
)

OUT_DIR = r"c:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\SAP\SAP Site\html\powerapp-vhplan"

# ---------------------------------------------------------------------------
# Generic small helpers
# ---------------------------------------------------------------------------

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
    return Ctrl(name, "ModernText", props=props)


def group(name, children, direction="Vertical", gap=8, height=None, width="Parent.Width",
          align_items="Stretch", fill=None, border_color=None, border_thickness=None,
          radius=None, pad=None, fill_portions=None, wrap=None, justify=None,
          overflow_y=None, visible=None, drop_shadow="None", align_in_container=None,
          layout_min_width=None):
    props = {
        "BorderStyle": "BorderStyle.None" if not border_color else None,
        "BorderColor": border_color,
        "BorderThickness": str(border_thickness) if border_thickness is not None else ("1" if border_color else None),
        "DropShadow": f"DropShadow.{drop_shadow}",
        "LayoutAlignItems": f"LayoutAlignItems.{align_items}",
        "LayoutDirection": f"LayoutDirection.{direction}",
        "LayoutGap": str(gap),
        "LayoutMinWidth": str(layout_min_width) if layout_min_width is not None else "0",
        # The working reference app (powerapp-materialer) always declares FillPortions
        # explicitly on every GroupContainer/Gallery - default to 0 (don't flex-grow;
        # size from the Height formula/content) unless the caller opts into growing (1).
        # Omitting this property entirely appears to leave flex sizing ambiguous in
        # Studio's modern layout engine, which can collapse containers to near-zero size.
        "FillPortions": str(fill_portions) if fill_portions is not None else "0",
    }
    if fill is not None:
        props["Fill"] = fill
    if height is not None:
        props["Height"] = str(height)
    if width is not None:
        props["Width"] = str(width)
    if radius is not None:
        props["RadiusBottomLeft"] = str(radius)
        props["RadiusBottomRight"] = str(radius)
        props["RadiusTopLeft"] = str(radius)
        props["RadiusTopRight"] = str(radius)
    if pad is not None:
        if isinstance(pad, tuple):
            t, r, b, l = pad
        else:
            t = r = b = l = pad
        props["PaddingTop"] = str(t)
        props["PaddingRight"] = str(r)
        props["PaddingBottom"] = str(b)
        props["PaddingLeft"] = str(l)
    if wrap is not None:
        props["LayoutWrap"] = wrap
    if justify is not None:
        props["LayoutJustifyContent"] = f"LayoutJustifyContent.{justify}"
    if overflow_y is not None:
        props["LayoutOverflowY"] = f"LayoutOverflow.{overflow_y}"
    if visible is not None:
        props["Visible"] = visible
    if align_in_container is not None:
        props["AlignInContainer"] = f"AlignInContainer.{align_in_container}"
    props = {k: v for k, v in props.items() if v is not None}
    return Ctrl(name, "GroupContainer", variant="AutoLayout", props=props, children=children)


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
    return Ctrl(name, "ModernButton", props=props)


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
    return Ctrl(name, "ModernTextInput", props=props)


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
    return Ctrl(name, "ModernNumberInput", props=props)


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
    return Ctrl(name, "ModernDropdown", props=props)


def label_row(name, label_text, required=False, width="Parent.Width"):
    kids = [text_ctrl(f"{name}Lbl", f"\"{label_text}\"", size=13, weight="Semibold", height=20, wrap="false")]
    if required:
        kids.append(text_ctrl(f"{name}Star", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                               height=20, width=10, wrap="false", accessible="\"Skal udfyldes\""))
    return group(f"{name}Row", kids, direction="Horizontal", gap=3, height=20, align_items="Center", width=width)


def field_cell(name, label_text, input_ctrl, required=False, hint_text=None, width=None, height=62,
               fill_portions_formula="If(App.Width < 1024, 0, 1)"):
    kids = [label_row(name, label_text, required=required), input_ctrl]
    h = height
    if hint_text is not None:
        kids.append(text_ctrl(f"{name}Hint", hint_text, size=12, color=C_MUTED, height=16, wrap="false"))
        h = height + 18
    return group(name, kids, direction="Vertical", gap=6, height=h,
                 width=width or "If(App.Width < 640, Parent.Width, (Parent.Width - 20) / 2)",
                 align_items="Stretch", fill_portions=fill_portions_formula, align_in_container="Start")


def two_col_row(name, cell_a, cell_b, height=62):
    return group(name, [cell_a, cell_b], direction="Horizontal", gap=20,
                 height=f"If(App.Width < 640, 2 * {height} + 20, {height})", wrap="true")


def badge(name, text, size=11, width=64):
    return text_ctrl(name, text, size=size, color=C_MUTED, weight="Semibold", height=22,
                      width=width, wrap="false",
                      extra={"Fill": C_NEUTRAL_BG, "Align": "Align.Center",
                             "AlignInContainer": "AlignInContainer.Center",
                             "PaddingLeft": "10", "PaddingRight": "10",
                             "RadiusBottomLeft": "12", "RadiusBottomRight": "12",
                             "RadiusTopLeft": "12", "RadiusTopRight": "12"})


print("build helpers ready")
