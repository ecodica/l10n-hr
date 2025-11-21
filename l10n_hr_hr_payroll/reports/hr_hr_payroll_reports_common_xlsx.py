# -*- coding: utf-8 -*-
from odoo import models


class HrHrPayrollReportsCommonXlsx(models.AbstractModel):
    _name = 'hr.hr.payroll.reports.common.xlsx'
    _description = 'Common class for xlsx reports'

    def _get_range(self, column_start, column_end, row_start, row_end=False):
        """
        Method for merging cell ranges in xlsx reports.
        In Excel columns indexes are type Char, and row indexes are type Integer.
        To create a report there is often the need to merge cells, which means adding together Chars and Integers.
        This method is a helper to do that operation efficiently.

        Args:
            column_start (char): First column of the range
            column_end (char): Last column of the range 
            row_start (int): First row of the range
            row_end (int, optional): Last row of the range. Defaults to False.

        Returns:
            char: the range to merge, e.g. 'C5:E8'
        """
        if not row_end:
            row_end = row_start
        return column_start + str(row_start) + ':' + column_end + str(row_end)

    def _get_display_city_name(self, company):
        return (f"{company.city_id.zipcode or ''} {company.city_id.name or ''}")
    