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
from build_helpers import app_frame
from gen_screen import C_APP_BG
from side_nav import side_nav

# Tom vaerdi pr. feltart i samlingsskemaet.
EMPTY = {"num": "0", "date": "Blank()", "long": '""', "choice": '""', "text": '""',
         "bool": "false"}


def _row_schema(cfg):
    s = {"RowId": "0", "ItemKey": '""', "RequestNo": '""',
         "Status": '""', "FileCount": "0",
         cfg.C_TEXT: '""', "Plant": '""'}
    for col, _lab, kind, _ch in dp.FIELDS:
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
    ]


def formulas(cfg):
    return (
        tok.formula() + "\n\n" + lay.formula() + "\n\n" + perm.formula() + "\n\n"
        "// Vaerkerne. Eneste opslagsliste appen laeser, og den laeses foerst,\n"
        "// naar dropdownen aabnes.\n"
        f"colDomPlants = Sort(ForAll({cfg.L_PLANTS} As R, {{ Value: R.Title }}), Value);"
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
// Listen: false = Compact, true = All columns (issue #67/#68).
Set(varDomAllCols, false);

// Er formularen blevet tjekket? Styrer om en kraevet feltkant maa vaere
// roed. false ved opstart: en tom formular, ingen har roert, skal ikke
// staa og lyse roedt. Saettes af Gem/Indsend - se domain_parts.REQUIRED.
Set(varDomValidated, false)'''


def onstart(cfg, extra_collections=(), extra_state=""):
    # Temaet saettes FOER resten: skaermen tegner sig selv ud af C, og C
    # laeser darkModeEnabled.
    body = _collection_block(cfg, extra_collections) + "\n\n" + tok.onstart_block() + "\n\n" + STATE
    if extra_state:
        body += ";\n\n" + extra_state
    return body


def write_app(cfg, app_dir, extra_collections=(), extra_state=""):
    """App.pa.yaml. OnStart HENTER INGEN DATA - raekkerne hentes i
    skaermens OnVisible. Kun samlingsskemaerne og tilstanden staar her.

    extra_collections / extra_state: det, der kun er den ene apps - fx
    Materials' fakturaimport (Material App/build/invoice_parts.py). De
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


def build_screen(cfg, parts, render):
    """Skaermen: formularen og listen i een spalte; detaljer og dokumenter
    er popups. parts er appens *_parts (build_form, build_rows); render er
    gen_screen.render_screen - eller BIO SAP's opsamler."""
    dp.use(cfg)
    root = app_frame("Dom", dp.build_bar(), [parts.build_form(), parts.build_rows()])
    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    nav, overlay = side_nav("Dom", cfg.APP_KEY)
    # Appens EGNE popupper ([sloer, popup], fx Materials' fakturaimport).
    # De staar efter de faelles og foer sidebarens aabne panel.
    own = parts.build_popups() if hasattr(parts, "build_popups") else []
    # Sloeret FOER popupperne: kontrollerne tegnes i den raekkefoelge, de
    # staar, saa det, der skal ligge bagved, skal staa foerst.
    return render(cfg.SCREEN,
                  {"Fill": C_APP_BG, "OnVisible": on_visible()},
                  [root, *nav, dp.build_backdrop(), dp.build_details(),
                   dp.build_attachments(), *own, *overlay,
                   # Bekraeftelserne og ventespinneren - oeverst.
                   *dp.build_delete_confirm(), *dp.build_submit_confirm()])


def write_screen(cfg, parts, app_dir, render):
    content = build_screen(cfg, parts, render)
    out = os.path.join(app_dir, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")
