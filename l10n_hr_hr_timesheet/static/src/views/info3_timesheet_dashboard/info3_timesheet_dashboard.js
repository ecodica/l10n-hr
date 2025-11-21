/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

import { Component, onWillStart, useState, onMounted, useEffect } from "@odoo/owl";

export class Info3TimesheetDashboard extends Component {
    // #region Init
    async setup() {
        // Services
        this.orm = useService("orm");
        this.action = useService("action");

        // Props
        this.employees = []; // { id, name, active, department_id }
        this.departments = []; // { id, name }
        this.analytic_accounts = []; // list of all accounts - domain for selection
        this.analytic_accounts_with_children = {}; // list of children for each account, used for filtering
        this.months = [];
        this.years = [];
        this.employee_id = 0;
        this.department_employees = []; // TODO: Remove this when backend starts using proper data structure
        this.department_employees_objs = [] // { employee_id, name, active, department_id }

        // State
        this.state = useState({
            current_employee: null,
            current_department: null,
            current_day: '',
            current_month: '',
            current_year: '',
            current_analytic_account: null,
            current_department_filter: 'current_dep_only',
            show_active: 'active',
            date: null,
            days: [],
            filtered_employees: []
        });

        // Lifecycles
        onWillStart(async () => {
            await this.fetchInitialData();
        });

        onMounted(() => {
            const currentDate = luxon.DateTime.now();
            this.state.current_month = currentDate.toFormat('MM');
            this.state.current_year = currentDate.toFormat('yyyy');
            this.state.current_day = currentDate.toFormat('dd');
            this.state.filtered_employees = this.employees;
        });

        // Side effect
        useEffect(() => {
            // Update days when month or year changes
            const daysInMonth = luxon.DateTime.local(
                Number(this.state.current_year),
                Number(this.state.current_month)
            ).daysInMonth;
            this.state.current_day = '';
            this.state.days = Array.from({ length: daysInMonth }, (_, i) => {
                const day = String(i + 1).padStart(2, '0');
                // We need key because of DOM recycling
                return {
                    value: day,
                    key: `${day}${this.state.current_month}`
                };
            });
            this.fetchAndFilter();
        }, () => [this.state.current_month, this.state.current_year]);
    }
    // #endregion

    // #region Click Handlers
    async onClickRefreshForm() {
        await this.refreshView();
    }

    async onClickAddEmployees() {
        await this.callWizard("info3.timesheet.wizard", {
            employees: this.employees,
            departments: this.departments,
            date: this.getChoosenDate,
            department_id: this.state.current_department,
            current_employee: this.state.current_employee,
            current_analytic_account: this.state.current_analytic_account,
        });
    }

    async onClickGetWorkTimeControl() {
        await this.callWizard("info3.timesheet.work.time.control.wizard", {
            employees: this.employees,
            departments: this.departments,
            date: this.getChoosenDate,
            department_id: this.state.current_department,
            current_employee: this.state.current_employee,
        });
    }

    async onClickAutofill() {
        await this.callWizard("hr.timesheet.autofill.wizard", {
            employees: this.employees,
            departments: this.departments,
            date: this.getChoosenDate,
            department_id: this.state.current_department,
            current_employee: this.state.current_employee,
            current_analytic_account: this.state.current_analytic_account,
        });
    }

    async onClickPrintReport() {
        await this.callWizard("timesheet.report.wizard", {
            active_ids: [0],
            date: this.getChoosenDate,
            employee: this.state.current_employee,
            employees: this.employees,
            current_filter: this.state.current_department_filter,
            active_filter: this.state.show_active,
            aditional_emps: this.department_employees,
            department: this.state.current_department,
            analytic_account: this.state.current_analytic_account,
            month: this.state.current_month,
            year: this.state.current_year,
            report_name: 'l10n_hr_hr_timesheet.report_info3_timesheet',
            hr_timesheet_skip_onchange_category: true,
        });
    }

    async onClickPrintReportSum() {
        await this.callWizard("timesheet.report.wizard", {
            active_ids: [0],
            date: this.getChoosenDate,
            employee: this.state.current_employee,
            employees: this.employees,
            current_filter: this.state.current_department_filter,
            active_filter: this.state.show_active,
            aditional_emps: this.department_employees,
            department: this.state.current_department,
            analytic_account: this.state.current_analytic_account,
            month: this.state.current_month,
            year: this.state.current_year,
            report_name: 'l10n_hr_hr_timesheet.report_info3_timesheet_sum',
            hr_timesheet_skip_onchange_category: true,
        })
    }
    //#endregion

