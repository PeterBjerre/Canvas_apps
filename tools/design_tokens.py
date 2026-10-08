# -*- coding: utf-8 -*-
"""
DESIGNTOKENS - den eneste kilde til farve i hele repoet.

HVORFOR DEN HER FIL FINDES
--------------------------
Foer stod farverne tre steder: 20 konstanter i hver apps gen_screen.py,
otte statusfarvepar som RAA TAL i hub_config.py, og en haandfuld literaler
spredt i build_modal.py og build_domain.py. Otte af hub_config.py's ni
statusfarver var tal, der allerede havde et navn et andet sted. Skiftede
nogen den groenne i gen_screen.py, skiftede feltkanterne farve i alle fire
apps - og statuschippen "Created in SAP" paa landingssiden gjorde det ikke.
De var den samme farve, og bagefter var de to groenne, der ligner hinanden.

HVORDAN
-------
Builderne skriver ALDRIG en RGBA-vaerdi i en skaerm. De skriver en
TOKENREFERENCE:

    Fill: =C.'bg-app'

'C' er en navngiven formel i App.Formulas, som denne fil ogsaa skriver:

    C = If(!darkModeEnabled, { ...lyse vaerdier... }, { ...moerke... });

Og dermed er moerk tilstand ikke en funktion, nogen skal bygge. Den er en
konsekvens af, at farven kun staar eet sted. Skifter darkModeEnabled,
genberegner Power Fx den navngivne formel, og hver eneste kontrol, der
laeser C.'et-eller-andet', skifter med. Ingen kontrol ved, at moerk
tilstand findes.

REGLEN
------
Ingen builder maa indeholde strengen "RGBA(". tools/build_all.py haandhaever
det. Den ene undtagelse er TRANSPARENT herunder: gennemsigtig er
gennemsigtig i begge temaer og er ikke en farve, nogen kan aendre.

AT TILFOEJE EN TOKEN
--------------------
Skriv den i BAADE LIGHT og DARK. _check() nedenfor afviser at bygge, hvis
et navn kun staar det ene sted - for den fejl ville ellers vise sig som en
kontrol, der bliver usynlig, naar brugeren skifter tema.
"""

# Gennemsigtig er ikke en token. Den er den samme i begge temaer, den kan
# ikke gaa i stykker, og at lade den vaere en token ville betyde, at nogen
# kunne saette den til en farve.
TRANSPARENT = "RGBA(0, 0, 0, 0)"


