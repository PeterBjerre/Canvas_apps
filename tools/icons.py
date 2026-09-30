# -*- coding: utf-8 -*-
"""
Ikoner, der skal vaere ENS overalt i Power Apps-loesningen.

Stierne er SVG-path-data i en 24 x 24 viewBox, tegnet som streg (fill
none, round caps/joins) - samme form som resten af ikonerne i sidebaren
(tools/side_nav.py) og hubben (Masterdata Hub/build/build_hub.py), som
selv bestemmer stregtykkelse og farve.

FUNCTIONAL LOCATION (issue #70)
-------------------------------
Et kraftvaerk i en lokationsnaal: naalens omrids og et vaerk med
savtakket tag, skorsten og roeg. Et koeletaarn blev proevet, men var
ikke til at genkende i 18-24 px. Det afloeser den tomme lokationsnaal, der
stod to steder med hver sin kopi af stien (sidebaren og hubben). Nu
staar den her, og begge laeser den - et nyt ikon er een linje.
"""

FUNCTIONAL_LOCATION = (
    # naalen
    "M12 21.5s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z "
    # vaerket: savtakket tag og skorsten
    "M8.5 14.5v-3l2 1.2v-1.2l2 1.2V8h2.5v6.5Z "
    # roegen fra skorstenen
    "M13.3 6.2c.4-.6 1.2-.6 1.6 0"
)

# Et ikon, der skal spejles vandret, tegnes med denne transform om
# stien (viewBox 24). Bruges af Measuring Points lineal, saa den peger
# samme vej som Equipments skruenoegle (issue #70).
MIRROR_X = "matrix(-1 0 0 1 24 0)"
