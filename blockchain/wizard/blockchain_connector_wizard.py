from odoo import models, fields


class BlockchainConnectorWizard(models.TransientModel):
    _name = 'blockchain.connector.wizard'
    _description = 'Blockchain Connector Wizard'

    message = fields.Text(readonly=True)
