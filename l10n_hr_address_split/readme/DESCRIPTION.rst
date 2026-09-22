Replaces the ``res.partner`` street splitter shipped by
``base_address_extended`` with the improved implementation from Odoo 19,
which correctly extracts the house number from more address shapes
(leading house number, trailing whitespace, comma separators) than the
Odoo 17/18 regex does. A recovery step keeps non-numeric door designations
(e.g. "prizemlje", "potkrovlje") that the Odoo 19 regex would otherwise drop.
