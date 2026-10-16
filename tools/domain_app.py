# -*- coding: utf-8 -*-
"""
Equipments og Materials: det, de to apps' indgange havde ORDRET ens.

Her stod generate_app_onstart.py (145 linjer) og assemble_screen.py (79
linjer) i begge build-mapper med een funktionel forskel: Equipments EMPTY
manglede "bool" (REVIEW.md C5). Nu er indgangene faa linjer - appens
config og dens *_parts - og alt det faelles staar her.

Kompositionsfriheden fra SKILL.md er uaendret: en app, der skal noget
andet, giver sine egne dele (parts) eller bygger sin skaerm selv.
"""
import os

import app_yaml
import design_tokens as tok
import layout_tokens as lay
import domain_parts as dp
import permissions as perm
import display_text as dt
from build_helpers import (click_outside_overlay, app_frame, sticky_actions, request_shell, row_editor_panel,
                           button, fit_button_width, group, ICON_W)
from gen_screen import C_APP_BG
from side_nav import side_nav

# Tom vaerdi pr. feltart i samlingsskemaet.
# "dec" er et tal med decimaler, der tastes som tekst og gemmes i en
# Number-kolonne (tools/domain_parts.py) - i samlingen er det tekst.
EMPTY = {"num": "0", "date": "Blank()", "long": '""', "choice": '""', "text": '""',
         "bool": "false", "dec": '""'}


def _row_schema(cfg):
    s = {"RowId": "0", "ItemKey": '""', "RequestNo": '""',
         "Status": '""', "FileCount": "0",
         cfg.C_TEXT: '""', "Plant": '""'}
    for col, _lab, kind, _ch in dp.ROW_FIELDS:
        s[col] = EMPTY[kind]
    return s


def collections(cfg):
    return [
        # Spejlet af SharePoint-listen. ALDRIG sandheden - den hentes forfra
        # efter hver skrivning.
        ("colDomRows", _row_schema(cfg)),
        # Dokumenterne som de ligger i biblioteket. Identifier er den, en
        # sletning skal bruge; FileUrl er linket.
        ("colDomAttachments",
         {"RowId": "0", "FileName": '""', "FileUrl": '""', "Identifier": '""',
          "Selected": "false"}),
        # Hvad upload-flowet svarede pr. fil.
        ("colDomAttUp", {"Name": '""', "Ok": "false"}),
        # FL-soegningens resultat (tools/build_flsearch.py).
        ("colDomFl",
         {"Code": '""', "Description": '""', "Display": '""',
          "Maintainable": "false", "Level": '""'}),
        # Brugerens temavalg (tools/design_tokens.py).
        tok.prefs_schema(),
        # Paste rows' forhaandsvisning (UX-review L3).
        dp.paste_schema(),
    ]


def formulas(cfg):
    return (
        tok.formula() + "\n\n"
        + lay.formula("varDomEditorOpen" if getattr(cfg, "ROW_PANEL_ENABLED", False) else None)
        + "\n\n" + perm.formula() + "\n\n" +
        dt.formula() + "\n\n"
        "// Vaerkerne. Eneste opslagsliste appen laeser, og den laeses foerst,\n"
        "// naar dropdownen aabnes.\n"
        f"colDomPlants = Sort(ForAll({cfg.L_PLANTS} As R, {{ Value: R.Title }}), Value);"
        # Appens EGNE navngivne formler - fx Measuring Points opslagsliste
        # over karakteristikker (issue #210). Navngivne formler evalueres
        # dovent, saa en liste, ingen spoerger om, laeses ikke.
        + ("\n\n" + cfg.EXTRA_FORMULAS if getattr(cfg, "EXTRA_FORMULAS", "") else "")
    )


def _collection_block(cfg, extra=()):
    out = []
    for name, schema in list(collections(cfg)) + list(extra):
        fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
        # If(false, ...): kun skemaet. OnStart koerer samtidig med foerste
        # skaerms OnVisible, og ClearCollect+Clear her kunne toemme det,
        # OnVisible lige havde hentet (som hubbens fliser, issue #84).
        # Temaets samling (SaveData) er undtaget: den fyldes af LoadData i
        # selve OnStart, og BIO SAP fjerner blokken som ordret tekst.
        if name == tok.prefs_schema()[0]:
            out.append(f"ClearCollect({name}, {{ {fields} }});\nClear({name});")
        else:
            out.append(f"If(false, ClearCollect({name}, {{ {fields} }}));")
    return "\n\n".join(out)


