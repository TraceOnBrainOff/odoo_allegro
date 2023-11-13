from odoo import fields, models, api


class AllegroProduct(models.Model):
    _inherit = "product.template"
    _sql_constraints = [
    ('barcode_uniq', 'CHECK(1=1)', "A barcode can only be assigned to one product !")
    ]
    ASIN = fields.Char(
        string = 'ASIN',
        help = 'ASIN Code',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    EAN = fields.Char(
        string = 'EAN',
        help = 'EAN Code',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    LPN = fields.Char(
        string = 'LPN',
        help = 'LPN Code',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    amazon_category = fields.Text(
        string = 'Amazon Category',
        help = 'Category as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True
    )
    amazon_cat_code = fields.Char(
        string = 'Amazon Category Code',
        help = 'Code of the category as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 32,
        invisible = True
    )
    amazon_subcat_code = fields.Char(
        string = 'Amazon Subcategory Code',
        help = 'Code of the subcategory as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 32,
        invisible = True
    )
    amazon_subcategory = fields.Text(
        string = 'Amazon Subcategory',
        help = 'Subcategory as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True
    )
    amazon_condition = fields.Text(
        string = 'Amazon Condition',
        help = 'Condition as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True
    )
    amazon_currency_code = fields.Char(
        string = 'Amazon Currency Code',
        help = 'Type of currency used as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 8
    )
    amazon_gl = fields.Char(
        string = 'GL',
        help = 'GL code of a department as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 8
    )
    amazon_gl_desc = fields.Char(
        string = 'GL Description',
        help = 'GL shortened description of a department as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    amazon_department = fields.Text(
        string = 'Department',
        help = 'Department as stated sby Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True
    )
    amazon_item_pkg_weight_uom = fields.Char(
        string = 'Unit of Measure',
        help = 'Unit of Measure used to weigh the product as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 8
    )
    amazon_pallet_id = fields.Char(
        string = 'Pallet ID',
        help = 'The ID of the pallet the product came from as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    amazon_pkg_id = fields.Char(
        string = 'Package ID',
        help = 'The ID of the package the product came from as stated by Amazon\'s manifest',
        readonly = False,
        default = None,
        translate = True,
        size = 32
    )
    condition = fields.Text(
        string = 'Condition',
        help = 'Conditioned determined by our in-house testing',
        readonly = False,
        default = "Not yet tested!",
        translate = True
    )
    send_allegro_offer_pending = fields.Boolean(
        help="Whether an offer must be sent for this product. Handled by a cron.",
        invisible = True
    )
    allegro_offer_id = fields.Char(
        string="Allegro Offer ID",
        help="ID of the offer on Allegro",
        readonly = False,
        size = 32,
        translate = True
    )
    allegro_offer_url = fields.Char(
        string="Allegro Offer URL",
        help="URL of the offer on Allegro",
        readonly = True,
        compute = "_compute_URL"
    )
    @api.depends("allegro_offer_id")
    def _compute_URL(self):
        for record in self:
            record.allegro_offer_url = f"https://allegro.pl/offer/{record.allegro_offer_id}/"

