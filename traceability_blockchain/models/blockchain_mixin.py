from odoo import models, fields, api, _
from odoo.exceptions import UserError
from web3 import Web3
import json
import hashlib
import logging

_logger = logging.getLogger(__name__)

class BlockchainLogMixin(models.AbstractModel):
    _name = 'blockchain.log.mixin'
    _description = 'Mixin to Log data to Blockchain'

    tx_hash = fields.Char(string="Blockchain Tx Hash", readonly=True, copy=False)
    blockchain_sealed_hash = fields.Char(string="Sealed Data Hash", readonly=True, copy=False)
    
    blockchain_status = fields.Selection([
        ('draft', 'New'),
        ('done', 'Synced'),
        ('error', 'Error')
    ], string="Blockchain Status", default='draft', copy=False, readonly=True)
    blockchain_message = fields.Text(string="Blockchain Log", readonly=True, copy=False)

    def _get_blockchain_config(self):
        contract = self.env['blockchain.contract'].search([('name', '=', 'SupplyChainTraceability')], limit=1)
        account = self.env['blockchain.account'].search([('name', '=', 'AdminWallet')], limit=1)
        
        if not contract or not account:
            raise UserError("Lỗi cấu hình: Chưa thiết lập Contract hoặc Ví Admin.")
        return contract, account

    def _compute_data_hash(self, data_dict):
        json_str = json.dumps(data_dict, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def get_hash_from_chain(self, ref_id):
        """Đọc Hash từ Storage của Smart Contract (Miễn phí Gas)"""
        contract_record, _ = self._get_blockchain_config()
        
        w3 = Web3(Web3.HTTPProvider(contract_record.connector_id.service_url))
        if not w3.is_connected():
            raise UserError("Mất kết nối tới Node Blockchain.")

        try:
            contract_inst = w3.eth.contract(
                address=contract_record.address, 
                abi=json.loads(contract_record.abi)
            )
            # Gọi hàm getLog
            return contract_inst.functions.getLog(str(ref_id)).call()
            
        except Exception as e:
            raise UserError(f"Không thể đọc dữ liệu từ Blockchain: {str(e)}")

    def write_log_to_blockchain(self, ref_id, final_hash):
        """Ghi Hash vào Smart Contract (Tốn Gas)"""
        self.ensure_one()
        try:
            contract_record, account_record = self._get_blockchain_config()
            w3 = Web3(Web3.HTTPProvider(contract_record.connector_id.service_url))
            
            if not w3.is_connected():
                raise UserError("Mất kết nối tới RPC Node.")

            contract_inst = w3.eth.contract(
                address=contract_record.address, 
                abi=json.loads(contract_record.abi)
            )
            
            ACCOUNT_PASS = "admin" 
            try:
                private_key = w3.eth.account.decrypt(eval(account_record.encrypted_key), ACCOUNT_PASS)
            except Exception:
                raise UserError("Sai mật khẩu ví Admin.")

            nonce = w3.eth.get_transaction_count(account_record.address)
            
            # Build Transaction
            txn = contract_inst.functions.recordLog(
                str(ref_id),
                str(final_hash)
            ).build_transaction({
                'chainId': contract_record.connector_id.chain,
                'gas': 2000000, 
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
            })

            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            
            raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'raw_transaction', None))
            tx_hash_bytes = w3.eth.send_raw_transaction(raw_tx)
            
            tx_hex = tx_hash_bytes.hex()
            if not tx_hex.startswith('0x'):
                tx_hex = '0x' + tx_hex
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
            
            if receipt['status'] == 0:
                raise UserError(f"Transaction Reverted! Có thể ID '{ref_id}' đã tồn tại trên Chain.")

            EXPLORER_BASE_URL = "https://sepolia.etherscan.io/tx/"
            msg = f"Blockchain Synced. Tx: {EXPLORER_BASE_URL}{tx_hex}"
            self.message_post(body=msg)
            
            return tx_hex
        
        except Exception as e:
            self.write({'blockchain_status': 'error', 'blockchain_message': str(e)})
            raise UserError(f"Lỗi Blockchain: {str(e)}")