from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta , time , date


class ApiLog(models.Model):
    _name = 'api.log'
    _description = 'API Log'

    name = fields.Char("Name")
    api_name = fields.Selection([('activity_master', 'Activity Master'),('amendment_items', 'Amendment Items'), ('bu', 'Business Unit'),('item_master', 'Item Master'),('vj_po', 'Purchase Order'),('sub_bu', 'Sub Business Unit'),('wo', 'Work Order'),('bu_hierarchy', 'Bu Hierarchy'),('inventory', 'Inventory'),('wo_amd', 'Work Order Amendment')], string="APi Name")
    create_datetime = fields.Datetime("DateTime")
    state = fields.Selection([('done', 'Done'),('failed', 'Failed'),('partial','Partial')], string="State")
    error = fields.Text("Error")
    message = fields.Text("Message")
    logs = fields.Text("Message")