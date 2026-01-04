from odoo import fields, models
from ast import literal_eval
from web3 import Web3

import logging

_logger = logging.getLogger(__name__)


class BlockchainConnector(models.Model):
    """
    Blockchain Network connector
    """
    _name = 'blockchain.connector'
    _description = "Blockchain Network connector"

    name = fields.Char(required=True)
    service_url = fields.Char(required=True)
    chain = fields.Integer(required=True, string='Chain ID')
    symbol = fields.Char()
    explorer_url = fields.Char()
    fund_url = fields.Char()

    def _get_default_connector(self):
        """
        Returns the default configured Blockchain Connector
        """
        ICPSudo = self.env['ir.config_parameter'].sudo()
        connector_id = literal_eval(ICPSudo.get_param(
            'blockchain.blockchain_connector_id', default='False'
        ))
        blockchain_connector = None
        if connector_id:
            blockchain_connector = self.env['blockchain.connector'].browse(connector_id)
        return blockchain_connector

    def action_test(self):
        """
        Simple connection test
        """
        self.ensure_one()

        blockchain_provider = Web3.HTTPProvider(self.service_url)
        w3 = Web3(blockchain_provider)
        connected = w3.is_connected()
        result = self._action_blockchain_connector_wizard(
            'Connected to {}:{}'.format(self.name, connected))
        return result

    def _action_blockchain_connector_wizard(self, message):
        """
        simple wizard call to show the messsage
        """
        action = self.env.ref('blockchain.blockchain_connector_wizard_form_action')
        result = action.sudo().read()[0]
        result['context'] = {'default_message': message}
        return result