# ---------------------------------------------------------------------------
# LYST TEMA
#
# ROLIGE FARVER (issue #199). Accentfarverne var Fluent/Tailwind-standard:
# maettet "Microsoft-blaa" (#0067AE), neonlilla (#9333EA), klar orange og
# lime. De er nu trukket ned i maetning (CIE-chroma ca. 25-40 % lavere,
# lilla 40 %) og en anelse mod graa/skifer, saa de passer til appens
# blaagraa flader. Det er de SAMME farvefamilier - blaa, teal, oliven, ler/
# orange, lilla - saa et domaene og en status kan genkendes som foer:
#
#   - brand: daempet staalblaa i stedet for Fluents klare blaa.
#   - statusfarverne: roed, groen og gul bevarer deres betydning; kun
#     maetningen er taget ned, og chippens baggrund er justeret sammen med
#     teksten, saa begge stadig klarer 4,5:1 (CONTRAST nedenfor).
#   - domaenerne: hvert par er stadig mindst DOMAIN_MIN_DELTA_E fra
#     hinanden. Lilla er drejet mod blomme (h 313 -> 327), fordi en
#     daempet lilla ellers kommer for taet paa den daempede blaa.
#
# Lys/moerk, hover, tryk, fokus og deaktiveret er ikke rettet hver for
# sig: de er de samme navne som foer, og vagterne herunder (CONTRAST,
# BALANCED, DOMAIN_MIN_DELTA_E) regner dem efter i begge temaer.
# ---------------------------------------------------------------------------
LIGHT = {
    # --- brand ---
    'color-brand-primary':       "RGBA(44, 90, 140, 1)",
    'color-brand-primary-hover': "RGBA(58, 106, 158, 1)",
    'color-brand-primary-soft':  "RGBA(212, 224, 238, 1)",

    # --- baggrunde ---
    'bg-app':     "RGBA(237, 241, 247, 1)",
    'bg-surface': "RGBA(255, 255, 255, 1)",
    'bg-card':    "RGBA(250, 251, 253, 1)",
    'bg-muted':   "RGBA(240, 243, 248, 1)",

    # --- tekst ---
    'text-primary':    "RGBA(26, 34, 49, 1)",
    'text-muted':      "RGBA(89, 102, 122, 1)",
    'text-on-primary': "RGBA(255, 255, 255, 1)",
    # Tekst paa en DOMAENEFARVE. Den er hvid i lys tilstand - altsaa den
    # samme som text-on-primary - men de to kan ikke vaere eet navn: i
    # moerk tilstand er domaenefarverne LYSE (lyse pasteller), og hvid
    # tekst paa den lyse orange gav 1,67:1. Se DARK.
    'text-on-domain':  "RGBA(255, 255, 255, 1)",

    # --- kanter ---
    'border-default': "RGBA(215, 222, 232, 1)",
    'border-subtle':  "RGBA(228, 233, 241, 1)",

    # --- inputfelter ---
    'input-bg':          "RGBA(255, 255, 255, 1)",
    'input-bg-disabled': "RGBA(240, 243, 248, 1)",
    # Teksten i ALLE redigerbare felter. Lys tilstand: som text-primary.
    'input-fg':          "RGBA(26, 34, 49, 1)",
    # Fluents liste under en dropdown/combobox/datovaelger. Den kan IKKE
    # saettes - den er lys i begge temaer. Tokenet findes kun, saa
    # kontrastvagten kan holde input-fg op mod den.
    'flyout-bg':         "RGBA(255, 255, 255, 1)",

    # --- tilstande. Bruges BAADE af feltkanter og af statuschips ---
    # KANTEN ER IKKE TEKSTEN. state-*-fg er valgt for at kunne LAESES
    # (4,5:1). En 1 px kant skal kun kunne SES (3,0:1), og en forgrund,
    # der er valgt til tekst, bliver en neonstreg, naar den bruges som
    # kant paa en moerk baggrund. I lys tilstand er de to ens; se DARK.
    'border-ok':        "RGBA(28, 112, 84, 1)",
    'border-error':     "RGBA(172, 56, 64, 1)",

    'state-ok-fg':      "RGBA(28, 112, 84, 1)",
    'state-ok-bg':      "RGBA(231, 242, 236, 1)",
    'state-warn-fg':    "RGBA(130, 88, 24, 1)",
    'state-warn-bg':    "RGBA(249, 241, 228, 1)",
    'state-error-fg':   "RGBA(172, 56, 64, 1)",
    'state-error-bg':   "RGBA(250, 236, 236, 1)",
    'state-info-fg':    "RGBA(40, 84, 128, 1)",
    'state-info-bg':    "RGBA(229, 237, 246, 1)",
    'state-neutral-fg': "RGBA(89, 102, 122, 1)",
    'state-neutral-bg': "RGBA(228, 233, 241, 1)",
    # Tre farver til, saa hver anmodningsstatus faar sin egen (issue: Draft,
    # Submitted og In progress var alle blaa; Ready for SAP og Created in
    # SAP begge groenne).
    'state-violet-fg':  "RGBA(98, 70, 148, 1)",
    'state-violet-bg':  "RGBA(239, 235, 246, 1)",
    'state-lime-fg':    "RGBA(72, 94, 40, 1)",
    'state-lime-bg':    "RGBA(236, 241, 226, 1)",
    'state-rose-fg':    "RGBA(160, 52, 98, 1)",
    'state-rose-bg':    "RGBA(247, 234, 240, 1)",

    # --- modalen. De 2% gennemsigtighed er der i dag og bevares, saa
    #     lys tilstand ser ud praecis som foer ---
    'bg-modal': "RGBA(255, 255, 255, 0.98)",
    'overlay':  "RGBA(15, 23, 42, 0.35)",

    # --- en klikbar raekkes hover og tryk (build_helpers.row_hit, issue
    #     #79). Gennemsigtige: laget ligger OVEN PAA raekkens tekster, saa
    #     det farver raekken uden at skjule den. Tekstfarven i ALLE tokens
    #     ovenfor gaelder stadig, fordi tonen er under 10 % ---
    'row-hover':   "RGBA(44, 90, 140, 0.06)",
    'row-pressed': "RGBA(44, 90, 140, 0.12)",

    # --- de fem domaener paa landingssiden ---
    # Issue #70: fem tydeligt adskilte farver - se DOMAIN_MIN_DELTA_E.
    # -soft er domaenet blandet 8 % ind i bg-card: den valgte flises fyld.
    'domain-fl':  "RGBA(26, 76, 138, 1)",
    'domain-eq':  "RGBA(24, 126, 124, 1)",
    'domain-mp':  "RGBA(98, 114, 40, 1)",
    'domain-mat': "RGBA(166, 90, 52, 1)",
    'domain-vhp': "RGBA(158, 66, 158, 1)",
    'domain-fl-soft':  "RGBA(232, 237, 244, 1)",
    'domain-eq-soft':  "RGBA(232, 241, 243, 1)",
    'domain-mp-soft':  "RGBA(238, 240, 236, 1)",
    'domain-mat-soft': "RGBA(243, 238, 237, 1)",
    'domain-vhp-soft': "RGBA(243, 236, 245, 1)",
}


