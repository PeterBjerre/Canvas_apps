#!/usr/bin/env python3
"""Strenge tjek af VH-plan Opretter (excel/opretter/*.bas).

    python3 tools/check_vba.py        # koerer ogsaa disse

HVORFOR
-------
Opretteren er skrevet uden en Excel at kompilere i. Excel melder foerst
fejlene, naar modulerne er importeret - og saa hos den, der skal bruge dem.
Tre slags fejl er de almindelige, og de kan findes uden Excel:

  1. BLOKKE. Et If uden End If, et For uden Next, et With uden End With.
     Excel siger "Block If without End If" og peger et andet sted hen.
  2. OPTION EXPLICIT. Et navn, der ikke er erklaeret - typisk en
     stavefejl i et variabelnavn. Excel siger "Variable not defined",
     men foerst naar proceduren kaldes.
  3. TEGNSAET. VBA-editoren laeser .bas-filer i Windows' tegnsaet. Et
     UTF-8 "ae" bliver til to tegn. Kildekoden skal vaere ren ASCII;
     danske bogstaver paa skaermen laves med VhpUtil.Dk("{ae}").

Tjek 2 kender VBA's egne ord og funktioner og de dele af Excel, opretteren
bruger (BUILTINS nedenfor). Et nyt indbygget navn, der giver et fund, skal
ind i listen - IKKE et navn, der er stavet forkert.

Moduler fra andre (JsonConverter, VBA-JSON) springes over: de er afproevet,
og de bruger betinget kompilering, tjekket ikke forsoeger at forstaa.
"""
from __future__ import annotations

import re

THIRD_PARTY = {"jsonconverter"}

KEYWORDS = {
    "if", "then", "else", "elseif", "end", "for", "each", "in", "to", "step",
    "next", "do", "loop", "while", "until", "wend", "select", "case", "with",
    "sub", "function", "property", "get", "let", "set", "dim", "redim",
    "preserve", "static", "const", "private", "public", "global", "friend",
    "byval", "byref", "optional", "paramarray", "as", "new", "nothing", "null",
    "empty", "true", "false", "and", "or", "not", "xor", "eqv", "imp", "mod",
    "like", "is", "typeof", "exit", "goto", "gosub", "return", "on", "error",
    "resume", "call", "option", "explicit", "compare", "text", "binary", "base",
    "attribute", "declare", "lib", "alias", "ptrsafe", "type", "enum", "me",
    "open", "close", "print", "input", "output", "append", "line", "write",
    "put", "seek", "lock", "unlock", "name", "kill", "mkdir", "rmdir", "stop",
    "debug", "err", "erase", "lset", "rset", "event", "raiseevent",
    "withevents", "implements", "access", "shared", "random", "len",
}

