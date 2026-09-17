#!/usr/bin/env python3
"""Statisk kontrol af VBA-modulerne i excel/src.

Regnearket kan kun kompileres i Excel, og hver kompilering koster en runde
frem og tilbage. Det her fanger de fejl, der ellers foerst dukker op der:
en procedure uden End, en GoTo uden label, et modul-kvalificeret kald til
noget, der ikke er Public.

Kontrollerne er bevidst konservative. En kontrol, der raaber op om noget,
der er i orden, bliver slaaet fra - og saa fanger den heller ikke det, den
var sat til.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "excel" / "src"

PROC_START = re.compile(
    r"^\s*(?:(Public|Private|Friend)\s+)?(?:Static\s+)?"
    r"(Sub|Function|Property\s+(?:Get|Let|Set))\s+([A-Za-z_]\w*)",
    re.IGNORECASE,
)
PROC_END = re.compile(r"^\s*End\s+(Sub|Function|Property)\b", re.IGNORECASE)
DECL_START = re.compile(r"^\s*(?:Public|Private)\s+Declare\b", re.IGNORECASE)
LABEL = re.compile(r"^\s*([A-Za-z_]\w*):\s*(?:'.*)?$")
GOTO = re.compile(r"\bGoTo\s+([A-Za-z_]\w*)", re.IGNORECASE)
RESUME = re.compile(r"\bResume\s+([A-Za-z_]\w*)", re.IGNORECASE)
PUBLIC_CONST = re.compile(
    r"^\s*(?:Public\s+)?Const\s+([A-Za-z_]\w*)", re.IGNORECASE)
PUBLIC_VAR = re.compile(r"^\s*Public\s+(?!Const|Declare|Type|Enum)([A-Za-z_]\w*)",
                        re.IGNORECASE)

# Dokumentmoduler er ogsaa objekter og opfoerer sig ikke som navnerum.
DOCUMENT_MODULES = {"thisworkbook"}

# Betinget kompilering. Et #If VBA7-blok deklarerer typisk den SAMME
# procedure to gange med hver sin signatur. Laeser man begge grene, ser
# den anden ud som en procedure, der starter foer den foerste er slut.
COND_IF = re.compile(r"^\s*#\s*(If|ElseIf)\b", re.IGNORECASE)
COND_ELSE = re.compile(r"^\s*#\s*Else\b", re.IGNORECASE)
COND_END = re.compile(r"^\s*#\s*End\s+If\b", re.IGNORECASE)


def strip_comment(line: str) -> str:
    """Fjerner en kommentar, men kun uden for en streng."""
    out, in_str = [], False
    for ch in line:
        if ch == '"':
            in_str = not in_str
        elif ch == "'" and not in_str:
            break
        out.append(ch)
    return "".join(out)


def logical_lines(raw: list[str]):
    """Slaar fortsaettelseslinjer sammen. Giver (linjenr, tekst)."""
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


class Module:
    def __init__(self, path: Path):
        self.path = path
        self.raw = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
        m = re.match(r'Attribute VB_Name = "(.+)"', self.raw[0] if self.raw else "")
        self.name = m.group(1) if m else path.stem
        self.public: set[str] = set()
        self.procs: list[tuple[str, int, int, str]] = []  # name, start, end, visibility


def parse(mod: Module, problems: list[str]):
    cur = None          # (name, startline, visibility, kind)
    labels: set[str] = set()
    jumps: list[tuple[int, str]] = []
    skip_branch = False

    for lineno, text in logical_lines(mod.raw):
        if not text.strip():
            continue

        # Kun den foerste gren laeses. Det er nok til at holde styr paa
        # strukturen, og det er strukturen, kontrollen handler om.
        if COND_END.match(text):
            skip_branch = False
            continue
        if COND_ELSE.match(text):
            skip_branch = True
            continue
        if COND_IF.match(text):
            continue
        if skip_branch:
            continue

        if DECL_START.match(text):
            continue

        if cur is None:
            m = PROC_START.match(text)
            if m:
                vis = (m.group(1) or "Public").title()
                cur = (m.group(3), lineno, vis, m.group(2).split()[0].title())
                labels, jumps = set(), []
                if vis == "Public":
                    mod.public.add(m.group(3).lower())
                continue
            mc = PUBLIC_CONST.match(text)
            if mc and not re.match(r"^\s*Private\s", text, re.IGNORECASE):
                mod.public.add(mc.group(1).lower())
                continue
            mv = PUBLIC_VAR.match(text)
            if mv:
                mod.public.add(mv.group(1).lower())
            continue

        # inde i en procedure
        if PROC_END.match(text):
            for jline, target in jumps:
                if target.lower() not in {l.lower() for l in labels}:
                    problems.append(
                        f"{mod.path}:{jline}: GoTo/Resume '{target}' har intet label "
                        f"i {cur[3]} {cur[0]}")
            mod.procs.append((cur[0], cur[1], lineno, cur[2]))
            cur = None
            continue

        m = PROC_START.match(text)
        if m:
            problems.append(
                f"{mod.path}:{cur[1]}: {cur[3]} {cur[0]} mangler 'End {cur[3]}' "
                f"- {m.group(2).title()} {m.group(3)} starter paa linje {lineno}")
            cur = (m.group(3), lineno, (m.group(1) or "Public").title(),
                   m.group(2).split()[0].title())
            labels, jumps = set(), []
            continue

        ml = LABEL.match(text)
        if ml and not re.search(r"\b(Case|Then|Else)\b", text, re.IGNORECASE):
            labels.add(ml.group(1))

        for rx in (GOTO, RESUME):
            for target in rx.findall(text):
                if target.lower() in {"0", "next"}:
                    continue
                jumps.append((lineno, target))

    if cur is not None:
        problems.append(f"{mod.path}:{cur[1]}: {cur[3]} {cur[0]} mangler 'End {cur[3]}'")


def check_qualified_calls(mods: dict[str, Module], problems: list[str]):
    """modX.Member skal findes og vaere Public i modX.

    Kun standardmoduler (.bas). ThisWorkbook og Sheet1 er ogsaa objekter,
    saa ThisWorkbook.Worksheets er et helt almindeligt opslag paa
    Excel-objektet og ikke et kald til modulets egne medlemmer.
    """
    known = {
        m.name.lower(): m
        for m in mods.values()
        if m.path.suffix.lower() == ".bas"
        and m.name.lower() not in DOCUMENT_MODULES
    }
    rx = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)")
    for mod in mods.values():
        for lineno, text in logical_lines(mod.raw):
            for owner, member in rx.findall(text):
                target = known.get(owner.lower())
                if target is None or target is mod:
                    continue
                if member.lower() not in target.public:
                    problems.append(
                        f"{mod.path}:{lineno}: {owner}.{member} findes ikke som "
                        f"Public i {target.name}")


def main() -> int:
    if not SRC.is_dir():
        print(f"fandt ikke {SRC}")
        return 2

    paths = sorted(SRC.rglob("*.bas")) + sorted(SRC.rglob("*.cls"))
    problems: list[str] = []
    mods: dict[str, Module] = {}

    for p in paths:
        mod = Module(p)
        mods[mod.name] = mod
        parse(mod, problems)

    check_qualified_calls(mods, problems)

    print(f"{len(paths)} moduler, "
          f"{sum(len(m.procs) for m in mods.values())} procedurer")

    if problems:
        print(f"\n{len(problems)} problemer:\n")
        for line in problems:
            print("  " + line)
        return 1

    print("ingen problemer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
