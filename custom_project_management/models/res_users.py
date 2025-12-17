from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_key = fields.Char(string='API Key', readonly=True, copy=False)
