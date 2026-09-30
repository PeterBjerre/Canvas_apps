# -*- coding: utf-8 -*-
"""
Bygger den samlede apps fem skaerme af de fem appers egne byggere.

    python3 build_screens.py            # alle fem
    python3 build_screens.py vhplan     # kun VH-planen

HVER APP I SIN EGEN PROCES
--------------------------
Equipments og Materials importerer begge et modul, der hedder
domain_config, fra hver sin build-mappe. I samme Python-proces ville den
anden faa den foerstes. Derfor bygges hver app i sin egen proces med kun
sin egen build-mappe paa sys.path - praecis som naar den bygges alene.

HVAD DER AENDRES I FORHOLD TIL DE FEM APPS
------------------------------------------
Kompositionen er appens egen: skaermen bygges af dens EGEN
build_screen(). Kun render_screen() byttes ud, saa skaermens navn og
OnVisible kan saettes - og sidebaren og hubben faar deres Navigate-kroge
(side_nav.SCREENS, build_hub.NEW_ACTION/OPEN_ACTION).

Oveni faar hver domaeneskaerm en ventespinner (loading_overlay), mens den
klargoeres - den faelles build_helpers.loading_overlay, og kun den.
"""
import importlib.util
import os
import subprocess
import sys

import combined as cb

PARTS = ["hub", "functionallocation", "vhplan", "equipment", "material"]