# ---------------------------------------------------------------------------
# MOERKT TEMA
#
# Ikke "det lyse tema med omvendt lysstyrke". Hver vaerdi er valgt og
# EFTERREGNET - kontrastforholdene staar i docs/26-designtokens.md.
#
# De tre valg, der ikke var frie:
#
# 1. 'color-brand-primary' er en daempet staalblaa (issue #199), lys nok
#    til at kunne SES mod det moerke kort - den er ogsaa fokusrammen -
#    og moerk nok til hvid knaptekst: hvid tekst giver 5,09:1 (AA for de
#    14 px halvfede knaptekster), og den staar 3,51:1 fra kortet bagved.
#    Begge krav staar i CONTRAST.
# 2. 'color-brand-primary-hover' er MOERKERE end grundfarven - ikke
#    lysere, som man ellers goer paa moerk baggrund. Grunden er den
#    samme: en lysere hover ville tage knaptekstens kontrast med sig ned.
#    Knappen er allerede afgraenset af sin hvilefarve, saa den maa gerne
#    blive lidt moerkere, naar musen er over den.
# 3. 'border-default' er slate-500 og ikke slate-700. Kanten er det, der
#    afgraenser et INPUTFELT, og skal derfor selv kunne ses: slate-700
#    giver 1,95:1 mod feltets baggrund, slate-500 giver 4,24:1.
#    'border-subtle' - de rene skillelinjer - maa godt vaere svagere.
# ---------------------------------------------------------------------------
DARK = {
    # --- brand ---
    'color-brand-primary':       "RGBA(68, 112, 168, 1)",
    'color-brand-primary-hover': "RGBA(56, 94, 144, 1)",
    'color-brand-primary-soft':  "RGBA(36, 56, 88, 1)",

    # --- baggrunde ---
    'bg-app':     "RGBA(12, 15, 23, 1)",
    'bg-surface': "RGBA(15, 23, 42, 1)",
    'bg-card':    "RGBA(15, 23, 42, 1)",
    'bg-muted':   "RGBA(30, 41, 59, 1)",

    # --- tekst ---
    'text-primary':    "RGBA(229, 231, 235, 1)",
    'text-muted':      "RGBA(148, 163, 184, 1)",
    'text-on-primary': "RGBA(255, 255, 255, 1)",
    # Domaenefarverne er LYSE her (daempede pasteller), saa
    # teksten paa dem skal vaere moerk. Hvid gav 1,67-2,72:1 - chippen var
    # ulaeselig i moerk tilstand. Slate-950 giver 8,9-13,4.
    'text-on-domain':  "RGBA(2, 6, 23, 1)",

    # --- kanter ---
    'border-default': "RGBA(100, 116, 139, 1)",
    'border-subtle':  "RGBA(51, 65, 85, 1)",

    # --- inputfelter ---
    # SORT, ikke slate-950 (2, 6, 23). Feltteksten skal kunne laeses baade
    # paa feltet og paa Fluents HVIDE liste (se input-fg). Mod slate-950
    # kan ingen farve naa 4,5:1 mod begge; mod sort kan en mellemgraa.
    'input-bg':          "RGBA(0, 0, 0, 1)",
    'input-bg-disabled': "RGBA(30, 41, 59, 1)",
    # MELLEMGRAA (valgt 2026-09-30). Color paa en moderne dropdown eller
    # combobox farver OGSAA teksten i dens liste, og listen er Fluents
    # lyse flade, som vi ikke kan farve. Een farve skal derfor kunne
    # laeses paa det sorte felt (4,60:1) og paa den hvide liste (4,57:1).
    # Alle felter har den, saa de ser ens ud. Laaste felter beholder
    # text-muted: de er Outline (kortets flade), og de aabner ingen liste.
    'input-fg':          "RGBA(113, 118, 127, 1)",
    'flyout-bg':         "RGBA(255, 255, 255, 1)",

    # --- tilstande ---
    # Daempet groen og roed (issue #199; foer emerald-600 og red-500).
    # Oprindeligt valgt i stedet for -400 og -400. Kanten paa et
    # udfyldt kraevet felt gav 10,49:1 mod feltbaggrunden - dobbelt saa
    # meget som i lys tilstand (5,45), og det SES: hvert udfyldt felt fik
    # en lysende groen streg om sig. Nu 5,35 og 5,36, altsaa det samme
    # indtryk i begge temaer. BALANCED nedenfor holder det paa plads.
    'border-ok':        "RGBA(44, 138, 106, 1)",
    'border-error':     "RGBA(214, 88, 88, 1)",

    'state-ok-fg':      "RGBA(112, 196, 160, 1)",
    'state-ok-bg':      "RGBA(20, 46, 38, 1)",
    'state-warn-fg':    "RGBA(222, 186, 110, 1)",
    'state-warn-bg':    "RGBA(54, 42, 22, 1)",
    'state-error-fg':   "RGBA(234, 136, 136, 1)",
    'state-error-bg':   "RGBA(64, 28, 32, 1)",
    'state-info-fg':    "RGBA(136, 174, 222, 1)",
    'state-info-bg':    "RGBA(28, 40, 64, 1)",
    'state-neutral-fg': "RGBA(148, 163, 184, 1)",
    'state-neutral-bg': "RGBA(30, 41, 59, 1)",
    'state-violet-fg':  "RGBA(186, 170, 228, 1)",
    'state-violet-bg':  "RGBA(44, 36, 70, 1)",
    'state-lime-fg':    "RGBA(178, 206, 128, 1)",
    'state-lime-bg':    "RGBA(38, 48, 26, 1)",
    'state-rose-fg':    "RGBA(228, 166, 196, 1)",
    'state-rose-bg':    "RGBA(64, 30, 48, 1)",

    # --- modalen. Sloeret er moerkere end i lys tilstand: det skal skille
    #     modalen fra en baggrund, der i forvejen er moerk ---
    'bg-modal': "RGBA(15, 23, 42, 0.98)",
    'overlay':  "RGBA(2, 6, 23, 0.72)",

    # --- raekke-hover: lys tone paa moerkt, samme styrke som i lys tilstand ---
    'row-hover':   "RGBA(160, 190, 225, 0.08)",
    'row-pressed': "RGBA(160, 190, 225, 0.16)",

    # --- domaener. Lysere udgaver, saa striben kan ses mod det moerke kort ---
    # -soft: domaenet blandet 16 % ind i bg-card - den valgte flises fyld.
    'domain-fl':  "RGBA(112, 158, 222, 1)",
    'domain-eq':  "RGBA(96, 202, 188, 1)",
    'domain-mp':  "RGBA(176, 206, 110, 1)",
    'domain-mat': "RGBA(226, 158, 108, 1)",
    'domain-vhp': "RGBA(222, 130, 214, 1)",
    'domain-fl-soft':  "RGBA(31, 45, 71, 1)",
    'domain-eq-soft':  "RGBA(28, 52, 65, 1)",
    'domain-mp-soft':  "RGBA(41, 52, 53, 1)",
    'domain-mat-soft': "RGBA(49, 45, 53, 1)",
    'domain-vhp-soft': "RGBA(48, 40, 70, 1)",
}


