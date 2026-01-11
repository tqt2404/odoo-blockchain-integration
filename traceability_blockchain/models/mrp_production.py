from odoo import models, fields
import hashlib

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):

        res = super(MrpProduction, self).button_mark_done()
        
        ingredient_hashes = []
        
        for move in self.move_raw_ids:
            for line in move.move_line_ids:
                if line.lot_id:
                    h = (
                        line.lot_id.genesis_hash 
                        or hashlib.sha256((line.lot_id.name or "").encode()).hexdigest()
                    )
                    ingredient_hashes.append(h)
        sorted_ingredients = sorted(list(set(ingredient_hashes)))
        
        source_prev_hash = False
        
        if len(sorted_ingredients) == 0:
            source_prev_hash = hashlib.sha256("NO_INGREDIENT_DATA".encode()).hexdigest()
            
        elif len(sorted_ingredients) == 1:
            source_prev_hash = sorted_ingredients[0]
            
        else:
            combined_data = "|".join(sorted_ingredients)
            source_prev_hash = hashlib.sha256(combined_data.encode()).hexdigest()

        for finish_move in self.move_finished_ids:
            for line in finish_move.move_line_ids:
                if line.lot_id and line.quantity > 0:
                    content = f"{line.product_id.name}|{line.lot_id.name}"
                    new_genesis_hash = hashlib.sha256(content.encode()).hexdigest()
                    
                    vals = {
                        'genesis_hash': new_genesis_hash,
                        'prev_hash': source_prev_hash,
                    }
                    
                    line.lot_id.sudo().write(vals)

        return res