STATE = '''Set(varDomMe, Lower(User().Email));
Set(varDomRequestNo, "");
Set(varDomRequestGuid, "");
// Kun raekker oprettet siden nu hoerer til en ny anmodning (refresh_rows_fx).
Set(varDomSessionStart, DateAdd(Now(), -2, TimeUnit.Minutes));
Set(varDomViewOnly, false);
Set(varDomBadgeOn, false);
Set(varDomCanEdit, false);
Set(varDomActiveRowId, Blank());
// Hvilken raekke detaljeruden viser. Blank = ruden er skjult.
Set(varDomDetailsId, Blank());
// Sletning sker bag en bekraeftelse: hvilken raekke, og om den er aaben.
Set(varDomDeleteId, Blank());
Set(varDomConfirmDelete, false);
// Hvilken raekke dokumentpopuppen viser. Blank = lukket.
Set(varDomDocsId, Blank());
Set(varDomRowStatus, "valid");
Set(varDomAttJson, "");
Set(varDomFlMsg, "");
// FL-vaelgeren (tools/fl_picker.py): soegeteksten, den sidste soegning,
// og om flowet koerer.
Set(varDomFlQuery, "");
Set(varDomFlLast, "");
Set(varDomFlBusy, false);
Set(varDomInfo, "");
// Er formularen blevet tjekket? Styrer om en kraevet feltkant maa vaere
// roed. false ved opstart: en tom formular, ingen har roert, skal ikke
// staa og lyse roedt. Saettes af Gem/Indsend - se domain_parts.REQUIRED.
Set(varDomValidated, false);
// Paste rows (UX-review L3): popuppen og den indsatte tekst.
Set(varDomPasteOpen, false);
Set(varDomPasteText, "")'''


def onstart(cfg, extra_collections=(), extra_state=""):
    # Temaet saettes FOER resten: skaermen tegner sig selv ud af C, og C
    # laeser darkModeEnabled.
    state = STATE
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        state = state.replace("Set(varDomDetailsId, Blank());\n", "")
    body = (_collection_block(cfg, extra_collections) + "\n\n"
            + tok.onstart_block() + "\n\n" + state)
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        body += ";\n\nSet(varDomEditorOpen, false)"
        if any(action.name == "btnDomRowMore" for action in (dp.HOOKS["row_actions"] or ())):
            body += ";\nSet(varDomMoreRowId, Blank())"
    if getattr(cfg, "ROW_EDITOR_TAB_VAR", None):
        body += f';\n\nSet({cfg.ROW_EDITOR_TAB_VAR}, "Details")'
    if extra_state:
        body += ";\n\n" + extra_state
    return body


def write_app(cfg, app_dir, extra_collections=(), extra_state=""):
    """App.pa.yaml. OnStart HENTER INGEN DATA - raekkerne hentes i
    skaermens OnVisible. Kun samlingsskemaerne og tilstanden staar her.

    extra_collections / extra_state: det, der kun er den ene apps. De
    skrives efter de faelles, i samme form."""
    dp.use(cfg)
    body = onstart(cfg, extra_collections, extra_state)
    content = app_yaml.write(app_dir, formulas(cfg), body, cfg.SCREEN)
    n = sum(body.count(x) for x in (cfg.L_ROWS, cfg.L_INDEX))
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer,",
          len(collections(cfg)), "arbejdssamlinger,", n, "datahentninger i OnStart.")


def on_visible():
    return (
        "Set(varDomMe, Lower(User().Email));\n"
        + dp.open_request_fx() + ";\n"
        + dp.refresh_rows_fx() + ";\n"
        + dp.clear_form_fx()
    )


SAVE_W = fit_button_width('"Save"') + ICON_W + 8


