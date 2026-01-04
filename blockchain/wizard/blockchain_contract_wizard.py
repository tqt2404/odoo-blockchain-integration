from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from web3 import Web3


class BlockchainContractWizardInput(models.TransientModel):
    _name = 'blockchain.contract.wizard.input'
    _description = 'Blockchain Contract Wizard Input'

    input_id = fields.Many2one('blockchain.contract.function.input', readonly=True)
    input_type = fields.Char(related='input_id.input_type')
    position = fields.Integer(related='input_id.position')
    value = fields.Char()
    account_id = fields.Many2one('blockchain.account')
    wizard_id = fields.Many2one('blockchain.contract.wizard')

    @api.onchange('account_id')
    def _onchange_(self):
        self.value = self.account_id and self.account_id.address or ''


class BlockchainContractWizard(models.TransientModel):
    _name = 'blockchain.contract.wizard'
    _description = 'Blockchain Contract Wizard'

    account_id = fields.Many2one('blockchain.account')
    value = fields.Integer()
    password = fields.Char()
    function_id = fields.Many2one('blockchain.contract.function', readonly=True)
    contract_id = fields.Many2one(related='function_id.contract_id')

    state_mutability = fields.Selection(related='function_id.state_mutability')
    input_ids = fields.One2many(
        'blockchain.contract.wizard.input', 'wizard_id')

    @api.model
    def default_get(self, fields):
        res = super(BlockchainContractWizard, self).default_get(fields)
        if self._context.get('function_id'):
            blockchain_func_obj = self.env['blockchain.contract.function']
            blockchain_func = blockchain_func_obj.browse(self._context.get('function_id'))
            inputs = []
            for input in blockchain_func.input_ids:
                inputs.append((0, 0, {'input_id': input.id}))
            res.update({
                'input_ids': inputs,
                'function_id': blockchain_func.id,
            })
        return res

    input_ids = fields.One2many('blockchain.contract.wizard.input', 'wizard_id')

    def action_test_function(self):
        """
        Simple test to retrieve the functions from the smart contract
        """
        self.ensure_one()
        blockchain_provider = Web3.HTTPProvider(
            self.contract_id.connector_id.service_url)
        w3 = Web3(blockchain_provider)
        contract = w3.eth.contract(
            address=self.contract_id.address, abi=self.contract_id.abi)
        if self.function_id.state_mutability == 'view':
            return self.action_test_view(contract)
        elif self.function_id.state_mutability == 'payable':
            return self.action_test_payable(contract, w3)
        elif self.function_id.state_mutability == 'nonpayable':
            return self.action_test_payable(contract, w3)

    def action_test_view(self, contract):
        """
        Thực thi hàm view (read-only) và hiển thị kết quả
        """
        self.ensure_one()
        args = self._get_args()
        
        try:
            response = contract.functions[self.function_id.name](*args).call()
        except Exception as e:
            return self.contract_id._action_blockchain_connector_wizard("ERROR calling contract: " + str(e))

        msg = "Function: %s\n" % self.function_id.name
        msg += "Input Args: %s\n" % str(args)
        msg += "----------------------\n"
        msg += "RETURN VALUE: %s" % str(response)

        result = self.contract_id._action_blockchain_connector_wizard(msg)
        return result

    def _execute_transaction(self, w3, contract, args, account, password):
        try:
            privatekey = w3.eth.account.decrypt(
                eval(account.encrypted_key), password)
        except Exception:
            raise ValidationError(_(
                "Wrong Password for {}".format(account.name)
            ))
        
        if privatekey:
            nonce = w3.eth.get_transaction_count(account.address)
            txn_values = {
                'nonce': nonce,
                'chainId': self.contract_id.connector_id.chain,
                'gasPrice': w3.eth.gas_price,
                'gas': 1000000 # Có thể tăng lên 3000000 nếu cần
            }
            if self.value:
                txn_values.update({'value': self.value})
            
            txn = contract.functions[self.function_id.name](
                *args).build_transaction(txn_values)

            signed_tx = w3.eth.account.sign_transaction(txn, privatekey)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)
            
        return tx_hash

    def _get_msg(self, args, response=None, tx_hash=None):
        msg = 'Function {}'.format(self.function_id.name)
        if args:
            for input in self.input_ids:
                msg += '{}:{}'.format(input.input_id.input_type,
                                      input.value)
        if response:
            msg += '\n Response: {}\n'.format(str(response))
        if tx_hash:
            url = self.contract_id.connector_id.explorer_url+'tx/'+tx_hash.hex()
            msg += 'Transaction:{} \n'.format(tx_hash.hex())
            msg += 'Explorer:{} \n'.format(url)
        return msg

    def _get_args(self):
        args = []
        for input in self.input_ids:
            val = input.value
            if input.input_id.input_type in 'uint256': 
                val = int(input.value)
            args.append(val)
        return args

    def action_test_payable(self, contract, w3):
        """
        """
        self.ensure_one()
        args = self._get_args()
        tx_hash = self._execute_transaction(
            w3, contract, args, self.account_id, self.password)
        msg = self._get_msg(args, response=None, tx_hash=tx_hash)
        self.contract_id.message_post(body=msg)
        result = self.contract_id._action_blockchain_connector_wizard(msg)
        return result