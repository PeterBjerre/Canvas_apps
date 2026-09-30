# -*- coding: utf-8 -*-
"""
Brugerbeskederne for gem og indsend - de SAMME ord i alle apps.

Her stod "Save failed:", "It failed:" og "Submit failed:" for den samme
haendelse, og "Submitted as X." (FL), "... - see it on the landing page."
(Equipment/Material) og "MP... submitted." (VH-plan) for en anden
(REVIEW.md A6). Nu kalder alle apps funktionerne her.

Argumenterne er Power Fx-udtryk; funktionerne returnerer et Notify(...).
"""

LANDING = " - see it on the landing page."


def saved(no_expr):
    """Anmodningen er gemt som kladde og staar paa landingssiden."""
    return f'Notify("Saved as " & {no_expr} & "{LANDING}", NotificationType.Success)'


def submitted(no_expr):
    """Anmodningen er indsendt."""
    return f'Notify("Submitted as " & {no_expr} & "{LANDING}", NotificationType.Success)'


def failed(action, detail="FirstError.Message"):
    """action er "Save", "Submit" eller "Delete"."""
    return f'Notify("{action} failed: " & {detail}, NotificationType.Error)'
