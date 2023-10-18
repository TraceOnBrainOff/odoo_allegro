from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    send_allegro_offer_pending = fields.Boolean(
        help="Whether an offer must be sent for this product. Handled by a cron.",
    )
