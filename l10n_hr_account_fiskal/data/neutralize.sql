-- remove fiskalization certificates
DELETE FROM l10n_hr_fiskal_certificate;

-- set automatic fiskalization to False
UPDATE res_company SET l10n_hr_fiskal_on_confirm = False;
