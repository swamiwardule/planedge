
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    on_off_value = fields.Boolean(string="Fields Function On/Off", default=True)
    whatsapp_auth_token = fields.Char("WhatsApp API Authorization Token")

    def set_values(self):
        """Save settings values into system parameters"""
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('custom_project_management.on_off_value', self.on_off_value)
        params.set_param('custom_project_management.whatsapp_auth_token', self.whatsapp_auth_token or "")

    @api.model
    def get_values(self):
        """Retrieve stored values from system parameters"""
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            on_off_value=params.get_param('custom_project_management.on_off_value', default='False') == 'True',
            whatsapp_auth_token=params.get_param('custom_project_management.whatsapp_auth_token', default=""),
        )
        return res
