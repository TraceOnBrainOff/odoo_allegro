{
    'name': "Allegro Integration",
    'version': '0.2.0',
    'depends': ['base', 'stock', 'product'],
    'author': "7",
    'category': 'Inventory/Allegro Integration',
    'summary': 'Send Products as Allegro listings',
    'description': "A module capable of sending products present in Odoo's database as Allegro listings.",
    'data': [
        'data/ir_cron_data.xml',
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/product_send_allegro_offer_wizard_views.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
}