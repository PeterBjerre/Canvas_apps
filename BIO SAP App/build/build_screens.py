# -*- coding: utf-8 -*-
"""
Bygger den samlede apps seks skaerme af de fem appers egne byggere.

    python3 build_screens.py            # alle seks
    python3 build_screens.py vhplan     # kun VH-planens to

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

Undtagelsen er VH-planen, som her er TO skaerme (se build_vhplan). Dens
komposition staar derfor her, og check_vhplan_split() stopper byggeriet,
hvis VH-plan-appen faar en kontrol, som ingen af de to skaerme har.
"""
import importlib.util
import os
import re
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
    if seen["props"].get("OnVisible"):
        raise SystemExit("Masterdata Hub har faaet en OnVisible - byg den ind her.")
    _write(d["screen"], render_screen(d["screen"], seen["props"], seen["children"]))


# ---------------------------------------------------------------------------
# Functional Location
# ---------------------------------------------------------------------------
def build_functionallocation():
    d = cb.BY_KEY["functionallocation"]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen = _capture(asm)
    asm.build_screen()
    own = seen["props"]["OnVisible"]
    if 'Param("reqid")' not in own:
        raise SystemExit("Functional Location: OnVisible laeser ikke laengere "
                         "Param(\"reqid\") - ret build_functionallocation().")
    # Appens egen OnVisible bliver staaende: den henter anmodningen, naar
    # dens id er et andet end det, der er hentet, og laegger en tom raekke,
    # naar der ingen er. Foran den staar domaenets OnStart, koert naar
    # hubben beder om en ny eller en anden anmodning.
    init = cb.with_reqid(cb.domain_onstart(d), d)
    seen["props"]["OnVisible"] = (open_block(d, init) + ";\n\n"
                                  + cb.with_reqid(own, d))
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], seen["props"], seen["children"]))


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
    expected = me + dp.refresh_rows_fx() + ";\n" + dp.clear_form_fx()
    if own != expected:
        raise SystemExit("%s: OnVisible er ikke laengere 'mig + hent raekker + ryd "
                         "formularen'.\nRet build_domain_app(), saa den passer." % d["folder"])
    # I den enkelte app ryddes formularen ved HVERT besoeg - appen startes
    # jo forfra hver gang. Her ville det smide en halvudfyldt formular
    # vaek, hver gang man kiggede forbi et andet domaene. Den ryddes derfor
    # kun, naar hubben beder om en ny; raekkerne hentes ved hvert besoeg,
    # saa listen viser det, der staar i SharePoint nu.
    # clear_form_fx() har stadig appens Dom-navne; de doebes om sammen med
    # resten, naar skaermen skrives (_write).
    init = cb.domain_onstart(d) + ";\n" + dp.clear_form_fx()
    seen["props"]["OnVisible"] = (open_block(d, init) + ";\n\n"
                                  + me + dp.refresh_rows_fx())
    # Felternes kontroller hedder inp<Kolonne>, con<Kolonne> og
    # con<Kolonne>Lbl - uden Dom. Manufacturer er et felt i begge domaener,
    # saa ogsaa de skal have domaenets praefiks. De faar Dom her, og _write
    # doeber det om sammen med resten.
    names = {c.name for r in seen["children"] for c in _walk(r)}
    plain = {}
    for n in names:
        m = re.match(r"([a-z]{2,5})([A-Z]\w*)$", n)
        if m and not m.group(2).startswith("Dom"):
            plain[n] = m.group(1) + "Dom" + m.group(2)
    if plain:
        pat = re.compile(r"\b(%s)\b" % "|".join(
            re.escape(n) for n in sorted(plain, key=len, reverse=True)))
        for r in seen["children"]:
            for c in _walk(r):
                c.name = plain.get(c.name, c.name)
        _subst_props(seen["children"], lambda v: pat.sub(lambda m: plain[m.group(1)], v))
        seen["props"] = {k: pat.sub(lambda m: plain[m.group(1)], v)
                         for k, v in seen["props"].items()}
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], seen["props"], seen["children"]), d)


# ---------------------------------------------------------------------------
# VH-planen: to skaerme
# ---------------------------------------------------------------------------
def _walk(c):
    yield c
    for k in c.children:
        yield from _walk(k)


def _subst_props(roots, fn):
    for r in roots:
        for c in _walk(r):
            for k, v in list(c.props.items()):
                if isinstance(v, str):
                    c.props[k] = fn(v)


