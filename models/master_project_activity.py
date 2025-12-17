from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ProjectActivityName(models.Model):
    _inherit = 'project.activity.name'
    #_order = 'notification_dt desc, id desc'
    _description = "ActivityMaster"

    activity_master_id = fields.Many2one("activity.master",'Activity Master')