    // #region OnChange Handlers
    onChangeEmployeeFilter(e) {
        this.state.show_active = e.target.value || "active_and_inactive";
        this.fetchAndFilter();
    }

    onChangeDepartmentFilter(e) {
        this.state.current_department_filter = e.target.value || "current_dep_only";
        this.fetchAndFilter();
    }

    onChangeEmployee(e) {
        this.state.current_employee = e.target.value ? Number(e.target.value) : null;
        this.fetchAndFilter();
    }

    onChangeDepartment(e) {
        this.state.current_department = e.target.value ? Number(e.target.value) : null;
        this.fetchAndFilter();
    }

    onChangeDay(e) {
        this.state.current_day = e.target.value ? e.target.value : '';
        this.fetchAndFilter();
    }

    onChangeMonth(e) {
        this.state.current_month = e.target.value ? e.target.value : '';
    }

    onChangeYear(e) {
        this.state.current_year = e.target.value ? e.target.value : '';
    }
    //#endregion

    // #region Custom Functions
    get getChoosenDate() {
        if (this.currenty_year && this.current_month && this.current_day) {
            return this.current_year + "-" + this.current_month + "-" + this.current_day;
        }
        return null;
    }

    get getSearchDomain() {
        const domainArray = [];

        if (this.state.current_employee) {
            const employeeIdDomain = `('employee_id', '=', ${this.state.current_employee})`;
            domainArray.push(employeeIdDomain);
        }

        if (this.state.current_department) {
            const departmentIdDomain = `('department_id', '=', ${this.state.current_department})`;
            domainArray.push(departmentIdDomain);
        }

        const currentDay = this.state.current_day;
        const currentMonth = this.state.current_month;
        const currentYear = this.state.current_year;

        if (currentDay) {
            const date = `${currentYear}-${currentMonth}-${currentDay}`;
            const dateDomain = `('date', '=', '${date}')`;
            domainArray.push(dateDomain);
        } else if (currentMonth) {
            const startDate = `${currentYear}-${currentMonth}-01`;
            const endDate = new Date(currentYear, currentMonth, 0).getDate();
            domainArray.push(`("date", ">=", "${startDate}")`);
            domainArray.push(`("date", "<=", "${currentYear}-${currentMonth}-${endDate}")`);
        } else if (currentYear) {
            const startDate = `${currentYear}-01-01`;
            const endDate = `${currentYear}-12-31`;
            domainArray.push(`("date", ">=", "${startDate}")`);
            domainArray.push(`("date", "<=", "${endDate}")`);
        }

        // We need number of 'domainArray - 1' & operators
        let domain = domainArray.join(", ");
        if (domainArray.length > 1) {
            domain = `"&", `.repeat(domainArray.length - 1) + domain;
        }

        domain = `[${domain}]`;

        return domain;
    }

    async fetchInitialData() {
        this.employees = await this.orm.call(
            "info3.timesheet",
            "list_employees",
        );

        this.departments = await this.orm.call(
            "info3.timesheet",
            "list_departments",
        );

        const analyticAccountsDict = await this.orm.call(
            "info3.timesheet",
            "list_analytic_accounts",
        );
        this.analytic_accounts = analyticAccountsDict["account_list"];
        this.analytic_accounts_with_children = analyticAccountsDict["account_list_with_children"];

        const datesDict = await this.orm.call(
            "info3.timesheet",
            "get_date_span",
        );
        // Set initial days
        this.state.days = datesDict[0].map(day => ({
            value: day,
            key: `${day}`
        }));
        this.months = datesDict[1];
        this.years = datesDict[2];

        this.employee_id = await this.orm.searchRead(
            "hr.employee",
            [
                ["id", "in", [session.uid]]
            ],
            ["id", "name"],
        );
    }