# ---------------------------------------------------------------------------
# Faelles
# ---------------------------------------------------------------------------
def _load(domain, module_file):
    """Importer en fil fra domaenets build-mappe under et unikt navn."""
    build = os.path.join(cb.ROOT, domain["folder"], "build")
    if build not in sys.path:
        sys.path.insert(0, build)
    path = os.path.join(build, module_file)
    spec = importlib.util.spec_from_file_location(
        "src_%s_%s" % (domain["key"], module_file[:-3]), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _navigation():
    """Sidebaren navigerer mellem skaerme i stedet for at starte apps."""
    import side_nav
    side_nav.SCREENS = dict(cb.SCREENS)


def _capture(mod):
    """Byt modulets render_screen ud med en, der gemmer argumenterne.

    Modulet har gjort 'from gen_screen import render_screen', saa navnet
    bor i DETS navnerum - det er dér, det skal byttes."""
    seen = {}

    def fake(name, props, children):
        seen["name"], seen["props"], seen["children"] = name, dict(props), children
        return ""
    mod.render_screen = fake
    return seen


def open_block(domain, init):
    """Klargoer domaeneskaermen, naar hubben eller et dyblink beder om det.

    FOERSTE BESOEG, "NEW REQUEST" OG "OPEN"
    ---------------------------------------
    want er det, der er bedt om: "new:<n>" fra flisens New request,
    "req:<guid>" fra raekkens Open, "link:<guid>" fra et dyblink - og ellers
    "new". Er det det samme, som skaermen sidst blev klargjort til
    (var<X>Opened), sker der INGENTING: man kommer tilbage til det, man
    forlod. Det er hele pointen med at samle apperne.

    Ellers koeres domaenets egen OnStart (init) - den, der i den enkelte
    app koerte ved opstart - med anmodningens id i stedet for Param("reqid").

    HVORFOR IKKE App.OnStart
    ------------------------
    Den koerer SAMTIDIG med skaermens OnVisible (non-blocking OnStart), saa
    en variabel sat dér er ikke sikkert sat her. Og den betales af alle, ogsaa
    dem der kun kigger paa hubben. Her betales et domaene, naar det aabnes."""
    t = domain["tag"]
    want = (f'Coalesce(\n'
            f'        {cb.want_var(t)},\n'
            f'        If(Lower(Param("{cb.DOMAIN_PARAM}")) = "{domain["key"]}", '
            f'"link:" & Param("reqid")),\n'
            f'        "new"\n'
            f'    )')
    body = "\n".join(("        " + l) if l.strip() else "" for l in init.split("\n")).lstrip()
    return (
        "// DEN SAMLEDE APP: klargoer skaermen, naar hubben eller et dyblink\n"
        "// beder om noget andet end det, den viser. Se BIO SAP App/build/\n"
        "// build_screens.py, open_block().\n"
        "With(\n"
        f"    {{ wantKey: {want} }},\n"
        "    If(\n"
        f"        wantKey <> Coalesce({cb.opened_var(t)}, \"\"),\n"
        f"        Set({cb.loading_var(t)}, true);\n"
        f"        Set({cb.opened_var(t)}, wantKey);\n"
        f"        Set(\n"
        f"            {cb.reqid_var(t)},\n"
        f'            If(StartsWith(wantKey, "req:"), Mid(wantKey, 5),\n'
        f'               StartsWith(wantKey, "link:"), Mid(wantKey, 6), "")\n'
        f"        );\n"
        f"        {body}\n"
        "    )\n"
        ")"
    )


def done(domain):
    """Sidste linje i domaeneskaermens OnVisible: klargoeringen er faerdig,
    spinneren forsvinder."""
    return (";\n\n// Klar - ventespinneren forsvinder.\n"
            f"Set({cb.loading_var(domain['tag'])}, false)")


def screen_props(props):
    """Skaermens egne egenskaber - uden Power Apps' LoadingSpinner.

    Her stod LoadingSpinner.Data. Den tegner Power Apps' EGET hjul midt paa
    skaermen, mens data hentes - samtidig med loading_overlay, som staar
    det samme sted. Resultatet var et hjul inden i hjulet (issue #64). Der
    skal vaere praecis een spinner, og det er den faelles
    (build_helpers.loading_overlay)."""
    props = dict(props)
    props.pop("LoadingSpinner", None)
    props.pop("LoadingSpinnerColor", None)
    return props


def loading_overlay(domain, label):
    """Ventespinneren, mens et domaene klargoeres - den FAELLES komponent
    (build_helpers.loading_overlay), ikke en kopi af den.

    Synlig, saa laenge var<X>Loading er sand: open_block saetter den
    foerst, done() nulstiller den sidst i OnVisible. Imens venter OnVisible
    paa SharePoint, og saa laenge daekker sloeret skaermen - ogsaa
    sidebaren - saa ingen naar at trykke paa en formular, der er ved at
    blive fyldt."""
    from build_helpers import loading_overlay as shared
    return shared(f"img{domain['tag']}Loading", cb.loading_var(domain["tag"]),
                  f"Loading {label}, please wait")


def _write(screen_name, text, domain=None):
    if domain is not None:
        text = cb.rename(text, domain)
        left = cb.leftover_shared_names(text)
        if left:
            raise SystemExit("%s: navne med det faelles praefiks er ikke doebt om:\n  %s"
                             % (screen_name, "\n  ".join(left[:20])))
    if "Launch(\"https://apps.powerapps.com" in text:
        raise SystemExit("%s: skaermen starter stadig en anden app med Launch().\n"
                         "I den samlede app er domaenerne skaerme - se "
                         "side_nav.SCREENS og build_hub.*_ACTION." % screen_name)
    out = os.path.join(cb.APP_DIR, screen_name + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("Wrote", os.path.relpath(out, cb.ROOT), "-", text.count("\n") + 1, "lines")


# ---------------------------------------------------------------------------
# Hubben
# ---------------------------------------------------------------------------
def build_hub():
    d = cb.BY_KEY["hub"]
    _navigation()
    sys.path.insert(0, os.path.join(cb.ROOT, d["folder"], "build"))
    # Importeret under sit EGET navn, foer assemble_hub goer det - saa er
    # det det samme modul, og krogene nedenfor gaelder ogsaa dér.
    import build_hub
    import hub_config

    by_app = {x["key"]: x for x in cb.DOMAINS if x["key"] != "hub"}

    def new_action(dom):
        x = by_app.get(dom["app"])
        if x is None:
            return None
        return (f"Set({cb.NEW_SEQ}, Coalesce({cb.NEW_SEQ}, 0) + 1);\n"
                f'Set({cb.want_var(x["tag"])}, "new:" & {cb.NEW_SEQ});\n'
                f"Navigate({x['screen']}, ScreenTransition.None)")

    branches = []
    for dom in hub_config.DOMAINS:
        x = by_app.get(dom["app"])
        if x is None:
            continue
        branches.append(
            f'        "{dom["key"]}",\n'
            f'            Set({cb.want_var(x["tag"])}, "req:" & ThisItem.RequestGuid);\n'
            f"            Navigate({x['screen']}, ScreenTransition.None)")
    open_action = (
        "If(\n"
        "    IsBlank(ThisItem.RequestGuid),\n"
        '    Notify("This request has no ID.", NotificationType.Error),\n'
        "    Switch(\n"
        "        ThisItem.Domain.Value,\n"
        + ",\n".join(branches) + ",\n"
        '        Notify("This kind of request has no screen in the app yet.", '
        "NotificationType.Warning)\n"
        "    )\n"
        ")")
    build_hub.NEW_ACTION = new_action
    build_hub.OPEN_ACTION = open_action

    asm = _load(d, "assemble_hub.py")
    seen = _capture(asm)
    asm.build_screen()
    from gen_screen import render_screen
    # Hubbens OnVisible henter flisernes taellesamling (colMdScope). Den
    # skal koere ved hvert besoeg - ogsaa her, hvor man kommer tilbage fra
    # et domaene, der netop har gemt.
    if seen["props"].get("OnVisible") != build_hub.SCOPE_REFRESH:
        raise SystemExit("Masterdata Hub's OnVisible er aendret - byg den ind her.")
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]))