def build_vhplan():
    """Skaerm 1 (ScreenVhPlan): Plan og Items - trin 1 og 2.
    Skaerm 2 (ScreenVhTasks): det aktive items task list, operationer,
    pakker, materialer og dokumenter, samt dispatch - trin 3 til 5.
    Gem-kortet (trin 6) staar paa begge, saa en kladde kan gemmes fra
    begge skaerme.

    SNITTET GAAR VED ITEMET. Alt paa skaerm 2 handler om det aktive item,
    og det vaelges paa skaerm 1 - eller i vaelgeren oeverst paa skaerm 2.

    DEN ENE REFERENCE PAA TVAERS
    ----------------------------
    Naar et andet item aabnes, nulstiller Items-kortet alle editorens
    felter - OGSAA task list-vaelgeren, som nu staar paa skaerm 2. En
    kontrol paa en anden skaerm kan ikke nulstilles derfra, saa den
    nulstilles i stedet, naar skaerm 2 vises. Dens OnChange skriver kun,
    naar valget er et andet end itemets eget, saa nulstillingen er en ren
    nulhandling. Omvendt: skifter man item paa skaerm 2, nulstilles
    editoren paa skaerm 1, naar den vises igen (varVhpEditorStale)."""
    d = cb.BY_KEY["vhplan"]
    _navigation()
    build = os.path.join(cb.ROOT, d["folder"], "build")
    sys.path.insert(0, build)
    from gen_screen import render_screen, C_APP_BG
    from build_helpers import app_frame, button, card, field_cell, dropdown
    from side_nav import side_nav
    import build_hero
    from build_hero import HELP_ON, HELP_ACTION
    from build_plan_header import build_plan_header, section_header
    import build_items
    from build_items import build_items_section
    from build_tasklist import (build_tasklist_section, build_dispatch_section,
                                build_email_fab, OPS_CW)
    from build_modal import (build_tasklist_picker_modal, build_longtext_modal,
                             build_modal_backdrop)
    from build_save import build_save_section
    from layout_tokens import fits, TWO_COL_MIN

    s1, s2 = d["screen"], cb.VH_TASKS_SCREEN
    reset_tl = "; Reset(drpVhpItemTasklist)"
    if reset_tl not in build_items.RESET_EDITOR_CONTROLS:
        raise SystemExit("VH-plan: Items-kortet nulstiller ikke laengere "
                         "drpVhpItemTasklist som forventet - ret build_vhplan().")

    def top_bar(nav):
        """VH-planens egen topbjaelke med een knap mere: til den anden skaerm."""
        orig = build_hero._actions
        build_hero._actions = lambda: orig() + [nav]
        try:
            return build_hero.build_top_bar()
        finally:
            build_hero._actions = orig

    # --- skaerm 1 -----------------------------------------------------------
    to_tasks = button("btnVhpToTasks", '"Task list"', f"Navigate({s2}, ScreenTransition.None)",
                      primary=True, width=120, height=36,
                      accessible='"Go to task list, operations and dispatch for the active item"')
    sec1 = [build_plan_header(), build_items_section(), build_save_section()]
    root1 = app_frame("Vhp", top_bar(to_tasks), sec1, body_gap=20)
    rail1, overlay1 = side_nav("Vhp", "vhplan", HELP_ON, HELP_ACTION)
    kids1 = [root1, rail1, *overlay1]
    _subst_props(kids1, lambda v: v.replace(reset_tl, ""))

    # I VH-plan-appen er en ny plan en ny app, saa editorens felter staar
    # altid paa deres Default. Her kan "New request" komme, mens en anden
    # plan er aaben - editoren nulstilles derfor ogsaa efter klargoeringen.
    init = (cb.with_reqid(cb.domain_onstart(d), d)
            + ";\nSet(varVhpEditorStale, true)")
    stale = ("// Skiftede man item paa skaerm 2, viser editoren her stadig det\n"
             "// gamle. Kontrollerne kan kun nulstilles fra deres egen skaerm.\n"
             "If(\n"
             "    varVhpEditorStale,\n"
             "    Set(varVhpEditorStale, false);\n"
             "    " + build_items.SEED_FL_PICKER.replace("\n", "\n    ") + ";\n"
             "    " + build_items.RESET_EDITOR_CONTROLS.replace(reset_tl, "") + "\n"
             ")")
    props1 = {"Fill": C_APP_BG, "OnVisible": open_block(d, init) + ";\n\n" + stale}

    # --- skaerm 2 -----------------------------------------------------------
    to_plan = button("btnVhtToPlan", '"Plan and items"',
                     f"Navigate({s1}, ScreenTransition.None)", width=150, height=36,
                     accessible='"Back to the plan and its items"')
    # ItemDisplayText maa kun vaere et felt: Studio afviser fx Coalesce dér
    # (issue #51). Teksten regnes derfor i Items, og Default slaar op i den
    # SAMME tabel, saa recorden har samme kolonner som listen.
    choices = ("ForAll(\n"
               "    Sort(colVhpItems, ItemId) As I,\n"
               '    { ItemId: I.ItemId, Label: "Item " & I.ItemId & " - " &\n'
               '        If(IsBlank(I.ShortText), "no short text", I.ShortText) }\n'
               ")")
    pick = dropdown(
        "drpVhtActiveItem", choices,
        f"LookUp({choices}, ItemId = varVhpActiveItemId)",
        item_display="ThisItem.Label",
        value_field="ItemId", label='"Active item"')
    pick.props["OnChange"] = (
        "If(\n"
        "    !IsBlank(Self.Selected.ItemId) && Self.Selected.ItemId <> varVhpActiveItemId,\n"
        "    Set(varVhpActiveItemId, Self.Selected.ItemId);\n"
        "    Set(varVhpItemValidated, false);\n"
        '    Set(varVhpFlMeta, "");\n'
        "    Set(varVhpEditorStale, true);\n"
        "    Reset(drpVhpItemTasklist)\n"
        ")")
    item_card = card("conVhtItemCard", [
        section_header("conVhtItemHead", "Active item",
                       "Everything below belongs to this item. Items are added on the plan screen.",
                       "Step 2"),
        field_cell("conVhtCellItem", "Item", pick,
                   width=fits(OPS_CW, TWO_COL_MIN, OPS_CW, "360"), container_w=OPS_CW,
                   fill_portions_formula="0"),
    ])
    sec2 = [item_card, build_tasklist_section(), build_dispatch_section(), build_save_section()]
    root2 = app_frame(cb.VH_TASKS_TAG, top_bar(to_plan), sec2, body_gap=20, body_pad_b=100)
    rail2, overlay2 = side_nav(cb.VH_TASKS_TAG, "vhplan", HELP_ON, HELP_ACTION)
    kids2 = [root2, rail2, build_modal_backdrop(), build_tasklist_picker_modal(),
             build_longtext_modal(), build_email_fab(), *overlay2]
    # Sidebarens VH-plan-punkt er markeret paa begge skaerme og lukker kun
    # menuen, naar man staar i appen, det peger paa. Paa skaerm 2 skal det
    # foere tilbage til skaerm 1.
    here = [c for r in kids2 for c in _walk(r)
            if c.name in ("img%sNavVhplan" % cb.VH_TASKS_TAG,
                          "img%sNavVhplanOpen" % cb.VH_TASKS_TAG)]
    if len(here) != 2:
        raise SystemExit("VH-plan: fandt ikke sidebarens VH-plan-punkt paa skaerm 2.")
    for c in here:
        c.props["OnSelect"] = f"Set(gblNavOpen, false); Navigate({s1}, ScreenTransition.None)"
    props2 = {"Fill": C_APP_BG,
              "OnVisible": ("// Task list-vaelgeren skal vise det AKTIVE items liste - det\n"
                            "// kan vaere skiftet paa skaerm 1. Se build_vhplan().\n"
                            "Reset(drpVhpItemTasklist)")}

    # Topbjaelken og gem-kortet staar paa begge skaerme. Paa skaerm 2 faar
    # de Vht i stedet for Vhp i navnet - et kontrolnavn er unikt i hele appen.
    names1 = {c.name for r in kids1 for c in _walk(r)}
    dup = sorted({c.name for r in kids2 for c in _walk(r)} & names1)
    new = {n: n.replace("Vhp", cb.VH_TASKS_TAG, 1) for n in dup}
    bad = [n for n in dup if "Vhp" not in n or new[n] in names1]
    if bad:
        raise SystemExit("VH-plan: kan ikke give disse et unikt navn paa skaerm 2:\n  "
                         + "\n  ".join(bad))
    if dup:
        pat = re.compile(r"\b(%s)\b" % "|".join(re.escape(n) for n in dup))
        for r in kids2:
            for c in _walk(r):
                c.name = new.get(c.name, c.name)
        _subst_props(kids2, lambda v: pat.sub(lambda m: new[m.group(1)], v))

    check_vhplan_split(kids1, kids2, set(new.values()))
    _write(s1, render_screen(s1, props1, kids1))
    _write(s2, render_screen(s2, props2, kids2))


