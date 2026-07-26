import functools
from odoo.exceptions import UserError
from odoo.tools.translate import _
from ..fiscal import fiscal


def fisc_handler(msg_type):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Header
            time_start = self.company_id.get_l10n_hr_time_formatted()
            fiscal_data = self.company_id.get_fiscal_data()
            fiscal_obj = fiscal.Fiscalization(data=fiscal_data)

            # Check Msg type handler
            try:
                service_proxy = fiscal_obj.client.service[msg_type]
            except Exception:
                raise UserError(_("Service proxy %s not found", msg_type))

            try:
                req_kw = func(self, *args, **kwargs)
            except Exception as e:
                # Handle standard Odoo errors
                raise e

            response = None
            odoo_error = {}

            # Send request and process response
            try:
                response = fiscal_obj._call_service(service_proxy, req_kw)
                # Create log in fiscal logs
                self.company_id.create_fiscal_log(msg_type, fiscal_obj, response, time_start, self)

            except AttributeError as e:
                error_obj = getattr(e, 'obj', '')
                odoo_error = {'error_message': f"{str(e)}\n{str(error_obj)}"}

            except Exception as e:
                error_msg = e.args[0] if e.args else str(e)
                odoo_error = {'error_message': error_msg}

            if odoo_error.get('error_message'):
                self.company_id.create_fiscal_log(msg_type, fiscal_obj, odoo_error, time_start, self)

            error_message = odoo_error.get('error_message')

            if response and not error_message:
                if hasattr(response, 'error_message') and response['error_message']:
                    error_message = response['error_message']

                elif hasattr(response, 'Greske') and response.Greske:
                    error_messages = [g.PorukaGreske for g in response.Greske.Greska]
                    error_message = "\n".join(error_messages)

            # Raise if not silent logging
            if error_message and not self.company_id.l10n_hr_fiscal_silent_error_logging:
                raise UserError(_("Fiscalization Error:\n %s") % error_message)

            # Handle only success response
            if not error_message:
                self._handle_fisc_response(response, msg_type)
            return response

        return wrapper

    return decorator
