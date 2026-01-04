from odoo import models, fields, api, _
from odoo.exceptions import UserError
import hashlib

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'blockchain.log.mixin']

    blockchain_status = fields.Selection([
        ('draft', 'Chưa gửi'),
        ('queue', 'Đang chờ gửi (Queue)'),
        ('done', 'Đã lưu Blockchain'),
        ('error', 'Lỗi gửi')
    ], string="Trạng thái Blockchain", default='draft', copy=False)

    previous_data_hash = fields.Char(string="Hash Hàng Hóa (Prev Hash)", copy=False)
    blockchain_sealed_hash = fields.Char(string="Hash Tổng (Sealed Hash)", copy=False)
    tx_hash = fields.Char(string="Mã Giao dịch (TxHash)", copy=False)


    def get_blockchain_url_for_lot(self, lot):
        """Hàm tạo URL riêng biệt cho từng đối tượng lot truyền vào"""
        self.ensure_one()
        if not lot:
            return ""
        try:
            # Lấy địa chỉ Ngrok từ System Parameters
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            base_url = base_url.rstrip('/') 
            
            # Tạo link dẫn tới trang truy xuất cụ thể của Lô hàng đó
            return f"{base_url}/traceability/info/{lot.id}?picking_id={self.id}"
        except Exception:
            return ""

    def button_validate(self):
        if self.picking_type_code == 'outgoing':
            if not self.carrier_id:
                raise UserError(_("RÀNG BUỘC BLOCKCHAIN: Vui lòng chọn 'Đơn vị vận chuyển'."))
            if not self.carrier_tracking_ref:
                raise UserError(_("RÀNG BUỘC BLOCKCHAIN: Vui lòng nhập 'Mã vận đơn'."))

        res = super(StockPicking, self).button_validate()

        if self.picking_type_code == 'outgoing':
            # KHÔNG GỬI NGAY – ĐƯA VÀO QUEUE
            self._seal_and_queue_blockchain()

        elif self.picking_type_code == 'incoming':
            self._generate_genesis_hash_incoming()

        return res

    def _generate_genesis_hash_incoming(self):
        for move in self.move_ids_without_package:
            for line in move.move_line_ids:
                if line.lot_id and not line.lot_id.genesis_hash:
                    raw = f"{line.product_id.name}|{line.lot_id.name}"
                    gh = hashlib.sha256(raw.encode()).hexdigest()
                    line.lot_id.sudo().write({'genesis_hash': gh})

    # ĐÓNG GÓI HASH & ĐƯA VÀO QUEUE (ASYNC)
    def _seal_and_queue_blockchain(self):
        prev_hash, curr_hash = self._compute_hashes_from_lots()

        self.write({
            'previous_data_hash': prev_hash,
            'blockchain_sealed_hash': curr_hash,
            'blockchain_status': 'queue'
        })

    #  CRON JOB – GỬI BLOCKCHAIN BẤT ĐỒNG BỘ
    @api.model
    def _cron_process_blockchain_queue(self):
        pickings = self.search([
            ('blockchain_status', '=', 'queue'),
            ('picking_type_code', '=', 'outgoing')
        ], limit=10)

        for picking in pickings:
            try:
                tx = picking.write_log_to_blockchain(
                    picking.name,
                    picking.blockchain_sealed_hash
                )

                picking.write({
                    'tx_hash': tx,
                    'blockchain_status': 'done'
                })

                self.env.cr.commit()

            except Exception as e:
                _logger.error(
                    "Blockchain Sync Error for %s: %s",
                    picking.name, str(e)
                )
                picking.write({
                    'blockchain_status': 'error'
                })
                self.env.cr.commit()

    def _compute_hashes_from_lots(self):
        self.ensure_one()

        lot_hashes = []
        for move in self.move_ids_without_package:
            for line in move.move_line_ids:
                if line.lot_id:
                    h = (
                        line.lot_id.genesis_hash
                        or hashlib.sha256((line.lot_id.name or "").encode()).hexdigest()
                    )
                    lot_hashes.append(h)

        sorted_lots = sorted(list(set(lot_hashes)))

        if len(sorted_lots) == 0:
            prev_hash = hashlib.sha256("NO_LOT_DATA".encode()).hexdigest()
        elif len(sorted_lots) == 1:
            prev_hash = sorted_lots[0]
        else:
            prev_hash = hashlib.sha256("|".join(sorted_lots).encode()).hexdigest()

        carrier_name = self.carrier_id.name or "Unknown"
        tracking_ref = self.carrier_tracking_ref or "NoRef"
        safe_carrier = f"{carrier_name} - {tracking_ref}"

        safe_ref = str(self.name or "")

        seal_data = f"REF:{safe_ref}|CARRIER:{safe_carrier}|PREV:{prev_hash}"
        curr_hash = hashlib.sha256(seal_data.encode()).hexdigest()

        return prev_hash, curr_hash

    # VERIFY 4 LỚP 
    def action_verify_4_layers(self):
        self.ensure_one()

        if self.blockchain_status != 'done':
            raise UserError("Phiếu này chưa được gửi lên Blockchain.")

        chain_hash = self.get_hash_from_chain(self.name)
        if not chain_hash:
            raise UserError("Lỗi: Không tìm thấy ID này trên Blockchain.")

        ui_sealed_hash = (self.blockchain_sealed_hash or "").strip()
        if ui_sealed_hash != chain_hash:
            msg = "LỖI 1: Ô 'DATA HASH' BỊ SAI KHÁC!\n"
            msg += f"- Blockchain: {chain_hash}\n- Màn hình: {ui_sealed_hash}"
            raise UserError(msg)

        real_prev_hash_from_lots, _ = self._compute_hashes_from_lots()
        ui_prev_hash = (self.previous_data_hash or "").strip()

        if real_prev_hash_from_lots != ui_prev_hash:
            msg = "LỖI 2: DỮ LIỆU HÀNG HÓA KHÔNG KHỚP!\n"
            msg += "Đã sửa ô 'Previous Hash' hoặc thay đổi Lô hàng."
            raise UserError(msg)

        carrier_name = self.carrier_id.name or "Unknown"
        tracking_ref = self.carrier_tracking_ref or "NoRef"
        ui_carrier = f"{carrier_name} - {tracking_ref}"

        safe_ref = str(self.name or "")
        raw_data_check = f"REF:{safe_ref}|CARRIER:{ui_carrier}|PREV:{real_prev_hash_from_lots}"
        calc_hash = hashlib.sha256(raw_data_check.encode()).hexdigest()

        if calc_hash == chain_hash:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ XÁC THỰC THÀNH CÔNG (4 LỚP)',
                    'message': 'Toàn bộ dữ liệu khớp tuyệt đối với Blockchain.',
                    'type': 'success',
                    'sticky': False
                }
            }

        msg = "LỖI 3: THÔNG TIN VẬN CHUYỂN BỊ SAI!\n"
        msg += "Dữ liệu hàng hóa đúng, nhưng Hash tổng không khớp Blockchain."
        raise UserError(msg)
