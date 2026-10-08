# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml for den samlede app.

App.Formulas   alle fem appers navngivne formler i een. Formler, der staar
               ORDRET ens i flere apps (temaet C, LayoutContext,
               LayoutRank), staar her een gang. Har to apps en formel med
               samme navn og forskelligt indhold, stopper byggeriet.
               Navngivne formler evalueres dovent, saa en formel for et
               domaene, man ikke aabner, koster ingenting.

App.OnStart    KUN temaet og hubbens fire variabler - ingen datahentning,
               intet domaene. Hvert domaenes OnStart koerer i dets skaerms
               OnVisible, naar skaermen aabnes (build_screens.open_block).

StartScreen    hubben, eller domaenets skaerm ved et dyblink:
               <play-url>?domain=vhplan&reqid=<RequestGuid>

De fem appers App.pa.yaml laeses, efter at deres egne generatorer er koert
igen, saa den samlede app aldrig bygges af en forældet udgave.
"""
import os
import subprocess
import sys

import combined as cb

if cb.TOOLS not in sys.path:
    sys.path.insert(0, cb.TOOLS)
import app_yaml  # noqa: E402


def regenerate_sources():
    """Koer de fem appers egne App.pa.yaml-generatorer. De er hurtige og
    skriver kun det, de altid skriver."""
    sys.path.insert(0, cb.TOOLS)
    import build_all
    folders = {d["folder"] for d in cb.DOMAINS}
    for app, scripts in build_all.APPS:
        if app not in folders:
            continue
        build = os.path.join(cb.ROOT, app, "build")
        for s in scripts:
            if s.startswith("generate"):
                r = subprocess.run([sys.executable, s], cwd=build,
                                   stdout=subprocess.DEVNULL)
                if r.returncode:
                    raise SystemExit("%s/build/%s fejlede." % (app, s))


def build_formulas():
    merged, owner = {}, {}
    order = []
    for d in cb.DOMAINS:
        for name, text in cb.split_formulas(cb.app_yaml(d)["Formulas"]):
            text = cb.rename(text, d)
            name = cb.rename(name, d)
            if name in merged:
                if merged[name] != text:
                    raise SystemExit(
                        "App.Formulas: '%s' staar baade i %s og %s med forskelligt "
                        "indhold.\nI een app kan et navn kun betyde een ting - "
                        "giv den ene et domaenepraefiks." % (name, owner[name], d["folder"]))
                continue
            merged[name], owner[name] = text, d["folder"]
            order.append(name)
    # Sidebarens app-logo (issue #203) - kun den samlede app har sidebaren.
    import side_nav
    if side_nav.LOGO in merged:
        raise SystemExit("App.Formulas: '%s' findes allerede." % side_nav.LOGO)
    merged[side_nav.LOGO] = side_nav.logo_formula()
    order.append(side_nav.LOGO)
    return "\n\n".join(merged[n] for n in order), len(order)


def build_onstart():
    hub = cb.BY_KEY["hub"]
    return "\n\n".join([
        cb.prefs_block(),
        cb.theme_block(),
        "// Hubbens visning. Den er startskaermen, og den eneste, der ikke\n"
        "// klargoeres i sin OnVisible - se build_screens.open_block().\n"
        + cb.domain_onstart(hub),
    ])


def build_start_screen():
    parts = [f'"{d["key"]}", {d["screen"]}' for d in cb.DOMAINS if d["key"] != "hub"]
    return ("Switch(\n"
            f'    Lower(Param("{cb.DOMAIN_PARAM}")),\n    '
            + ",\n    ".join(parts) + ",\n"
            f"    {cb.BY_KEY['hub']['screen']}\n"
            ")")


def main():
    regenerate_sources()
    formulas, n_fx = build_formulas()
    content = app_yaml.write(cb.APP_DIR, formulas, build_onstart(), build_start_screen())
    print("App.pa.yaml skrevet. %d linjer, %d navngivne formler, "
          "0 datahentninger i OnStart." % (content.count("\n") + 1, n_fx))

if __name__ == "__main__":
    main()
