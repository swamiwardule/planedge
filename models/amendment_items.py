from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta , time , date
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
amendmentItems = config.get('settings', 'AmendmentItems', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)

class AmendmentItems(models.Model):
    _name = 'amendment.items'
    _description = 'Amendment Items'
    _rec_name = "documentNo"


    documentNo = fields.Char(string="Document No", required=True)
    amendment_id = fields.Integer(string="Amendment ID")
    buId = fields.Integer(string="Business Unit ID")
    bu_description = fields.Char(string="Business Unit Description")
    documentDate = fields.Date(string="Document Date")
    ledger_id = fields.Integer(string="Ledger ID")
    ledger_description = fields.Char(string="Ledger Description")
    purchase_order_id = fields.Char(string="Purchase Order ID")
    # One2many relation to AmendmentDetails
    detail_ids = fields.One2many('amendment.details', 'amendment_item_id', string="Details")
    ItemId = fields.Integer('ItemId')

    @api.model
    def action_amendment_items(self, timestamp):
        _logger.info("--- action_amendment_items --- (time: %s)", timestamp)
        api_log_obj = self.env['api.log']
        log_vals = {
            'name': f'AmendmentItems Sync - {timestamp}',
            'api_name': 'amendment_items',
            'create_datetime': datetime.now(),
        }

        amendment_details_obj = self.env['amendment.details']
        headers = {
            "Authorization": Authorization,  # Replace with actual value
            "Content-Type": ContentType,
        }

        today_date = datetime.today().strftime('%Y-%m-%d')
        payload = {
            "startDate": today_date,
            "endDate": today_date
        }

        try:
            response = requests.get(amendmentItems, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                _logger.info("--- action_amendment_items --- (records: %s)", len(data.get('data', [])))

                for entry in data.get('data', []):
                    amendment = entry.get('amendment', {})
                    details = entry.get('details', [])
                    amendment_id = int(amendment.get('Id', 0))

                    existing_record = self.search([('amendment_id', '=', amendment_id)], limit=1)

                    if existing_record:
                        existing_record.write({
                            'buId': amendment.get('BUId'),
                            'documentNo': amendment.get('DocumentNo'),
                            'bu_description': amendment.get('BUDescription'),
                            'documentDate': amendment.get('DocumentDate'),
                            'ledger_id': amendment.get('LedgerId'),
                            'ledger_description': amendment.get('LedgerDescription'),
                            'purchase_order_id': amendment.get('PurchaseOrderId'),
                            'ItemId': amendment.get('ItemId'),
                        })
                        parent_order = existing_record
                    else:
                        parent_order = self.create({
                            'amendment_id': amendment_id,
                            'buId': amendment.get('BUId'),
                            'documentNo': amendment.get('DocumentNo'),
                            'bu_description': amendment.get('BUDescription'),
                            'documentDate': amendment.get('DocumentDate'),
                            'ledger_id': amendment.get('LedgerId'),
                            'ledger_description': amendment.get('LedgerDescription'),
                            'purchase_order_id': amendment.get('PurchaseOrderId'),
                            'ItemId': amendment.get('ItemId'),
                        })

                        for detail in details:
                            amendment_details_obj.create({
                                'amendment_item_id': parent_order.id,
                                'business_unit': detail.get('BusinessUnit'),
                                'documentNo': detail.get('DocumentNo'),
                                'documentDate': detail.get('DocumentDate'),
                                'quotation_date': detail.get('QuotationDate', ''),
                                'parent_ledger_description': detail.get('ParentLedgerDescription'),
                                'ledger_description': detail.get('LedgerDescription'),
                                'gstin': detail.get('Gstin'),
                                'hsn': detail.get('Hsn'),
                                'pos_state_description': detail.get('PosStateDescription'),
                                'code': detail.get('Code'),
                                'description': detail.get('Description'),
                                'uom_code': detail.get('UomCode'),
                                'quantity': detail.get('Quantity'),
                                'rate': detail.get('Rate'),
                                'amount': detail.get('Amount'),
                            })

                message = f"action_amendment_items ---success-----records processed: {len(data.get('data', []))}"
                log_vals.update({'state': 'done', 'message': message})
                api_log_obj.sudo().create(log_vals)

                return {'status': 'success', 'message': message}

            else:
                error_msg = f"API response error. Status code: {response.status_code}, Response: {response.text}"
                _logger.error(error_msg)
                log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Data fetch failed from amendmentItems API'})
                api_log_obj.sudo().create(log_vals)

                return {'status': 'failed', 'message': 'Data not received'}

        except Exception as e:
            error_msg = f"Exception during API sync: {str(e)}"
            _logger.exception(error_msg)
            log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Exception during amendmentItems API call'})
            api_log_obj.sudo().create(log_vals)

            return {'status': 'failed', 'message': 'Exception occurred during sync'}

    # @api.model
    # def action_amendment_items(self, timestamp):
    #     _logger.info("--- action_amendment_items --- (time: %s)", timestamp)
    #     api_log_obj = self.env['api.log']
    #     log_vals = {
    #         'name': f'ActivityMaster Sync - {timestamp}',
    #         'api_name': 'activity_master',
    #         'create_datetime': datetime.now(),
    #         'api_name':'activity_master',
    #     }
    #     amendment_details_obj = self.env['amendment.details']
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token
    #         "Content-Type": ContentType,
    #     }
    #     today_date = datetime.today().strftime('%Y-%m-%d')
    #     payload = {
    #         "startDate": today_date,
    #         "endDate": today_date
    #     }
    #     # payload = {
    #     #     "startDate": '2025-04-15',
    #     #     "endDate": '2025-05-07'
    #     # }

    #     # Make the GET request
    #     response = requests.get(amendmentItems, headers=headers, json=payload)
    #     #_logger.info("---  action_amendment_items--. ""(data: %s)", len(data.get('data', [])))

    #     if response.status_code == 200:
    #         data = response.json()
    #         _logger.info("---  action_amendment_items--. ""(data: %s)", len(data.get('data', [])))

    #         for entry in data.get('data', []):
    #             #try:
    #             if 1:
    #                 amendment = entry.get('amendment', {})
    #                 details = entry.get('details', [])
    #                 amendment_id = int(amendment.get('Id', 0))

    #                 # Check if amendment exists
    #                 existing_record = self.search([('amendment_id', '=', amendment_id)], limit=1)

    #                 if existing_record:
    #                     # Update the parent record
    #                     existing_record.write({
    #                         'buId': amendment.get('BUId'),
    #                         'documentNo': amendment.get('DocumentNo'),
    #                         'bu_description': amendment.get('BUDescription'),
    #                         'documentDate': amendment.get('DocumentDate'),
    #                         'ledger_id': amendment.get('LedgerId'),
    #                         'ledger_description': amendment.get('LedgerDescription'),
    #                         'purchase_order_id': amendment.get('PurchaseOrderId'),
    #                         'ItemId': amendment.get('ItemId'),

    #                     })
    #                     parent_order = existing_record
    #                     # Delete old child records
    #                     #parent_order.detail_ids.unlink()
    #                 else:
    #                     # Create the parent record
    #                     parent_order = self.create({
    #                         'amendment_id': amendment_id,
    #                         'buId': amendment.get('BUId'),
    #                         'documentNo': amendment.get('DocumentNo'),
    #                         'bu_description': amendment.get('BUDescription'),
    #                         'documentDate': amendment.get('DocumentDate'),
    #                         'ledger_id': amendment.get('LedgerId'),
    #                         'ledger_description': amendment.get('LedgerDescription'),
    #                         'purchase_order_id': amendment.get('PurchaseOrderId'),
    #                         'ItemId': amendment.get('ItemId'),

    #                     })

    #                     # Create child records (after update or create)
    #                     for detail in details:
    #                         amendment_details_obj.create({
    #                             'amendment_item_id': parent_order.id,  # Link to the parent
    #                             'business_unit': detail.get('BusinessUnit'),
    #                             'documentNo': detail.get('DocumentNo'),
    #                             'documentDate': detail.get('DocumentDate'),
    #                             'quotation_date': detail.get('QuotationDate', ''),
    #                             'parent_ledger_description': detail.get('ParentLedgerDescription'),
    #                             'ledger_description': detail.get('LedgerDescription'),
    #                             'gstin': detail.get('Gstin'),
    #                             'hsn': detail.get('Hsn'),
    #                             'pos_state_description': detail.get('PosStateDescription'),
    #                             'code': detail.get('Code'),
    #                             'description': detail.get('Description'),
    #                             'uom_code': detail.get('UomCode'),
    #                             'quantity': detail.get('Quantity'),
    #                             'rate': detail.get('Rate'),
    #                             'amount': detail.get('Amount'),
    #                         })
    #                     message = f"action_amendment_items ---success-----data created len = {len(data)}"

    #                     log_vals.update({
    #                             'state': 'done',
    #                             'message': message,
    #                         })
    #                     api_log_obj.sudo().create(log_vals)

    #             # except Exception as e:
    #             #     _logger.error("Error processing entry: %s. Error: %s", entry, e)
    #         _logger.info("---  action_amendment_items ---sucess----. ""(data: %s)", len(data))

    #         return {'status': 'success', 'message': 'Order and Detail Data Created/Updated Successfully'}
    #     else:
    #         _logger.error("Failed to retrieve data. Status code: %s", response.status_code)
    #         _logger.error("Error message: %s", response.text)
    #         return {'status': 'failed', 'message': 'Data not received'}


    # @api.model
    # def action_amendment_items(self, timestamp):
    #     _logger.info("---  action_amendment_items -------. ""(time: %s)", timestamp)
    #     amendment_details_obj = self.env['amendment.details']
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # payload = {
    #     #     "startDate": "2024-10-01",
    #     #     "endDate": "2024-10-02"
    #     # }
    #     today_date = datetime.today().strftime('%Y-%m-%d')
    #     payload = {
    #         "startDate": today_date,
    #         "endDate": today_date
    #     }
    #     # Make the GET request
    #     response = requests.get(amendmentItems, headers=headers,json=payload)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('amendment_id'))
    #         _logger.info("--existing_ids--. ""(%s)", existing_ids)

    #         # Prepare records to create
    #         for entry in data.get('data', []):
    #             try:
    #                 amendment = entry.get('amendment', {})
    #                 details = entry.get('details', [])
                    
    #                 # Check if the order ID already exists
    #                 if int(amendment.get('Id', 0)) not in existing_ids:
    #                     # Create the parent order record
    #                     parent_order = self.create({
    #                         'amendment_id': amendment.get('Id', 0),
    #                         'buId': amendment.get('BUId'),
    #                         'documentNo': amendment.get('DocumentNo'),
    #                         'bu_description': amendment.get('BUDescription'),
    #                         'documentDate': amendment.get('DocumentDate'),
    #                         'ledger_id': amendment.get('LedgerId'),
    #                         'ledger_description': amendment.get('LedgerDescription'),
    #                         'purchase_order_id': amendment.get('PurchaseOrderId'),
    #                     })
                        
    #                     # Create the child detail records linked to the parent order
    #                     for detail in details:
    #                         amendment_details_obj.create({
    #                             'amendment_item_id': parent_order.id,  # Link to the parent order
    #                             'business_unit': detail.get('BusinessUnit'),
    #                             'documentNo': detail.get('DocumentNo'),
    #                             'documentDate': detail.get('DocumentDate'),
    #                             'quotation_date': detail.get('QuotationDate', ''),
    #                             'parent_ledger_description': detail.get('ParentLedgerDescription'),
    #                             'ledger_description': detail.get('LedgerDescription'),
    #                             'gstin': detail.get('Gstin'),
    #                             'hsn': detail.get('Hsn'),
    #                             'pos_state_description': detail.get('PosStateDescription'),
    #                             'code': detail.get('Code'),
    #                             'description': detail.get('Description'),
    #                             'uom_code': detail.get('UomCode'),
    #                             'quantity': detail.get('Quantity'),
    #                             'rate': detail.get('Rate'),
    #                             'amount': detail.get('Amount'),
    #                         })

    #             except Exception as e:
    #                 _logger.error(" action_amendment_items Error processing entry: %s. Error: %s", entry, e)

    #         #_logger.info("--Data retrieved from API---. ""(service name: %s)", data)
    #         return {'status': 'success', 'message': 'Order and Detail Data Created Successfully'}
    #     else:
    #         _logger.info("- action_amendment_items-Failed to retrieve data. Status code:-. ""(%s)", response.status_code)
    #         _logger.info("-action_amendment_items -Error message--. ""(%s)", response.text)
    #         return {'status': 'failed', 'message': 'Data not received'}

class AmendmentDetails(models.Model):
    _name = 'amendment.details'
    _description = 'Amendment Details'

    amendment_item_id = fields.Many2one('amendment.items', string="Amendment", ondelete='cascade')
    business_unit = fields.Char(string="Business Unit")
    documentNo = fields.Char(string="Document No")
    documentDate = fields.Date(string="Document Date")
    quotation_date = fields.Date(string="Quotation Date")
    parent_ledger_description = fields.Char(string="Parent Ledger Description")
    ledger_description = fields.Char(string="Ledger Description")
    gstin = fields.Char(string="GSTIN")
    hsn = fields.Char(string="HSN")
    pos_state_description = fields.Char(string="POS State Description")
    code = fields.Char(string="Code")
    description = fields.Text(string="Description")
    uom_code = fields.Char(string="UOM Code")
    quantity = fields.Float(string="Quantity") # actual qty
    pending_qty = fields.Float(string="Pending Qty") # pending qty
    submitted_qty = fields.Float(string="Subimitted Qty") # submitted qty
    rate = fields.Float(string="Rate")
    amount = fields.Float(string="Amount")
    state = fields.Selection(
    [('draft', 'Draft'),('inprogress', 'In Progress'), ('done', 'Done')],
    default='draft',
    string="State",
    readonly=False)

    status = fields.Selection([
        ('new', 'New'),
        ('partial', 'Partially Submitted'),
        ('completed', 'Completed')
    ], default='new')
