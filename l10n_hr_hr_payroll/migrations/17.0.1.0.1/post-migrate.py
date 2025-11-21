def migrate(cr, version):
    """ Change l10n_hr_payroll -Add new RADN rules to configurations """

    cr.execute("""
                INSERT INTO salary_rule_configuration_rel (payroll_config_id, salary_rule_id)
                SELECT c.res_id, r.res_id
                FROM ir_model_data AS c
                JOIN ir_model_data AS r
                ON r.module = 'l10n_hr_hr_payroll'
                AND r.name = 'hr_salary_rule_238'
                AND r.model = 'hr.salary.rule'
                WHERE c.module = 'l10n_hr_hr_payroll'
                AND c.model = 'hr.payroll.salary.rule.configuration'
                AND c.name IN (
                    'hr_payroll_configuration_umanjenje_osnovice_za_doprinose',
                    'hr_payroll_configuration_worked',
                    'hr_payroll_configuration_earnings'
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM salary_rule_configuration_rel AS rel
                    WHERE rel.payroll_config_id = c.res_id
                    AND rel.salary_rule_id = r.res_id
                );
                Update hr_salary_rule
                SET is_for_contributions_base_deduction = TRUE where code ='RNED';
    """)

    cr.commit()
