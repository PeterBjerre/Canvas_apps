"""! binder staerkere end < og = i Power Fx: "!LayoutRank < 2" er
"(!LayoutRank) < 2" - en boolean sammenlignet med et tal, som Studio
afviser ("Invalid argument type", VH-planens header efter #445).
Negationen af en sammenligning skal i parentes: "!(LayoutRank < 2)"."""
import glob
import re

BAD = re.compile(r"(?<![!=<>])!\s*[A-Za-z_][A-Za-z0-9_.]*\s*(<=|>=|<>|<|>|=)(?!=)")


def test_no_negated_comparison_without_parentheses():
    hits = []
    for path in sorted(glob.glob("BIO SAP App/*.pa.yaml")):
        with open(path, encoding="utf-8") as f:
            for no, line in enumerate(f, 1):
                for m in BAD.finditer(line):
                    hits.append(f"{path}:{no}: {m.group(0)}")
    assert not hits, "\n".join(hits[:20])