# ---------------------------------------------------------------------------
# Functional Location
# ---------------------------------------------------------------------------
def build_functionallocation():
    d = cb.BY_KEY["functionallocation"]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen = _capture(asm)
    asm.build_screen()
    load = asm.load_part()
    if 'Param("reqid")' not in load:
        raise SystemExit("Functional Location: load_part() laeser ikke laengere "
                         "Param(\"reqid\") - ret build_functionallocation().")
    # Hentningen hoerer til KLARGOERINGEN (open_block): den koerer, naar
    # hubben beder om en ny eller en anden anmodning - ikke ved hvert
    # besoeg. Stod appens hele OnVisible her, genindlaeste et besoeg den
    # gamle anmodning oven i en ny, fordi New request ikke nulstiller
    # gblFlReqId (REVIEW.md D23). Den tomme raekke laegges stadig ved hvert
    # besoeg, naar der ingen er.
    init = (cb.with_reqid(cb.domain_onstart(d), d) + ";\n"
            + asm.ME + ";\n" + cb.with_reqid(load, d))
    seen["props"]["OnVisible"] = (open_block(d, init) + ";\n\n"
                                  + asm.ME + ";\n" + asm.ensure_row_part() + done(d))
    seen["children"].append(loading_overlay(d, "Functional Location"))
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]))


# ---------------------------------------------------------------------------
# Equipments og Materials
# ---------------------------------------------------------------------------
def build_domain_app(key):
    d = cb.BY_KEY[key]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen = _capture(asm)
    asm.build_screen()
    import domain_parts as dp
    own = seen["props"]["OnVisible"]
    me = "Set(varDomMe, Lower(User().Email));\n"
    expected = (me + dp.open_request_fx() + ";\n" + dp.refresh_rows_fx() + ";\n"
                + dp.clear_form_fx())
    if own != expected:
        raise SystemExit("%s: OnVisible er ikke laengere 'mig + dyblink + hent raekker + "
                         "ryd formularen'.\nRet build_domain_app(), saa den passer." % d["folder"])
    # I den enkelte app ryddes formularen ved HVERT besoeg - appen startes
    # jo forfra hver gang. Her ville det smide en halvudfyldt formular
    # vaek, hver gang man kiggede forbi et andet domaene. Den ryddes derfor
    # kun, naar hubben beder om en ny; raekkerne hentes ved hvert besoeg,
    # saa listen viser det, der staar i SharePoint nu.
    # clear_form_fx() har stadig appens Dom-navne; de doebes om sammen med
    # resten, naar skaermen skrives (_write).
    # Dyblinket/Open fra hubben hoerer til klargoeringen - den koerer kun,
    # naar hubben beder om en anden anmodning (samme greb som FL, D23).
    init = (cb.domain_onstart(d) + ";\n" + dp.clear_form_fx() + ";\n"
            + cb.with_reqid(dp.open_request_fx(), d))
    seen["props"]["OnVisible"] = (open_block(d, init) + ";\n\n"
                                  + me + dp.refresh_rows_fx() + done(d))
    # Her stod en regex-omdoebning: felternes kontroller hed inp<Kolonne>
    # og con<Kolonne> uden Dom, og Manufacturer findes i begge domaener.
    # domain_parts navngiver dem nu selv inpDom<Kolonne>/conDom<Kolonne>
    # (REVIEW.md A2). Slipper et navn uden Dom igennem, stopper
    # check_combined paa dubletten.
    # Spinneren har allerede domaenets eget praefiks.
    seen["children"].append(loading_overlay(
        d, {"equipment": "Equipments", "material": "Materials"}[key]))
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]), d)


# ---------------------------------------------------------------------------
# VH-planen
# ---------------------------------------------------------------------------
def build_vhplan():
    """VH-planen som EEN skaerm, som i appen selv.

    I VH-plan-appen er en ny plan en ny app, saa editorens felter staar
    altid paa deres Default. Her kan "New request" eller "Open" komme, mens
    en anden plan er aaben - editoren nulstilles derfor efter klargoeringen,
    med det samme, som Items-kortets "Open" goer."""
    d = cb.BY_KEY["vhplan"]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen = _capture(asm)
    asm.build_screen()
    if seen["props"].get("OnVisible"):
        raise SystemExit("VH-plan har faaet en OnVisible - byg den ind i build_vhplan().")
    import build_items
    init = (cb.with_reqid(cb.domain_onstart(d), d) + ";\n"
            "// Editoren skal vise den plan, der lige er klargjort.\n"
            + build_items.SEED_FL_PICKER + ";\n"
            + build_items.RESET_EDITOR_CONTROLS)
    seen["props"]["OnVisible"] = open_block(d, init) + done(d)
    seen["children"].append(loading_overlay(d, "VH-plan"))
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]))


# ---------------------------------------------------------------------------
BUILDERS = {
    "hub": build_hub,
    "functionallocation": build_functionallocation,
    "vhplan": build_vhplan,
    "equipment": lambda: build_domain_app("equipment"),
    "material": lambda: build_domain_app("material"),
}


def main(argv):
    if len(argv) > 1 and argv[1] == "--part":
        BUILDERS[argv[2]]()
        return 0
    which = argv[1:] or PARTS
    for k in which:
        if k not in BUILDERS:
            raise SystemExit("Ukendt del '%s'. Vaelg blandt: %s" % (k, ", ".join(PARTS)))
    for k in which:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--part", k],
                           cwd=cb.HERE)
        if r.returncode:
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
