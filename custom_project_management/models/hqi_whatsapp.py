from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
import base64
import re
import requests
import json
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class HqiWhatsappLog(models.Model):
    _name = 'hqi.whatsapp.log'
    _description = "HQI Whatsapp"

    project = fields.Char("Project")
    tower = fields.Char("Tower")
    unit = fields.Char("Unit")
    message = fields.Text(string="Message")
    datetime = fields.Datetime(string="Date and Time", default=lambda self: fields.Datetime.now())
    state = fields.Selection([('draft', 'Draft'),('sent', 'Sent'),('failed', 'Failed')], string="State", default='draft')
    from_user = fields.Many2one('res.users', string="From User")
    to_user = fields.Many2one('res.users', string="To User")
    error = fields.Text(string="Error")
    response = fields.Text(string="Response")

    def send_checker_ticket_message(self):
        """Send WhatsApp message via Quality App API"""

        # Get token from system parameters
        token = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.whatsapp_auth_token')
        if not token:
            self.error = "API Authorization Token not set. Please configure it in Settings."
            return
            #ise ValueError("API Authorization Token not set. Please configure it in Settings.")

        url = "https://api.vjerp.com/api/qualityAppCheckerTicket"

        # Build dynamic message
        message_text = (
            f"Hey {self.to_user.name},\n"
            f"📍 {self.project} | {self.tower} | Flat {self.unit}\n"
            f"✅ All points have been resolved.\n"
            f"🏠 Flat is now resubmitted for your review.\n"
            f"Please check and let us know if anything else is needed."
        )
        self.message = message_text

        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        payload = {
            "message": message_text
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                self.state = 'sent'
                self.response = str(response)
                return {
                    "status": "success",
                    "message": result.get("message", "Message sent successfully")
                }
            else:
                self.state = 'failed'
                self.error = str(response)
                return {
                    "status": "error",
                    "message": result.get("message", "Failed to send message")
                }

        except Exception as e:
            self.state = 'failed'
            self.error = str(e)
            return {
                "status": "error",
                "message": str(e)
            }