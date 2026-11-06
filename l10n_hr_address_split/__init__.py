from . import models
from . import tools


def post_init_hook(env):
    """Force a recompute of the split street fields with the new splitter.

    Odoo does not recompute a stored field merely because its compute method
    was overridden, so every partner with a street needs to be marked dirty
    once on install.
    """
    partners = env['res.partner'].search([('street', '!=', False)])
    for field_name in ('street_name', 'street_number', 'street_number2'):
        env.add_to_compute(partners._fields[field_name], partners)
    partners.flush_recordset()
