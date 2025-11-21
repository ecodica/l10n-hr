from odoo import api, models, fields


class ReportMainRegister(models.AbstractModel):
    _name = 'report.l10n_hr_hr.hr_main_register_report'
    _description = 'Main register report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_today = fields.Date.context_today(self)
        binding_contract = self.env.ref('l10n_hr_hr.hr_contract_area_type_2')

        employee_entries = self.env['hr.employee'].search([])
        contracts = self.env['hr.contract'].search([], order='date_start desc')

        employee_entries_list = []
        # if employee_entries:
        for emp in employee_entries:
            names = []
            if emp.father_name_surname:
                names.append(emp.father_name_surname)
            if emp.mother_name_surname:
                names.append(emp.mother_name_surname)
            parents_names = names and ', '.join(names) or ''
            for elem in docids:
                if emp.id == elem:
                    education_type_ids = [f.education_type_id.qualification_type for f in emp.education_ids if f.education_type_id.qualification_type]
                    is_employee= True
                    target_contracts = emp.get_consecutive_contracts(date_today)
                    target_contract = emp.contract_id
                    for contract in target_contracts :
                        if contract.date_end:
                            if contract.date_start < date_today < contract.date_end:
                                target_contract = contract
                                break
                    type_counter = len(education_type_ids)
                    education_type_id_1 = ''
                    education_type_id_2 = ''
                    education_type_id_3 = ''
                    if type_counter == 1:
                        education_type_id_1 = education_type_ids[0]
                    elif type_counter == 2:
                        education_type_id_1 = education_type_ids[0]
                        education_type_id_2 = education_type_ids[1]
                    elif type_counter >= 3:
                        education_type_id_1 = education_type_ids[0]
                        education_type_id_2 = education_type_ids[1]
                        education_type_id_3 = education_type_ids[2]
                        # if there are no qualification_type's on employee - take the degree name for the report.
                    if not type_counter:
                        education_type_id_1 = emp.degree_id.name
                    # Check employee contract
                    if target_contract and target_contract.area and target_contract.area != binding_contract:
                        is_employee = False

                    vocation_ids = [f.vocation for f in emp.education_ids if f.vocation]
                    vocation_counter = len(vocation_ids)
                    vocation_1 = ''
                    vocation_2 = ''
                    vocation_3 = ''
                    if vocation_counter == 1:
                        vocation_1 = vocation_ids[0]
                    elif vocation_counter == 2:
                        vocation_1 = vocation_ids[0]
                        vocation_2 = vocation_ids[1]
                    elif vocation_counter >= 3:
                        vocation_1 = vocation_ids[0]
                        vocation_2 = vocation_ids[1]
                        vocation_3 = vocation_ids[2]

                    # Get work permit number
                    #Iterate through emp.work_permit_ids, find type equal to work_permit and get work_permit_number
                    work_permit_number = ''
                    work_permit = self.env['hr.employee.work.permit']
                    prev_work_permit = None
                    for wpn in emp.work_permit_ids:
                        permit_type = self.env['hr.permit.type'].search([('id', '=', wpn.permit_type_id.id)])
                        if permit_type.type == 'work_permit' and (wpn.start_date > prev_work_permit.start_date if prev_work_permit else True):
                            work_permit_number = wpn.work_permit_number
                            prev_work_permit = wpn
                            work_permit = wpn
                    cession_overseas = []
                    for cession in emp.cession_overseas_ids:
                        cession_date_start=cession.date_from
                        cession_date_end=cession.date_to
                        cession_place_of_work=cession.place_of_work
                        cession_overseas.append(
                            {
                                'date_start':cession_date_start,
                                'date_end':cession_date_end,
                                'place_of_work':cession_place_of_work
                            }
                        )
                    cession_overseas.sort(key=lambda x: x['date_start'], reverse=True)

                    vals = {
                        'employee': emp,
                        'work_permit': work_permit,
                        'id': emp.id,
                        'code':emp.code,
                        'last_name': emp.last_name,
                        'first_name': emp.first_name,
                        'parent_name': parents_names,
                        'oib':emp.oib,
                        'gender': emp.gender,
                        'birthday':emp.birthday if emp.birthday else "",
                        'place_of_birth': emp.place_of_birth,
                        'country_id': emp.country_id.name,
                        'date_start': emp.hire_date if emp.hire_date else "",
                        'addr_type': emp.addr_type.name,
                        'street2': emp.street2 if emp.street2 else "",
                        'street': emp.street if emp.street and emp.street2 else emp.street,
                        'city': emp.city.name,
                        'zip': emp.zip,
                        'work_permit_number': work_permit_number,
                        'education_type_id_1': education_type_id_1,
                        'education_type_id_2': education_type_id_2,
                        'education_type_id_3': education_type_id_3,
                        'vocation_1': vocation_1,
                        'vocation_2': vocation_2,
                        'vocation_3': vocation_3,
                        'job_id': str(emp.job_id.name) if emp.job_id.name else "",
                        'department_id': str(emp.department_id.name) if emp.department_id.name else "",
                        'contract_no': '[' + emp.contract_no + '] ' + emp.name if hasattr(emp, 'contract_no') and emp.contract_no else emp.name,
                        'is_employee':is_employee,
                        'cession_overseas':cession_overseas,
                        'work_location': str(emp.work_location_id.name if emp.work_location_id.name else emp.address_work_id.city_id.name),
                        'internship_until_emp_years': emp.internship_until_emp_years,
                        'internship_until_emp_months': emp.internship_until_emp_months,
                        'internship_until_emp_days': emp.internship_until_emp_days,
                        'internship_total_years': emp[0].internship_total_years,
                        'internship_total_months': emp[0].internship_total_months,
                        'internship_total_days': emp[0].internship_total_days,
                        'insurance_start': emp.insurance_start if emp.insurance_start else '',
                        'insurance_change': emp.insurance_change if emp.insurance_change else '',
                        'insurance_end': emp.insurance_end if emp.insurance_end else '',
                    }
                    employee_entries_list.append(vals)


        contracts_list = []
        if contracts:
            for contr in contracts:
                vals1 = {
                    'contract': contr,
                    'id': contr.employee_id.id,
                    'date_start': contr.date_start if contr.date_start else "",
                    'contract_no': '[' + contr.contract_no + '] ' + contr.name if hasattr(contr, 'contract_no') and contr.contract_no else contr.name,
                    'contract_area_type': contr.area_type.name,
                    'trial_date_start': contr.trial_date_start if contr.trial_date_start else "",
                    'trial_date_end': contr.trial_date_end if contr.trial_date_end else "",
                    'internship_date_start': contr.internship_date_start if contr.internship_date_start else "",
                    'internship_date_end': contr.internship_date_end if contr.internship_date_end else "",
                    'internship_type': contr.internship_type,
                    'date_end':contr.termination_date  if contr.termination_date else "",
                    'termination_reason': contr.termination_reason.name,
                    'resource_calendar_id': contr.resource_calendar_id.name,
                }
                contracts_list.append(vals1)

        return {
            'doc_ids': self.ids,
            'employee': employee_entries_list,
            'contract': contracts_list,
            'data': data,
        }
