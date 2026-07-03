from odoo import fields, models, api, _
from odoo.exceptions import UserError
from ..fiscal import fiscal
from datetime import date

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
    regular_working_hours_valid_from = fields.Date(string='Regular Working Hours Valid From')
    regular_working_hours_valid_to = fields.Date(string='Regular Working Hours Valid To')
    regular_working_hours_note = fields.Date(string='Regular Working Hours - Note')
    exception_working_hours_valid_from = fields.Text(string='Exception Working Hours Valid From')
    exception_working_hours_valid_to = fields.Date(string='Exception Working Hours Valid To')
    exception_working_hours_note = fields.Text(string='Exception Working Hours - Note')

    def _prepare_fiscal_working_hours(self, factory, fiscal_data, msg_type):
        grouped_regular_hours, grouped_exception_hours = [], []
        if self.regular_working_hours_ids:
            regular_hours = factory.type_factory.RedovnoType(
                DatumOd=_fina_date_format(self.regular_working_hours_valid_from),
                DatumDo=_fina_date_format(self.regular_working_hours_valid_to),
                Napomena=self.regular_working_hours_note or None,
            )
            for regular in self.regular_working_hours_ids:
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
            exception_hours = factory.type_factory.IznimkaType(
                DatumOd=_fina_date_format(self.exception_working_hours_valid_from),
                DatumDo=_fina_date_format(self.exception_working_hours_valid_to),
                Napomena=self.exception_working_hours_note or None
            )
            for exception in self.exception_working_hours_ids:
                flavor = factory.type_factory.DvokratnoType if exception.split_shift else factory.type_factory.JednokratnoType
                shift = flavor(
                    DanUTjednu=regular.dow,
                    RadnoVrijemeOd=regular.time_from,
                    RadnoVrijemeDo=regular.time_to,
                )
                if regular.split_shift:
                    exception_hours.Dvokratno.append(shift)
                else:
                    exception_hours.Jednokratno.append(shift)
            grouped_exception_hours.append(exception_hours)

        poslovni_prostor = factory.type_factory.PoslovniProstorType(
            Oib=fiscal_data['cert_vat'],
            OznPosPr=self.l10n_hr_fiscal_code,
            RadnoVrijeme=factory.type_factory.RadnoVrijemeType(grouped_regular_hours + grouped_exception_hours)
        )
        return poslovni_prostor

    def _handle_fisc_response(self, response, msg_type):
        return True

    def button_l10n_hr_test_fiscal_echo(self):
        self.company_id.button_l10n_hr_test_fiscal_echo(self)

    def button_l10n_hr_register_working_hours(self):
        msg_type = 'prijaviRadnoVrijeme'
        time_start = self.company_id.get_l10n_hr_time_formatted()
        fiscal_data = self.company_id.get_fiscal_data()
        fisk = fiscal.Fiscalization(data=fiscal_data)
        try:
            service_proxy = fisk.client.service[msg_type]
        except:
            raise UserError(_("Service proxy %s not found", msg_type))

        zaglavlje = fisk.create_request_header()
        working_hours = self._prepare_fiscal_working_hours(fisk, fiscal_data, msg_type)
        req_kw = dict(Zaglavlje=zaglavlje, PoslovniProstor=working_hours,
                      OibOper=self.env.user.company_registry)
        response = None
        odoo_error = {}
        try:
            response = fisk._call_service(service_proxy, req_kw)
            self.company_id.create_fiscal_log(msg_type, fisk, response, time_start, self)
            self._handle_fisc_response(response, msg_type)
        except AttributeError as e:
            odoo_error = {'error_message': str(e) + '\n' + str(e.obj)}
        except Exception as e:
            # NOTE: handle cases when response is not received from FINA
            odoo_error = {'error_message': e.args[0]}
        # log odoo error
        if odoo_error.get('error_message'):
            self.company_id.create_fiscal_log(msg_type, fisk, odoo_error, time_start, self)
        # raise error
        error_message = response and hasattr(response, 'error_message') and response['error_message'] or odoo_error.get(
            'error_message')
        if error_message and not self.company_id.l10n_hr_fiscal_silent_error_logging:
            raise UserError(_("Fiscalization Error:\n %s") % error_message)
