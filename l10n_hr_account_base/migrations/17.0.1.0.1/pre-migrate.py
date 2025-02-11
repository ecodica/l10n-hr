def migrate(cr, version):
    """ Change l10n_hr_vrijeme_izdavanja from char to a Datetime field and convert the value to UTC timezone. """

    cr.execute("""
        ALTER TABLE account_move
        ALTER COLUMN l10n_hr_vrijeme_izdavanja
        TYPE TIMESTAMP WITHOUT TIME ZONE
        USING TO_TIMESTAMP(l10n_hr_vrijeme_izdavanja, 'DD.MM.YYYY HH24:MI')
        AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Zagreb';
    """)

    cr.commit()
