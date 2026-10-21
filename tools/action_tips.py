# -*- coding: utf-8 -*-
"""
HANDLINGSIKONERNES TOOLTIPS, EET STED (issue #515).

Hvert handlingsikon har et tooltip, der siger, hvad det GOER - kort og i
bydeform - og en AccessibleLabel med det samme indhold. Har handlingen
data (dokumenter, funktionspladser, udfyldte felter), staar antallet i
tooltippet:

    Edit row / View row            (raekken kan kun ses)
    View 3 documents / Add documents / No documents
    3 Functional Locations selected / No Functional Locations selected
    Copy row
    Delete row
    Edit manufacturer - 2 fields filled / Add manufacturer

ANTALLET ER DET, POPUPPEN VISER
-------------------------------
Udtrykket for antallet gives af den, der bygger ikonet, og skal vaere
det SAMME tal, som popuppen/sidepanelet viser: raekkens egen kolonne
(FileCount, ObjectList) eller en samling, der allerede er i hukommelsen
(colFlVals, colIbActN). Aldrig et nyt opslag i en datakilde pr. raekke.

TOOLTIP OG ACCESSIBLELABEL
--------------------------
Tooltippet gentager ikke det, der staar ved siden af ikonet - raekkens
noegle staar i raekken. En skaermlaeser hoerer derimod ikonerne i et
galleri efter hinanden uden raekken, saa label() saetter noeglen bag
det samme tooltip: "View 3 documents - M-000123".

Alt her er Power Fx-udtryk (tekst), klar til Tooltip/AccessibleLabel.
"""
import display_text as dt


def lit(text):
    """En Power Fx-tekstkonstant."""
    return '"' + text.replace('"', '""') + '"'


def label(tip, key=None):
    """AccessibleLabel til et ikon: tooltippet, og i et galleri raekkens
    noegle bagefter (key er et Power Fx-udtryk)."""
    return tip if key is None else f'{tip} & " - " & {key}'


def _count(n_expr, body):
    """body med _n = antallet, regnet een gang. Blank er 0."""
    return f"With({{ _n: Coalesce({n_expr}, 0) }}, {body})"


# ---------------------------------------------------------------------------
# Raekkens handlinger
# ---------------------------------------------------------------------------
EDIT_ROW = lit("Edit row")
VIEW_ROW = lit("View row")
COPY_ROW = lit("Copy row")
DELETE_ROW = lit("Delete row")


def edit_row(locked=None):
    """Edit-ikonet: "View row", naar raekken kun kan ses (locked er et
    Power Fx-udtryk), ellers "Edit row"."""
    return EDIT_ROW if locked is None else f"If({locked}, {VIEW_ROW}, {EDIT_ROW})"


def view_count(n_expr, one, many=None, empty="", empty_locked=None, locked=None):
    """ "View 3 documents". Ved 0: empty ("Add documents") - eller
    empty_locked ("No documents"), naar locked er sand."""
    none = lit(empty)
    if empty_locked is not None and locked is not None:
        none = f"If({locked}, {lit(empty_locked)}, {lit(empty)})"
    return _count(n_expr, f'If(_n = 0, {none}, "View " & {dt.plural("_n", one, many)})')


def documents(n_expr, locked=None):
    """Documents-ikonet: "View 3 documents" / "Add documents" (eller
    "No documents", naar raekken kun kan ses)."""
    return view_count(n_expr, "document", empty="Add documents",
                      empty_locked="No documents", locked=locked)


def attachments(n_expr):
    """Papirclipsen: "View 2 attachments" / "No attachments"."""
    return view_count(n_expr, "attachment", empty="No attachments")


def selected(n_expr, one, many=None):
    """ "No Functional Locations selected" / "1 Functional Location
    selected" / "3 Functional Locations selected" (issue #515)."""
    many = many or one + "s"
    return _count(n_expr, f'If(_n = 0, {lit("No " + many + " selected")}, '
                          f'{dt.plural("_n", one, many)} & " selected")')


def functional_locations(n_expr):
    return selected(n_expr, "Functional Location")


def filled(what, n_expr, locked=None):
    """En popup med felter (Manufacturer, Warranty, Class data):
    "Edit manufacturer - 2 fields filled" / "Add manufacturer". what er
    handlingens navn med lille forbogstav. Kan raekken kun ses: "View
    manufacturer - 2 fields filled" / "No manufacturer"."""
    verb = "Edit" if locked is None else f'If({locked}, "View", "Edit")'
    empty = lit("Add " + what)
    if locked is not None:
        empty = f'If({locked}, {lit("No " + what)}, {empty})'
    return _count(n_expr, f'If(_n = 0, {empty}, '
                          f'{verb} & " {what} - " & {dt.plural("_n", "field")} & " filled")')


# ---------------------------------------------------------------------------
# Ikoner uden data
# ---------------------------------------------------------------------------
VIEW_ACTIVITY = lit("View activity")
DELETE_REQUEST = lit("Delete request")
NEW_ISSUE = lit("Report a new issue")


def toggle(on, when_on, when_off):
    """En kontakt: tooltippet siger, hvad et klik GOER."""
    return f"If({on}, {lit(when_on)}, {lit(when_off)})"
