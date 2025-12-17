from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ProjectInfo(models.Model):
    _inherit = 'project.info'
    #_order = 'notification_dt desc, id desc'
    _description = "Project Info"

    businessUnit = fields.Many2one('business.unit','Business Unit',tracking=True)


