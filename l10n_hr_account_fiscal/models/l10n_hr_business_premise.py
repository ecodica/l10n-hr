from odoo import fields, models, api, _
from ..fiscal import fiscal
from datetime import date, datetime
from ..helpers.fiscal_wrapper import fisc_handler
import logging

DATE_FORMAT = '%d.%m.%Y'
_logger = logging.getLogger(__name__)


def _fina_date_format(date: date):
    return date and date.strftime(DATE_FORMAT) or None


def _fina_date_parse(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except (ValueError, TypeError):
        return None


def _as_list(value):
    """Normalize a zeep response attribute to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
    regular_working_hours_valid_from = fields.Date('Regular Working Hours Valid From', required=False)
    regular_working_hours_valid_to = fields.Date('Regular Working Hours Valid To', required=False)
    regular_working_hours_note = fields.Text('Regular Working Hours Note', required=False)

    def _handle_fisc_response(self, response, msg_type):
        self.ensure_one()
        if msg_type == 'dohvatiRadnoVrijeme':
            self._import_fiscal_working_hours(response)
        if msg_type == 'prijaviRadnoVrijeme':
            # Uncheck, prevent double jeopardy
            (self.regular_working_hours_ids + self.exception_working_hours_ids). \
                filtered('to_register').to_register = False
        if msg_type == 'obrisiRadnoVrijeme':
            # Remove working hours flagged to be removed
            self.regular_working_hours_ids.filtered('to_remove').unlink()
            self.exception_working_hours_ids.filtered('to_remove').unlink()

    def _import_fiscal_working_hours(self, response):
        """Parse DohvatiRadnoVrijemeOdgovor and store working hours locally."""
        self.ensure_one()
        poslovni_prostor = getattr(response, 'PoslovniProstor', None)
        if not poslovni_prostor:
            return
        radno_vrijeme = getattr(poslovni_prostor, 'RadnoVrijeme', None)
        if not radno_vrijeme:
            return

        # Replace local working hours with data received from FINA
        self.regular_working_hours_ids.unlink()
        self.exception_working_hours_ids.unlink()

        vals_list = []
        for regular in _as_list(getattr(radno_vrijeme, 'Redovno', None)):
            vals_list.extend(self._parse_regular_working_hours(regular))
        for exception in _as_list(getattr(radno_vrijeme, 'Iznimke', None)):
            vals_list.extend(self._parse_exception_working_hours(exception))

        if vals_list:
            self.env['l10n_hr.business.working.hours'].create(vals_list)

    def _parse_regular_working_hours(self, regular):
        """Parse a RedovnoType object and return a list of create vals."""
        self.ensure_one()
        valid_from = _fina_date_parse(getattr(regular, 'DatumOd', None))
        description = getattr(regular, 'Napomena', None)
        base_vals = {
            'business_premise_id': self.id,
            'type': 'regular',
            'valid_from': valid_from,
            'description': description,
        }
        vals_list = []
        for shift in _as_list(getattr(regular, 'Jednokratno', None)):
            vals_list.append(dict(base_vals, **{
                'dow': getattr(shift, 'DanUTjednu', None),
                'time_from': getattr(shift, 'RadnoVrijemeOd', None),
                'time_to': getattr(shift, 'RadnoVrijemeDo', None),
                'split_shift': False,
            }))
        for shift in _as_list(getattr(regular, 'Dvokratno', None)):
            vals_list.append(dict(base_vals, **{
                'dow': getattr(shift, 'DanUTjednu', None),
                'time_from': getattr(shift, 'RadnoVrijemeOd', None),
                'time_to': getattr(shift, 'RadnoVrijemeDo', None),
                'split_shift': getattr(shift, 'DioDvokratnog', None),
            }))
        if getattr(regular, 'PoDogovoru', None):
            _logger.warning("Regular working hours 'PoDogovoru' received from FINA but not supported.")
        if getattr(regular, 'ParniNeparni', None):
            _logger.warning("Regular working hours 'ParniNeparni' received from FINA but not supported.")
        return vals_list

    def _parse_exception_working_hours(self, exception):
        """Parse an IznimkeType object and return a list of create vals."""
        self.ensure_one()
        valid_on = _fina_date_parse(getattr(exception, 'Datum', None))
        base_vals = {
            'business_premise_id': self.id,
            'type': 'exception',
            'valid_on': valid_on,
        }
        vals_list = []
        for shift in _as_list(getattr(exception, 'Jednokratno', None)):
            vals_list.append(dict(base_vals, **{
                'dow': valid_on and str(valid_on.isoweekday()) or None,
                'time_from': getattr(shift, 'RadnoVrijemeOd', None),
                'time_to': getattr(shift, 'RadnoVrijemeDo', None),
                'split_shift': False,
            }))
        for shift in _as_list(getattr(exception, 'Dvokratno', None)):
            vals_list.append(dict(base_vals, **{
                'dow': valid_on and str(valid_on.isoweekday()) or None,
                'time_from': getattr(shift, 'RadnoVrijemeOd', None),
                'time_to': getattr(shift, 'RadnoVrijemeDo', None),
                'split_shift': getattr(shift, 'DioDvokratnog', None),
            }))
        return vals_list

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
        regulars = self.regular_working_hours_ids.filtered('to_register')
        exceptions = self.exception_working_hours_ids.filtered('to_register')
        if regulars:
            for valid_from, regulars in regulars.grouped('valid_from').items():
                # Get distinct descriptions by records, ought to be unique
                desc = ', '.join(set(regulars.mapped(lambda r: r.description or '')))
                regular_hours = factory.type_factory.RedovnoType(
                    DatumOd=_fina_date_format(valid_from),
                    Napomena=desc or None,
                )
                # zeep does not always pre-initialize these lists
                if regular_hours.Jednokratno is None:
                    regular_hours.Jednokratno = []
                if regular_hours.Dvokratno is None:
                    regular_hours.Dvokratno = []
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
        if exceptions:
            for valid_on, exceptions in exceptions.grouped('valid_on').items():
                exception_hours = factory.type_factory.IznimkeType(
                    Datum=_fina_date_format(valid_on),
                )
                # zeep does not always pre-initialize these lists
                if exception_hours.Jednokratno is None:
                    exception_hours.Jednokratno = []
                if exception_hours.Dvokratno is None:
                    exception_hours.Dvokratno = []
                for exception in exceptions:
                    if exception.split_shift:
                        shift = factory.type_factory.DvokratnoIznimkeType(
                            DioDvokratnog=exception.split_shift,
                            RadnoVrijemeOd=exception.time_from,
                            RadnoVrijemeDo=exception.time_to,
                        )
                        exception_hours.Dvokratno.append(shift)
                    else:
                        shift = factory.type_factory.JednokratnoIznimkeType(
                            RadnoVrijemeOd=exception.time_from,
                            RadnoVrijemeDo=exception.time_to,
                        )
                        exception_hours.Jednokratno.append(shift)
                grouped_exception_hours.append(exception_hours)
        poslovni_prostor = factory.type_factory.PoslovniProstorType(
            Oib=self.company_id.company_registry,
            OznPosPr=self.l10n_hr_fiscal_code,
            RadnoVrijeme=factory.type_factory.RadnoVrijemeType(Redovno=grouped_regular_hours,
                                                               Iznimke=grouped_exception_hours)
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
        self.ensure_one()
        response = self._get_working_hours()
        return True

    def button_register_working_hours(self):
        self.ensure_one()
        response = self._register_working_hours()
        return True

    def button_remove_working_hours(self):
        self.ensure_one()
        response = self._remove_working_hours()
        if response and response.Greske:
            # Reset flag "to be removed"
            self.regular_working_hours_ids.write({'to_remove': False})
            self.exception_working_hours_ids.write({'to_remove': False})
