from odoo import models, fields, api

class StockLot(models.Model):
    _inherit = 'stock.lot'

    genesis_hash = fields.Char(string="Genesis Hash", copy=False)
    prev_hash = fields.Char(string="Previous Hash", copy=False)

    def get_traceability_info(self):
        self.ensure_one()
        
        info = {
            'lot_name': self.name,
            'product': self.product_id.display_name,
            'type': 'unknown',
            'genesis_hash': self.genesis_hash,
            'data': {} 
        }

        # 1. TÌM MO
        mos = self.env['mrp.production'].sudo().search([
            ('lot_producing_id', '=', self.id),
            ('state', '=', 'done')
        ], order='date_finished asc') # Sắp xếp ngày tăng dần

        if mos:
            info['type'] = 'manufacturing'
            
            # Xử lý Ngày & Reference
            mo_names = [mo.name for mo in mos]
            
            # Lấy ngày đầu và ngày cuối
            dates = mos.mapped('date_finished')
            date_str = ""
            if dates:
                start_date = min(dates).strftime('%d/%m/%Y')
                end_date = max(dates).strftime('%d/%m/%Y')
                if start_date == end_date:
                    date_str = start_date
                else:
                    date_str = f"{start_date} - {end_date}"

            comp_map = {}

            for mo in mos:
                for move in mo.move_raw_ids.filtered(lambda m: m.state == 'done'):
                    for line in move.move_line_ids:
                        # Key để định danh nguyên liệu duy nhất: (ID Sản phẩm, ID Lô)
                        p_id = line.product_id.id
                        l_id = line.lot_id.id if line.lot_id else 0
                        key = (p_id, l_id)
                        
                        qty = line.qty_done if hasattr(line, 'qty_done') else line.quantity

                        if key in comp_map:
                            # Nếu đã có -> Cộng dồn số lượng
                            comp_map[key]['qty'] += qty
                        else:
                            # Nếu chưa có -> Tạo mới
                            lot_name = line.lot_id.name if line.lot_id else "Không có lô"
                            comp_supplier = self._get_supplier_info(line.lot_id) if line.lot_id else None
                            
                            comp_map[key] = {
                                'product': line.product_id.name,
                                'lot': lot_name,
                                'qty': qty,
                                'uom': line.product_uom_id.name,
                                'supplier': comp_supplier
                            }

            # Chuyển map thành list
            info['data'] = {
                'mo_reference': ", ".join(mo_names),
                'date_finished_str': date_str, # Dùng string đã format
                'factory': self.env.company.name,
                'components': list(comp_map.values()) # Danh sách đã gộp
            }
        
        else:
            # THƯƠNG MẠI
            supplier_info = self._get_supplier_info(self)
            if supplier_info:
                info['type'] = 'trading'
                info['data'] = {
                    'supplier': supplier_info.get('partner'),
                    'receipt_date': supplier_info.get('date'),
                    'reference': supplier_info.get('reference')
                }
            else:
                info['type'] = 'inventory'

        return info

    def _get_supplier_info(self, lot_record):
        move_line = self.env['stock.move.line'].sudo().search([
            ('lot_id', '=', lot_record.id),
            ('state', '=', 'done'),
            ('picking_id.picking_type_code', '=', 'incoming')
        ], limit=1, order='date desc')

        if move_line and move_line.picking_id:
            return {
                'partner': move_line.picking_id.partner_id.name,
                'date': move_line.picking_id.date_done,
                'reference': move_line.picking_id.name
            }
        return None