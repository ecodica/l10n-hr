-- remove fiskalization certificates
DELETE FROM l10n_hr_fiskal_certificate;

-- set automatic fiskalization to False on all Fiskal devices
UPDATE l10n_hr_fiscal_device SET enable_fiskalise_on_confirm = False;
