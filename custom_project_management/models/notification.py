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
import json

class ResUsers(models.Model):
    _inherit = "res.users"

    player_line_ids = fields.One2many('app.notification', 'res_user_id', string='Player ID')


class AppNotificationLog(models.Model):
    _name = 'app.notification.log'
    _rec_name = "res_user_id"
    _order = 'notification_dt desc, id desc'
    _description = "AppNotificationLog"


    title = fields.Text('Title')
    notification_dt = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    read_unread = fields.Boolean('Is Read')
    res_user_id = fields.Many2one('res.users','To')
    project_info_id = fields.Many2one('project.info','Project')
    activity_type_id = fields.Many2one('project.activity.type','Activity Type')
    mi_id = fields.Many2one('material.inspection','Material Inspection')
    observation_id = fields.Many2one('site.visit.location.observation','Observation')
    tower_id = fields.Many2one('project.tower','Tower')
    player_id = fields.Char("Player Id")
    hide_notification = fields.Boolean('Hide Notification')
    message = fields.Text("Message")
    table_id = fields.Char("Checklist Id")
    seq_no = fields.Char("Seq No")
    status = fields.Selection([('sent', 'Sent'),('failed', 'Failed')],string="status")
    #overall_checklist_status = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    #('approver_reject','Approver Rejected')],default='approve',string="Overall Checklist Status",readonly=1,store=True)
    checklist_status=fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    ('approver_reject','Approver Rejected')],default='draft',string="Checklist Status",readonly=1,store=True)
    checklist_status_two = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    ('approver_reject','Approver Rejected')],default='draft',string="Checklist Status Two",readonly=1,store=True)
    detail_line = fields.Selection([('mi', 'MI'),('wi', 'WI'),('hqi','HQI')],string="Detail Line Value")
    hqi_state = fields.Selection([
    ('in_review_by_checker', 'In Review by Checker'),  # Checker reviewing first time
    ('correction_by_maker', 'Correction by Maker'),    # Maker correcting
    ('re_review_by_checker', 'Re-review by Checker'),  # Checker re-checking after correction
    ('completed', 'Completed'),                        # Finalized
    ],string="HQI State")
    
    @api.model
    def action_hide_notification(self):
        _logger.info("===========action_hide_notification===========called")
        active_ids = self.env.context.get('active_ids')

        if not active_ids:
            _logger.warning("No records selected for Hide.")
            return

        records = self.browse(active_ids).filtered(
            lambda r: r.activity_type_id and r.activity_type_id.status == 'approve')
        if records:
            records.write({'hide_notification': True})

    
    def hide_checker_notifications_on_approval(self, checklist_id):
        """
        Hides notifications for checkers related to a specific checklist once it's approved.
        """
        _logger.info("Running hide_checker_notifications_on_approval for checklist ID: %s", checklist_id)

        logs_to_hide = self.search([
            ('table_id', '=', str(checklist_id)),  # assuming checklist ID is stored in table_id
            ('hide_notification', '=', False),
            '|',
            ('checklist_status', '=', 'approve'),
            ('checklist_status_two', '=', 'approve'),
        ])

        if logs_to_hide:
            logs_to_hide.write({'hide_notification': True})
            _logger.info("Notifications hidden for logs: %s", logs_to_hide.ids)
        else:
            _logger.info("No notifications found to hide for checklist ID: %s", checklist_id)
    
    def get_users_notification_details(self, user_id):
        notifications = self.search([
            ('res_user_id', '=', user_id),
            ('status', '=', 'sent'),
            ('hide_notification', '=', False)
        ])

        #('res_user_id', '=', self.env.user.id)
        data = []
        for notification in notifications:
            try:
                visit_id = False
                flat_id = False
                if notification.observation_id:
                    obs = notification.observation_id.site_visit_location_id
                    visit_id = obs.flat_site_visit_id.id or False
                    flat_id = obs.flat_id.id or False
                
                ndata = {
                    'mi_id': notification.mi_id.id if notification.mi_id else False,
                    'activity_type_id': notification.activity_type_id.id if notification.activity_type_id else False,
                    'checklist_status_two': notification.checklist_status_two or 'approve',
                    'checklist_status': notification.checklist_status or 'approve',
                    'tower_id': notification.tower_id.id if notification.tower_id else '',
                    'project_id': notification.project_info_id.id if notification.project_info_id else '',
                    'visit_id': visit_id,
                    'flat_id': flat_id,
                    'detail_line': notification.detail_line or '',
                    'seq_no': notification.seq_no or 0,
                    'id': notification.id,
                    'title': notification.title,
                    'notification_dt': str(notification.notification_dt),
                    'redirect_id': notification.table_id or '',
                    'location_id': notification.observation_id.site_visit_location_id.id if notification.observation_id else False,
                    #'observation_id': notification.observation_id.id if notification.observation_id else False

                }
            except Exception as e:
                _logger.info("---get_users_notification_details---,%s",str(e))
            data.append(ndata)

        return data
    
