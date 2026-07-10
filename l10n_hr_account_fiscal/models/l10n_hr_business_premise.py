from odoo import fields, models, api, _
from ..fiscal import fiscal
from datetime import date
from .fiscal_wrapper import fisc_handler

DATE_FORMAT = '%d.%m.%Y'


def _fina_date_format(date: date):
    return date and date.strftime(DATE_FORMAT) or None


class L10nHrBusinessPremise(models.Model):
    _inherit = "l10n_hr.business.premise"

    l10n_hr_fiscal_log_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.log",
        inverse_name="business_premise_id",
        string="Fiscal message logs",
        help="Log of all messages sent and received for FINA",
        readonly=True,
    )
    regular_working_hours_ids = fields.One2many(
        comodel_name='l10n_hr.business.working.hours',
        inverse_name='business_premise_id',
        string='Regular Working Hours',
        domain=[('type', '=', 'regular')],
    )
    exception_working_hours_ids = fields.One2many(
        comodel_name='l10n_hr.business.working.hours',
        inverse_name='business_premise_id',
        string='Exception Working Hours',
        domain=[('type', '=', 'exception')],
    )
    regular_working_hours_valid_from = fields.Date('Regular Working Hours Valid From', required=True)
    regular_working_hours_valid_to = fields.Date('Regular Working Hours Valid To', required=True)
    regular_working_hours_note = fields.Text('Regular Working Hours Note', required=True)

    def _handle_fisc_response(self, response, msg_type):
        self.ensure_one()
        if msg_type == 'dohvatiRadnoVrijeme':
            pass
        if msg_type == 'obrisiRadnoVrijeme':
            # Remove working hours flagged to be removed
            self.regular_working_hours_ids.filtered('to_remove').unlink()
            self.exception_working_hours_ids.filtered('to_remove').unlink()

    def _prepare_remove_fiscal_working_hours(self, factory):
        regulars = self.regular_working_hours_ids.filtered('to_remove')
        exceptions = self.exception_working_hours_ids.filtered('to_remove')
        regulars_to_remove, exceptions_to_remove = [], []
        for distinct_valid_from in set(regulars.mapped('valid_from')):
            if distinct_valid_from:
                regulars_to_remove.append(dict(DatumOd=_fina_date_format(distinct_valid_from)))
        for distinct_valid_on in set(exceptions.mapped('valid_on')):
            if distinct_valid_on:
                exceptions_to_remove.append(dict(Datum=_fina_date_format(distinct_valid_on)))
        poslovni_prostor = factory.type_factory.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=self.l10n_hr_fiscal_code,
            BrisanjeRadnogVremena=factory.type_factory.RadnoVrijemeBrisanjeType(Redovno=regulars_to_remove,
                                                                                Iznimke=exceptions_to_remove)
        )
        return poslovni_prostor

    def _prepare_set_fiscal_working_hours(self, factory):
        grouped_regular_hours, grouped_exception_hours = [], []
        if self.regular_working_hours_ids:
            for valid_from, regulars in self.regular_working_hours_ids.grouped('valid_from').items():
                # Get distinct descriptions by records, ought to be unique
                desc = ', '.join(set(regulars.mapped(lambda r: r.description or '')))
                regular_hours = factory.type_factory.RedovnoType(
                    DatumOd=_fina_date_format(valid_from),
                    Napomena=desc or None,
                )
                for regular in regulars:
                    flavor = factory.type_factory.DvokratnoType if regular.split_shift else factory.type_factory.JednokratnoType
                    shift = flavor(
                        DanUTjednu=regular.dow,
                        RadnoVrijemeOd=regular.time_from,
                        RadnoVrijemeDo=regular.time_to,
                    )
                    if regular.split_shift:
                        regular_hours.Dvokratno.append(shift)
                    else:
                        regular_hours.Jednokratno.append(shift)
                grouped_regular_hours.append(regular_hours)
        if self.exception_working_hours_ids:
            for valid_on, exceptions in self.exception_working_hours_ids.grouped('valid_on').items():
                exception_hours = factory.type_factory.IznimkeType(
                    Datum=_fina_date_format(valid_on),
                )
                # Dunno why zeep Client types behave this inconsistent
                if exception_hours.Jednokratno is None:
                    exception_hours.Jednokratno = []
                for exception in exceptions:
                    flavor = factory.type_factory.DvokratnoType if exception.split_shift else factory.type_factory.JednokratnoType
                    shift = flavor(
                        DanUTjednu=exception.dow,
                        RadnoVrijemeOd=exception.time_from,
                        RadnoVrijemeDo=exception.time_to,
                    )
                    if exception.split_shift:
                        exception_hours.Dvokratno.append(shift)
                    else:
                        exception_hours.Jednokratno.append(shift)
                grouped_exception_hours.append(exception_hours)

        poslovni_prostor = factory.type_factory.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=self.l10n_hr_fiscal_code,
            RadnoVrijeme=factory.type_factory.RadnoVrijemeType(grouped_regular_hours + grouped_exception_hours)
        )
        return poslovni_prostor

    def button_l10n_hr_test_fiscal_echo(self):
        self.company_id.button_l10n_hr_test_fiscal_echo(self)

    @fisc_handler(msg_type='dohvatiRadnoVrijeme')
    def _get_working_hours(self):
        fiscal_data = self.company_id.get_fiscal_data()
        fisk = fiscal.Fiscalization(fiscal_data)
        zaglavlje = fisk.create_request_header()
        fisc_data = dict(Zaglavlje=zaglavlje, Oib=self.company_id.company_registry,
                         OznPosPr=self.l10n_hr_fiscal_code, OibOper=self.env.user.company_registry,
                         VrstaRadnogVremena='SVE')
        return fisc_data

    @fisc_handler(msg_type='prijaviRadnoVrijeme')
    def _register_working_hours(self):
        fiscal_data = self.company_id.get_fiscal_data()
        fisk = fiscal.Fiscalization(fiscal_data)
        zaglavlje = fisk.create_request_header()
        working_hours = self._prepare_set_fiscal_working_hours(fisk)
        fisc_data = dict(Zaglavlje=zaglavlje, PoslovniProstor=working_hours,
                         OibOper=self.env.user.company_registry)
        return fisc_data

    @fisc_handler(msg_type='obrisiRadnoVrijeme')
    def _remove_working_hours(self):
        fiscal_data = self.company_id.get_fiscal_data()
        fisk = fiscal.Fiscalization(fiscal_data)
        zaglavlje = fisk.create_request_header()
        working_hours_to_remove = self._prepare_remove_fiscal_working_hours(fisk)
        fisc_data = dict(Zaglavlje=zaglavlje, PoslovniProstor=working_hours_to_remove,
                         OibOper=self.env.user.company_registry,
                         )
        return fisc_data

    def button_get_working_hours(self):
        response = self._get_working_hours()
        return True

    def button_register_working_hours(self):
        response = self._register_working_hours()
        return True

    def button_remove_working_hours(self):
        response = self._remove_working_hours()
        if response and response.Greske:
            # Reset flag "to be removed"
            self.regular_working_hours_ids.write({'to_remove': False})
            self.exception_working_hours_ids.write({'to_remove': False})
