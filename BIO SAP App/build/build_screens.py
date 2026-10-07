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
build_screen(render=...). BIO SAP giver sin egen render (_capture), saa
skaermens navn og OnVisible kan saettes - og sidebaren og hubben faar
deres Navigate-kroge (side_nav.use_screens, build_hub.use_actions).

Oveni faar hver domaeneskaerm et indlaesningskort (build_helpers.
open_overlay, issue #92), mens den klargoeres: hjul, det trin der er i
gang, en besked hvis det tager lang tid, og Retry/Close ved en fejl.
Klargoeringen staar paa en skjult knap (attach_open), saa Retry kan koere
den igen.
"""
import importlib.util
import os
import re
import subprocess
import sys

import combined as cb

PARTS = [d["key"] for d in cb.DOMAINS]


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
    side_nav.use_screens(cb.SCREENS)
    side_nav.NAV_PRE = {
        d["key"]: f'Set(gblNavTo, "{d["tag"]}")'
        for d in cb.DOMAINS if d["key"] != "hub" and d["key"] not in cb.LOOKUPS}
    # Issue Board vil vide, hvilken skaerm man kom fra, saa en ny sag kan
    # faa Application udfyldt (issue #114). Noeglen er appens noegle i
    # canvas_apps.json - den samme, IB_AppSections.ScreenKey bruger.
    if "issueboard" in cb.BY_KEY:
        side_nav.NAV_PRE["issueboard"] = lambda cur: f'Set(gblNavFrom, "{cur or ""}")'


def _capture():
    """En render, der gemmer argumenterne i stedet for at skrive YAML.

    Gives til appens build_screen(render=...). Her stod en udskiftning af
    render_screen i appens modul (monkeypatch) - nu er det en parameter,
    som appen selv tager imod (REVIEW.md C4)."""
    seen = {}

    def fake(name, props, children):
        seen["name"], seen["props"], seen["children"] = name, dict(props), children
        return ""
    return seen, fake

# ---------------------------------------------------------------------------
# Live status, mens en anmodning aabnes (issue #92)
#
# POWER APPS TEGNER KUN, NAAR DEN VENTER
# --------------------------------------
# En Set() midt i en formel bliver foerst synlig, naar formlen venter paa
# data - et kald til SharePoint. Derfor saettes trinteksten LIGE FOER et
# rigtigt kald, og kun dér. Et trin uden ventetid (afledte samlinger,
# Reset af felterne) naar aldrig at blive tegnet, og et kald, der kommer
# fra cachen (fx standardarbejdsplanerne anden gang), heller ikke. Det er
# netop "spring de hurtige trin over" - uden en timer og uden pauser.
# ---------------------------------------------------------------------------
STEP_FIND = "Finding the request"
STEP_NEW = "Setting up a new request"

# Trin -> den besked, der vises under det, naar det tager lang tid.
SLOW_HINTS = {
    STEP_FIND: "The request list is responding slowly.",
    "Loading plan details": "Still waiting for the plan details.",
    "Loading items and operations": "Plans with many items and operations take longer.",
    "Loading materials and documents": "Plans with many materials and documents take longer.",
    "Loading standard task lists": "Standard task lists load once per session.",
    "Loading functional locations": "Requests with many rows take longer to load.",
    "Loading saved rows": "Many saved rows take longer to load.",
}
SLOW_DEFAULT = "Still working on it."


def step_var(tag):
    """Det trin, indlaesningen er i - teksten, kortet viser."""
    return f"var{tag}LoadStep"


def failed_var(tag):
    """Sand, naar indlaesningen stoppede med en fejl. Kortet viser saa
    Retry og Close i stedet for hjulet."""
    return f"var{tag}LoadFailed"


def slow_var(tag):
    """Sat af timeren, naar indlaesningen tager laengere end ventet."""
    return f"var{tag}LoadSlow"


def open_button(tag):
    """Den skjulte knap, der baerer klargoeringen - se attach_open()."""
    return f"btn{tag}Open"


def set_step(tag, text):
    if text not in SLOW_HINTS:
        raise SystemExit("Trinet '%s' har ingen besked i SLOW_HINTS." % text)
    return f'Set({step_var(tag)}, "{text}")'


def mark_step(text, pattern, tag, step, what):
    """Saet trinet lige foer det kald, pattern finder - som et eget udsagn
    paa linjen foer, med samme indrykning. Findes moensteret ikke praecis
    een gang, er domaenets indlaesning aendret, og saa skal det ses her."""
    rx = re.compile(pattern, re.M)
    hits = list(rx.finditer(text))
    if len(hits) != 1:
        raise SystemExit("%s: fandt %d steder til trinet '%s' (forventet 1). "
                         "Ret mark_step-moenstrene i build_screens.py." % (what, len(hits), step))
    m = hits[0]
    return text[:m.start()] + m.group(1) + set_step(tag, step) + ";\n" + text[m.start():]


def open_block(domain, init, new_step=STEP_NEW):
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
    want = (f'If(\n'
            f'        gblNavTo = "{t}",\n'
            f'        "new:0",\n'
            f'        Coalesce(\n'
            f'        {cb.want_var(t)},\n'
            f'        If(Lower(Param("{cb.DOMAIN_PARAM}")) = "{domain["key"]}", '
            f'"link:" & Param("reqid")),\n'
            f'        "new"\n'
            f'    )\n    )')
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
            f'        Set(\n'
        f"            {cb.reqid_var(t)},\n"
        f'            If(StartsWith(wantKey, "req:"), Mid(wantKey, 5),\n'
        f'               StartsWith(wantKey, "edit:"), Mid(wantKey, 6),\n'
        f'               StartsWith(wantKey, "link:"), Mid(wantKey, 6), "")\n'
        f"        );\n"
        f'        Set({cb.mode_var(t)}, If(StartsWith(wantKey, "edit:") || (StartsWith(wantKey, "link:") && Lower(Coalesce(Param("mode"), "")) = "edit"), "edit", "view"));\n'
        "        // Live status (issue #92): the first step is the request itself.\n"
        f"        Set({failed_var(t)}, false);\n"
        f"        Set({slow_var(t)}, false);\n"
        f'        Set({step_var(t)}, If(IsBlank({cb.reqid_var(t)}), "{new_step}", "{STEP_FIND}"));\n'
        f"        {body}\n"
        "    )\n"
        ")"
    )


def stale_check(domain):
    """Foerst i domaeneskaermens OnVisible: har en sletning (hubbens eller
    skaermens egen, tools/request_delete.py) roert det, skaermen viser?

    gbl<X>Stale saettes af sletningen. Er skaermens aabne anmodning vaek,
    glemmes den (want og opened nulstilles), og open_block klargoer en ny,
    tom anmodning lige efter - ellers ville naeste gem oprette
    indeksraekken igen. Ellers koster det intet: opslaget sker kun, naar
    flaget er sat. var<X>StaleNow bruges af Equipments og Materials til at
    hente listen igen."""
    t = domain["tag"]
    now, stale = f"var{t}StaleNow", cb.stale_var(t)
    return (
        "// Har en sletning roert det, skaermen viser? (tools/request_delete.py)\n"
        f"Set({now}, Coalesce({stale}, false));\n"
        "If(\n"
        f"    {now},\n"
        f"    Set({stale}, false);\n"
        "    If(\n"
        f"        !IsBlank(var{t}RequestGuid) && IsBlank(LookUp(MD_RequestIndex, RequestGuid = var{t}RequestGuid)),\n"
        f"        Set({cb.want_var(t)}, Blank());\n"
        f'        Set({cb.opened_var(t)}, "")\n'
        "    )\n"
        ");\n\n")


def _drop_repeated_sets(onstart, later):
    """Fjern de Set(), som clear_form_fx() lige efter goer IGEN med samme
    vaerdi. Domaenets OnStart (domain_app.STATE) og formularens nulstilling
    satte fx varEqActiveRowId, varEqRowStatus og FL-soegningen to gange i
    traek. Kommentaren lige over en fjernet linje gaar med."""
    def norm(stmt):
        return re.sub(r"\s+", " ", stmt.strip().rstrip(";").strip())
    again = {norm(x) for x in re.split(r";\s*\n|;\s+(?=Set\()", later)
             if x.strip().startswith("Set(")}
    lines = onstart.split("\n")
    keep = []
    for line in lines:
        if line.strip().startswith("Set(") and norm(line) in again:
            while keep and keep[-1].strip().startswith("//"):
                keep.pop()
            continue
        keep.append(line)
    out = "\n".join(keep).rstrip()
    out = re.sub(r"\n\s*\n(\s*\n)+", "\n\n", out)
    return out.rstrip(";").rstrip()


def done(domain):
    """Sidste linje i domaeneskaermens OnVisible: klargoeringen er faerdig,
    spinneren forsvinder."""
    t = domain['tag']
    o = f"Coalesce({cb.opened_var(t)}, \"\")"
    return (";\n\n// Klar - ventespinneren forsvinder.\n"
            f"Set(var{t}BadgeOn, StartsWith({o}, \"req:\") || StartsWith({o}, \"edit:\") "
            f"|| StartsWith({o}, \"link:\"));\n"
            f"Set({cb.loading_var(t)}, false);\nSet({slow_var(t)}, false);\n"
            "Set(gblNavigating, false);\nSet(gblNavTo, \"\")")


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


def guarded(domain, body):
    """body (klargoeringen) i IfError. Fejler et kald, stopper hjulet, og
    kortet viser fejlen med Retry og Close (issue #92) - i stedet for en
    teknisk fejlbesked i et banner. Skaermen er ikke klargjort
    (var<X>Opened = ""), saa naeste besoeg proever igen."""
    t = domain["tag"]
    body = "\n".join(("    " + l) if l.strip() else "" for l in body.split("\n"))
    return ("IfError(\n" + body + ",\n"
            f"    Set({failed_var(t)}, true);\n"
            f'    Set({cb.opened_var(t)}, "")\n'
            ")" + done(domain))


def attach_open(domain, seen, fx, label):
    """Klargoeringen paa en skjult knap, kortet og timeren (issue #92).

    HVORFOR EN KNAP
    ---------------
    Retry skal koere klargoeringen igen, og en skaerms OnVisible kan ikke
    kaldes. Formlen staar derfor paa en skjult knap (samme greb som
    btnFlVerify), og baade OnVisible og Retry kalder den med Select().
    Formlen er den samme som foer - den er bare flyttet.

    Select() koerer knappen EFTER OnVisible. Saa skaermen ikke naar at vise
    den forrige anmodning et oejeblik, taender OnVisible sloeret selv, naar
    det er tydeligt, at der skal klargoeres (foerste besoeg, en ny
    anmodning, en anden anmodning). Klargoeringen slukker det igen sidst
    (done) - ogsaa naar den ender med ikke at have noget at goere."""
    from build_helpers import open_overlay, button
    t = domain["tag"]
    btn = open_button(t)
    loading, failed, slow, step = cb.loading_var(t), failed_var(t), slow_var(t), step_var(t)
    opened, want, reqid = cb.opened_var(t), cb.want_var(t), cb.reqid_var(t)
    seen["props"]["OnVisible"] = (
        "// Klargoeringen staar paa en skjult knap, saa Retry kan koere den igen\n"
        "// (BIO SAP App/build/build_screens.py, attach_open). Sloeret taendes\n"
        "// her med det samme, naar der tydeligvis skal klargoeres.\n"
        f'If(IsBlank({opened}) || If(gblNavTo = "{t}", "new:0", Coalesce({want}, {opened})) <> {opened},\n'
        f"    Set({loading}, true)\n);\n"
        f"Select({btn})")
    hidden = button(btn, '"Open"', fx, width=72, height=36, visible="false",
                    accessible='"Open the request"')
    hidden.props["X"] = "0"
    hidden.props["Y"] = "0"
    hints = ", ".join(f'"{k}", "{v}"' for k, v in SLOW_HINTS.items())
    lower_step = f'Lower(Left(Coalesce({step}, ""), 1)) & Mid(Coalesce({step}, ""), 2)'
    hub = cb.BY_KEY["hub"]["screen"]
    seen["children"].append(hidden)
    seen["children"].extend(open_overlay(
        t, loading, failed, slow,
        title_fx=(f'If(IfError({failed}, false), "Could not open the request", '
                  f'IsBlank({reqid}), "Preparing a new request", "Opening request")'),
        step_fx=(f'If(IfError({failed}, false), "Stopped while " & {lower_step}, '
                 f'Coalesce({step}, ""))'),
        hint_fx=(f'If(IfError({failed}, false), "Check your connection and try again.", '
                 f'IfError({slow}, false) && IfError({loading}, false), '
                 f'"Taking longer than usual. " & Switch(Coalesce({step}, ""), {hints}, '
                 f'"{SLOW_DEFAULT}"), "")'),
        retry_fx=(f"Set({failed}, false);\nSet({slow}, false);\n"
                  f'Set({opened}, "");\nSet({loading}, true);\nSelect({btn})'),
        close_fx=(f"Set({failed}, false);\nSet({want}, Blank());\n"
                  f'Set({opened}, "");\nNavigate({hub}, ScreenTransition.None)'),
        label=f"Loading {label}, please wait"))


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
                "Set(gblNavigating, true);\n"
                f'Set({cb.want_var(x["tag"])}, "new:" & {cb.NEW_SEQ});\n'
                f"Navigate({x['screen']}, ScreenTransition.None)")

    def request_action(prefix):
        branches = []
        for dom in hub_config.DOMAINS:
            x = by_app.get(dom["app"])
            if x is None:
                continue
            branches.append(
                f'        "{dom["key"]}",\n'
                f'            Set(gblNavigating, true);\n'
                f'            Set({cb.opened_var(x["tag"])}, "");\n'
                f'            Set({cb.want_var(x["tag"])}, "{prefix}:" & ThisItem.RequestGuid);\n'
                f"            Navigate({x['screen']}, ScreenTransition.None)")
        return (
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

    build_hub.use_actions(new_action, request_action("req"), request_action("edit"))

    asm = _load(d, "assemble_hub.py")
    seen, fake = _capture()
    asm.build_screen(render=fake)
    from gen_screen import render_screen
    # Hubbens OnVisible henter flisernes taellesamling (colMdScope). Den
    # skal koere ved hvert besoeg - ogsaa her, hvor man kommer tilbage fra
    # et domaene, der netop har gemt.
    if seen["props"].get("OnVisible") != build_hub.HUB_ON_VISIBLE:
        raise SystemExit("Masterdata Hub's OnVisible er aendret - byg den ind her.")
    from build_helpers import loading_overlay as shared_overlay
    seen["children"].append(shared_overlay("imgMdNavigating", "gblNavigating",
                                           "Opening, please wait", "Opening..."))
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]))


# ---------------------------------------------------------------------------
# Functional Location
# ---------------------------------------------------------------------------
def build_functionallocation():
    d = cb.BY_KEY["functionallocation"]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen, fake = _capture()
    asm.build_screen(render=fake)
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
    # Live status (issue #92): raekkerne er det ene tunge kald efter opslaget.
    load = mark_step(load, r"^([ \t]*)ClearCollect\(\n\s*colFlLoad,", d["tag"],
                     "Loading functional locations", "Functional Location")
    init = (cb.with_reqid(cb.domain_onstart(d), d) + ";\n"
            + asm.ME + ";\n" + cb.with_reqid(load, d))
    load_all = stale_check(d) + open_block(d, init) + ";\n\n" + asm.ME + ";\n" + asm.ensure_row_part()
    attach_open(d, seen, guarded(d, load_all), "Functional Location")
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
    seen, fake = _capture()
    asm.build_screen(render=fake)
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
    #
    # RAEKKERNE HENTES KUN VED KLARGOERINGEN (2026-10-05). De stod efter
    # open_block og blev hentet forfra ved HVERT besoeg - ogsaa naar man
    # bare skiftede tilbage via sidebaren. Kun skaermen selv skriver i
    # listen, og den henter selv forfra efter hver skrivning
    # (refresh_rows_fx). Det eneste andet sted, der aendrer raekkerne, er
    # hubbens sletning; den saetter gbl<X>Stale, og saa hentes de her.
    form = dp.clear_form_fx()
    init = (_drop_repeated_sets(cb.domain_onstart(d), cb.rename(form, d)) + ";\n" + form + ";\n"
            + cb.with_reqid(dp.open_request_fx(), d) + ";\n"
            # Live status (issue #92): opslaget i indekset er "Finding the
            # request" (open_block), raekkerne er det andet kald.
            + set_step(d["tag"], "Loading saved rows") + ";\n"
            + dp.refresh_rows_fx())
    # A failed load must neither leave the spinner on nor mark the screen as
    # prepared: the loading flag is cleared after IfError and the next visit retries.
    load = (stale_check(d) + open_block(d, init) + ";\n\n"
            f"If(\n    var{d['tag']}StaleNow,\n"
            + "\n".join("    " + l for l in dp.refresh_rows_fx().split("\n")) + "\n)")
    label = {"equipment": "Equipments", "material": "Materials"}[key]
    # Her stod en regex-omdoebning: felternes kontroller hed inp<Kolonne>
    # og con<Kolonne> uden Dom, og Manufacturer findes i begge domaener.
    # domain_parts navngiver dem nu selv inpDom<Kolonne>/conDom<Kolonne>
    # (REVIEW.md A2). Slipper et navn uden Dom igennem, stopper
    # check_combined paa dubletten.
    # Kortet og knappen har allerede domaenets eget praefiks.
    attach_open(d, seen, guarded(d, load), label)
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]), d)


# ---------------------------------------------------------------------------
# VH-planen
# ---------------------------------------------------------------------------
def vhplan_steps(onstart, tag):
    """Trinene i VH-planens indlaesning (Maintenance Plan App/build/
    build_load.py) - hvert sat lige foer det kald, det handler om.

        Finding the request              MD_RequestIndex (open_block)
        Loading plan details             MaintenancePlans + planens status
        Loading items and operations     boelge 1: MaintenanceItems, TaskListMain
        Loading materials and documents  boelge 2: materialer og dokumenter
        Loading standard task lists      MD_StandardTaskOperations - kun
                                         foerste gang i sessionen; ellers
                                         cachet og aldrig tegnet

    Adgangen (View/Edit) afgoeres af indeksraekken og IsAdmin, som hubben
    allerede har spurgt om. Den har ingen egen ventetid og derfor intet
    eget trin. Den tekniske fejlbesked (FirstError.Message) i banneret
    erstattes af kortets fejltilstand med Retry og Close."""
    what = "Maintenance Plan"
    onstart = mark_step(onstart, r"^([ \t]*)With\(\n\s*\{ pl: LookUp\(", tag,
                        "Loading plan details", what)
    onstart = mark_step(onstart, r"^([ \t]*)Concurrent\(\n\s*ClearCollect\(\n\s*colVhpItems,", tag,
                        "Loading items and operations", what)
    onstart = mark_step(onstart, r"^([ \t]*)Concurrent\(\n\s*ClearCollect\(\n\s*colVhpMaterials,", tag,
                        "Loading materials and documents", what)
    onstart = mark_step(onstart, r"^([ \t]*)With\(\n\s*\{ tl: LookUp\(colVhpTasklists", tag,
                        "Loading standard task lists", what)
    rx = re.compile(r'Notify\(\n\s*"Could not open the request: " & FirstError\.Message,'
                    r'\n\s*NotificationType\.Error\n\s*\);')
    onstart, n = rx.subn(f"Set({failed_var(tag)}, true);", onstart)
    if n != 1:
        raise SystemExit("Maintenance Plan: fejlbeskeden i build_load.py er aendret - "
                         "ret vhplan_steps() i build_screens.py.")
    return onstart


def build_vhplan():
    """VH-planen som EEN skaerm, som i appen selv.

    I VH-plan-appen er en ny plan en ny app, saa editorens felter staar
    altid paa deres Default. Her kan "New request" eller "Open" komme, mens
    en anden plan er aaben - editoren nulstilles derfor efter klargoeringen,
    med det samme, som Items-kortets "Open" goer."""
    d = cb.BY_KEY["vhplan"]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen, fake = _capture()
    asm.build_screen(render=fake)
    if seen["props"].get("OnVisible"):
        raise SystemExit("VH-plan har faaet en OnVisible - byg den ind i build_vhplan().")
    import build_items
    init = ("// A new or another request starts from a clean plan.\n"
            "Clear(colVhpItems);\nClear(colVhpOperations);\nClear(colVhpItemObjects);\n"
            "Clear(colVhpObjDraft);\nClear(colVhpMaterials);\nClear(colVhpAttachments);\n"
            + vhplan_steps(cb.with_reqid(cb.domain_onstart(d), d), d["tag"]) + ";\n"
            "// Editoren skal vise den plan, der lige er klargjort.\n"
            + build_items.SEED_FL_PICKER + ";\n"
            + build_items.RESET_EDITOR_CONTROLS)
    body = stale_check(d) + open_block(d, init, "Setting up a new plan")
    attach_open(d, seen, guarded(d, body), "Maintenance Plan")
    from gen_screen import render_screen
    _write(d["screen"], render_screen(d["screen"], screen_props(seen["props"]),
                                      seen["children"]))


# ---------------------------------------------------------------------------
# Opslagsskaermene: KKS-opslaget og Issue Board
# ---------------------------------------------------------------------------
def build_lookup(key):
    """En OPSLAGSSKAERM (combined.LOOKUPS): ingen anmodning at aabne, saa
    ingen open_block. Skaermens egen OnVisible saetter tilstanden og henter
    data foerste gang - ogsaa i den samlede app. Domaenets OnStart (kun
    skemaerne for samlingerne) staar foran den, som i de andre domaener,
    og ventespinneren har skaermen i forvejen. KKS-opslaget og Issue Board
    (issue #114) bygges ens."""
    d = cb.BY_KEY[key]
    _navigation()
    asm = _load(d, "assemble_screen.py")
    seen, fake = _capture()
    asm.build_screen(render=fake)
    if seen["props"].get("OnVisible") != asm.P.on_visible():
        raise SystemExit("%s: OnVisible er ikke laengere <parts>.on_visible() - "
                         "ret build_lookup()." % d["folder"])
    seen["props"]["OnVisible"] = (cb.domain_onstart(d) + ";\n\n"
                                  + seen["props"]["OnVisible"])
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
    "kks": lambda: build_lookup("kks"),
    "issueboard": lambda: build_lookup("issueboard"),
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