class AppNotification(models.Model):
    _name = 'app.notification'
    _order = 'id desc'
    _description = "AppNotification"

    notification_dt = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    res_user_id = fields.Many2one('res.users','Res Users')
    player_id = fields.Char("Player Id")
    datetime = fields.Datetime('Date Time',default=lambda self: fields.Datetime.now())
    table_id = fields.Char("Id")

    def hqi_send_push_notification(self, title, player_ids, message, user_ids, insp_value, obj):
        _logger.info("----- Sending Push Notification -----")
        _logger.info("Title: %s, Player IDs: %s, Message: %s, User IDs: %s", title, player_ids, message, user_ids)

        NotificationLog = self.env['app.notification.log']

        # OneSignal config — ideally move these to system parameters or ir.config_parameter
        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        # API endpoint
        url = "https://onesignal.com/api/v1/notifications"

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {rest_api_key}"
            }

            data = {
                "app_id": app_id,
                "include_player_ids": player_ids,
                "contents": {"en": message},
                "headings": {"en": title},
            }

            response = requests.post(url, data=json.dumps(data), headers=headers)

            status = 'sent' if response.status_code == 200 else 'failed'
            log_title = title if response.status_code == 200 else f"{title} | status: {response.status_code}"

            for user_id, player_id in zip(user_ids, player_ids):
                NotificationLog.sudo().create({
                    'observation_id': obj.id,
                    'detail_line': insp_value,
                    'status': status,
                    'hqi_state': obj.state,
                    'title': log_title,
                    'res_user_id': user_id,
                    'player_id': player_id,
                    'message': message,
                    'table_id': obj.id,
                    'project_info_id': obj.site_visit_location_id.flat_id.project_id.id or False,
                    'tower_id': obj.site_visit_location_id.flat_id.tower_id.id or False,
                    'seq_no': obj.sequence or False
                })

            return True

        except Exception as e:
            _logger.exception("Failed to send push notification: %s", str(e))
            for user_id, player_id in zip(user_ids, player_ids):
                NotificationLog.sudo().create({
                    'observation_id': obj.id,
                    'detail_line': insp_value,
                    'status': 'error',
                    'title': f"{title} | exception: {str(e)}",
                    'res_user_id': user_id,
                    'player_id': player_id,
                    'message': message,
                    'table_id': obj.id,
                    'project_info_id': '',
                    'tower_id': '',
                })
            return False

    def send_push_notification(self,title,player_ids,message,user_ids,seq_no,insp_value,obj):
        # OneSignal API endpoint
        _logger.info("-----send_push_notification------,%s,%s,%s,%s",title,player_ids,message,user_ids)
        app_log_obj = self.env['app.notification.log']
        ck_status = ck_status_two = ''
        try:
            #onesignal_url = 'https://dashboard.onesignal.com/'
            project_id = tower_id = ''
            activity_type_id = False
            mi_id = False
            # For WI
            #_logger.info("--objobjobjobjobj---,%s",str(obj))

            try:
                if obj:
                    if obj.project_id:
                        project_id = obj.project_id.id
                    if obj.tower_id:
                        tower_id = obj.tower_id.id
                    ck_status = obj.status or ''
                    ck_status_two = obj.type_status or ''
                    activity_type_id = obj.id

            except:
                pass
            # For MI
            try:
                if obj:
                    if obj.project_info_id:
                        project_id = obj.project_info_id.id
                    if obj.tower_id:
                        tower_id = obj.tower_id.id
                    ck_status = obj.status or ''
                    ck_status_two = obj.mi_status or ''
                    mi_id = obj.id
 
            except:
                pass
            
            app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
            rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

            # Notification contents
        
            # Data to send in the notification
            data = {
                "app_id": app_id,
                "include_player_ids": [player_ids[0]],
                "contents": {"en": message},
                "headings": {"en": title},
            }

            # Convert data to JSON
            data_json = json.dumps(data)

            # URL for OneSignal REST API
            url = "https://onesignal.com/api/v1/notifications"

            # Headers for the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {rest_api_key}"
            }

            # Send the notification
            response = requests.post(url, data=data_json, headers=headers)

            if response.status_code == 200:
                
                for user_id ,player_id in zip(user_ids , player_ids):
                    app_log_obj.sudo().create({'mi_id':mi_id,'activity_type_id':activity_type_id,'detail_line':insp_value,'seq_no':seq_no,'status':'sent','title':title,'res_user_id':user_id,'player_id':player_id,'message':message,'table_id':obj.id,'project_info_id':project_id,'tower_id':tower_id,'checklist_status':ck_status,'checklist_status_two':ck_status_two})
                
                try:
                    if activity_type_id:
                        rec = app_log_obj.search([('activity_type_id','=',activity_type_id)])
                        if rec:
                            rec.write({'checklist_status':ck_status})
                except Exception as e:
                    _logger.info("---activity_type_idactivity_type_id exception notification-----,%s",str(e))
                    pass

                try:
                    if mi_id:
                        rec = app_log_obj.search([('mi_id','=',mi_id)])
                        if rec:
                            rec.write({'checklist_status':ck_status})
                except Exception as e:
                    _logger.info("---mi_idmi_idmi_idmi_id exception notification-----,%s",str(e))
                    pass


                return True
            else:
                for user_id ,player_id in zip(user_ids , player_ids):
                    app_log_obj.sudo().create({'mi_id':mi_id,'activity_type_id':activity_type_id,'detail_line':insp_value,'seq_no':seq_no,'status':'failed','title':title +' status code : '+str(response.status_code),'res_user_id':user_id,'player_id':player_id,'message':message,'table_id':obj.id,'project_info_id':project_id,'tower_id':tower_id,'checklist_status':ck_status,'checklist_status_two':ck_status_two})
                return True
        
        except Exception as e:
            _logger.info("---exception--------,%s",str(e))
            pass
           
    @api.model
    def updateDetailsOfOneSignal(self, domain=None, fields=None, limit=None, userId=None,openId=None,id=None,token=None,context=None):
        try:
            #self.env['res.users'].sudo().create({'res_user_id':userId,'player_id':id})
            user_record = self.env['res.users'].browse(userId)
            if user_record:
                child_records = [(0, 0, {'player_id': id})]
                user_record.write({
            'player_line_ids': child_records,
        })
                
        except Exception as ex:
            _logger.info("---exception--------,%s",str(ex))

            self.env['error.log'].sudo().create({'model':'onesignal.notification','method_name':'updateDetailsOfOneSignal','datetime':datetime.now(),'error':str(ex)})
        response = {
            "status": 200,
            "message": "Meeting status updated successfully!"
        }
        return response

   