def _row_editor(form, panel_content=None, reset=None):
    order = f"Sort({dp.LIST_SCOPE}, RowId, SortOrder.Descending)"
    position = f"CountRows(Filter({order}, RowId > varDomActiveRowId)) + 1"
    record = "LookUp(colDomRows, RowId = varDomActiveRowId)"
    load = dp.load_row_fx().replace("ThisItem.", record + ".")
    previous_id = f"Index({order}, Max(1, {position} - 1)).RowId"
    next_id = f"Index({order}, Min(CountRows({order}), {position} + 1)).RowId"
    previous = f"Set(varDomActiveRowId, {previous_id});\n{load}"
    next_ = f"Set(varDomActiveRowId, {next_id});\n{load}"
    previous_mode = (f"If(IsBlank(varDomActiveRowId) || {position} <= 1, "
                     "DisplayMode.Disabled, DisplayMode.Edit)")
    next_mode = (f"If(IsBlank(varDomActiveRowId) || {position} >= CountRows({order}), "
                 "DisplayMode.Disabled, DisplayMode.Edit)")
    delete = button(
        "btnDomEditorDelete", '"Delete row"',
        "Set(varDomDeleteId, varDomActiveRowId); Set(varDomConfirmDelete, true)",
        danger=True, width=fit_button_width('"Delete row"'), height=lay.HIT_TOUCH,
        display_mode="If(varDomViewOnly, DisplayMode.Disabled, DisplayMode.Edit)",
        visible="!IsBlank(varDomActiveRowId)")
    cancel = button("btnDomEditorCancel", '"Cancel"', dp.clear_form_fx(),
                    width=fit_button_width('"Cancel"'), height=lay.HIT_TOUCH)
    # Gem-knappen hedder "Save" - baade for en ny og en hentet raekke. Den
    # har et ikon foran teksten, saa bredden skal have plads til ikonet
    # ogsaa (uden det blev "Save" klippet i hoejre side).
    save = button("btnDomSave", '"Save"',
                  dp.ADD_ROW_FX[0] or "false", primary=True,
                  width=SAVE_W, height=lay.HIT_TOUCH,
                  display_mode=dp.DM_ROW, icon='"Save"')
    save.props["AccessibleLabel"] = "Self.Text"
    if reset is None:
        reset = button("btnDomNew", '"Reset"', dp.clear_form_fx(),
                       tooltip='"Clear the form and start a new row"')
    reset.props["Width"] = str(fit_button_width('"Reset"'))
    reset.props["Height"] = str(lay.HIT_TOUCH)
    reset.h = lay.HIT_TOUCH
    # Bundbjaelken: Delete og Reset til venstre, Cancel og Save til hoejre.
    # Grupperne er Start-justeret og praecis knaphoeje - med Center tegnede
    # Studio de indlejrede knapper forskudt nedad og klippede dem. Er
    # panelet for smalt til begge par paa een linje (mobil), staar parrene
    # under hinanden.
    left_w = fit_button_width('"Delete row"') + 8 + fit_button_width('"Reset"')
    right_w = fit_button_width('"Cancel"') + 8 + SAVE_W
    for b in (delete, reset, cancel, save):
        b.props["AlignInContainer"] = "AlignInContainer.Start"
        b.props["LayoutMinWidth"] = b.props["Width"]
    left = group("conDomEditorDeleteAction", [delete, reset], direction="Horizontal",
                 gap=8, height=lay.HIT_TOUCH, width=left_w, align_items="Start",
                 align_in_container="Start")
    right = group("conDomEditorSaveActions", [cancel, save], direction="Horizontal",
                  gap=8, height=lay.HIT_TOUCH, width=right_w, align_items="Start",
                  align_in_container="Start", justify="End")
    one_line = f"({lay.PANEL_W_AT}) - 2 * 20 >= {left_w + 16 + right_w}"
    footer = group("conDomEditorFooter", [left, right], direction="Horizontal",
                   gap=8, height=f"If({one_line}, {lay.HIT_TOUCH}, {2 * lay.HIT_TOUCH + 8})",
                   width="Parent.Width", justify="SpaceBetween", align_items="Start")
    # Under hinanden (mobil) staar Cancel og Save stadig til hoejre.
    right.props["AlignInContainer"] = (f"If({one_line}, AlignInContainer.Start, "
                                       "AlignInContainer.End)")
    footer.props["LayoutDirection"] = (f"If({one_line}, LayoutDirection.Horizontal, "
                                       "LayoutDirection.Vertical)")
    footer.props["LayoutAlignItems"] = (f"If({one_line}, LayoutAlignItems.Start, "
                                        "LayoutAlignItems.Stretch)")
    content = (list(form.children[:-2]) + [form.children[-1]]
               if panel_content is None else panel_content)
    return row_editor_panel(
        "Dom", f'If(IsBlank(varDomActiveRowId), "New row", "Row " & Text({position}) & '
        f'" of " & Text(CountRows({order})))', content, footer,
        previous, next_, dp.clear_form_fx(), "varDomEditorOpen",
        previous_mode=previous_mode, next_mode=next_mode, side_by_side=True,
        multiple=f"CountRows({order}) > 1")