# Navnet paa den globale variabel, der baerer valget. Staar her, fordi
# BAADE den navngivne formel og de tre knapper, der skifter tema, skal
# bruge det samme navn.
DARK_VAR = "darkModeEnabled"

# Navnet paa den navngivne formel. Et enkelt bogstav, fordi det staar i
# hver eneste farveegenskab i fire apps - "C.'bg-app'" er til at laese,
# "AppColorTokens.'bg-app'" er stoej.
RECORD = "C"

# Noeglen SaveData/LoadData gemmer under. Lageret er isoleret pr. app-id,
# saa navnet kan ikke kollidere med en anden apps.
PREFS_KEY = "prefs"
PREFS_COLLECTION = "colAppPrefs"

# Navnet paa den parameter, hubben sender med i play-URL'en. Se
# launch_suffix().
THEME_PARAM = "theme"


def _check():
    """De to temaer skal have ORDRET de samme navne.

    Staar en token kun i LIGHT, er dens vaerdi blank i moerk tilstand - og
    en blank farve er gennemsigtig. Kontrollen forsvinder, men kun for de
    brugere der har slaaet moerk tilstand til, og kun i den ene app nogen
    glemte. Derfor stopper byggeriet her i stedet."""
    only_light = sorted(set(LIGHT) - set(DARK))
    only_dark = sorted(set(DARK) - set(LIGHT))
    if only_light or only_dark:
        msg = ["Designtokens: de to temaer er ikke ens."]
        if only_light:
            msg.append("  mangler i DARK:  " + ", ".join(only_light))
        if only_dark:
            msg.append("  mangler i LIGHT: " + ", ".join(only_dark))
        raise SystemExit("\n".join(msg))


_check()

# ---------------------------------------------------------------------------
# KONTRASTKRAVENE
#
# HVORFOR DE STAAR SOM EN TABEL OG IKKE I ET DOKUMENT
# ---------------------------------------------------
# state-ok-fg laa paa 4,44:1 mod sin egen chipbaggrund - 0,06 under WCAG
# AA. Ingen havde skrevet den forkert; den var valgt for sig selv, foer
# chippen fandtes, og ingenting regnede efter. Den slags glider hver gang
# nogen retter en farve "lige en anelse".
#
# Parrene herunder er dem, apperne FAKTISK saetter ved siden af hinanden -
# aflaest i de byggede skaerme, ikke gaettet:
#
#     C.'text-on-primary'  paa  C.'domain-mp'      (domaenechippen i hubben)
#     C.'state-ok-fg'      paa  C.'state-ok-bg'    (statuschippen)
#     C.'state-ok-fg'      paa  kortets baggrund   (Fill = gennemsigtig)
#     C.'border-default'   paa  C.'input-bg'       (feltkanten)
#
# TAERSKLERNE
#   4.5  WCAG 2.1 AA for broedtekst
#   3.0  WCAG 2.1 AA for kanter og andre ikke-tekstlige elementer (1.4.11)
#
# Alfa ignoreres. De eneste tokens med alfa under 1 er bg-modal (0,98) og
# overlay; 0,98 flytter tredje decimal, og overlay staar ikke i et par.
# ---------------------------------------------------------------------------
TEXT_MIN = 4.5
UI_MIN = 3.0

# De baggrunde, almindelig tekst kan lande paa.
_TEXT_BG = ("bg-app", "bg-surface", "bg-card", "bg-muted", "bg-modal",
            "input-bg", "input-bg-disabled")