    async filterEmployees(){
        await this.fetchDepartmentEmployees();

        // Filter employees by active status
        this.state.filtered_employees = this.employees?.filter(employee => {
            if (this.state.show_active == "active") {
                return employee.active == true;
            } else if (this.state.show_active == "inactive") {
                return employee.active == false;
            }
            return true;
        });

        // Filter employees by department filter
        const departmentNotSelected = this.state.current_department == null
         // current_dep_only - Shows all employees currently in that department, regardless of whether they have a timesheet for that department in the database
        if (this.state.current_department_filter == 'current_and_has_records') {
            this.state.filtered_employees = (this.state.filtered_employees || []).filter(employee => {
                return departmentNotSelected ? true : employee.department_id == this.state.current_department;
            });
            const filteredEmployeeIds = new Set((this.state.filtered_employees || []).map(
                emp => emp.id
            ));
            (this.department_employees_objs || []).forEach(deptEmp => {
                if (this.state.show_active == "active_and_inactive" || deptEmp.active == (this.state.show_active === "active")) {
                    if (!filteredEmployeeIds.has(deptEmp.employee_id)) {
                        const employee = this.employees.find(emp => emp.id === deptEmp.employee_id);
                        this.state.filtered_employees.push(employee);
                    }
                }
            });
        // has_dep_records - Shows all employees who have at least one timesheet for that department in the database, regardless of their current department
        } else if (this.state.current_department_filter == 'has_dep_records') {
            this.state.filtered_employees = (this.department_employees_objs || []).filter(deptEmp => {
                return this.state.show_active == "active_and_inactive" || deptEmp.active == (this.state.show_active === "active");
            }).map(deptEmp => {
                return this.employees.find(emp => emp.id === deptEmp.employee_id);
            }).filter(employee => employee !== undefined);
        // current_and_has_records - Shows all current employees and those who have at least one timesheet for that department in the database
        } else if (this.state.current_department_filter == 'current_dep_only') {
            this.state.filtered_employees = (this.state.filtered_employees || []).filter(employee => {
                return departmentNotSelected ? true : employee.department_id == this.state.current_department;
            }).map(employee => {
                return this.employees.find(emp => emp.id === employee.id);
            }).filter(employee => employee !== undefined);
        }

        // employee-red - Inactive employees
        // employee-blue - Employees who have records but are no longer in that department
        this.state.filtered_employees = this.state.filtered_employees.map(employee => {
            let employeeClass = '';
            if (!employee.active) {
                employeeClass = 'employee-red';
            } else if (this.state.current_department && this.department_employees_objs.some(deptEmp =>
                deptEmp.employee_id === employee.id &&
                deptEmp.department_id === this.state.current_department &&
                employee.department_id !== this.state.current_department)) {
                employeeClass = 'employee-blue';
            }
            return { ...employee, class: employeeClass };
        });
    };

    async fetchDepartmentEmployees() {
        this.department_employees = await this.orm.call(
            "info3.timesheet",
            "list_department_employees",
            [
                Number(this.state.current_day),
                Number(this.state.current_month),
                Number(this.state.current_year),
                this.state.current_department,
                this.state.filtered_employees,
            ]
        );
        // For easier manipulation
        this.department_employees_objs = (this.department_employees || []).map(deptEmp => ({
            employee_id: deptEmp[0],
            name: deptEmp[1],
            active: deptEmp[2],
            department_id: deptEmp[3]
        }));
    }

    async callWizard(wizardName, args) {
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: wizardName,
                view_mode: "form",
                view_type: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    ...args,
                },
            },
            {
                onClose: async () => {
                    await this.refreshView();
                },
            }
        );
    }

    async refreshView() {
        await this.env.model.root.load();
    }

    loadSelectedFilters() {
        // When deactivating group, remove only the domain that was added by this component
        const domain = this.getSearchDomain
        const facets = this.env.searchModel._getFacets();
        facets.forEach(facet => {
            if (facet.type === 'filter' && /date|employee_id|department_id/.test(facet.domain)) {
                this.env.searchModel.deactivateGroup(facet.groupId);
            }
        });
        this.env.searchModel.splitAndAddDomain(domain);
    }

    async fetchAndFilter() {
        await this.fetchDepartmentEmployees();
        await this.filterEmployees();
        this.loadSelectedFilters();
    };

    // #endregion
}

Info3TimesheetDashboard.template = "l10n_hr_hr_timesheet.Info3TimesheetDashboard";
