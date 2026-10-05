# -*- coding: utf-8 -*-
"""
Hvem maa aendre og slette en anmodning - EET sted for hubben og de fire
domaeneskaerme (2026-10-05).

ADMIN
-----
Admin-listen er den samme, de gamle apps brugte: UserAndGroups med
Title = "Admin" og Member = brugerens e-mail med smaa bogstaver
(sharepoint/inspect/out/schema.json: begge kolonner er Text, 7 raekker).
Opslaget er een delegerbar LookUp i en navngiven formel. Navngivne formler
evalueres dovent og huskes, saa listen laeses hoejst een gang pr. session,
og kun hvis en formel faktisk spoerger.

UserAndGroups skal tilfoejes som datakilde i Studio (BIO SAP App har den
ikke i dag).

REGLEN
------
  Ejer:   maa aendre og slette sin egen anmodning, mens den er en kladde.
  Admin:  maa aendre og slette ALLE anmodninger i Kladde og AfventerInfo,
          uanset hvem der ejer dem.

Reglen staar baade i UI'et (Visible/DisplayMode) og i selve handlingen
(gem, indsend, slet), som slaar raekken op igen foer den skriver. En
skjult knap er ikke en sikring.
"""
import request_index as ri

ADMIN_LIST = "UserAndGroups"
ADMIN_GROUP = "Admin"
IS_ADMIN = "IsAdmin"

OWNER_STATUSES = (ri.DRAFT,)
ADMIN_STATUSES = (ri.DRAFT, "AfventerInfo")


def formula():
    """Den navngivne formel til App.Formulas. Ordret ens i alle apps, saa
    BIO SAP App's sammenlaegning (generate_app.build_formulas) beholder een."""
    return (
        "// ADMIN. Genereret af tools/permissions.py - ret ikke her.\n"
        "// Een delegerbar LookUp i admin-listen, laest dovent og kun een gang.\n"
        f"{IS_ADMIN} = !IsBlank(LookUp({ADMIN_LIST}, Title = \"{ADMIN_GROUP}\" "
        "&& Member = Lower(User().Email)));"
    )


def _in(status, statuses):
    return "(" + " || ".join(f'{status} = "{s}"' for s in statuses) + ")"


def is_owner(email, me):
    """email: udtryk for anmodningens RequesterEmail. me: brugerens e-mail
    med smaa bogstaver (var<X>Me)."""
    return f'Lower(Coalesce({email}, "")) = {me}'


def may_change(email, status, me):
    """Maa brugeren aendre/slette? status er et tekstudtryk (fx
    R.Status.Value)."""
    return (f"(({is_owner(email, me)} && {_in(status, OWNER_STATUSES)}) || "
            f"({IS_ADMIN} && {_in(status, ADMIN_STATUSES)}))")


def as_admin(email, me):
    """Aendrer brugeren som admin - altsaa i en andens anmodning? Saa
    skal aendringen logges (opgave 4). En admin i sin egen anmodning er
    en almindelig aendring."""
    return f"({IS_ADMIN} && !({is_owner(email, me)}))"


def may_change_ui(item, me):
    """Hubbens Edit/Delete-knapper. En almindelig bruger ser dem som i dag
    (paa alle sine egne anmodninger - handlingen afgoer status); en admin
    ser dem ogsaa paa andres i Kladde og AfventerInfo."""
    return (f"{is_owner(item + '.RequesterEmail', me)} || "
            f"({IS_ADMIN} && {_in(item + '.Status.Value', ADMIN_STATUSES)})")