def check_vhplan_split(kids1, kids2, copies):
    """Har de to skaerme tilsammen hver kontrol, VH-plan-appen har?

    Faar VH-plan en ny sektion eller en ny popup i sin assemble_screen.py,
    kommer den ikke automatisk med her - kompositionen er to skaerme og
    staar derfor i build_vhplan(). Uden det tjek ville den bare mangle."""
    d = cb.BY_KEY["vhplan"]
    asm = _load(d, "assemble_screen.py")
    seen = _capture(asm)
    asm.build_screen()
    alone = {c.name for r in seen["children"] for c in _walk(r)}
    both = {c.name for r in kids1 + kids2 for c in _walk(r)}
    # Sidebaren og rammen paa skaerm 2 hedder Vht; det gaelder ogsaa dem, der
    # ikke er kopier, fordi side_nav og app_frame navngiver efter praefikset.
    missing = sorted(n for n in alone - both
                     if n.replace("Vhp", cb.VH_TASKS_TAG, 1) not in both)
    if missing:
        raise SystemExit(
            "VH-plan har kontroller, som ingen af den samlede apps to VH-skaerme "
            "har:\n  " + "\n  ".join(missing[:30]) +
            "\n\nEr der kommet en ny sektion eller popup i Maintenance Plan App/"
            "build/assemble_screen.py? Saa skal den ogsaa placeres i\n"
            "BIO SAP App/build/build_screens.py, build_vhplan().")


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
