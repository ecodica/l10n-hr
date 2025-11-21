# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from operator import itemgetter
from . import hr_hr_payroll_reports_common as reports_common


class IpFormReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_ip_form'
    _description = 'IP form report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        reports_common_obj = self.env['hr.hr.payroll.reports.common']
        company = self.env.user.company_id
        year = data['year']
        date = data['date']
        doc_ids = data['employee_ids']
        doc_model = 'hr.employee'
        docs = self.env[doc_model].browse(doc_ids)
        report_data = {}
        for emp in docs:
            report_data.update({
                emp.id: {
                    'report_data': self.get_report_data(emp, year, date),
                    'address': reports_common_obj.get_employee_address(emp),
                }
            })
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
            'year': year,
            'date': date,
            'company': company,
            'company_address': reports_common_obj.get_company_address(company),
        }

    def get_report_data(self, emp, year, date):
        joppd_data = self.get_joppd_data(emp, year)
        joppd_corrected = self.correct_joppd_data(joppd_data)
        joppd_sorted = self.sort_joppd_data_by_month(joppd_corrected)
        ip_list = self.group_data_by_month(joppd_sorted)
        return ip_list
    
    def get_joppd_data(self, emp, year):
        """
        Podaci za zaposlenika sa svih joppd obrazaca u odabranoj godini.
        ID obrasca, redni broj retka, vrsta obrasca i parent_id nam treba za simuliranje ispravaka obrazaca.
        Sortiramo po vrsti da redak s izvornog izvješća bude prvi pa ga kasnije prebrišemo retkom s ispravka.
        Sortiramo po create_date za slučaj da se isti redak ispravlja više puta.
        """
        query = """
            SELECT substring(to_char(joppd.datum,'YYYY-MM-DD') from 6 for 2) as month,
            city.code,
            sum(jb.b11) as "Isplaćeno",
            sum(jb.b121 + jb.b122)as "Doprinos",
            sum(jb.b133) AS "Dohodak",
            sum(jb.b134) AS "Odbitak",
            sum(jb.b135) AS "Osnovica",
            sum(jb.b141 + jb.b142) as "Porez i prirez",
            sum(CASE WHEN joppd_sifre.name = '0' THEN jb.b162 ELSE 0 END) as "Neto plaća",
            joppd.id as joppd_id, jb.b1 as jb_b1, joppd.vrsta as vrsta, joppd.parent_id as parent_id
            FROM hr_joppd_form_b as jb
            LEFT JOIN hr_employee AS he ON(jb.hr_employee_id = he.id)
            LEFT JOIN res_city AS city ON(he.city = city.id)
            LEFT JOIN hr_joppd_form AS joppd ON (jb.joppd_id = joppd.id)
            LEFT JOIN l10n_hr_joppd_sifre AS joppd_sifre ON (jb.b151 = joppd_sifre.id)
            WHERE hr_employee_id = {0}
            AND substring(to_char(joppd.datum, 'YYYY-MM-DD') from 1 for 4) = '{1}'
            AND jb.b61 != '49'
            -- 49 is profit payment
            AND (joppd.joppd_payslip_run_type != 'nonpaid_salary' OR joppd.joppd_payslip_run_type IS NULL)
            AND joppd.form_type='payroll'
            GROUP BY joppd.id, jb.b1, city.code
            ORDER BY joppd.datum ASC, joppd.vrsta, joppd.create_date
        """.format(emp.id, year)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        return res

    def correct_joppd_data(self, joppd_data):
        """
        'Ispravljamo' retke izvornog (ili dopunskog) obrasca na način da ih prebrišemo retcima s ispravka obrasca.
        Podaci su sortirani po create_date pa se uvijek uzima posljednji podatak.
        """
        corrected_data = {}
        for line in joppd_data:
            # kolona 9 je joppp.id, 10 je joppd_b.b1 (redni broj), 12 je joppd.parent_id
            # ako je rijec o ispravku, prebrisemo originalni redak
            if line[11] == '2':
                key = (line[12], line[10])
            else:
                key = (line[9], line[10])
            corrected_data.update({key: line})
        return corrected_data

    def sort_joppd_data_by_month(self, joppd_corrected):
        joppd_list = [joppd_corrected[key] for key in joppd_corrected]
        joppd_list = sorted(joppd_list, key = itemgetter(0))
        return joppd_list

    def group_data_by_month(self, joppd_sorted):
        # there needs to be one line per month
        ip_list = []
        for line in joppd_sorted:
            if ip_list and line[0] == ip_list[-1][0]:
                ip_list[-1][2] += line[2]
                ip_list[-1][3] += line[3]
                ip_list[-1][4] += line[4]
                # na nekim listicima je zapisan cijeli umjesto iskoristenog osobnog odbitka
                if racunaj_odbitak:
                    ip_list[-1][5] += min(line[4], line[5])
                ip_list[-1][6] += line[6]
                ip_list[-1][7] += line[7]
                ip_list[-1][8] += line[8]
                if line[4] > line[5] and line[5] > 0:
                   racunaj_odbitak = False
            # different month
            else:
                racunaj_odbitak = True
                line = list(line)
                line[5] = min(line[4], line[5])
                ip_list.append(line)
        return ip_list
