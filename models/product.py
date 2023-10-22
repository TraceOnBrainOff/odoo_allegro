from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    send_allegro_offer_pending = fields.Boolean(
        help="Whether an offer must be sent for this product. Handled by a cron.",
    )
    #allegro_offer_id = fields.Integer(
    #    help="ID of the offer on Allegro"
    #)
    _sql_constraints = [
    ('barcode_uniq', 'CHECK(1=1)', "A barcode can only be assigned to one product !")
    ]
