import functools
import logging
from dataclasses import dataclass

from zeep.exceptions import ValidationError as ZeepValidationError

from odoo.exceptions import UserError
from odoo.tools.translate import _

from ..fiscal import fiscal

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FiscalExchange:
    """An exchange outcome, independent of silent logging and local application."""

    status: str
    response: object = None
    log: object = None
    error: str = ''


def fisc_handler(msg_type, handle_response=True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                with self.env.cr.savepoint():
                    time_start = self.company_id.get_l10n_hr_time_formatted()
                    fiscal_data = self.company_id.get_fiscal_data()
                    fiscal_obj = fiscal.Fiscalization(data=fiscal_data)
                    try:
                        service_proxy = fiscal_obj.client.service[msg_type]
                    except Exception as error:
                        raise UserError(_("Service proxy %s not found", msg_type)) from error
                    req_kw = func(self, *args, **kwargs)
            except Exception as error:
                if handle_response:
                    raise
                _logger.exception('Fiscal request preparation failed for %s (id=%s)', self._name, self.id)
                return FiscalExchange('not_sent', error=str(error))

            response = None
            error_message = ''
            status = 'uncertain'
            try:
                response = fiscal_obj._call_service(service_proxy, req_kw)
            except ZeepValidationError as error:
                # Zeep validates the payload before dispatching it.
                status, error_message = 'not_sent', str(error)
            except Exception as error:
                # A timeout does not establish whether FINA accepted the request.
                error_message = str(error)
                _logger.exception('Fiscal exchange failed for %s (id=%s)', self._name, self.id)
            else:
                verified = getattr(getattr(fiscal_obj, 'fiscal_plugin', None), 'last_verification_ok', None)
                if response is None:
                    error_message = _('The tax authority returned no response.')
                elif verified is not True:
                    error_message = _('The FINA response signature could not be verified.')
                elif getattr(response, 'error_message', None):
                    status, error_message = 'rejected', str(response.error_message)
                elif getattr(response, 'Greske', None):
                    status = 'rejected'
                    error_message = '\n'.join(g.PorukaGreske for g in response.Greske.Greska)
                else:
                    status = 'success'

            log = None
            try:
                # A logging failure must not poison the cursor after an external call.
                with self.env.cr.savepoint():
                    log = self.company_id.create_fiscal_log(
                        msg_type, fiscal_obj,
                        response if response is not None else {'error_message': error_message},
                        time_start, self, outcome=status, error_message=error_message,
                    )
            except Exception as error:
                # Exit-time flushing can roll back a log whose create already returned.
                log = None
                _logger.exception('Could not record fiscal exchange for %s (id=%s)', self._name, self.id)
                error_message = '\n'.join(filter(None, [error_message, str(error)]))
                if status == 'success':
                    status = 'uncertain'

            if not handle_response:
                return FiscalExchange(status, response=response, log=log, error=error_message)

            if error_message and not self.company_id.l10n_hr_fiscal_silent_error_logging:
                raise UserError(_('Fiscalization Error:\n %s') % error_message)
            if status == 'success':
                self._handle_fisc_response(response, msg_type)
            # An untrusted/lost reply must not be mistaken for a confirmation by callers.
            return None if status in ('uncertain', 'not_sent') else response

        return wrapper

    return decorator
