from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountMovePostJOPPD(models.TransientModel):
    _name = 'account.move.post.joppd'
    _description = 'Post Account Move Joppd Entries'

    joppd_post_date = fields.Date('JOPPD Post Date')

    @api.model
    def _check_moves_before_processing(self, moves):
        for move in moves:
            if move.state != 'posted':
                raise UserError(_('Moves must be posted before processing!'))
            if move.l10n_hr_joppd_posted:
                raise UserError(_('Move %s already posted in JOPPD!') % (move.name,))
        if not any(moves.filtered('l10n_hr_is_for_joppd')):
            raise UserError(_('No moves for posting in JOPPD!'))

    def post_joppd(self):
        move_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(move_ids)
        self._check_moves_before_processing(moves)
        moves.post_joppd(post_date=self.joppd_post_date)
