-- remove fiscalization certificates
DELETE FROM l10n_hr_fiscal_certificate;

-- set automatic fiscalization to False
UPDATE res_company SET l10n_hr_fiscal_on_confirm = False;
