import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill Racun/DatVrijeme for invoices fiscalized before it was stored.

    The datetime sent to FINA used to be re-rendered on every read, from the
    naive-UTC ``l10n_hr_vrijeme_izdavanja`` and the timezone of whoever happened
    to be reading. That is why the QR code printed on a fiscalized invoice was
    1-2 hours off the record registered with FINA. It is now frozen on the move
    at fiscalisation time, and this fills it in for everything already issued.

    The value is reconstructed as Croatian local time, deliberately *not* read
    back out of ``l10n_hr_fiskal_log``. An invoice can have several request
    envelopes - retries and business rejections both leave one behind - and
    nothing in the log identifies which attempt FINA actually accepted, because
    the response envelopes were never stored. A log-derived value can therefore
    silently come from a message that was rejected. Recomputing from the
    timestamp column is deterministic and matches what was sent, to the minute
    that the QR code and the ZKI both truncate to.

    Limitation: this assumes the fiscal message was built in Europe/Zagreb, which
    holds for any user with a Croatian timezone. An invoice fiscalized by a
    user with no timezone set went out in UTC and will be reconstructed 1-2 hours
    off - that invoice's QR code was equally wrong before this migration, so
    nothing regresses, but nothing is repaired either. Compare
    ``l10n_hr_fiskal_dat_vrijeme`` against the ``DatVrijeme`` in the invoice's
    fiscal log if you need to audit a specific document.

    to_char() here must produce byte-identical output to FISKAL_DATETIME_FORMAT
    ('%d.%m.%YT%H:%M:%S'), because that is what the QR code is built from.
    """
    _logger.info(
        "--- MIGRATION SCRIPT STARTED: l10n_hr_account_fiskal 17.0.1.1.2 "
        "backfilling l10n_hr_fiskal_dat_vrijeme ---"
    )

    cr.execute(
        """
        WITH updated AS (
            UPDATE account_move
               SET l10n_hr_fiskal_dat_vrijeme = to_char(
                       l10n_hr_vrijeme_izdavanja AT TIME ZONE 'UTC'
                                                 AT TIME ZONE 'Europe/Zagreb',
                       'DD.MM.YYYY"T"HH24:MI:SS')
             WHERE l10n_hr_zki IS NOT NULL
               AND l10n_hr_vrijeme_izdavanja IS NOT NULL
               AND l10n_hr_fiskal_dat_vrijeme IS NULL
            RETURNING id
        )
        SELECT count(*) FROM updated;
        """
    )
    updated_count = cr.fetchone()[0]

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
        "--- MIGRATION SCRIPT COMPLETED: %s account.move records updated field "
        "l10n_hr_fiskal_dat_vrijeme, %s fiscalized invoices left without a value "
        "(no time of invoicing - these print no QR code) ---",
        updated_count,
        left_null,
    )
