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
    allegro_refresh_token_override = fields.Char(
        string="Manually inserted refresh token (WIP)",
        config_parameter='allegro.application.refresh_token_ovr',
    )
    allegro_token = fields.Char( #No json field type forces my hand to do this garbage
        string="Current state of the tokens",
        config_parameter='allegro.application.token',
    )
