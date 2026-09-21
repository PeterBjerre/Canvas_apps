# -*- coding: utf-8 -*-
"""
MILJOE OG APP-ID'ER - den eneste kilde.

HVORFOR DEN HER FIL FINDES
--------------------------
Det samme miljoe-id og de samme app-id'er stod FIRE steder:

    tools/canvas_apps.json                        environment_id + 4 app_id
    Masterdata Hub/build/hub_config.py            ENV_ID + 5 app_id i DOMAINS
    Equipment App/build/domain_config.py          PLAY_URL + HUB_URL
    Material App/build/domain_config.py           PLAY_URL + HUB_URL
    Maintenance Plan App/build/sp_config.py       HUB_URL

Det var erkendt, og loesningen var check_app_ids() i build_all.py: 60
linjer, der laeste hub_config.py med import og de tre andre med REGEX -
inklusive en, der skulle samle en streng, som var braekket over tre
linjer. Vagten var skrevet, fordi fejlen goer ondt: brugeren trykker
"Open" og lander i en tom app. Men en vagt over fire kopier er stadig
fire kopier, og skrev nogen HUB_URL paa een lang linje i stedet for tre,
fejlede regex'en tavst.

Nu staar id'erne eet sted, og builderne laeser dem herfra. Vagten er
slettet - den fejlklasse findes ikke laengere.

HVILKET MILJOE
--------------
Miljoeet vaelges af CANVAS_ENV i omgivelserne, ellers af
default_environment i canvas_apps.json. tools/build_all.py --env <navn>
saetter CANVAS_ENV for de byggescripts, den starter.

Det er dén ALM-gevinst, spoergsmaalet om miljoevariabler egentlig var ude
efter (se docs/26-designtokens.md): at kunne bygge mod et andet miljoe
uden at rette i koden - og uden et opslag ved opstart.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "tools", "canvas_apps.json")

# Navnet paa den omgivelsesvariabel, der vaelger miljoe. Staar her, fordi
# BAADE build_all.py (som saetter den) og denne fil (som laeser den) skal
# bruge det samme navn.
ENV_VAR = "CANVAS_ENV"

PLAY = "https://apps.powerapps.com/play/e/{env}/a/{app}"


def _load():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise SystemExit("Kan ikke laese %s: %s" % (CONFIG, e))
    except ValueError as e:
        raise SystemExit(
            "tools/canvas_apps.json er ikke gyldig JSON:\n  %s\n\n"
            "Filen ligger i git og er gyldig der:\n"
            "    git checkout tools/canvas_apps.json" % e)


_CFG = _load()


def env_names():
    return sorted(_CFG.get("environments", {}))


def resolve(name=None):
    """Det valgte miljoe, som en flad record.

    Formen er den, tools/canvas_mcp.py i forvejen forventer
    (environment_id, environment_category, apps, mcp_package_args), saa
    den kan bruge den uden at blive lavet om."""
    envs = _CFG.get("environments") or {}
    if not envs:
        raise SystemExit(
            "tools/canvas_apps.json har ingen 'environments'.\n"
            "Se kommentaren i filen for formen.")
    name = name or os.environ.get(ENV_VAR) or _CFG.get("default_environment")
    if not name:
        if len(envs) == 1:
            name = list(envs)[0]
        else:
            raise SystemExit(
                "Vaelg et miljoe med --env eller saet default_environment.\n"
                "Kendte: " + ", ".join(env_names()))
    if name not in envs:
        raise SystemExit(
            "Ukendt miljoe '%s'. Kendte: %s\n"
            "Miljoeerne staar i tools/canvas_apps.json under 'environments'."
            % (name, ", ".join(env_names())))
    out = dict(envs[name])
    out["name"] = name
    out["mcp_package_args"] = _CFG.get("mcp_package_args")
    return out


ENV = resolve()
ENV_NAME = ENV["name"]
ENV_ID = ENV["environment_id"]
APPS = ENV["apps"]


def app_id(key):
    """App-id'et, eller None hvis appen ikke findes endnu.

    None er en gyldig vaerdi: hubbens fliser for de domaener, der ikke er
    bygget, staar som "Kommer snart". Et UKENDT navn er derimod en fejl -
    den ville ellers ogsaa blive til "Kommer snart", og flisen ville
    tavst holde op med at virke."""
    if key not in APPS:
        raise KeyError(
            "Ukendt app '%s' i miljoeet '%s'. Kendte: %s"
            % (key, ENV_NAME, ", ".join(sorted(APPS))))
    return APPS[key].get("app_id") or None


def folder(key):
    return APPS[key]["folder"]


def play_url(key):
    """Play-URL'en til en app. Tom streng, hvis appen ikke findes endnu."""
    aid = app_id(key)
    return PLAY.format(env=ENV_ID, app=aid) if aid else ""


def hub_url():
    """Landingssiden. De tre satellitter aabner den med Launch - de er
    selvstaendige apps, ikke skaerme i hubben, saa Back() kan ikke foere
    tilbage."""
    url = play_url("hub")
    if not url:
        raise SystemExit(
            "Hubben har intet app_id i miljoeet '%s'.\n"
            "Uden det ved satellitterne ikke, hvor 'Til hubben' skal hen."
            % ENV_NAME)
    return url


if __name__ == "__main__":
    print("miljoe:", ENV_NAME, "(%s)" % ENV.get("_navn", ""))
    print("id:    ", ENV_ID)
    for k in sorted(APPS):
        print("  %-10s %-24s %s" % (k, APPS[k]["navn"], app_id(k) or "(intet id)"))