# VBA's funktioner og konstanter samt de dele af Excel og Office, opretteren
# bruger. Smaa bogstaver; et "$" bag paa navnet fjernes foer opslaget.
BUILTINS = {
    # strenge
    "left", "right", "mid", "trim", "ltrim", "rtrim", "ucase", "lcase",
    "instr", "instrrev", "replace", "split", "join", "format", "cstr", "clng",
    "cint", "cdbl", "cdate", "cbool", "cbyte", "ccur", "cvar", "csng", "val",
    "str", "chr", "chrw", "asc", "ascw", "space", "string", "strcomp",
    "strconv", "hex", "oct",
    # typer og tests
    "isnumeric", "isdate", "isempty", "isnull", "isobject", "isarray",
    "iserror", "ismissing", "typename", "vartype", "lbound", "ubound", "array",
    # datoer og tal
    "now", "date", "time", "timer", "year", "month", "day", "hour", "minute",
    "second", "dateadd", "datediff", "dateserial", "timeserial", "datevalue",
    "weekday", "int", "fix", "abs", "round", "sgn", "sqr", "rnd",
    # andet
    "iif", "choose", "switch", "environ", "shell", "doevents", "createobject",
    "getobject", "getsetting", "savesetting", "deletesetting", "freefile",
    "eof", "lof", "dir", "filelen", "filedatetime", "msgbox", "inputbox",
    "callbyname", "filter", "appactivate", "beep", "rgb",
    # konstanter
    "vbcrlf", "vblf", "vbcr", "vbtab", "vbnullstring", "vbnullchar",
    "vbtextcompare", "vbbinarycompare", "vbobjecterror", "vbokonly",
    "vbokcancel", "vbyesno", "vbyesnocancel", "vbyes", "vbno", "vbok",
    "vbcancel", "vbinformation", "vbexclamation", "vbcritical", "vbquestion",
    "vbsystemmodal", "vbdefaultbutton1", "vbdefaultbutton2",
    "vbmsgboxsetforeground", "vbnormalfocus", "vbstring", "vbboolean",
    "vblong", "vbdouble", "vbempty", "vbnull", "vbobject", "vbarray",
    # Excel
    "application", "thisworkbook", "activesheet", "activecell",
    "activeworkbook", "worksheets", "sheets", "range", "cells", "rows",
    "columns", "selection", "xlsrcrange", "xlyes", "xlno", "xlup",
    "xltoleft", "xlcontinuous", "xledgebottom",
}

PROC_HEAD = re.compile(
    r"^\s*(?:(?:Public|Private|Friend)\s+)?(?:Static\s+)?"
    r"(Sub|Function|Property\s+(?:Get|Let|Set))\s+([A-Za-z_]\w*)\s*(\((.*)\))?",
    re.IGNORECASE)
PROC_END = re.compile(r"^\s*End\s+(Sub|Function|Property)\b", re.IGNORECASE)
LABEL = re.compile(r"^\s*([A-Za-z_]\w*):\s*$")
STRING = re.compile(r'"(?:[^"]|"")*"')
NUMBER = re.compile(r"&[HhOo][0-9A-Fa-f]+&?|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[#!@&%]?")
DATE_LIT = re.compile(r"#[^#\n]+#")
AS_TYPE = re.compile(r"\bAs\s+(?:New\s+)?[A-Za-z_][\w.]*", re.IGNORECASE)
NEW_TYPE = re.compile(r"\bNew\s+[A-Za-z_][\w.]*", re.IGNORECASE)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*[$]?")
DECL = re.compile(r"^\s*(?:Dim|Static|Const|ReDim(?:\s+Preserve)?|Private|Public|Global)\s+(.*)$",
                  re.IGNORECASE)


def strip_comment(line: str) -> str:
    out, in_str = [], False
    for ch in line:
        if ch == '"':
            in_str = not in_str
        elif ch == "'" and not in_str:
            break
        out.append(ch)
    return "".join(out)


def logical_lines(raw: list[str]):
    buf, start = "", None
    for i, line in enumerate(raw, 1):
        code = strip_comment(line).rstrip()
        if start is None:
            start = i
        if code.endswith(" _"):
            buf += code[:-1]
            continue
        yield start, buf + code
        buf, start = "", None
    if start is not None:
        yield start, buf


def clean(code: str) -> str:
    """Strenge, tal og datoer ud - tilbage er navne og tegn."""
    code = STRING.sub('""', code)
    code = DATE_LIT.sub("0", code)
    code = NUMBER.sub("0", code)
    return code


def statements(code: str):
    """En logisk linje delt ved ":" (men ikke ":=")."""
    return [s for s in re.split(r":(?!=)", code)]


