/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Info3TimesheetDashboard } from '@l10n_hr_hr_timesheet/views/info3_timesheet_dashboard/info3_timesheet_dashboard';

export class Info3TimesheetRenderer extends ListRenderer {};

Info3TimesheetRenderer.template = 'l10n_hr_hr_timesheet.Info3TimesheetRenderer';
Info3TimesheetRenderer.components = {
    ...ListRenderer.components,
    Info3TimesheetDashboard
}

export const Info3TimesheetListView = {
    ...listView,
    Renderer: Info3TimesheetRenderer,
};

registry.category("views").add("info3_timesheet", Info3TimesheetListView);
