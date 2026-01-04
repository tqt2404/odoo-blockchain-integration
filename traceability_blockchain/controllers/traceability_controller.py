# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class TraceabilityController(http.Controller):

    @http.route('/traceability/ping', type='http', auth='none', csrf=False)
    def ping_server(self):
        return "Odoo Server on Ngrok is working."

    @http.route('/traceability/info/<int:lot_id>', type='http', auth='public', website=True, csrf=False)
    def view_traceability_page(self, lot_id, **kw):
        """
        website=True nên giữ lại nếu bạn dùng Template của Website Odoo
        """
        _logger.info(f"===> Bắt đầu xử lý Request cho Lot ID: {lot_id}")
        
        try:
            # Kiểm tra Database đang kết nối
            db_name = request.db
            _logger.info(f"DEBUG: Kết nối tới Database: {db_name}")

            # 1. TÌM LÔ HÀNG 
            lot = request.env['stock.lot'].sudo().browse(lot_id)
            
            error_msg = None
            success_msg = None
            picking = None
            
            if not lot or not lot.exists():
                return f"<h1>Lỗi</h1><p>Không tìm thấy số Lô (ID: {lot_id}) trong hệ thống {db_name}.</p>"

            # 2. LOGIC TÌM PHIẾU KHO (PICKING)
            picking_id = kw.get('picking_id')
            if picking_id:
                try:
                    picking = request.env['stock.picking'].sudo().browse(int(picking_id))
                    if not picking.exists():
                        picking = None
                except (ValueError, TypeError):
                    picking = None
            
            # Nếu không có picking_id từ URL, tìm picking xuất kho gần nhất của lô này
            if not picking:
                move_line = request.env['stock.move.line'].sudo().search([
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done'),
                    ('picking_id.picking_type_code', '=', 'outgoing')
                ], limit=1, order='date desc')
                if move_line:
                    picking = move_line.picking_id

            # 3. KIỂM TRA BLOCKCHAIN 
            if picking and hasattr(picking, 'blockchain_status') and picking.blockchain_status == 'done':
                try:
                    # Kiểm tra xem phương thức action_verify_4_layers có tồn tại không trước khi gọi
                    if hasattr(picking, 'action_verify_4_layers'):
                        picking.sudo().with_context(lang='vi_VN').action_verify_4_layers()
                        success_msg = "DỮ LIỆU TOÀN VẸN TRÊN BLOCKCHAIN"
                except Exception as b_err:
                    _logger.error(f"Lỗi khi verify Blockchain: {str(b_err)}")
                    error_msg = f"Cảnh báo Blockchain: {str(b_err)}"

            # 4. LẤY THÔNG TIN TRUY XUẤT
            trace_info = {}
            if hasattr(lot, 'get_traceability_info'):
                try:
                    trace_info = lot.get_traceability_info()
                except Exception as e:
                    _logger.error(f"Lỗi hàm get_traceability_info: {str(e)}")
            
            if not trace_info:
                trace_info = {
                    'product': lot.product_id.display_name,
                    'lot_name': lot.name,
                    'type': 'N/A',
                    'genesis_hash': 'N/A'
                }

            move_lines = request.env['stock.move.line'].sudo().search([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done')
            ], order='date desc')

            values = {
                'lot': lot,
                'picking': picking,
                'trace_info': trace_info,
                'move_lines': move_lines,
                'error_msg': error_msg,
                'success_msg': success_msg,
            }
            
            # 5. RENDER
            return request.render('traceability_blockchain.traceability_full_page', values)

        except Exception as e:
            _logger.error(f"CRITICAL ERROR: {str(e)}", exc_info=True)
            return f"<h1>Lỗi Hệ Thống (500)</h1><p>Chi tiết lỗi: {str(e)}</p>"