CONTRAST = (
    # -- tekst ------------------------------------------------------------
    [("text-primary", bg, TEXT_MIN) for bg in _TEXT_BG] +
    [("text-muted", bg, TEXT_MIN) for bg in _TEXT_BG] +
    # Feltteksten paa feltet OG paa Fluents liste (se input-fg).
    [("input-fg", bg, TEXT_MIN) for bg in ("input-bg", "flyout-bg")] +
    # Hvid tekst paa en farvet chip eller knap.
    [("text-on-primary", bg, TEXT_MIN) for bg in
     ("color-brand-primary", "color-brand-primary-hover")] +
    # Brandfarven er OGSAA fokusrammen (FocusedBorderColor) og kanten paa
    # det valgte segment - den skal kunne ses mod fladen bagved (1.4.11).
    # Tilfoejet med issue #199, da brandfarven blev daempet.
    [("color-brand-primary", bg, UI_MIN) for bg in ("bg-card", "bg-app")] +
    # Domaenechippen i hubben: hvid i lys tilstand, moerk i moerk.
    [("text-on-domain", bg, TEXT_MIN) for bg in
     ("text-muted", "domain-fl", "domain-eq", "domain-mp", "domain-mat",
      "domain-vhp")] +
    # Statuschippen: forgrund paa SIN EGEN baggrund.
    [("state-%s-fg" % s, "state-%s-bg" % s, TEXT_MIN) for s in
     ("ok", "warn", "error", "info", "neutral", "violet", "lime", "rose")] +
    # Hubbens Awaiting-badge (approval_flow, issue #90): blaa tekst paa den
    # neutrale, blaagraa flade.
    [("state-info-fg", "state-neutral-bg", TEXT_MIN)] +
    # De samme forgrunde bruges ogsaa som ren tekst uden chip (Fill er
    # gennemsigtig), og saa er det kortet eller skaermen bagved.
    [("state-%s-fg" % s, bg, TEXT_MIN) for s in
     ("ok", "warn", "error", "info", "neutral", "violet", "lime", "rose")
     for bg in ("bg-card", "bg-app")] +
    # -- kanter og streger (1.4.11) ---------------------------------------
    # border-default staar IKKE her - se CONTRAST_OPEN nedenfor.
    # Feltkanten, naar et krav er opfyldt eller mangler.
    [(fg, bg, UI_MIN) for fg in ("border-ok", "border-error")
     for bg in ("input-bg", "input-bg-disabled", "bg-card")] +
    # Domaenestriben langs hubbens fliser.
    [(fg, "bg-card", UI_MIN) for fg in
     ("domain-fl", "domain-eq", "domain-mp", "domain-mat", "domain-vhp")] +
    # Den VALGTE flise (issue #70): tekst paa det tonede fyld, og
    # domaenets kant, ikon og knaptekst paa det samme fyld.
    [(fg, "domain-%s-soft" % d, TEXT_MIN) for d in ("fl", "eq", "mp", "mat", "vhp")
     for fg in ("text-primary", "text-muted")] +
    [("domain-%s" % d, "domain-%s-soft" % d, UI_MIN)
     for d in ("fl", "eq", "mp", "mat", "vhp")]
)


# ---------------------------------------------------------------------------
# KENDT, IKKE OPFYLDT
#
# Parrene herunder DUMPER kontrastkravet i dag. De staar her i stedet for
# at vaere udeladt, fordi en udeladt regel er en regel, ingen kan se.
#
# _check_contrast() efterproever at de STADIG dumper. Bliver et af dem
# rettet, fejler byggeriet og beder om at faa parret flyttet op i
# CONTRAST - saa kan undtagelsen ikke blive staaende, efter den er
# overfloedig.
#
# border-default paa lys baggrund: 1,19-1,35:1 mod kravets 3,0
# ---------------------------------------------------------------------
# Feltkanten er RGBA(215, 222, 232) - lysegraa paa naesten hvid. Et hvidt
# inputfelt paa et naesten hvidt kort (1,02:1) har ingen anden afgraensning
# end den kant, saa WCAG 2.1 1.4.11 gaelder den.
#
# Den er IKKE rettet her, fordi det ikke er een vaerdi som state-ok-fg:
# border-default staar paa 160 kontroller - 53 knapper, 29 inputfelter, 25
# containere, 20 dropdowns, 20 tekster. For at naa 3,0 mod hvid skal den
# ned omkring RGBA(130, 138, 152), altsaa et MIDTERGRAAT. Hver kant i alle
# fire apper bliver synligt tungere. Det er en designbeslutning, ikke en
# talrettelse, og den hoerer til hos den, der ejer udtrykket.
#
# Moerk tilstand klarer kravet: slate-500 paa slate-950 giver 4,24.
# ---------------------------------------------------------------------------
CONTRAST_OPEN = [("border-default", bg, UI_MIN, "lys") for bg in
                 ("input-bg", "input-bg-disabled", "bg-card", "bg-app",
                  "bg-surface")]


def _srgb(rgba):
    """De tre kanaler som 0-255. Alfa laeses ikke - se kommentaren ovenfor."""
    body = rgba[rgba.index("(") + 1:rgba.rindex(")")]
    return [int(round(float(n))) for n in body.split(",")[:3]]


def _rel_lum(rgba):
    """Relativ luminans, WCAG 2.1 definitionen."""
    out = []
    for v in _srgb(rgba):
        v /= 255.0
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    """Kontrastforholdet mellem to RGBA-strenge. 1.0 = ens, 21.0 = sort/hvid."""
    la, lb = _rel_lum(a), _rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


_THEMES = {"lys": LIGHT, "moerk": DARK}


def _lookup(where, theme, name):
    values = _THEMES[theme]
    if name not in values:
        raise SystemExit("%s naevner en token, der ikke findes: %r"
                         % (where, name))
    return values[name]


