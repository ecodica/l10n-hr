-- Function: oe_rep_aged_partner_balance(date,int)

-- DROP FUNCTION oe_opz_stat(date, bigint);

/* DEBUG
select *
from oe_opz_stat(
        _date_to   := '2016-12-31'
        ,_opz_id   := 38998192
)

*/
CREATE OR REPLACE FUNCTION oe_opz_stat(IN _date_to date, IN _opz_id bigint, IN _company_id bigint) RETURNS varchar AS
$BODY$
BEGIN

WITH inv_data AS (
    WITH r_line AS (
        SELECT apr.credit_move_id, apr.debit_move_id
               ,COALESCE(apr.amount, 0.0) AS closing_amount
               ,COALESCE(apr.debit_amount_currency, 0.0) AS closing_debit_amount_currency
               ,COALESCE(apr.credit_amount_currency, 0.0) AS closing_credit_amount_currency
            FROM account_partial_reconcile apr
            WHERE 1 = 1
            AND apr.max_date <= _date_to
    )
    ,ml_debit_closed AS (
        SELECT rl.credit_move_id AS move_line_id
            ,SUM(rl.closing_amount) AS closed_amount
            ,SUM(rl.closing_credit_amount_currency) AS closed_amount_currency
            FROM r_line rl
        GROUP BY move_line_id
    )
    ,ml_credit_closed AS (
        SELECT rl.debit_move_id AS move_line_id
            ,SUM(rl.closing_amount) AS closed_amount
            ,SUM(rl.closing_debit_amount_currency) AS closed_amount_currency
            FROM r_line rl
        GROUP BY move_line_id
    )
    ,ml_closed AS (
        SELECT * FROM ml_credit_closed
        UNION
        SELECT * FROM ml_debit_closed
    )
    ,open_move_line AS (
        -- DOMESTIC
        SELECT aml.partner_id
            ,COALESCE(am.invoice_date, aml.date) AS date_invoice
            ,COALESCE(aml.date_maturity, am.invoice_date_due) AS date_due
            ,am."id" AS invoice_id
            ,COALESCE(am.l10n_hr_fiskalni_broj, aml.name, 'NO-REFERENCE') AS invoice_number
            ,aml.currency_id
            ,COALESCE(am.amount_untaxed, 0.0) AS invoice_amount
            ,COALESCE(am.amount_tax, 0.0) AS invoice_amount_tax
            ,COALESCE(am.amount_total, 0.0) AS invoice_amount_total
            ,am.state AS move_state
            ,COALESCE( NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit) AS amount_currency
            ,CASE WHEN (aml.debit + aml.credit) != 0.0
                  THEN COALESCE(ABS(NULLIF(aml.amount_currency, 0.0)), ABS(aml.debit + aml.credit)) / ABS(aml.debit + aml.credit)
                  ELSE 1.0
              END AS currency_rate
            ,CASE WHEN (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) > 0.00
                  THEN (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) - COALESCE(mc.closed_amount, 0.0)
                  ELSE (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) + COALESCE(mc.closed_amount, 0.0)
              END as open_amount
             ,(CASE WHEN COALESCE(mc.closed_amount, 0.0) > 0.0 THEN mc.closed_amount ELSE 0.0 END) AS closed_amount
        FROM account_move_line aml
        JOIN account_move am ON (aml.move_id = am.id)
        JOIN res_company rc ON (aml.company_id = rc.id)
        JOIN account_account aa ON (aml.account_id = aa.id)
        LEFT JOIN ml_closed mc ON (mc.move_line_id = aml.id)
        WHERE 1 = 1
        AND aa.account_type in ('asset_receivable')
        AND am.state = 'posted'
        AND aml.company_id = _company_id
        AND aml.currency_id = aml.company_currency_id
        AND COALESCE(aa.exclude_from_opz_stat, FALSE) = FALSE
        AND COALESCE(aml.date_maturity, am.invoice_date_due) <= _date_to  --+ INTERVAL '1 month'
        UNION
        -- FOREIGN
        SELECT aml.partner_id
            ,COALESCE(am.invoice_date, aml.date) AS date_invoice
            ,COALESCE(aml.date_maturity, am.invoice_date_due) AS date_due
            ,am."id" AS invoice_id
            ,COALESCE(am.l10n_hr_fiskalni_broj, aml.name, 'NO-REFERENCE') AS invoice_number
            ,aml.currency_id
            ,COALESCE(am.amount_untaxed, 0.0) AS invoice_amount
            ,COALESCE(am.amount_tax, 0.0) AS invoice_amount_tax
            ,COALESCE(am.amount_total, 0.0) AS invoice_amount_total
            ,am.state AS move_state
            ,COALESCE( NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit) AS amount_currency
            ,CASE WHEN (aml.debit + aml.credit) != 0.0
                  THEN COALESCE(ABS(NULLIF(aml.amount_currency, 0.0)), ABS(aml.debit + aml.credit)) / ABS(aml.debit + aml.credit)
                  ELSE 1.0
              END AS currency_rate
            ,CASE WHEN (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) > 0.00
                  THEN (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) - COALESCE(mc.closed_amount_currency, 0.0)
                  ELSE (COALESCE(NULLIF(aml.amount_currency, 0.0), aml.debit - aml.credit)) + COALESCE(mc.closed_amount_currency, 0.0)
              END as open_amount
             ,(CASE WHEN COALESCE(mc.closed_amount_currency, 0.0) > 0.0 THEN mc.closed_amount_currency ELSE 0.0 END) AS closed_amount
        FROM account_move_line aml
        JOIN account_move am ON (aml.move_id = am.id)
        JOIN res_company rc ON (aml.company_id = rc.id)
        JOIN account_account aa ON (aml.account_id = aa.id)
        LEFT JOIN ml_closed mc ON (mc.move_line_id = aml.id)
        WHERE 1 = 1
        AND aa.account_type in ('asset_receivable')
        AND am.state = 'posted'
        AND aml.company_id = _company_id
        AND aml.currency_id != aml.company_currency_id
        AND COALESCE(aa.exclude_from_opz_stat, FALSE) = FALSE
        AND COALESCE(aml.date_maturity, am.invoice_date_due) <= _date_to  --+ INTERVAL '1 month'
    )
    SELECT oml.partner_id
        ,par.name AS partner_name
        ,COALESCE((CASE WHEN par.vat LIKE 'HR%'
                        THEN SUBSTRING(par.vat, 3)
                   ELSE par.vat
                   END), '-') AS partner_vat_number
        ,par.opz_stat_vat_id AS partner_vat_type
        ,(CASE WHEN oml.date_invoice > oml.date_due THEN oml.date_due ELSE oml.date_invoice END ) AS date_invoice
        ,oml.date_due
        ,oml.invoice_id
        ,oml.invoice_number
        ,oml.currency_id
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.amount_currency / oml.currency_rate
            ELSE oml.amount_currency
        END::numeric), 2) AS lcy_aml_amount
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.invoice_amount / oml.currency_rate
            ELSE oml.invoice_amount
         END::numeric), 2) AS lcy_invoice_amount
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.invoice_amount_tax / oml.currency_rate
            ELSE oml.invoice_amount_tax
        END::numeric),2) AS lcy_invoice_amount_tax
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.invoice_amount_total / oml.currency_rate
            ELSE oml.invoice_amount_total
        END::numeric),2) AS lcy_invoice_amount_total
        ,(_date_to - oml.date_due) AS overdue_days
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.closed_amount / oml.currency_rate
            ELSE oml.closed_amount
        END::numeric), 2) AS closed_amount  -- lcy_closed_amount
        --,oml.date_maturity::date
        --,oml.posting_date::date
        ,ROUND((CASE WHEN oml.currency_rate != 0.0
            THEN oml.open_amount / oml.currency_rate
            ELSE oml.open_amount
        END::numeric), 2) AS open_amount_lcy
        FROM open_move_line as oml
        JOIN res_partner par ON par.id = oml.partner_id
        WHERE 1 = 1
        AND COALESCE(oml.open_amount, oml.invoice_amount_total) != 0.0
)
INSERT INTO opz_stat_line(
        create_uid, create_date, write_date, write_uid, opz_id
        ,partner_id, partner_name, partner_vat_number, partner_vat_type
        ,invoice_id, invoice_number, invoice_date, due_date, overdue_days
        ,amount, amount_tax, amount_total, currency_id
        ,paid, unpaid
        )
SELECT
        1, timezone('UTC', now()), timezone('UTC', now()), 1, _opz_id
        ,d.partner_id, d.partner_name, d.partner_vat_number, d.partner_vat_type
        ,d.invoice_id, d.invoice_number, d.date_invoice, d.date_due, d.overdue_days
        ,COALESCE(NULLIF(d.lcy_invoice_amount, 0.0), d.lcy_aml_amount, 0.0), COALESCE(d.lcy_invoice_amount_tax, 0.0)
        ,COALESCE(NULLIF(d.lcy_invoice_amount_total, 0.0), d.lcy_aml_amount, 0.0), d.currency_id
        ,d.closed_amount, d.open_amount_lcy
 FROM inv_data d
WHERE 1 = 1
AND d.open_amount_lcy != 0.0
AND d.invoice_number IS NOT NULL -- can happen, garbage in data
AND CASE
        WHEN EXISTS (SELECT 1 FROM opz_stat_res_partner_rel WHERE opz_stat_id = _opz_id) THEN
        CASE
            WHEN d.partner_id IN (SELECT partner_id FROM opz_stat_res_partner_rel WHERE opz_stat_id = _opz_id) THEN 1
            ELSE 0
        END
        ELSE 1
    END = 1

;
RETURN '';
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
