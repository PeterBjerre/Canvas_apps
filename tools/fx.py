# -*- coding: utf-8 -*-
"""
Power Fx-tekst som struktur - EEN scanner til alle tjek.

HVORFOR DEN HER FIL FINDES
--------------------------
check_layout.py havde syv haandskrevne scannere, der hver fandt
parenteser og argumenter paa sin egen maade (REVIEW.md C7): nogle saa kun
"...", andre ogsaa '...', een ingen af dem, og ingen kendte kommentarer.
En parentes inde i en streng eller en apostrof i en kommentar ("don't")
kunne derfor faa et tjek til at laese resten af formlen forkert.

Her er reglerne een gang:

    "tekst"        streng. "" inde i den er et escaped anfoerselstegn.
    'navn'         et navn i anfoerselstegn ('@odata.type', 'text-primary').
    // ...         kommentar til linjens slutning.
    /* ... */      kommentar.

Alt, hvad der staar inde i en af dem, er ikke kode: parenteser og kommaer
dér taeller ikke.
"""


def walk(text, start=0):
    """(position, tegn) for hvert tegn, der er KODE - ikke streng, navn
    eller kommentar. Anfoerselstegnene selv er heller ikke kode."""
    i, n = start, len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
            j = i + 1
            while j < n:
                if text[j] == c:
                    if j + 1 < n and text[j + 1] == c:
                        j += 2          # "" eller '' - escaped
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        yield i, c
        i += 1


def open_string(text):
    """Sand, hvis en streng eller et navn i anfoerselstegn aldrig lukkes."""
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and text[i:i + 2] == "//":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and text[i:i + 2] == "/*":
            j = text.find("*/", i + 2)
            if j < 0:
                return False
            i = j + 2
            continue
        if c in "\"'":
            j = i + 1
            while j < n:
                if text[j] == c:
                    if j + 1 < n and text[j + 1] == c:
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                return True
            i = j + 1
            continue
        i += 1
    return False


def matching_paren(text, open_at):
    """Positionen af den ')', der lukker '(' ved open_at. -1 hvis ingen."""
    depth = 0
    for j, c in walk(text, open_at):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _open_paren(text, at):
    return text.index("(", at)


def call_end(text, at):
    """Positionen lige efter det kald, hvis '(' er den foerste efter at.
    Hele teksten, hvis kaldet aldrig lukkes."""
    j = matching_paren(text, _open_paren(text, at))
    return len(text) if j < 0 else j + 1


def call_args(text, at):
    """Argumenterne (uden trim) i det kald, hvis '(' er den foerste efter
    at. Delt paa komma i kaldets egen dybde. Lukkes kaldet aldrig, er det
    de argumenter, der naaede at staa."""
    i = _open_paren(text, at)
    depth, start, out = 0, i + 1, []
    for j, c in walk(text, i):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                out.append(text[start:j])
                return out
        elif c == "," and depth == 1:
            out.append(text[start:j])
            start = j + 1
    if start < len(text):
        out.append(text[start:])
    return out


def first_arg(text, at):
    """Foerste argument, trimmet - fx maalet i Patch(maal, ...)."""
    args = call_args(text, at)
    return args[0].strip() if args else ""


def rest_args(text, at):
    """Alt efter foerste argument - fx kilden i ClearCollect(col, kilde).
    Tom, hvis kaldet kun har eet argument."""
    args = call_args(text, at)
    return ",".join(args[1:]) if len(args) > 1 else ""


def split_top(text, seps):
    """Del text paa et af tegnene i seps - kun i yderste dybde, og aldrig
    inde i en streng, et navn eller en kommentar. Stykkerne trimmes."""
    parts, depth, last = [], 0, 0
    for j, c in walk(text):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and c in seps:
            parts.append(text[last:j].strip())
            last = j + 1
    parts.append(text[last:].strip())
    return parts


def paren_balance(text):
    """(slutdybde, gik under nul). Til tjekket for ubalancerede parenteser."""
    depth = 0
    for _j, c in walk(text):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                return depth, True
    return depth, False
