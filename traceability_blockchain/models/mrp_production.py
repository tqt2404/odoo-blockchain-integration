from odoo import models, fields
import hashlib

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):
        
        res = super(MrpProduction, self).button_mark_done()
        
        # 2. Tìm Hash của nguyên liệu đầu vào
        source_prev_hash = False
        
        # Duyệt các nguyên liệu đã dùng
        for move in self.move_raw_ids:
            for line in move.move_line_ids:
                # Nếu tìm thấy nguyên liệu có Hash, lấy luôn và dừng vòng lặp
                if line.lot_id and line.lot_id.genesis_hash:
                    source_prev_hash = line.lot_id.genesis_hash
                    break 
            if source_prev_hash:
                break

        # 3. Ghi vào Lô Thành Phẩm
        for finish_move in self.move_finished_ids:
            for line in finish_move.move_line_ids:
                if line.lot_id and line.quantity > 0:
                    
                    # Tạo Hash mới cho thành phẩm (Genesis Hash)
                    content = f"{line.product_id.name}|{line.lot_id.name}"
                    new_genesis_hash = hashlib.sha256(content.encode()).hexdigest()
                    
                    # Ghi dữ liệu vào Lô
                    vals = {
                        'genesis_hash': new_genesis_hash,
                        'prev_hash': source_prev_hash, 
                    }
                
                    
                    line.lot_id.write(vals)

        return res