def _check_contrast():
    """Hvert par i CONTRAST skal klare sin taerskel i BEGGE temaer.

    Og hvert par i CONTRAST_OPEN skal STADIG dumpe. Den anden halvdel er
    lige saa vigtig som den foerste: uden den ville en undtagelse blive
    staaende for evigt, ogsaa efter nogen havde rettet farven."""
    bad = []
    for theme in _THEMES:
        for fg, bg, need in CONTRAST:
            got = contrast(_lookup("CONTRAST", theme, fg),
                           _lookup("CONTRAST", theme, bg))
            if got + 0.005 < need:
                bad.append("  %-6s %-18s paa %-18s %.2f  (kraever %.1f)"
                           % (theme, fg, bg, got, need))
    if bad:
        raise SystemExit(
            "Designtokens: kontrastkravet er ikke opfyldt.\n"
            + "\n".join(bad) +
            "\n\nRet farven i LIGHT/DARK, eller ret parret i CONTRAST, hvis\n"
            "apperne ikke laengere saetter de to ved siden af hinanden.")

    fixed = []
    for fg, bg, need, theme in CONTRAST_OPEN:
        got = contrast(_lookup("CONTRAST_OPEN", theme, fg),
                       _lookup("CONTRAST_OPEN", theme, bg))
        if got + 0.005 >= need:
            fixed.append("  %-6s %-18s paa %-18s %.2f  (kraever %.1f)"
                         % (theme, fg, bg, got, need))
    if fixed:
        raise SystemExit(
            "Designtokens: et par i CONTRAST_OPEN klarer nu kravet.\n"
            + "\n".join(fixed) +
            "\n\nFlyt det op i CONTRAST, saa det bliver ved at vaere et krav.\n"
            "En undtagelse, der ikke laengere er en undtagelse, skal ikke\n"
            "blive staaende - saa er den bare et sted, reglen ikke gaelder.")


_check_contrast()


# ---------------------------------------------------------------------------
# BALANCE MELLEM DE TO TEMAER
#
# CONTRAST sikrer, at intet er for SVAGT. Den fangede ikke det, der
# faktisk var galt i moerk tilstand: at noget var for KRAFTIGT.
#
#     kanten paa et udfyldt kraevet felt, mod feltbaggrunden
#         lys    state-ok-fg  paa input-bg    5,45
#         moerk  state-ok-fg  paa input-bg   10,49
#
# Begge klarede kravet paa 3,0 med god margin, saa vagten var tavs. Men en
# kant, der er dobbelt saa kraftig i det ene tema, SES som noget andet -
# hvert udfyldt felt fik en lysende groen streg om sig, som lys tilstand
# ikke har. Det var ikke en fejl i en vaerdi; det var en fejl i FORHOLDET
# mellem to vaerdier, og det kan kun ses ved at regne dem mod hinanden.
#
# Aarsagen er den samme som ved text-on-domain: EET navn lavede TO ting.
# state-ok-fg er valgt for at kunne LAESES som tekst (4,5:1). En kant skal
# kun kunne SES (3,0:1). De to krav peger hver sin vej, naar baggrunden
# vender - derfor border-ok og border-error.
# ---------------------------------------------------------------------------
MAX_SKEW = 1.6

# (forgrund, baggrund) hvis kontrast skal vaere nogenlunde ens i de to
# temaer. Kun kanter: en tekstfarve maa gerne have mere luft i moerk
# tilstand, for dér er baggrunden ikke bare den omvendte.
BALANCED = [(fg, "input-bg") for fg in ("border-ok", "border-error")]


def _check_balance():
    """Ingen kant maa vaere mere end MAX_SKEW gange saa kraftig i det ene
    tema som i det andet."""
    bad = []
    for fg, bg in BALANCED:
        lys = contrast(_lookup("BALANCED", "lys", fg),
                       _lookup("BALANCED", "lys", bg))
        mrk = contrast(_lookup("BALANCED", "moerk", fg),
                       _lookup("BALANCED", "moerk", bg))
        hi, lo = max(lys, mrk), min(lys, mrk)
        if lo > 0 and hi / lo > MAX_SKEW + 0.005:
            bad.append("  %-14s paa %-10s lys %.2f  moerk %.2f  "
                       "(faktor %.2f, hoejst %.1f)"
                       % (fg, bg, lys, mrk, hi / lo, MAX_SKEW))
    if bad:
        raise SystemExit(
            "Designtokens: en kant er meget kraftigere i det ene tema.\n"
            + "\n".join(bad) +
            "\n\nDen klarer maaske kontrastkravet i begge temaer, men den SES\n"
            "som to forskellige ting. Daemp den kraftigste, eller tag parret\n"
            "ud af BALANCED, hvis forskellen er med vilje.")


_check_balance()


# ---------------------------------------------------------------------------
# DOMAENEFARVERNE SKAL KUNNE SKELNES (issue #70)
#
# Equipments turkis og Measuring Points groenne laa ΔE 20-28 fra hinanden
# (CIE76) - to nuancer af det samme, naar de stod side om side i hubben.
# Functional Location og VH-plan laa 31-33. Ingen regel sagde noget, fordi
# kontrasten mod baggrunden var fin for dem alle.
#
# Nu skal hvert par vaere mindst DOMAIN_MIN_DELTA_E fra hinanden i BEGGE
# temaer. Paletten ligger paa ~58.
# ---------------------------------------------------------------------------
DOMAIN_MIN_DELTA_E = 45
DOMAINS = ("domain-fl", "domain-eq", "domain-mp", "domain-mat", "domain-vhp")


