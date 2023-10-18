from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allegro_client_id = fields.Char(
        string="Client ID of the Allegro application",
        config_parameter='allegro.application.id',
    )
    allegro_client_secret = fields.Char(
        string="Client Secret of the Allegro application",
        config_parameter='allegro.application.secret',
    )
