# -*- coding: utf-8 -*-
"""
En lille fortolker af Power Automates udtrykssprog (WDL) - kun de
funktioner, flowenes Compose-handlinger og mailtekster bruger. Testene
bruger den til at koere et flows udtryk paa et eksempel og se den faerdige
mail-HTML (fx escaping og linjeskift i BioSap-SendFeedbackMail, #194).

Ukendte funktioner giver en fejl - testen maa ikke gaette.
"""
import json
import re
from urllib.parse import unquote

_TOKEN = re.compile(r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<num>-?\d+(?:\.\d+)?)"
                    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<op>\?\[|[(),\[\]]))")


def _tokens(src):
    pos, out = 0, []
    src = src.rstrip()
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise SyntaxError("WDL: kan ikke laese %r" % src[pos:pos + 30])
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "str":
            val = val[1:-1].replace("''", "'")
        elif kind == "num":
            val = float(val) if "." in val else int(val)
        out.append((kind, val))
    return out


class _Ctx:
    def __init__(self, trigger_body, headers, outputs, item=None):
        self.trigger_body = trigger_body
        self.headers = headers
        self.outputs = outputs
        # item() - elementet i en Query, en Select eller en loekke.
        self.item = item

    def with_item(self, item):
        return _Ctx(self.trigger_body, self.headers, self.outputs, item)


def _min(*a):
    return min(a)


FUNCS = {
    "replace": lambda s, a, b: str(s).replace(a, b),
    "coalesce": lambda *a: next((x for x in a if x is not None), None),
    "decodeUriComponent": lambda s: unquote(s),
    "json": lambda s: json.loads(s),
    "if": None,                                  # doven - se _call
    "equals": lambda a, b: a == b,
    "empty": lambda x: x is None or len(x) == 0,
    "trim": lambda s: str(s).strip(),
    "toLower": lambda s: str(s).lower(),
    "startsWith": lambda s, p: str(s).lower().startswith(str(p).lower()),
    "concat": lambda *a: "".join(_str(x) for x in a),
    "and": lambda *a: all(a),
    "not": lambda x: not x,
    # Laengden er valgfri, som i flowet: substring(s, 2) er "resten".
    "substring": lambda s, i, n=None: s[i:] if n is None else s[i:i + n],
    "min": _min,
    "length": lambda x: len(x),
    "greater": lambda a, b: a > b,
    "first": lambda x: x[0] if len(x) else None,
    "toUpper": lambda s: str(s).upper(),
    # Measuring Points godkendelse (issue #210).
    "or": lambda *a: any(a),
    "contains": lambda c, x: x in (c or ()),
    "string": lambda x: _str(x),
}


def _str(x):
    if isinstance(x, bool):
        return "True" if x else "False"
    return "" if x is None else str(x)


class _Parser:
    def __init__(self, toks, ctx):
        self.t, self.i, self.ctx = toks, 0, ctx

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise SyntaxError("WDL: ventede %r, fik %r" % (val, tok[1]))
        self.i += 1
        return tok

    def expr(self):
        kind, val = self.take()
        if kind in ("str", "num"):
            res = val
        elif kind == "name" and val in ("true", "false", "null"):
            res = {"true": True, "false": False, "null": None}[val]
        elif kind == "name":
            res = self._call(val)
        else:
            raise SyntaxError("WDL: uventet %r" % (val,))
        # Egenskabsopslag: ?['x'] eller ['x']
        while self.peek()[1] in ("?[", "["):
            safe = self.take()[1] == "?["
            key = self.expr()
            self.take("]")
            if res is None and safe:
                continue
            res = res.get(key) if isinstance(res, dict) else res[key]
        return res

    def _args(self):
        self.take("(")
        args = []
        if self.peek()[1] != ")":
            args.append(self.i)
            self.skip()
            while self.peek()[1] == ",":
                self.take(",")
                args.append(self.i)
                self.skip()
        self.take(")")
        return args

    def skip(self):
        depth = 0
        while True:
            kind, val = self.peek()
            if val in ("(", "[", "?[") and kind == "op":
                depth += 1
            elif val in (")", "]") and kind == "op":
                if depth == 0:
                    return
                depth -= 1
            elif val == "," and depth == 0:
                return
            self.i += 1

    def _eval_at(self, idx):
        save = self.i
        self.i = idx
        val = self.expr()
        self.i = save
        return val

    def _call(self, name):
        starts = self._args()
        if name == "if":
            cond = self._eval_at(starts[0])
            return self._eval_at(starts[1] if cond else starts[2])
        args = [self._eval_at(s) for s in starts]
        if name == "triggerBody":
            return self.ctx.trigger_body
        if name == "triggerOutputs":
            return {"headers": self.ctx.headers, "body": self.ctx.trigger_body}
        if name in ("outputs", "body"):
            return self.ctx.outputs[args[0]]
        if name == "item":
            return self.ctx.item
        if name not in FUNCS:
            raise NotImplementedError("WDL-funktion %s" % name)
        return FUNCS[name](*args)


def evaluate(expr, ctx):
    p = _Parser(_tokens(expr), ctx)
    val = p.expr()
    if p.i != len(p.t):
        raise SyntaxError("WDL: rest efter udtryk: %r" % (p.t[p.i:],))
    return val


def _interpolate(s, ctx):
    out, i = [], 0
    while True:
        j = s.find("@{", i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:j])
        # Find den afsluttende } uden for strenge.
        k, depth, in_str = j + 2, 0, False
        while True:
            c = s[k]
            if in_str:
                if c == "'":
                    if k + 1 < len(s) and s[k + 1] == "'":
                        k += 1
                    else:
                        in_str = False
            elif c == "'":
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                if depth == 0:
                    break
                depth -= 1
            k += 1
        out.append(_str(evaluate(s[j + 2:k], ctx)))
        i = k + 1


def value(v, ctx):
    """En handlings input: "@udtryk", tekst med @{...}, eller et objekt."""
    if isinstance(v, dict):
        return {k: value(x, ctx) for k, x in v.items()}
    if isinstance(v, str):
        if v.startswith("@") and not v.startswith("@{"):
            return evaluate(v[1:], ctx)
        return _interpolate(v, ctx)
    return v


def _query(action, ctx):
    """En Query-handling: de elementer i "from", hvor "where" er sand."""
    src = value(action["inputs"]["from"], ctx) or []
    return [it for it in src
            if value(action["inputs"]["where"], ctx.with_item(it))]


def _select(action, ctx):
    """En Select-handling: "select" regnet for hvert element i "from"."""
    src = value(action["inputs"]["from"], ctx) or []
    return [value(action["inputs"]["select"], ctx.with_item(it)) for it in src]


def run(actions, names, trigger_body, headers):
    """Koer handlingerne names i raekkefoelge; returner outputs.

    Compose er sit input. Query og Select faar deres element bundet til
    item(), som i flowet - saa et filter eller et opslag kan koeres paa en
    eksempelraekke uden at skrive dets logik om i Python."""
    ctx = _Ctx(trigger_body, headers, {})
    for n in names:
        a = actions[n]
        if a.get("type") == "Query":
            ctx.outputs[n] = _query(a, ctx)
        elif a.get("type") == "Select":
            ctx.outputs[n] = _select(a, ctx)
        else:
            ctx.outputs[n] = value(a["inputs"], ctx)
    return ctx
