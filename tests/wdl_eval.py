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
    def __init__(self, trigger_body, headers, outputs):
        self.trigger_body = trigger_body
        self.headers = headers
        self.outputs = outputs


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
    "substring": lambda s, i, n: s[i:i + n],
    "min": _min,
    "length": lambda x: len(x),
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


def run(actions, names, trigger_body, headers):
    """Koer Compose-handlingerne names i raekkefoelge; returner outputs."""
    ctx = _Ctx(trigger_body, headers, {})
    for n in names:
        ctx.outputs[n] = value(actions[n]["inputs"], ctx)
    return ctx
