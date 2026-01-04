from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from web3 import Web3
import json

import logging

_logger = logging.getLogger(__name__)


class BlockchainContractFunctionInput(models.Model):
    """
    Blockchain Contract Function Input
    """
    _name = 'blockchain.contract.function.input'
    _description = "Blockchain Contract Function"

    name = fields.Char()
    position = fields.Integer()
    function_id = fields.Many2one('blockchain.contract.function', required=True)
    input_type = fields.Char(required=True)


class BlockchainContractFunction(models.Model):
    """
    Blockchain Contract Function
    """
    _name = 'blockchain.contract.function'
    _description = "Blockchain Contract Function"

    name = fields.Char(required=True)
    contract_id = fields.Many2one('blockchain.contract')
    state_mutability = fields.Selection(selection=[(
        'view', 'View'), ('payable', 'Payable'), ('nonpayable', 'Non Payable')])
    input_ids = fields.One2many(
        'blockchain.contract.function.input', 'function_id')


class BlockchainContract(models.Model):
    """
    Blockchain Contract
    """
    _name = 'blockchain.contract'
    _description = "Blockchain Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        help='The name must be the same used in the smart contract definition')
    connector_id = fields.Many2one('blockchain.connector')
    account_id = fields.Many2one('blockchain.account')
    address = fields.Char()
    abi = fields.Text()
    explorer_url = fields.Char(compute='_compute_url')
    function_ids = fields.One2many(
        'blockchain.contract.function', 'contract_id', auto_join=True,
        compute='_compute_functions')

    @api.depends('name', 'connector_id')
    def name_get(self):
        result = []
        for rec in self:
            result.append((
                rec.id, _("%(name)s [%(connector)s]") % {
                    'name': rec.name, 'connector': rec.connector_id.name,
                })
            )
        return result

    @api.depends('abi')
    def _compute_functions(self):
        """
        This function is to construct the smart contract functions and inputs
        based on the abi json
        """
        blockchain_fun_obj = self.env['blockchain.contract.function']
        for rec in self:
            rec.function_ids = None
            if rec.abi:
                data = json.loads(rec.abi)
                for e in data:
                    if e['type'] == 'function':
                        inputs = []
                        for i, input in enumerate(e['inputs']):
                            inputs.append(
                                (0, 0, {'name': input['name'],
                                        'input_type': input['type'],
                                        'position': i}))
                        blockchain_func = blockchain_fun_obj.create(
                            {'name': e['name'],
                             'contract_id': rec.id,
                             'state_mutability': e['stateMutability'],
                             'input_ids': inputs})
                        rec.function_ids |= blockchain_func

    @api.depends('address', 'connector_id')
    def _compute_url(self):
        for rec in self:
            url = ''
            if rec.connector_id and rec.connector_id.explorer_url and \
                    rec.address:
                url = rec.connector_id.explorer_url+'address/'+rec.address
            rec.explorer_url = url

    def action_test(self):
        """
        Simple test to retrieve the functions from the smart contract
        """
        self.ensure_one()
        blockchain_provider = Web3.HTTPProvider(self.connector_id.service_url)
        w3 = Web3(blockchain_provider)
        contract = w3.eth.contract(address=self.address, abi=self.abi)
        msg = 'Contract Address:{}'.format(contract.address)+'\n'
        msg += 'Functions:\n'
        for fx in contract.all_functions():
            msg += '{}'.format(fx)+'\n'
        result = self._action_blockchain_connector_wizard(msg)
        return result

    def _action_blockchain_connector_wizard(self, message):
        """
        simple wizard call to show the messsage
        """
        action = self.env.ref('blockchain.blockchain_connector_wizard_form_action')
        result = action.sudo().read()[0]
        result['context'] = {'default_message': message}
        return result