{
    'name': 'Blockchain Traceability',
    'version': '17.0.1.0.0', 
    'summary': 'Traceability from Purchase -> Manufacturing -> Sales on Blockchain',
    'author': 'myname',
    'depends': [
        'base', 
        'stock',     
        'blockchain',  
        'mrp',  
        'sale_stock',
        'website'   
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_lot_views.xml',
        'views/portal_return_button.xml',
        'views/traceability_template.xml',
        'views/portal_sale_order_views.xml',
        'views/stock_report_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}