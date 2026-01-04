from odoo import models, fields,api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    lot_genesis_hash = fields.Char(
        related='lot_id.genesis_hash', 
        string="Hash của Lô (Genesis)", 
        # readonly=True,
        store=True
    )

    def get_blockchain_lot_url(self):
        """Hàm tạo URL riêng cho từng dòng hàng có số Lô"""
        self.ensure_one()
        if not self.lot_id:
            return ""
        
        # Lấy base_url từ hệ thống Ngrok
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')
        
        # Tạo link: /traceability/info/<lot_id>?picking_id=<picking_id>
        return f"{base_url}/traceability/info/{self.lot_id.id}?picking_id={self.picking_id.id}"