def split_top(s: str):
    """Del ved kommaer, der ikke staar i parenteser."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def declared_names(decl_body: str):
    """Navnene i 'a As Long, b(1 To 3) As String' eller 'Function F(...)'."""
    names = []
    body = re.sub(r"^\s*(?:Sub|Function|Declare)\b.*", "", decl_body, flags=re.IGNORECASE)
    for part in split_top(body):
        part = re.sub(r"^\s*(?:WithEvents|Optional|ByVal|ByRef|ParamArray|Const)\s+", "",
                      part.strip(), flags=re.IGNORECASE)
        part = re.sub(r"^\s*(?:ByVal|ByRef)\s+", "", part, flags=re.IGNORECASE)
        m = re.match(r"([A-Za-z_]\w*\$?)", part)
        if m:
            names.append(m.group(1).rstrip("$").lower())
    return names


def norm(name: str) -> str:
    return name.rstrip("$").lower()


class Mod:
    def __init__(self, path, raw, name):
        self.path, self.raw, self.name = path, raw, name
        self.module_names: set[str] = set()
        self.procs: list[dict] = []      # name, start, end, params, lines


def scan(path, raw, name) -> Mod:
    m = Mod(path, raw, name)
    cur = None
    for lineno, code in logical_lines(raw):
        if not code.strip() or code.lstrip().startswith("Attribute "):
            continue
        if cur is None:
            h = PROC_HEAD.match(code)
            if h:
                params = declared_names(h.group(4) or "")
                cur = {"name": h.group(2).lower(), "start": lineno, "params": set(params),
                       "lines": [], "head": code}
                continue
            d = DECL.match(code)
            if d and not re.match(r"^\s*(?:Private|Public)\s+(?:Declare|Sub|Function|Property|Type|Enum)\b",
                                  code, re.IGNORECASE):
                body = re.sub(r"^\s*(?:Const|WithEvents)\s+", "", d.group(1), flags=re.IGNORECASE)
                for n in declared_names(clean(body)):
                    m.module_names.add(n)
            continue
        if PROC_END.match(code):
            cur["end"] = lineno
            m.procs.append(cur)
            cur = None
            continue
        cur["lines"].append((lineno, code))
    return m


#==============================================================================
# 1. Tegnsaet og hoved
#==============================================================================
def check_text(mod: Mod, problems: list[str]):
    for i, line in enumerate(mod.raw, 1):
        bad = [c for c in line if ord(c) > 127]
        if bad:
            problems.append(f"{mod.path}:{i}: tegn uden for ASCII ({''.join(bad[:3])!r}) - "
                            f"brug VhpUtil.Dk(\"{{ae}}\") til danske bogstaver")
    if not mod.raw or not mod.raw[0].startswith('Attribute VB_Name = "'):
        problems.append(f"{mod.path}:1: foerste linje skal vaere Attribute VB_Name = \"...\"")
    if not any(re.match(r"^\s*Option\s+Explicit\b", l, re.IGNORECASE) for l in mod.raw[:5]):
        problems.append(f"{mod.path}: mangler Option Explicit i toppen")


#==============================================================================
# 2. Blokke
#==============================================================================
OPENERS = [
    (re.compile(r"^\s*Select\s+Case\b", re.I), "Select"),
    (re.compile(r"^\s*For\b", re.I), "For"),
    (re.compile(r"^\s*Do\b", re.I), "Do"),
    (re.compile(r"^\s*While\b", re.I), "While"),
    (re.compile(r"^\s*With\b", re.I), "With"),
]
CLOSERS = [
    (re.compile(r"^\s*End\s+If\b", re.I), "If"),
    (re.compile(r"^\s*End\s+Select\b", re.I), "Select"),
    (re.compile(r"^\s*Next\b", re.I), "For"),
    (re.compile(r"^\s*Loop\b", re.I), "Do"),
    (re.compile(r"^\s*Wend\b", re.I), "While"),
    (re.compile(r"^\s*End\s+With\b", re.I), "With"),
]
IF_BLOCK = re.compile(r"^\s*If\b.*\bThen\s*$", re.I)
IF_LINE = re.compile(r"^\s*If\b.*\bThen\b\s*\S", re.I)


def check_blocks(mod: Mod, problems: list[str]):
    for proc in mod.procs:
        stack: list[tuple[str, int]] = []
        for lineno, code in proc["lines"]:
            code = clean(code)
            if LABEL.match(code):
                continue
            stmts = statements(code)
            # Et enkeltlinje-If ("If x Then y") aabner ingen blok - og alt
            # efter Then paa samme linje hoerer til det.
            if IF_LINE.match(code) and not IF_BLOCK.match(stmts[0]):
                continue
            for st in stmts:
                if not st.strip():
                    continue
                if IF_BLOCK.match(st):
                    stack.append(("If", lineno))
                    continue
                matched = False
                for rx, kind in CLOSERS:
                    if rx.match(st):
                        matched = True
                        if not stack or stack[-1][0] != kind:
                            want = stack[-1][0] if stack else "ingen"
                            problems.append(f"{mod.path}:{lineno}: {st.strip()[:20]!r} lukker {kind}, "
                                            f"men den aabne blok er {want} (i {proc['name']})")
                        else:
                            stack.pop()
                        break
                if matched:
                    continue
                for rx, kind in OPENERS:
                    if rx.match(st):
                        stack.append((kind, lineno))
                        break
        for kind, lineno in stack:
            problems.append(f"{mod.path}:{lineno}: {kind} uden afslutning i {proc['name']}")


#==============================================================================
# 3. Option Explicit
#==============================================================================
def check_names(mods: list[Mod], public: set[str], problems: list[str],
                all_module_names: set[str] = frozenset()):
    # Andre modulers procedurer er kun synlige, hvis de er Public - og de
    # staar i public. En Private procedure i et andet modul giver i Excel
    # "Sub or Function not defined", og det skal den ogsaa her.
    module_names = {m.name.lower() for m in mods} | {n.lower() for n in all_module_names}

    for mod in mods:
        own_procs = {p["name"] for p in mod.procs}
        for proc in mod.procs:
            local = set(proc["params"])
            labels = set()
            for _, code in proc["lines"]:
                c = clean(code)
                lm = LABEL.match(c)
                if lm:
                    labels.add(lm.group(1).lower())
                    continue
                for st in statements(c):
                    d = DECL.match(st)
                    if d:
                        body = AS_TYPE.sub("", d.group(1))
                        body = re.sub(r"^\s*Preserve\s+", "", body, flags=re.IGNORECASE)
                        local.update(declared_names(body))

            known = (KEYWORDS | BUILTINS | local | labels | mod.module_names | public |
                     module_names | own_procs | {proc["name"]})

            for lineno, code in proc["lines"]:
                c = clean(code)
                if LABEL.match(c):
                    continue
                c = AS_TYPE.sub("", c)
                c = NEW_TYPE.sub("", c)
                c = re.sub(r"\b(?:GoTo|Resume)\s+[A-Za-z_]\w*", "", c, flags=re.IGNORECASE)
                for tok in IDENT.finditer(c):
                    word = norm(tok.group(0))
                    before = c[:tok.start()].rstrip()
                    after = c[tok.end():].lstrip()
                    if before.endswith("."):
                        continue                 # medlem: obj.Text
                    if after.startswith(":="):
                        continue                 # navngivet argument
                    if word in known:
                        continue
                    problems.append(f"{mod.path}:{lineno}: '{tok.group(0)}' er ikke erklaeret "
                                    f"(Option Explicit) i {proc['name']}")


def run(modules, public_by_module, problems: list[str]):
    """modules: [(path, raw_lines, vb_name)]. public_by_module: {navn: set}."""
    mods = []
    for path, raw, name in modules:
        if name.lower() in THIRD_PARTY:
            continue
        m = scan(path, raw, name)
        check_text(m, problems)
        check_blocks(m, problems)
        mods.append(m)

    public = set()
    for name, names in public_by_module.items():
        public |= {n.lower() for n in names}
    check_names(mods, public, problems, set(public_by_module))
    return len(mods)