def _lab(rgba):
    body = rgba[rgba.index("(") + 1:rgba.rindex(")")]
    rgb = [float(n) for n in body.split(",")[:3]]

    def lin(u):
        u /= 255
        return ((u + 0.055) / 1.055) ** 2.4 if u > 0.04045 else u / 12.92
    r, g, b = (lin(u) for u in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def _check_domain_distance():
    import itertools, math
    bad = []
    for theme, values in (("lys", LIGHT), ("moerk", DARK)):
        for a, b in itertools.combinations(DOMAINS, 2):
            de = math.dist(_lab(values[a]), _lab(values[b]))
            if de < DOMAIN_MIN_DELTA_E:
                bad.append("  %-6s %-11s / %-11s ΔE %.1f" % (theme, a, b, de))
    if bad:
        raise SystemExit(
            "Designtokens: to domaenefarver er for ens (kraever ΔE >= %d).\n"
            % DOMAIN_MIN_DELTA_E + "\n".join(bad))


_check_domain_distance()


# ---------------------------------------------------------------------------
# HTML-kontrollernes farver
#
# VH-plans tabeloverskrifter er HtmlViewer-kontroller, og HTML kender ikke
# RGBA(). Farven stod derfor som "#59667A" midt i en stylestreng - et tal,
# der tilfaeldigvis var det samme som 'text-muted', men som ingenting vidste
# om det. I moerk tilstand ville overskriften blive staaende moerkegraa paa
# moerk baggrund.
#
# Hex-vaerdierne herunder AFLEDES af de samme tokens. De kan ikke glide,
# fordi de ikke er skrevet af - de er regnet ud.
#
# Alfa kan ikke udtrykkes i den korte hex-form og er ligegyldig her: de
# tokens, HTML bruger, er alle helt uigennemsigtige.
# ---------------------------------------------------------------------------
HTML_TOKENS = ("text-primary", "text-muted",
               # Temaskiftet er en SVG (build_helpers.theme_button) - dens
               # farver er de samme tokens som resten af appen.
               "state-neutral-bg", "bg-surface", "bg-app", "state-warn-fg",
               "border-default",
               # Hjaelpekontakten (build_helpers.help_toggle) - samme form.
               "state-info-fg", "state-info-bg",
               # Sidebaren (tools/side_nav.py): logoet og markeringen af
               # den app, man staar i.
               "color-brand-primary", "text-on-primary",
               # VH-planens trinindikator (build_hero.stepper): et faerdigt
               # trin er groent med et flueben.
               "state-ok-fg",
               # Hubbens fliser og liste (Masterdata Hub/build/build_hub.py):
               # domaeneikonerne og statusikonerne er SVG'er i de samme farver.
               "domain-fl", "domain-eq", "domain-mp", "domain-mat", "domain-vhp",
               "state-error-fg", "state-neutral-fg",
               "state-violet-fg", "state-lime-fg", "state-rose-fg",
               # Skillelinjerne i FL-strukturens tabel (issue #77) - de samme
               # som C_DIVIDER i galleriernes raekker.
               "border-subtle",
               # Operationstabellens overskrift er en grå kasse som listernes.
               "bg-muted")



def _hex(rgba):
    body = rgba[rgba.index("(") + 1:rgba.rindex(")")]
    r, g, b = (int(round(float(n))) for n in body.split(",")[:3])
    return "#%02X%02X%02X" % (r, g, b)


def ref_hex(name):
    """Tokenreferencen til brug INDE I en HTML-stylestreng: C.'hex-text-muted'.

    Bemaerk at den skal konkateneres ind i HTML'en med &, ikke skrives ind
    i strengen - den er et udtryk, ikke et tal."""
    if name not in HTML_TOKENS:
        raise KeyError(
            "%r er ikke en HTML-token. Tilfoej den til HTML_TOKENS.\nKendte: %s"
            % (name, ", ".join(HTML_TOKENS)))
    return "%s.'hex-%s'" % (RECORD, name)


# Flagene i sprogvaelgeren (tools/side_nav.py), tegnet i en 24 x 24 firkant.
# Flagfarver er faste - et flag skal ligne sig selv i begge temaer.
FLAG_SVG = {
    "en": ("<rect width='24' height='24' fill='#1F3A93'/>"
           "<path d='M0 0L24 24M24 0L0 24' stroke='#FFFFFF' stroke-width='4.4'/>"
           "<path d='M0 0L24 24M24 0L0 24' stroke='#D7263D' stroke-width='1.6'/>"
           "<path d='M12 0V24M0 12H24' stroke='#FFFFFF' stroke-width='7'/>"
           "<path d='M12 0V24M0 12H24' stroke='#D7263D' stroke-width='4'/>"),
    "da": ("<rect width='24' height='24' fill='#D7263D'/>"
           "<path d='M8.5 0V24M0 12H24' stroke='#FFFFFF' stroke-width='3.6'/>"),
    "de": ("<rect width='24' height='8' fill='#1B1B1B'/>"
           "<rect y='8' width='24' height='8' fill='#DD2A2A'/>"
           "<rect y='16' width='24' height='8' fill='#FFC72C'/>"),
}


def ref(name):
    """Tokenreferencen, som den skrives i en skaerm: C.'bg-app'.

    Et ukendt navn fanges HER og ikke i Studio. Power Fx ville bare give
    blank for et felt, recorden ikke har - og blank er gennemsigtig."""
    if name not in LIGHT:
        raise KeyError(
            "Ukendt designtoken: %r\nKendte: %s"
            % (name, ", ".join(sorted(LIGHT))))
    return "%s.'%s'" % (RECORD, name)


def _record(values, indent=8):
    pad = " " * indent
    lines = []
    for k in LIGHT:                       # samme raekkefoelge i begge grene
        lines.append("%s'%s': %s" % (pad, k, values[k]))
    # De afledte hex-vaerdier til HTML. De er STRENGE i recorden, mens
    # resten er farver - det er Power Fx ligeglad med, saa laenge de to
    # grene er enige om typen felt for felt.
    for k in HTML_TOKENS:
        lines.append('%s\'hex-%s\': "%s"' % (pad, k, _hex(values[k])))
    return "{\n" + ",\n".join(lines) + "\n" + " " * (indent - 4) + "}"


def formula():
    """Den navngivne formel til App.Formulas.

    Afsluttes med semikolon - det goer alle navngivne formler, ogsaa den
    sidste."""
    return (
        "// DESIGNTOKENS. Genereret af tools/design_tokens.py - ret ikke her.\n"
        "//\n"
        "// Hver farve i appen staar som C.'et-navn'. Moerk tilstand er ikke\n"
        "// en funktion; den er den anden gren af den her If.\n"
        "%s = If(\n"
        "    // LYS TILSTAND\n"
        "    !%s,\n"
        "    %s,\n"
        "    // MOERK TILSTAND\n"
        "    %s\n"
        ");" % (RECORD, DARK_VAR, _record(LIGHT), _record(DARK))
    )


def onstart_block():
    """Det, der skal staa OEVERST i App.OnStart.

    HVORFOR IfError
    ---------------
    SaveData/LoadData virker i den publicerede web-afspiller (1 MB), men
    IKKE naar appen koeres i Studio. Uden IfError fejler OnStart derfor
    hver gang nogen trykker Preview - og fejlen ser ud til at handle om
    noget helt andet, fordi resten af OnStart saa ikke naar at koere.

    HVORFOR Coalesce MED TRE LED
    ----------------------------
    1. Param(THEME_PARAM) - hubben sender temaet med i play-URL'en, saa et
       klik fra hubben over i en satellit lander i det SAMME tema. Uden
       det ville lageret vaere isoleret pr. app-id: temaet ville skifte
       tilbage til lyst, hver gang brugeren klikkede videre.
    2. Det gemte valg - appen aabnet direkte, uden om hubben.
    3. false - foerste gang nogen aabner appen.

    Bemaerk at Param() kun laeses ved opstart. Skifter brugeren tema inde i
    satellitten, er det DET valg, der gemmes, og som gaelder naeste gang."""
    return (
        "// TEMAVALGET. Skal staa foerst: alt hvad skaermen tegner, laeser C,\n"
        "// og C laeser %s.\n"
        "//\n"
        "// IfError fordi SaveData/LoadData ikke findes i Studio. Uden den\n"
        "// stopper hele OnStart, hver gang nogen trykker Preview.\n"
        "IfError(LoadData(%s, \"%s\", true), Blank());\n"
        "Set(\n"
        "    %s,\n"
        "    Coalesce(\n"
        "        If(Lower(Param(\"%s\")) = \"dark\", true,\n"
        "           Lower(Param(\"%s\")) = \"light\", false),\n"
        "        First(%s).Dark,\n"
        "        false\n"
        "    )\n"
        ");"
        % (DARK_VAR, PREFS_COLLECTION, PREFS_KEY, DARK_VAR,
           THEME_PARAM, THEME_PARAM, PREFS_COLLECTION)
    )


def toggle_action():
    """OnSelect paa temaknappen.

    Skriver BAADE variablen (saa skaermen skifter med det samme) og
    lageret (saa valget er der naeste gang). SaveData er pakket ind af
    samme grund som LoadData.

    FORUDSAETNING: appens "Formula-level error management" skal vaere slaaet
    TIL (Settings > Updates > Retired: "Disable formula-level management"
    skal staa OFF). Den er til som standard i nye apps. Er den slaaet fra,
    virker IfError ikke efter hensigten, og saa smider SaveData i Studio en
    fejl igennem i stedet for at blive fanget.

    Ingen trailing semikolon: OnStart-generatoren i dette repo klipper en
    afsluttende ';' af, og det samme moenster foelges her."""
    return (
        "Set(%s, !%s);\n"
        "ClearCollect(%s, { Dark: %s });\n"
        "IfError(SaveData(%s, \"%s\"), Blank())"
        % (DARK_VAR, DARK_VAR, PREFS_COLLECTION, DARK_VAR,
           PREFS_COLLECTION, PREFS_KEY)
    )


def prefs_schema():
    """Samlingen bag SaveData, som den skal erklaeres i OnStart.

    Samme moenster som alle andre arbejdssamlinger i repoet: ClearCollect
    med een raekke og derefter Clear, saa Power Fx kender kolonnetypen,
    foer der er data. Uden det kender den ikke typen paa .Dark, og
    Coalesce i onstart_block() kan ikke oversaettes."""
    return (PREFS_COLLECTION, {"Dark": "false"})


def launch_suffix(url_expr_is_literal=True):
    """Det, der skal haenges paa en play-URL, saa temaet foelger med over.

    Returnerer et Power Fx-UDTRYK, ikke en streng: temaet afgoeres paa
    klikketidspunktet, ikke da skaermen blev bygget.

    Bemaerk '?' vs '&': hubbens fliser sender ingen andre parametre, mens
    "Open" paa en raekke allerede sender ?reqid=. Derfor tager kalderen
    stilling til skilletegnet."""
    return 'If(%s, "dark", "light")' % DARK_VAR


def theme_query(sep="?"):
    """Hele parameterstumpen, klar til at blive konkateneret paa en URL."""
    return '"%s%s=" & %s' % (sep, THEME_PARAM, launch_suffix())


if __name__ == "__main__":
    print(formula())
    print()
    print(onstart_block())
    print()
    print(toggle_action())
