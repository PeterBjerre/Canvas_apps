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
# Vaerdierne er ORDRET dem, apperne har i dag. Det er med vilje: den her
# aendring flytter farverne et andet sted hen, den laver dem ikke om. Er
# appen lysegraa i dag, er den ogsaa lysegraa bagefter.
#
# EN KENDT AFVIGELSE: 'state-ok-fg' paa 'state-ok-bg' giver 4,44:1 og
# rammer dermed lige under WCAG AA's 4,5 for broedtekst. Det er en fejl,
# appen har i dag, og den staar her uaendret, saa lys tilstand ser ud
# praecis som foer. Rettelsen er een vaerdi - RGBA(19, 120, 87, 1) giver
# 4,86 og kan ikke ses med det blotte oeje.
# ---------------------------------------------------------------------------
LIGHT = {
    # --- brand ---
    'color-brand-primary':       "RGBA(0, 103, 174, 1)",
    'color-brand-primary-hover': "RGBA(0, 122, 204, 1)",
    'color-brand-primary-soft':  "RGBA(198, 224, 249, 1)",

    # --- baggrunde ---
    'bg-app':     "RGBA(237, 241, 247, 1)",
    'bg-surface': "RGBA(255, 255, 255, 1)",
    'bg-card':    "RGBA(250, 251, 253, 1)",
    'bg-muted':   "RGBA(240, 243, 248, 1)",

    # --- tekst ---
    'text-primary':    "RGBA(26, 34, 49, 1)",
    'text-muted':      "RGBA(89, 102, 122, 1)",
    'text-on-primary': "RGBA(255, 255, 255, 1)",

    # --- kanter ---
    'border-default': "RGBA(215, 222, 232, 1)",
    'border-subtle':  "RGBA(228, 233, 241, 1)",

    # --- inputfelter ---
    'input-bg':          "RGBA(255, 255, 255, 1)",
    'input-bg-disabled': "RGBA(240, 243, 248, 1)",

    # --- tilstande. Bruges BAADE af feltkanter og af statuschips ---
    'state-ok-fg':      "RGBA(21, 127, 92, 1)",
    'state-ok-bg':      "RGBA(232, 245, 238, 1)",
    'state-warn-fg':    "RGBA(138, 90, 0, 1)",
    'state-warn-bg':    "RGBA(253, 243, 226, 1)",
    'state-error-fg':   "RGBA(179, 50, 60, 1)",
    'state-error-bg':   "RGBA(253, 236, 236, 1)",
    'state-info-fg':    "RGBA(0, 83, 140, 1)",
    'state-info-bg':    "RGBA(222, 240, 252, 1)",
    'state-neutral-fg': "RGBA(89, 102, 122, 1)",
    'state-neutral-bg': "RGBA(228, 233, 241, 1)",

    # --- modalen. De 2% gennemsigtighed er der i dag og bevares, saa
    #     lys tilstand ser ud praecis som foer ---
    'bg-modal': "RGBA(255, 255, 255, 0.98)",
    'overlay':  "RGBA(15, 23, 42, 0.35)",

    # --- de fem domaener paa landingssiden ---
    'domain-fl':  "RGBA(0, 103, 174, 1)",
    'domain-eq':  "RGBA(14, 124, 134, 1)",
    'domain-mp':  "RGBA(21, 127, 92, 1)",
    'domain-mat': "RGBA(154, 99, 0, 1)",
    'domain-vhp': "RGBA(109, 74, 166, 1)",
}


# ---------------------------------------------------------------------------
# MOERKT TEMA
#
# Ikke "det lyse tema med omvendt lysstyrke". Hver vaerdi er valgt og
# EFTERREGNET - kontrastforholdene staar i docs/26-designtokens.md.
#
# De tre valg, der ikke var frie:
#
# 1. 'color-brand-primary' er blue-600 og ikke blue-500. Hvid tekst paa
#    blue-500 giver 3,68:1 og falder dermed under AA for de 14 px
#    halvfede knaptekster, appen bruger. Blue-600 giver 5,17:1 og staar
#    stadig 3,45:1 fra kortet bagved.
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
    'color-brand-primary':       "RGBA(37, 99, 235, 1)",
    'color-brand-primary-hover': "RGBA(29, 78, 216, 1)",
    'color-brand-primary-soft':  "RGBA(30, 58, 138, 1)",

    # --- baggrunde ---
    'bg-app':     "RGBA(12, 15, 23, 1)",
    'bg-surface': "RGBA(15, 23, 42, 1)",
    'bg-card':    "RGBA(15, 23, 42, 1)",
    'bg-muted':   "RGBA(30, 41, 59, 1)",

    # --- tekst ---
    'text-primary':    "RGBA(229, 231, 235, 1)",
    'text-muted':      "RGBA(148, 163, 184, 1)",
    'text-on-primary': "RGBA(255, 255, 255, 1)",

    # --- kanter ---
    'border-default': "RGBA(100, 116, 139, 1)",
    'border-subtle':  "RGBA(51, 65, 85, 1)",

    # --- inputfelter ---
    'input-bg':          "RGBA(2, 6, 23, 1)",
    'input-bg-disabled': "RGBA(30, 41, 59, 1)",

    # --- tilstande ---
    'state-ok-fg':      "RGBA(52, 211, 153, 1)",
    'state-ok-bg':      "RGBA(6, 46, 37, 1)",
    'state-warn-fg':    "RGBA(251, 191, 36, 1)",
    'state-warn-bg':    "RGBA(59, 38, 6, 1)",
    'state-error-fg':   "RGBA(248, 113, 113, 1)",
    'state-error-bg':   "RGBA(69, 19, 24, 1)",
    'state-info-fg':    "RGBA(96, 165, 250, 1)",
    'state-info-bg':    "RGBA(23, 37, 70, 1)",
    'state-neutral-fg': "RGBA(148, 163, 184, 1)",
    'state-neutral-bg': "RGBA(30, 41, 59, 1)",

    # --- modalen. Sloeret er moerkere end i lys tilstand: det skal skille
    #     modalen fra en baggrund, der i forvejen er moerk ---
    'bg-modal': "RGBA(15, 23, 42, 0.98)",
    'overlay':  "RGBA(2, 6, 23, 0.72)",

    # --- domaener. Lysere udgaver, saa striben kan ses mod det moerke kort ---
    'domain-fl':  "RGBA(96, 165, 250, 1)",
    'domain-eq':  "RGBA(45, 212, 191, 1)",
    'domain-mp':  "RGBA(52, 211, 153, 1)",
    'domain-mat': "RGBA(251, 191, 36, 1)",
    'domain-vhp': "RGBA(167, 139, 250, 1)",
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
HTML_TOKENS = ("text-primary", "text-muted")


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
