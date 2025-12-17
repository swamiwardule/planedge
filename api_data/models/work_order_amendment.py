from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta , time , date
import pytz
import re
import requests
import json
import ast
import os
import configparser

# Define the path to your config file
module_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the config file
config_path = os.path.join(module_dir, '..', 'config_file.conf')

# Initialize configparser and read the file
config = configparser.ConfigParser()
config.read(config_path)

# Read values from the configuration file
workOrderAmendment = config.get('settings', 'workOrderAmendment', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)
        
class WorkOrderAmendment(models.Model):
    _name = 'work.order.amendment'
    
    woa_id = fields.Integer(string="Work Order Amendment ID")
    buId = fields.Integer(string="Bu Id")
    amendmentDocumentNumber = fields.Char(string='Amd Document No')
    documentNo = fields.Char(string='Document No')
    documentDate = fields.Char(string='Document Date')
    partyLedger = fields.Char(string='Party Ledger')
    subProjectId = fields.Char(string='Sub Project Id')
    budgetId = fields.Char(string='Budget Id')
    subject = fields.Text(string='Subject')
    scope_of_work = fields.Text(string='Scope of Work')
    amount = fields.Float(string='Amount')
    grossAmount = fields.Float(string='Gross Amount')
    netAmount = fields.Float(string='Net Amount')
    buName = fields.Char(string='Business Unit Name')
    ledgerName = fields.Char(string='Ledger Name')
    completionDate = fields.Char(string='Completion Date')
    activities_ids = fields.One2many('work.order.amendment.activity', 'woa_id', string='Activities')


    @api.model
    def action_work_order_amendment(self, timestamp):
        _logger.info("--- action_work_order_amendment --- (Time: %s)", timestamp)
        ist = pytz.timezone('Asia/Kolkata')
        aware_dt = datetime.now(ist)                      # Aware datetime in IST
        utc_naive_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)

        api_log_obj = self.env['api.log']
        woaa_obj = self.env['work.order.amendment.activity']

        log_vals = {
            'name': f'Work Order Amendment Sync - {timestamp}',
            'api_name': 'wo_amd',
            'create_datetime': utc_naive_dt,
        }

        headers = {
            "Authorization": Authorization,
            "Content-Type": ContentType,
        }

        # today_date = datetime.today().strftime('%Y-%m-%d')
        # payload = {
        #     "start_date": today_date,
        #     "end_date": today_date
        # }

        today_date = datetime.today().strftime('%Y-%m-%d')
        yesterday_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        payload = {
            "start_date": yesterday_date,
            "end_date": today_date
        }
        payload = {
            "start_date": "2025-05-01",
            "end_date": "2025-05-23"
        }

        try:
            response = requests.get(workOrderAmendment, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                existing_ids = set(self.search([]).mapped('woa_id'))

                created_count = 0
                error_count = 0

                for entry in data:
                    #_logger.error("---entry----- %s-----------", entry)
                    try:
                        details = entry.get('Activities', [])

                        if int(entry.get('Id', 0)) not in existing_ids:
                            parent_order = self.create({
                                'woa_id': entry.get('Id', 0),
                                'buId': entry.get('BUId'),
                                'documentNo': entry.get('DocumentNo'),
                                'amendmentDocumentNumber': entry.get('amendmentDocumentNumber'),
                                'documentDate': entry.get('DocumentDate'),
                                'partyLedger': entry.get('PartyLedger'),
                                'subProjectId': entry.get('SubProjectId'),
                                'subject': entry.get('Subject'),
                                'scope_of_work': entry.get('ScopeOfWork'),
                                'amount': entry.get('Amount'),
                                'grossAmount': entry.get('GrossAmount'),
                                'netAmount': entry.get('NetAmount'),
                                'buName': entry.get('BuName'),
                                'ledgerName': entry.get('LedgerName'),
                                'completionDate': entry.get('CompletionDate'),
                            })

                            for detail in details:
                                woaa_obj.create({
                                    'woa_id': parent_order.id,
                                    'businessUnit': detail.get('BusinessUnit'),
                                    'subProject': detail.get('SubProject'),
                                    'supplier': detail.get('Supplier'),
                                    'activityId': detail.get('ActivityId', ''),
                                    'budgetHead': detail.get('BudgetHead'),
                                    'description': detail.get('Description'),
                                    'amendedQnty': detail.get('AmendedQnty'),
                                    'amendedAmt': detail.get('AmendedAmt'),
                                    'amendedRate': detail.get('AmendedRate'),
                                    'uomCode': detail.get('UomCode'),
                                    'create_type_description': detail.get('CreateTypeDescription'),
                                    'newActivity': detail.get('NewActivity'),
                                })

                            created_count += 1

                    except Exception as e:
                        _logger.error("Error processing entry in action_work_order_amendment: %s. Error: %s", entry, e)
                        error_count += 1

                log_vals.update({
                    'state': 'done' if error_count == 0 else 'partial',
                    'message': f'Work Order Amendment Sync completed. Records created: {created_count}, Errors: {error_count}',
                })
                api_log_obj.sudo().create(log_vals)

                return {'status': 'success', 'message': f'Created: {created_count}, Errors: {error_count}'}
            else:
                log_vals.update({
                    'state': 'failed',
                    'message': f'Status Code: {response.status_code}. Response: {response.text}',
                })
                api_log_obj.sudo().create(log_vals)

                return {'status': 'failed', 'message': 'Failed to retrieve data from API'}

        except Exception as e:
            _logger.error("Exception during API call in action_work_order_amendment: %s", e)
            log_vals.update({
                'state': 'failed',
                'message': f'Exception during API call: {e}',
            })
            api_log_obj.sudo().create(log_vals)

            return {'status': 'failed', 'message': 'Exception occurred during data fetch'}








    # @api.model
    # def action_work_order_amendment(self, timestamp):
    #     _logger.info("---  action_workOrderAmendment -------. ""(Time: %s)", timestamp)
    #     woaa_obj = self.env['work.order.amendment.activity']
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     payload = {
    #         "start_date": "2025-01-01",
    #         "end_date": "2025-05-08"
    #     }
    #     today_date = datetime.today().strftime('%Y-%m-%d')
    #     # payload = {
    #     #     "start_date": today_date,
    #     #     "end_date": today_date
    #     # }
    #     today_date = datetime.today().strftime('%Y-%m-%d')
    #     payload = {
    #         "start_date": today_date,
    #         "end_date": today_date
    #     }
    #     # Make the GET request
    #     response = requests.get(workOrderAmendment, headers=headers,json=payload)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('woa_id'))
    #         _logger.info("--existing_ids--. %s", existing_ids)

    #         # Prepare records to create
    #         for entry in data:
    #             try:
    #                 details = entry.get('Activities', [])
    #                 #_logger.info("-details. %s", details)

    #                 # Check if the order ID already exists
    #                 if int(entry.get('Id', 0)) not in existing_ids:
    #                     # Create the parent order record
    #                     parent_order = self.create({
    #                         'woa_id': entry.get('Id', 0),
    #                         'buId': entry.get('BUId'),
    #                         'documentNo': entry.get('DocumentNo'),
    #                         'amendmentDocumentNumber':entry.get('amendmentDocumentNumber'),
    #                         'documentDate': entry.get('DocumentDate'),
    #                         'partyLedger': entry.get('PartyLedger'),
    #                         'subProjectId': entry.get('SubProjectId'),
    #                         'subject': entry.get('Subject'),
    #                         'scope_of_work': entry.get('ScopeOfWork'),
    #                         'amount': entry.get('Amount'),
    #                         'grossAmount': entry.get('GrossAmount'),
    #                         'netAmount': entry.get('NetAmount'),
    #                         'buName': entry.get('BuName'),
    #                         'ledgerName': entry.get('LedgerName'),
    #                         'completionDate': entry.get('CompletionDate'),
    #                     })
                        
    #                     # Create the child detail records linked to the parent order
    #                     for detail in details:
    #                         a = woaa_obj.create({
    #                             'woa_id': parent_order.id,  # Link to the parent order
    #                             'businessUnit': detail.get('BusinessUnit'),
    #                             'subProject': detail.get('SubProject'),
    #                             'supplier': detail.get('Supplier'),
    #                             'activityId': detail.get('ActivityId', ''),
    #                             'budgetHead': detail.get('BudgetHead'),
    #                             'description': detail.get('Description'),
    #                             'amendedQnty': detail.get('AmendedQnty'),
    #                             'amendedAmt': detail.get('AmendedAmt'),
    #                             'amendedRate': detail.get('AmendedRate'),
    #                             'uomCode': detail.get('UomCode'),
    #                             'create_type_description': detail.get('CreateTypeDescription'),
    #                             'newActivity': detail.get('NewActivity'),

    #                         })
    #                         #_logger.info("--linelinelielinelinelinelinelneline--. %s", a)


    #             except Exception as e:
    #                 _logger.error("Error processing entry action_workOrder: %s. Error: %s", entry, e)

    #         #_logger.info("--Data retrieved from API---. ""(service name: %s)", data)
    #         return {'status': 'success', 'message': 'Order and Detail Data Created Successfully'}
    #     else:
    #         _logger.info("-action_workOrder-Failed to retrieve data. Status code:-%s", response.status_code)
    #         _logger.info("--Error message--action_workOrder%s", response.text)
    #         return {'status': 'failed', 'message': 'Data not received'}
        

class WorkOrderAmendmentActivity(models.Model):
    _name = 'work.order.amendment.activity'
    _description = 'Work Order Amendment Activity'
    
    woa_id = fields.Many2one('work.order.amendment', string='Work Order Amendment')
    businessUnit = fields.Char(string='Business Unit')
    subProject = fields.Char(string='Sub Project')
    supplier = fields.Char(string='Supplier')
    activityId = fields.Integer(string='Activity ID')
    budgetHead = fields.Char(string='Budget Head')
    description = fields.Text(string='Description')
    amendedQnty = fields.Float(string='Amended Quantity')
    amendedAmt = fields.Float(string='Amended Amount')
    amendedRate = fields.Float(string='Amended Rate')
    uomCode = fields.Char(string='UOM Code')
    create_type_description = fields.Char(string='Create Type Description')
    newActivity = fields.Boolean(string='New Activity')
