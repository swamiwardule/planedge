from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging
import requests
import json
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class HqiEmail(models.Model):
    _name = 'hqi.email'
    _description = "HQI Email"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    project = fields.Char(string="Project")
    building = fields.Char(string="Building")
    flat = fields.Char("Flat No.")
    project_incharge_id = fields.Many2one("res.users", string="Project In-Charge")
    email_to = fields.Char("Email To")
    datetime = fields.Datetime(string="Date and Time", default=lambda self: fields.Datetime.now())
    state = fields.Selection([('draft', 'Draft'),('sent', 'Sent'),('failed', 'Failed')], string="State", default='draft')
    error = fields.Text(string="Error Message")
    pdf_report = fields.Binary("Inspection Report", attachment=True)

    def action_send_email(self):
        for rec in self:
            try:
                template = rec.env.ref("hqi_email.email_template_hqi", raise_if_not_found=False)
                email_values = {}

                if rec.email_to:
                    email_values["email_to"] = rec.email_to

                if template:
                    template.send_mail(rec.id, force_send=True, email_values=email_values)
                else:
                    # Fallback if no template
                    mail_vals = {
                        "subject": _("HQI Inspection – %s, %s, %s") % (rec.project or "", rec.building or "", rec.flat or ""),
                        "body_html": "<p>Please find the attached HQI Inspection Report.</p>",
                        "email_to": rec.email_to,
                        "attachment_ids": [],
                    }

                    # Attach PDF if available
                    if rec.pdf_report:
                        attachment = self.env['ir.attachment'].create({
                            'name': f"HQI_Report_{rec.flat or rec.id}.pdf",
                            'type': 'binary',
                            'datas': rec.pdf_report,
                            'res_model': 'hqi.email',
                            'res_id': rec.id,
                            'mimetype': 'application/pdf',
                        })
                        mail_vals["attachment_ids"] = [(6, 0, [attachment.id])]

                    mail = rec.env["mail.mail"].create(mail_vals)
                    mail.send()

                rec.state = 'sent'

            except Exception as e:
                rec.state = 'failed'
                rec.error = str(e)
                _logger.error("Error sending email for HQI Email ID %s: %s", rec.id, str(e))
        return True


    # def action_send_email(self):

    #     try:
    #         for rec in self:
    #             template = rec.env.ref(
    #                 "hqi_email.email_template_hqi",  # <-- updated XML ID
    #                 raise_if_not_found=False,
    #             )
    #             if not template:
    #                 if not rec.email_to:
    #                     raise UserError(_("Please set 'Email To' before sending."))
    #                 mail_vals = {
    #                     "subject": _("HQI Inspection – %s, %s, %s") % (rec.project or "", rec.building or "", rec.flat or ""),
    #                     "body_html": _(
    #                 """
    #                 <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
    #                     <p>Dear %(incharge)s,</p>

    #                     <p>We would like to inform you that the HQI (Home Quality Inspection) has been successfully completed for the following unit:</p>

    #                     <p><b>Project Name:</b> %(project)s</p>
    #                     <p><b>Building:</b> %(building)s</p>
    #                     <p><b>Flat No.:</b> %(flat)s</p>

    #                     <p>Please find the attached PDF document containing the inspection observations for your review and necessary action.</p>

    #                     <p>Should you have any questions or require further clarification, feel free to contact us.</p>

    #                     <p>Best regards,<br/>
    #                     <b>Team HQI</b><br/>
    #                     Vilas Javdekar Developers</p>
    #                 </div>
    #                 """
    #             ) % {
    #                 "incharge": rec.project_incharge_id.name or "Project In-Charge",
    #                 "project": rec.project or "",
    #                 "building": rec.building or "",
    #                 "flat": rec.flat or "",
    #             },

    #                 "email_to": rec.email_to,
    #             }
    #             mail = rec.env["mail.mail"].create(mail_vals)
    #             mail.send()
    #             rec.state = 'sent'
    #         else:
    #             email_values = {}
    #             if rec.email_to:
    #                 email_values["email_to"] = rec.email_to
    #             template.send_mail(rec.id, force_send=True, email_values=email_values)
    #     except Exception as e:
    #         self.state = 'failed'
    #         _logger.error("Error sending email: %s", str(e))
    #         self.error = str(e)
    #         # raise UserError(_("Failed to send email: %s") % str(e))
    #     return True


    