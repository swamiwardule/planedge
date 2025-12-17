from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ProjectActivityName(models.Model):
    _inherit = 'project.activity.name'
    #_order = 'notification_dt desc, id desc'
    _description = "Project Activity NAme"

    construction_activity_group_id = fields.Many2one('construction.activity.group','Activity Group')
    construction_activity_group_ids = fields.Many2many(
        'construction.activity.group',    # The target model
        '_activity_group_rel',  # The relationship table name
        'project_activity_id',                    # Foreign key in the relation table pointing to vjd.inventory
        'activity_group_id',               # Foreign key in the relation table pointing to construction.activity.group
        string='Activity Group(s)'           # The label for the field
    )
    common_activity_group_ids = fields.Many2many(
        'construction.activity.group',    # The target model
        '_activity_group_rel_com',  # The relationship table name
        'project_activity_id_com',                    # Foreign key in the relation table pointing to vjd.inventory
        'activity_group_id_com',               # Foreign key in the relation table pointing to construction.activity.group
        string='Common Activity Group(s)'           # The label for the field
    )
    development_activity_group_ids = fields.Many2many(
        'construction.activity.group',    # The target model
        '_activity_group_rel_dev',  # The relationship table name
        'project_activity_id',                    # Foreign key in the relation table pointing to vjd.inventory
        'activity_group_id',               # Foreign key in the relation table pointing to construction.activity.group
        string='Development Activity Group(s)'           # The label for the field
    )