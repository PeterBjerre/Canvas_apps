# -*- coding: utf-8 -*-
"""
EEN indgang til byggeriet - hele kaeden i EEN proces (REVIEW.md C7).

    python3 tools/build.py                   # alle apps
    python3 tools/build.py --app equipment   # een app
    python3 tools/build.py --env test

Samme kaede og samme tjek som tools/build_all.py - config, generate,
App.pa.yaml (tools/app_yaml.py), assemble og tjek - men uden et nyt
Python-subprocess pr. script. Hvert script koeres med runpy, og repoets
egne moduler glemmes bagefter, saa apperne ikke deler tilstand. Outputtet
(*.pa.yaml) er byte for byte det samme som build_all's.

build_all.py er stadig den, CI koerer: den isolerer med rigtige processer.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_all  # noqa: E402


def main(argv=None):
    build_all.IN_PROCESS = True
    t0 = time.time()
    rc = build_all.main(argv)
    print("\nBygget i een proces paa %.1f s." % (time.time() - t0))
    return rc


if __name__ == "__main__":
    sys.exit(main())
