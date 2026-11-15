def migrate(cr, version):
    # VAT on payment moved here from l10n_hr_tax_returns / l10n_hr_tax_forms,
    # where it was set by hand; the tax model is now its only source, so a
    # company that had the flag becomes R2 before the column is resynced.
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'res_company' AND column_name = 'l10n_hr_pdv_po_naplati'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        UPDATE res_company
           SET l10n_hr_tax_model = 'r2'
         WHERE l10n_hr_pdv_po_naplati
           AND l10n_hr_tax_model = 'r1'
    """)
    cr.execute("""
        UPDATE res_company
           SET l10n_hr_pdv_po_naplati = (l10n_hr_tax_model = 'r2')
    """)
