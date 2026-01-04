from ast import literal_eval
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    blockchain_connector_id = fields.Many2one('blockchain.connector')

    @api.model
    def get_values(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res = super(ResConfigSettings, self).get_values()
        blockchain_connector_id = literal_eval(ICPSudo.get_param(
            'blockchain.blockchain_connector_id',
            default='False'))
        res.update(
            blockchain_connector_id=blockchain_connector_id,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param("blockchain.blockchain_connector_id",
                          self.blockchain_connector_id.id)
