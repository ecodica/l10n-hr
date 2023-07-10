# -*- coding: utf-8 -*-

import logging
from odoo import models
from odoo.tools.translate import _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


class JOPPDObrazacXlsx(models.AbstractModel):
    _name = 'report.l10n_hr_joppd.joppd_obrazac_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'JOPPD Obrazac XLSX report'

    def print_osnovni_podaci(self, workbook, joppd):
        sheet = workbook.add_worksheet(_('Osnovni podaci strane A'))
        label_style = workbook.add_format({'bold': True, 'bottom': 1})
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 40)
        sheet.fit_to_pages(1, 0)
        sheet.set_row(0, None, None, {'collapsed': 1})
        # datumi i razdoblja
        row = 1
        sheet.write(row, 0, _('Naziv'), label_style)
        sheet.write(row, 1, joppd.name)
        row += 1
        sheet.write(row, 0, _('Datum'), label_style)
        sheet.write(row, 1, format_date(self.env, joppd.date_joppd) or '')
        row += 1
        sheet.write(row, 0, _('Razdoblje (od - do)'), label_style)
        period_string = joppd.period_joppd.name_get()[0][1] or ''
        period_string += ' '
        period_string += '%s - %s' % (format_date(self.env, joppd.period_date_from_joppd) or '',
                                      format_date(self.env, joppd.period_date_to_joppd) or '')
        sheet.write(row, 1, period_string)
        row += 1
        # verzije i vrste
        sheet.write(row, 0, _('Verzija sheme'), label_style)
        sheet.write(row, 1, joppd.xml_schema)
        sheet.write(row, 2, _('I. Oznaka izvješća'), label_style)
        sheet.write(row, 3, joppd.oznaka or '')
        row += 1
        sheet.write(row, 0, _('II. Vrsta izvještaja'), label_style)
        sheet.write(row, 1, joppd.vrsta or '')
        sheet.write(row, 2, _('III.5 Oznaka podnositelja'), label_style)
        sheet.write(row, 3, joppd.podnositelj_oznaka or '')
        row += 1
        sheet.write(row, 0, _('III.5 Naziv/ime i prezime'), label_style)
        sheet.write(row, 1, joppd.podnositelj_naziv or '')
        row += 1
        sheet.write(row, 0, _('III.2 Adresa (mjesto, ulica, broj)'), label_style)
        sheet.write(row, 1, '%s, %s, %s' % (
        joppd.podnositelj_mjesto or '', joppd.podnositelj_ulica or '', joppd.podnositelj_kbr or ''))
        # kontakt
        sheet.write(row, 0, _('III.3 Adresa e-pošte'), label_style)
        sheet.write(row, 1, joppd.podnositelj_email)
        sheet.write(row, 2, _('III.4 OIB'), label_style)
        sheet.write(row, 3, joppd.podnositelj_oib)
        row += 1
        sheet.write(row, 0, _('IV.1 Broj osoba'), label_style)
        sheet.write(row, 1, str(joppd.broj_osoba))
        sheet.write(row, 2, _('IV.2 Broj redaka'), label_style)
        sheet.write(row, 3, str(joppd.broj_redaka))
        row += 2
        sheet.write(row, 0, _('Izvještaj sastavio:'), label_style)
        row += 1
        sheet.write(row, 0, _('Sastavio'), label_style)
        sheet.write(row, 1, joppd.sastavio_id.name_get()[0][1])
        row += 1
        sheet.write(row, 0, _('Ime'), label_style)
        sheet.write(row, 1, joppd.sast_ime)
        sheet.write(row, 2, _('Prezime'), label_style)
        sheet.write(row, 3, joppd.sast_prez)

    def print_a_strana(self, workbook, joppd):
        sheet = workbook.add_worksheet(_('Strana A'))
        sheet.fit_to_pages(1, 0)
        sheet.set_zoom(80)
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 120)
        sheet.set_column(2, 2, 20)
        title_style = workbook.add_format({'bold': True,
                                           'bg_color': '#FFFFCC',
                                           'bottom': 1})
        sheet_title = [_('Pozicija'),
                       _('Opis pozicije'),
                       _('Iznos'),
                       ]
        sheet.set_row(0, None, None, {'collapsed': 1})
        sheet.write_row(1, 0, sheet_title, title_style)
        sheet.freeze_panes(2, 0)
        i = 2
        for line in joppd.sideA_ids:
            sheet.write(i, 0, line.code or '')
            sheet.write(i, 1, line.position or '')
            sheet.write(i, 2, line.value)
            i += 1

    def print_b_strana(self, workbook, joppd):
        sheet = workbook.add_worksheet(_('Strana B'))
        sheet.fit_to_pages(1, 0)
        sheet.set_zoom(80)
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 2, 40)
        sheet.set_column(3, 15, 40)
        title_style = workbook.add_format({'bold': True,
                                           'bg_color': '#FFFFCC',
                                           'bottom': 1})
        sheet_title = [_('Redni broj'),
                       _('Ime i prezime stjecatelja/osiguranika'),
                       _('Oznaka stjecatelja/osiguranika'),
                       _('Oznaka primitka/obveze doprinosa'),
                       _('Iznos primitka (oporezivi)'),
                       _('Doprinos za mirovinsko osiguranje'),
                       _('Doprinos za mir. osig. II Stup'),
                       _('Zdravstveno osig.'),
                       _('Doprinos za zašt. zdravlja na radu'),
                       _('Doprinos za zapošljavanje'),
                       _('Izdatak - upla. dop. mir. osig.'),
                       _('Dohodak'),
                       _('Oznaka neopor. primitka'),
                       _('Iznos neopor. primitka'),
                       _('Oznaka načina isplate'),
                       _('Iznos za isplatu'),
                       ]
        sheet.set_row(0, None, None, {'collapsed': 1})
        sheet.write_row(1, 0, sheet_title, title_style)
        sheet.freeze_panes(2, 0)
        i = 2
        for line in joppd.sideB_ids:
            sheet.write(i, 0, line.b1 or '')
            sheet.write(i, 1, line.b5 or '')
            sheet.write(i, 2, line.b61 or '')
            sheet.write(i, 3, line.b62 or '')
            sheet.write(i, 4, line.b11)
            sheet.write(i, 5, line.b121)
            sheet.write(i, 6, line.b122)
            sheet.write(i, 7, line.b123)
            sheet.write(i, 8, line.b124)
            sheet.write(i, 9, line.b125)
            sheet.write(i, 10, line.b132)
            sheet.write(i, 11, line.b133)
            sheet.write(i, 12, line.b151 or '')
            sheet.write(i, 13, line.b152)
            sheet.write(i, 14, line.b161 or '')
            sheet.write(i, 15, line.b162)
            i += 1

    def generate_xlsx_report(self, workbook, data, objects):
        self.print_osnovni_podaci(workbook, objects)
        self.print_a_strana(workbook, objects)
        self.print_b_strana(workbook, objects)
        return super().generate_xlsx_report(workbook, data, objects)