def _panel_extras(parts):
    """Appens egne linjer under felterne (Materials materialenummer, MP's
    nummer og taeller) - nu i sidepanelet i stedet for detaljepopuppen."""
    row = dp.ACTIVE
    lines = list(dp.HOOKS["details_rows"](row)) if dp.HOOKS["details_rows"] else []
    if hasattr(parts, "details_extra"):
        lines += list(parts.details_extra(row))
    if not lines:
        return []
    return [group("conDomPanelExtras", lines, direction="Vertical", gap=8,
                  visible="!IsBlank(varDomActiveRowId)")]


def build_screen(cfg, parts, render):
    """Skaermen: formularen og listen i een spalte; detaljer og dokumenter
    er popups. parts er appens *_parts (build_form, build_rows); render er
    gen_screen.render_screen - eller BIO SAP's opsamler."""
    dp.use(cfg)
    bar = dp.build_bar()
    panel_enabled = bool(getattr(cfg, "ROW_PANEL_ENABLED", False))
    form = parts.build_form(panel=True) if panel_enabled else parts.build_form()
    rows = parts.build_rows()
    footer = sticky_actions("Dom", dp.BAR_ACTIONS)
    if panel_enabled:
        extras = _panel_extras(parts)
        if hasattr(parts, "editor_panel_content"):
            panel_content = parts.editor_panel_content(form, extras)
        elif extras:
            panel_content = list(form.children[:-2]) + extras + [form.children[-1]]
        else:
            panel_content = None
        shell = request_shell("Dom", bar, None, None, rows,
                              editor=_row_editor(form, panel_content,
                                                 getattr(parts, "editor_reset", lambda: None)()),
                              footer=footer)
        root, editor = shell[0], shell[1:]
    else:
        root = app_frame("Dom", bar, [form, rows], footer=footer)
        editor = []
    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    nav, overlay = side_nav("Dom", cfg.APP_KEY)
    # Appens EGNE popupper ([sloer, popup], fx en popup, kun den ene app har).
    # Uden sidepanel staar de efter de faelles og foer sidebarens aabne panel.
    # MED sidepanel aabnes de fra panelet (fx Materials Purchase order text
    # og Reset's spoergsmaal), saa de skal ligge EFTER panelet og dets
    # sloer/klik-udenfor-lag - ellers tegnes de bagved (issue #279).
    own = parts.build_popups() if hasattr(parts, "build_popups") else []
    below, above = ([], own) if panel_enabled else (own, [])
    # Appens egne linjer nederst i detaljeruden (opt-in, issue #210).
    extra = parts.details_extra if hasattr(parts, "details_extra") else ()
    # Sloeret FOER popupperne: kontrollerne tegnes i den raekkefoelge, de
    # staar, saa det, der skal ligge bagved, skal staa foerst.
    # Et klik UDEN FOR sidepanelet lukker det - ogsaa naar panelet staar ved
    # siden af listen (der er scrimmet i row_editor_panel skjult).
    outside = ([click_outside_overlay("imgDomEditorOutside", dp.clear_form_fx(),
                                      "IfError(varDomEditorOpen, false)", "Close row editor")]
               if panel_enabled else [])
    return render(cfg.SCREEN,
                  {"Fill": C_APP_BG, "OnVisible": on_visible(),
                   **({"OnHidden": "Set(varDomEditorOpen, false)"} if panel_enabled else {})},
                                    [root, *nav, dp.build_backdrop(),
                                     *([] if panel_enabled else [dp.build_details(extra=extra)]),
                                     *([] if panel_enabled and hasattr(parts, "editor_panel_content")
                                         else [dp.build_attachments()]), *below, *overlay, *outside, *editor,
                                     *above,
                                     *dp.build_row_menu(), *dp.build_paste(),
                   # Bekraeftelserne og ventespinneren - oeverst.
                   *dp.build_delete_confirm(), *dp.build_submit_confirm()])


def write_screen(cfg, parts, app_dir, render):
    content = build_screen(cfg, parts, render)
    out = os.path.join(app_dir, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")
