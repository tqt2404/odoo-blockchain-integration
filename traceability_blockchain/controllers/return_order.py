from odoo import http, _
from odoo.http import request
import logging 

_logger = logging.getLogger(__name__)

class ReturnOrderController(http.Controller):

    @http.route(['/my/orders/return/<int:order_id>'], type='http', auth="user", website=True)
    def portal_order_return(self, order_id, **kw):
        sale_order = request.env['sale.order'].browse(order_id)
        if not sale_order.exists():
            return request.render('http_routing.404')

        # 1. Tìm phiếu giao hàng gốc (Delivery)
        outgoing_picking = request.env['stock.picking'].sudo().search([
            ('origin', '=', sale_order.name),
            ('state', '=', 'done'),
            ('picking_type_code', '=', 'outgoing')
        ], order='id desc', limit=1)

        if not outgoing_picking:
            return request.redirect('/my/orders/%s?error_msg=Don_hang_chua_hoan_thanh' % order_id)

        # 2. Kiểm tra đã có phiếu trả hàng chưa
        existing_return = request.env['stock.picking'].sudo().search([
            '|', ('origin', '=', sale_order.name), ('origin', '=', outgoing_picking.name),
            ('picking_type_code', '=', 'incoming'),
            ('state', '!=', 'cancel')
        ], limit=1)

        if existing_return:
            return request.redirect('/my/orders/%s?error_msg=Da_co_yeu_cau_tra_hang' % order_id)

        # 3. Tạo phiếu trả hàng
        try:
            ReturnPicking = request.env['stock.return.picking'].sudo()
            ctx = {
                'active_ids': [outgoing_picking.id], 
                'active_id': outgoing_picking.id, 
                'active_model': 'stock.picking'
            }
            # Lấy dữ liệu mặc định (quan trọng)
            defaults = ReturnPicking.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists', 'location_id'])
            # Tạo wizard
            return_wizard = ReturnPicking.with_context(ctx).create(defaults)
            # Xác nhận tạo phiếu trả
            return_wizard.create_returns()

        except Exception as e:
            return request.redirect('/my/orders/%s?error_msg=%s' % (order_id, str(e)))
        
        return request.redirect('/my/orders/%s?return_created=True' % order_id)
