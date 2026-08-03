import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill Racun/DatVrijeme and Racun/IznosUkupno from the sent envelopes.

    Both values used to be recomputed on every read, which is why the QR code
    printed on an already fiscalised invoice did not match the record registered
    with CIS: ``datv`` was rendered from the naive-UTC ``l10n_hr_vrijeme_izdavanja``
    instead of the local time the message carried, and ``izn`` came from the
    unsigned invoice-currency ``amount_total`` instead of the signed
    company-currency ``IznosUkupno``.

    They are now frozen on the move. For invoices fiscalised before this version
    the only authoritative record of what CIS actually received is the request
    envelope kept in ``l10n_hr_fiskal_log.sadrzaj``, so read it back from there.

    Everything runs inside the database on purpose: the log table holds hundreds
    of MB of SOAP envelopes and must not be pulled through Python. The local name
    ``DatVrijeme`` cannot collide with the header's ``DatumVrijeme`` because the
    character preceding ">" differs, and the namespace prefix is ignored.

    Whatever no log can account for is reconstructed in Europe/Zagreb - the only
    timezone this module ever built a fiscal message in - so that the columns are
    never NULL on a fiscalized move and no reader has to guess. Those rows are
    counted separately and reported below so they can be spot-checked.
    """
    _logger.info("--- MIGRATION SCRIPT STARTED: l10n_hr_account_fiskal 17.0.1.1.2 "
                 "backfilling l10n_hr_fiskal_dat_vrijeme / l10n_hr_fiskal_iznos_ukupno ---")

    cr.execute(
        """
        WITH src AS (
            SELECT DISTINCT ON (l.invoice_id)
                   l.invoice_id,
                   btrim(substring(l.sadrzaj from 'DatVrijeme>([^<]+)<')) AS dat_vrijeme,
                   btrim(substring(l.sadrzaj from 'IznosUkupno>([^<]+)<')) AS iznos_ukupno
              FROM l10n_hr_fiskal_log l
              JOIN account_move m ON m.id = l.invoice_id
             WHERE l.sadrzaj IS NOT NULL
               AND l.type IN ('racuni', 'rac_pon')
               AND m.l10n_hr_zki IS NOT NULL
               AND m.l10n_hr_fiskal_dat_vrijeme IS NULL
             ORDER BY l.invoice_id,
                      -- the message that was accepted describes what CIS stored
                      CASE WHEN l.greska = 'OK' THEN 0 ELSE 1 END,
                      l.id
        ),
        updated AS (
            UPDATE account_move m
               SET l10n_hr_fiskal_dat_vrijeme = src.dat_vrijeme,
                   l10n_hr_fiskal_iznos_ukupno = src.iznos_ukupno
              FROM src
             WHERE m.id = src.invoice_id
               AND src.iznos_ukupno IS NOT NULL
               AND length(src.dat_vrijeme) = 19  -- dd.mm.yyyyThh:mm:ss
            RETURNING m.id
        )
        SELECT count(*) FROM updated;
        """
    )
    updated_count = cr.fetchone()[0]

    # No log to read the values back from: reconstruct them. to_char() here must
    # produce byte-identical output to FISKAL_DATETIME_FORMAT and
    # fiskal.format_decimal(), because that is what the QR code is built from.
    cr.execute(
        """
        WITH updated AS (
            UPDATE account_move
               SET l10n_hr_fiskal_dat_vrijeme = to_char(
                       l10n_hr_vrijeme_izdavanja AT TIME ZONE 'UTC'
                                                 AT TIME ZONE 'Europe/Zagreb',
                       'DD.MM.YYYY"T"HH24:MI:SS'),
                   l10n_hr_fiskal_iznos_ukupno = to_char(
                       amount_total_signed, 'FM9999999999990.00')
             WHERE l10n_hr_zki IS NOT NULL
               AND l10n_hr_vrijeme_izdavanja IS NOT NULL
               AND l10n_hr_fiskal_dat_vrijeme IS NULL
            RETURNING id
        )
        SELECT count(*) FROM updated;
        """
    )
    reconstructed_count = cr.fetchone()[0]

    cr.execute(
        """
        SELECT count(*)
          FROM account_move
         WHERE l10n_hr_zki IS NOT NULL
           AND l10n_hr_fiskal_dat_vrijeme IS NULL
        """
    )
    left_null = cr.fetchone()[0]

    _logger.info(
        "--- MIGRATION SCRIPT COMPLETED: %s account.move records updated fields "
        "l10n_hr_fiskal_dat_vrijeme / l10n_hr_fiskal_iznos_ukupno from their fiscal "
        "log, %s reconstructed in Europe/Zagreb for lack of a log envelope, %s left "
        "without a value (no time of invoicing - these print no QR code) ---",
        updated_count,
        reconstructed_count,
        left_null,
    )
