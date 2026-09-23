# tools/ paa sys.path. De tre store faellesfiler - gen_screen.py,
# build_helpers.py og check_layout.py - ligger DER og ikke i en kopi pr.
# app-mappe. sys.path er procesglobal, saa det raekker at saette den her i
# indgangen: alt hvad builderne importerer bagefter, finder dem selv.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__)))), "tools"))

# Selve tjekket staar i tools/check_layout.py. Den her fil er kun
# indgangen, saa "python3 check_layout.py" stadig virker fra app'ens
# build-mappe, som SKILL.md beskriver.
from check_layout import main

if __name__ == "__main__":
    _sys.exit(main())
