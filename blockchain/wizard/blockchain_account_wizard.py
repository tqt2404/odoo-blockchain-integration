from odoo import models, fields

class BlockchainAccountWizard(models.TransientModel):
    _name = 'blockchain.account.wizard'
    _description = 'Blockchain Account Wizard'

    password_1 = fields.Char()
    password_2 = fields.Char()

    def action_generate(self):
        for wizard in self:
            if wizard.password_1 and wizard.password_1 == wizard.password_2:
                account = self.env['blockchain.account'].browse(
                    self.env.context['active_id'])
                account._action_generate(wizard.password_1)
                return {'type': 'ir.actions.act_window_close'}
