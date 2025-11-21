# -*- coding: utf-8 -*-

from stdnum.hr import oib

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    city = fields.Char(string="City name")
    city_id = fields.Many2one(comodel_name="res.city", string="City")  # we ignore field city on res_partner
    zip = fields.Char()
    oib = fields.Char(string="OIB")
    oib_extension = fields.Char(size=3, string="OIB extension")
    vat_country_id = fields.Many2one(comodel_name="res.country", string="Country VAT ID")
    internal = fields.Boolean(string="Internal", help="If partner is internal OIB does not need to be supplied", default=lambda self: not self.env.user.has_group('hr_base.group_create_and_validate_customer'))
    not_validated = fields.Boolean(string="Not Validated", default=lambda self: not self.env.user.has_group('hr_base.group_create_and_validate_customer'))
    vat_form = fields.Boolean(string="VAT Form", default=True)
    company_type = fields.Selection(selection_add=[('gov_entity', 'Government Entity')],
        compute='_compute_company_type', inverse='_write_company_type')  # add Government Body to selection
    is_gov_entity = fields.Boolean(string="Is a Government Entity", default=False)
    county_id = fields.Many2one('res.country.state', 'County')
    customer = fields.Boolean(string='Is a Customer', default=False, help="Check this box if this contact is a customer. It can be selected in sales orders.")
    parent_type = fields.Selection(string="Parent Company Type", related='parent_id.company_type')


    @api.onchange('parent_id')
    def onchange_parent_id(self):
        """Add city_id from parent company.
        Reason: using city_id instead of city
        """
        result = super().onchange_parent_id()
        if result is not None and 'value' in result:
            result['value']['city_id'] = self.parent_id.city_id.id
        return result

    @api.model
    def _commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
         # extend to add pdv_id to newly created addresses etc.
        return super(ResPartnerInherit, self)._commercial_fields() + ['vat']


    @api.depends('is_company')
    def _compute_company_type(self):
        """Ading Government body to 'company_type' selection requires additional checks"""
        for partner in self:
            if partner.is_company and partner.is_gov_entity:
                partner.company_type = 'gov_entity'
            elif partner.is_company:
                partner.company_type = 'company'
            else:
                partner.company_type = 'person'

    def _write_company_type(self):
        """Ading Government body to 'company_type' selection requires additional checks"""
        for partner in self:
            if partner.company_type == 'gov_entity':
                partner.is_company = True
                partner.is_gov_entity = True
            elif partner.company_type == 'company':
                partner.is_company = True
                partner.is_gov_entity = False
            else:
                partner.is_company = False
                partner.is_gov_entity = False

    @api.onchange('company_type')
    def onchange_company_type(self):
        """Ading Government body to 'company_type' selection requires additional check"""
        if self.company_type == 'gov_entity':
            self.is_company = True
            self.is_gov_entity = True
        elif self.company_type == 'company':
            self.is_company = True
            self.is_gov_entity = False
        else:
            self.is_company = False
            self.is_gov_entity = False

    def _get_name(self):
        """ Utility method to allow name_get to be overriden without re-browsing the partner
        -- method is modified to display invoice, delivery and other adresses next to company name """
        partner = self
        name = partner.name or ''

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                # modified behaviour
                name = self._display_address(without_company=True, force_inline=True)
            if not partner.is_company:
                address = str(partner.street if partner.street else '') \
                + str(', ' + partner.street2 if partner.street2 else '') \
                + str(', ' + partner.zip if partner.zip else '') \
                + str(', ' + partner.city_id.name if partner.city_id.name else '')
                name = "%s, %s" % (partner.name, address)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('address_inline'):
            name = name.replace('\n', ', ')
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        return name

    def _display_address_depends(self):
        # field dependencies of method _display_address()
        # added city.name => city is Many2one field
        return self._address_fields() + [
            'country_id.address_format', 'country_id.code', 'country_id.name',
            'company_name', 'state_id.code', 'state_id.name', 'city_id.name',
        ]

    def _display_address(self, without_company=False, force_inline=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.
        -- modified to accept city name as one of the arguments
        :param address: browse record of the res.partner to format
        :param force_inline: strip newline characters before any processing
            -- used for inline addresses in display_name field
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'city': self.city_id.name or '',       # set city name
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            if field == 'city':
                # city is Many2one, fetching city would return a recordset(len == 1)
                continue
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format

        if force_inline:
            address = address_format % args
            return address.replace("\n", ", ")
        return address_format % args

    @api.onchange("city_id")
    def change_city_zip(self):
        """Auto-fill zip code in forms on city field onchange
        Field "city_id" is used instead of default Odoo12 field "city".
        Copying city_id.name just to be safe that any parts that depend
        on "city" and not "city_id" have the proper city name
        """
        for record in self:
            record.zip = record.city_id.zipcode
            record.city = record.city_id.name
            record.country_id = record.city_id.country_id

    @api.onchange('vat_country_id')
    def onchange_vat_country_id(self):
        if 'default_oib' not in self._context.keys():
            self.oib = False
            self.vat = False

    @api.onchange('oib')
    def onchange_oib(self):
        if self.oib:
            if not self.vat_country_id:
                raise ValidationError(_("You must first enter Country VAT ID."))
            if self.vat_country_id.code == 'HR':
                if len(self.oib) != 11:
                    raise ValidationError(_("OIB field must be exactly 11 characters long"))
                if not self.oib.isnumeric():
                    raise ValidationError(_("OIB field must be a number"))
                if not oib.is_valid(self.oib):
                    raise ValidationError(_("Partner OIB is not valid"))

                self.vat = 'HR' + self.oib
                self.not_validated = False
            else:
                self.vat = self.oib
                self.not_validated = False
        else:
            self.vat = False
            self.not_validated = True

    @api.constrains("oib")
    def check_oib_unique(self):
        """Check for OIB uniqueness
        - OIBs of records that are children of a distinct parent
            can share the same oib as their parent
        - delivery/invoice address oib not checked -- delivery/invoice addresses
            can share oib with base partner(contact)
        """
        for record in self:
            if record.oib and record.active and record.type not in ['invoice', 'delivery', 'other', 'private']:
                # invoice, delivery, other and private addr not checked
                rec_exist = self.env["res.partner"].search([('id','!=', record.id),('active','=', True),('oib','=', record.oib)])
                if rec_exist:
                    raise ValidationError(_("Partner OIB must be unique"))


    @api.onchange('child_ids')
    def onchange_child_ids(self):
        if self.parent_id:
            raise ValidationError(_("You cannot add address to adress that is already subaddress."))
