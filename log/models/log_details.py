from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
import random
from datetime import date
import datetime
from datetime import datetime, timedelta , time
from dateutil import parser
import re
import requests
import pytz


class ProjectCheckTempLog(models.Model):
    _name = 'project.checklist.template.log'
    _description = "ProjectCheckTempLog"


    title = fields.Text('Title')
    project_id = fields.Many2one("project.info",'Project')
    user_id = fields.Many2one('res.users','User')
    checklist_template_id = fields.Many2one('project.checklist.template','Project Checklist Template Name')
    is_pass = fields.Selection([('yes', 'Yes'),('no', 'No'),('nop', 'Not Applicable')],string="status")
    role = fields.Selection([('checker', 'Checker'),('maker', 'Maker'),('approver', 'Approver'),('manger', 'Manager'),('admin', 'Admin')],string="Role")
    activity_type_id = fields.Many2one('project.activity.type')
    reason = fields.Text("Reason")
    seq_no = fields.Char("Seq No",store=True)
    image_ids = fields.One2many("project.checklist.line.images",'checklist_line_id',string="Images")


class ProjectCheckLineLog(models.Model):
    _name = 'project.checklist.line.log'
    _rec_name = 'datetime'
    _order = 'id desc'
    _description = "ProjectCheckLineLog"


    title = fields.Text('Title')
    datetime = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    project_id = fields.Many2one("project.info",'Project')
    user_id = fields.Many2one('res.users','User')
    checklist_template_id = fields.Many2one('project.checklist.template','Project Checklist Template Name')
    mi_id = fields.Many2one('material.inspection')
    mi_line_id = fields.Many2one('material.inspection.line')
    checklist_line_log_line = fields.One2many('project.checklist.line.log.line','project_checklist_line_log_id')

    is_pass = fields.Selection([('yes', 'Yes'),('no', 'No'),('nop', 'Not Applicable')],string="status")
    role = fields.Selection([('checker', 'Checker'),('maker', 'Maker'),('approver', 'Approver'),('manger', 'Manager'),('admin', 'Admin')],string="Role")
    activity_type_id = fields.Many2one('project.activity.type')
    reason = fields.Text("Reason")
    seq_no = fields.Char("Seq No",store=True)
    overall_remarks = fields.Char()
    line_id = fields.Integer()
    #image_ids = fields.One2many("project.checklist.line.images",'checklist_line_id',string="Images")
    #log_image_ids = fields.Many2many(,string="Images")
    image_ids = fields.Many2many('ir.attachment', string='Images', domain=[('mimetype', 'ilike', 'image')])
    status=fields.Selection([('draft','Draft'),
                            ('submit','Submit'),
                            ('checked','Checked'),
                            ('approve','Approved'),('checker_reject','Checker Rejected'),
                            ('approver_reject','Approver Rejected')],default='draft',string="Status")


class ProjectCheckLineLogLine(models.Model):
    _name = 'project.checklist.line.log.line'
    _description = "ProjectCheckLineLogLine"


    project_checklist_line_log_id = fields.Many2one('project.checklist.line.log')
    url = fields.Char('Url')