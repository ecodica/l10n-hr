# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Improved street splitter backported from Odoo 19.

Odoo 17 and 18 ship a single-regex ``odoo.tools.street_split`` that fails to
extract a house number from several common address shapes (leading house
number, trailing whitespace, comma separators).  Odoo 19 replaced it with a
two-regex implementation; the regexes below are that implementation, ported
verbatim from ``odoo/tools/misc.py`` in 19.0.

An empty ``street_number`` means no ``<BldgNb>`` in a pain.001.001.09 payment
file, which the HR bank XSD requires for a structured ``<PstlAdr>``.
"""

import re

# Ported verbatim from odoo/tools/misc.py (Odoo 19.0), including comments.
ADDRESS_REGEXES = [
    # Same as regex bellow, but match if the building number is at the start of the string
    re.compile(r'''^
        (?P<building_number>[0-9][a-zA-Z0-9/-]*)[,\s]+
        (?P<street>.*?)
        # We want to capture the door number after the last comma of the string, as we could
        # have commas in the street name
        (?:\s*[-,/]\s*(?P<door_number>(?=.*\d)(?:(?!\s*,\s*|\s+-\s+).)+))?
    $''', flags=re.DOTALL | re.VERBOSE),
    # Match addresses where building number is between street name and door number
    re.compile(r'''^
        # Non greedy match on street name, so it will stops as soon as it faces a digit
        (?P<street>.*?)\s*
        # We will use this comma for a condition later
        (?P<comma>,)?\s*
        # Match the building number, it must starts with a digit, and it stops when facing
        # a blank space, a comma or end of string
        (?P<building_number>[0-9][a-zA-Z0-9/-]*)?
        # If we didn't capture a comma in the comma group, we do a positive lookahead to check
        # if we have a door number after
        (?(comma)|(?=\s+[,-/]|\s*$))
        # Door number group has to starts with '-', ',' or '/'
        (?:\s*[-,/]\s*(?P<door_number>(?=.*\d)(?:(?!\s*,\s*|\s+-\s+).)+))?
    ''', flags=re.DOTALL | re.VERBOSE),
]

# Legacy Odoo 17 door separator, used to recover door designations that the
# Odoo 19 regexes reject (see hr_street_split).
LEGACY_DOOR_REGEX = re.compile(r'^(.*?)\s+-\s+(.+)$', flags=re.DOTALL)


def _street_split_v19(street):
    """Split ``street`` using the Odoo 19 regexes.

    :param str street: raw street value, may be empty or False.
    :return: dict with street_name, street_number and street_number2 keys.
    """
    for regex in ADDRESS_REGEXES:
        match = regex.match(street or '')
        results = match.groupdict() if match else {}
        if results:
            return {
                'street_name': (results.get('street') or '').strip(),
                'street_number': (results.get('building_number') or '').strip(),
                'street_number2': (results.get('door_number') or '').strip(),
            }

    return {
        'street_name': '',
        'street_number': '',
        'street_number2': '',
    }


def hr_street_split(street):
    """Split ``street`` into name, house number and door number.

    Applies the Odoo 19 splitter, then recovers non-numeric door designations
    that it would discard.  Upstream requires the door group to contain a digit
    (``(?=.*\\d)``), so Croatian designations such as "prizemlje", "potkrovlje"
    or a bare letter are dropped where Odoo 17 kept them.  Falling back to the
    legacy " - " split prevents an existing street_number2 from being erased
    when the fields are recomputed.

    :param str street: raw street value, may be empty or False.
    :return: dict with street_name, street_number and street_number2 keys.
    """
    result = _street_split_v19(street)
    if not result['street_number2'] and street and ' - ' in street:
        match = LEGACY_DOOR_REGEX.match(street)
        if match:
            head = _street_split_v19(match.group(1))
            if head['street_name'] or head['street_number']:
                result = dict(head, street_number2=match.group(2).strip())
    return result
