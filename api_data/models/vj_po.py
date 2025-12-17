from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta , time , date
import pytz
from collections import defaultdict
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
purchaseOrder = config.get('settings', 'purchaseOrder', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)
        
class PurchaseOrder(models.Model):
    _name = 'vj.purchase.order'
    _rec_name = 'pid'

    pid = fields.Integer("Purchase Order ID")
    buId = fields.Integer("Bu Id")
    businessUnitDescription = fields.Char('Business Unit Description')
    documentNo = fields.Char('Document No')
    documentDate = fields.Char('Document Date')
    ledgerId = fields.Integer("Ledger Id")
    ledgerDescription = fields.Char('Ledger Description')
    basicAmount = fields.Float(string="Basic Amount")
    amount = fields.Float(string="Amount")
    remarks = fields.Char('Remarks')
    advanceAmount = fields.Float(string="Advance Amount")
    purchase_order_line_ids = fields.One2many('vj.purchase.order.line','poid')
    vj_po_product_detail_line_ids = fields.One2many('vj.po.product.details','poid')
    is_po_completed = fields.Boolean(string='Is PO Completed', default=False)
    po_status = fields.Selection([('draft', 'Draft'),
                                  ('inprogress', 'In Progress'),
                                  ('done', 'Done')],
                                 string='Status', default='draft')
    
    @api.model
    def action_vjpo(self, timestamp):
        _logger.info("---  action_vjpo -------. (%s)", timestamp)

        api_log_obj = self.env['api.log']
        record_created = 0
        ist = pytz.timezone('Asia/Kolkata')
        aware_dt = datetime.now(ist)                      # Aware datetime in IST
        utc_naive_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)
        log_vals = {
            'name': f'VJPO Sync - {timestamp}',
            'api_name': 'vj_po',
            'create_datetime': utc_naive_dt,
        }

        vj_pol_obj = self.env['vj.purchase.order.line']
        headers = {
            "Authorization": Authorization,
            "Content-Type": ContentType,
        }

        # today_date = datetime.today().strftime('%Y-%m-%d')
        # payload = {
        #     "startDate": today_date,
        #     "endDate": today_date
        # }
        today_date = datetime.today().strftime('%Y-%m-%d')
        yesterday_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        payload = {
            "startDate": yesterday_date,
            "endDate": today_date
        }

        payload = {
            "startDate": "2025-05-10",
            "endDate": "2025-05-23"
        }

        response = requests.get(purchaseOrder, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            existing_ids = set(self.search([]).mapped('pid'))
            _logger.info("--existing_ids--. (%s)", len(existing_ids))

            for entry in data.get('data', []):
                try:
                    order_data = entry.get('order', {})
                    details = entry.get('details', [])
                    order_id = int(order_data.get('Id', 0))

                    if order_id not in existing_ids:
                        record_created +=1
                        parent_order = self.create({
                            'pid': order_id,
                            'buId': order_data.get('BUId'),
                            'businessUnitDescription': order_data.get('BusinessUnitDescription'),
                            'documentNo': order_data.get('DocumentNo'),
                            'documentDate': order_data.get('DocumentDate'),
                            'ledgerId': order_data.get('LedgerId'),
                            'ledgerDescription': order_data.get('LedgerDescription'),
                            'basicAmount': order_data.get('BasicAmount'),
                            'amount': order_data.get('Amount'),
                            'remarks': order_data.get('Remarks'),
                            'advanceAmount': order_data.get('AdvanceAmount'),
                        })

                        detail_records = []
                        for detail in details:
                            detail_records.append((0, 0, {
                                'supplier': detail.get('Supplier'),
                                'code': detail.get('Code'),
                                'description': detail.get('Description'),
                                'longDescription': detail.get('LongDescription', ''),
                                'uomCode': detail.get('UomCode'),
                                'quantity': detail.get('Quantity'),
                                'rate': detail.get('Rate'),
                                'amount': detail.get('Amount'),
                                'subProject': detail.get('SubProject'),
                                'budgetHead': detail.get('BudgetHead'),
                                'serialNo': detail.get('SerialNo'),
                                'ItemId': detail.get('ItemId'),
                            }))

                        if detail_records:
                            parent_order.write({'purchase_order_line_ids': detail_records})
                    # else:
                    #     parent_order = self.search([('pid', '=', order_id)], limit=1)
                    #     if parent_order:
                    #         parent_order.write({
                    #             'buId': order_data.get('BUId'),
                    #             'businessUnitDescription': order_data.get('BusinessUnitDescription'),
                    #             'documentNo': order_data.get('DocumentNo'),
                    #             'documentDate': order_data.get('DocumentDate'),
                    #             'ledgerId': order_data.get('LedgerId'),
                    #             'ledgerDescription': order_data.get('LedgerDescription'),
                    #             'basicAmount': order_data.get('BasicAmount'),
                    #             'amount': order_data.get('Amount'),
                    #             'remarks': order_data.get('Remarks'),
                    #             'advanceAmount': order_data.get('AdvanceAmount'),
                    #         })

                except Exception as e:
                    _logger.error("Error processing order ID %s: %s", order_id, str(e))

            _logger.info("--Data retrieved from API---. (data: %s,Records Created %s)", len(data.get('data', [])),str(record_created))

            log_vals.update({
                'state': 'done',
                'message': f'action_vjpo ---success-----data created len = {record_created}',
            })
            api_log_obj.sudo().create(log_vals)

            return {'status': 'success', 'message': 'Order and Detail Data Created Successfully'}

        else:
            _logger.info("--action_vjpo Failed to retrieve data. Status code:-. (%s)", response.status_code)
            _logger.info("-action_vjpo -Error message--. (: %s)", response.text)

            log_vals.update({
                'state': 'failed',
                'message': f'Failed to retrieve data. Status code: {response.status_code}. Message: {response.text}',
            })
            api_log_obj.sudo().create(log_vals)

            return {'status': 'failed', 'message': 'Data not received'}


    # @api.model
    # def action_vjpo(self, timestamp):
    #     _logger.info("---  action_vjpo -------. ""(%s)", timestamp)
    #     vj_pol_obj = self.env['vj.purchase.order.line']
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # payload = {
    #     #     "startDate": "2025-04-15",
    #     #     "endDate": "2025-05-07"
    #     #     }
    #     today_date = datetime.today().strftime('%Y-%m-%d')
    #     payload = {
    #         "startDate": today_date,
    #         "endDate": today_date
    #     }
    #     # Make the GET request
    #     response = requests.get(purchaseOrder, headers=headers,json=payload)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('pid'))
    #         _logger.info("--existing_ids--. ""(%s)", len(existing_ids))
    #         # Prepare records to create/update
    #         for entry in data.get('data', []):
    #             try:
    #                 order_data = entry.get('order', {})
    #                 details = entry.get('details', [])
    #                 order_id = int(order_data.get('Id', 0))

    #                 if order_id not in existing_ids:
    #                     # Create the parent order record
    #                     parent_order = self.create({
    #                         'pid': order_id,
    #                         'buId': order_data.get('BUId'),
    #                         'businessUnitDescription': order_data.get('BusinessUnitDescription'),
    #                         'documentNo': order_data.get('DocumentNo'),
    #                         'documentDate': order_data.get('DocumentDate'),
    #                         'ledgerId': order_data.get('LedgerId'),
    #                         'ledgerDescription': order_data.get('LedgerDescription'),
    #                         'basicAmount': order_data.get('BasicAmount'),
    #                         'amount': order_data.get('Amount'),
    #                         'remarks': order_data.get('Remarks'),
    #                         'advanceAmount': order_data.get('AdvanceAmount'),
    #                     })
    #                     detail_records = []
    #                     for detail in details:
    #                         detail_records.append((0, 0, {
    #                             'supplier': detail.get('Supplier'),
    #                             'code': detail.get('Code'),
    #                             'description': detail.get('Description'),
    #                             'longDescription': detail.get('LongDescription', ''),
    #                             'uomCode': detail.get('UomCode'),
    #                             'quantity': detail.get('Quantity'),
    #                             'rate': detail.get('Rate'),
    #                             'amount': detail.get('Amount'),
    #                             'subProject': detail.get('SubProject'),
    #                             'budgetHead': detail.get('BudgetHead'),
    #                             'serialNo': detail.get('SerialNo'),
    #                             'ItemId': detail.get('ItemId'),

    #                         }))

    #                     if detail_records:
    #                         parent_order.write({'purchase_order_line_ids': detail_records})
    #                 else:
    #                     parent_order = self.search([('pid', '=', order_id)], limit=1)
    #                     if parent_order:
    #                         parent_order.write({
    #                             'buId': order_data.get('BUId'),
    #                             'businessUnitDescription': order_data.get('BusinessUnitDescription'),
    #                             'documentNo': order_data.get('DocumentNo'),
    #                             'documentDate': order_data.get('DocumentDate'),
    #                             'ledgerId': order_data.get('LedgerId'),
    #                             'ledgerDescription': order_data.get('LedgerDescription'),
    #                             'basicAmount': order_data.get('BasicAmount'),
    #                             'amount': order_data.get('Amount'),
    #                             'remarks': order_data.get('Remarks'),
    #                             'advanceAmount': order_data.get('AdvanceAmount'),
    #                         })
                            
    #                         # Delete existing one2many records before inserting new ones (optional, depends on use case)
    #                         #parent_order.purchase_order_line_ids.unlink()
    #                 # Create the child detail records linked to the parent order

    #             except Exception as e:
    #                 _logger.error("Error processing order ID %s: %s", order_id, str(e))

    #         _logger.info("--Data retrieved from API---. ""(data: %s)", len(data))
    #         return {'status': 'success', 'message': 'Order and Detail Data Created Successfully'}
    #     else:
    #         _logger.info("--action_vjpo Failed to retrieve data. Status code:-. ""(%s)", response.status_code)
    #         _logger.info("-action_vjpo -Error message--. ""(: %s)", response.text)
    #         return {'status': 'failed', 'message': 'Data not received'}
        
    def get_ledger_description(self, bu_id):
        supplier_data = []

        # Group by ledger_id where buId == bu_id
        grouped_data = self.env['vj.purchase.order'].read_group(
            domain=[('buId', '=', bu_id)],
            fields=['ledgerId'],
            groupby=['ledgerId']
        )

        for data in grouped_data:
            ledger_id = data.get('ledgerId')
            
            # Fetch one record to get supplier name (ledgeDescription) and all matching POs
            records = self.env['vj.purchase.order'].search([('ledgerId', '=', ledger_id), ('buId', '=', bu_id)])

            if records:
                supplier_name = records[0].ledgerDescription  # assuming ledgeDescription is a field on vj.purchase.order
                po_ids = records.mapped('id')  # or .mapped('pid') if 'pid' is a field

                supplier_data.append({
                    'ledger_id': ledger_id,
                    'supplier_name': supplier_name,
                    'po_ids': po_ids,
                })
    
        _logger.error("----supplier_data-----%s", len(supplier_data))

     
        return supplier_data
    def get_product_details_from_poline(self):
        grouped_data = {}
        for line in self.purchase_order_line_ids:
            desc = line.description
            if desc not in grouped_data:
                grouped_data[desc] = {
                    'ledger_description': line.supplier,
                    'description': desc,
                    'total_qty': 0.0,
                    'uom_code': line.uomCode  # assuming consistent uom_code per desc
                }
            grouped_data[desc]['total_qty'] += line.quantity
        for data in list(grouped_data.values()):
            #_logger.info("--data--- %s", str(data))

            existing_line = self.vj_po_product_detail_line_ids.filtered(lambda l: l.description == data['description'])

            if existing_line:
                #_logger.info("--existing_line.total_quantity--- %s", str(existing_line.total_quantity))
                total_quantity = existing_line.total_quantity
                new_pending_qty = existing_line.pending_quantity
                #_logger.info("--new_pending_qty--- %s", str(new_pending_qty))
                #_logger.info("--total_quantitytotal_quantitytotal_quantity--- %s", str(total_quantity))
                #_logger.info("--data['total_qty']-- %s", str(data['total_qty']))

                if total_quantity != data['total_qty']:
                    new_pending_qty = data['total_qty'] - existing_line.submitted_quantity
                #_logger.info("--new_pending_qtynew_pending_qty--- %s", str(new_pending_qty))
                

                # Update the existing line
                existing_line.write({
                    'ledger_description': data['ledger_description'],
                    'total_quantity': data['total_qty'],
                    'uom_code': data['uom_code'],
                    'pending_quantity':new_pending_qty,
                })
            else:
                # Create new line
                self.vj_po_product_detail_line_ids = [(0, 0, {
                    'ledger_description': data['ledger_description'],
                    'description': data['description'],
                    'total_quantity': data['total_qty'],
                    'pending_quantity': data['total_qty'],
                    'uom_code': data['uom_code'],
                })]
        #_logger.info("--list(grouped_data.values())--- %s", str(list(grouped_data.values())))
        # Return as list of dictionaries
        return

    
    def get_product_details(self, purchase_order_id=False):
        #_logger.info("--get_product_details called--- %s", str(self))
        latest_record = self.env['amendment.items'].search([
            ('purchase_order_id', '=', self.pid)
        ], order='documentDate desc', limit=1)
        _logger.info("--latest_record--- %s", str(latest_record))


        if not latest_record:
            self.get_product_details_from_poline()
            return {}
        grouped_data = {}
        _logger.info("---get_product_details----")


        for detail in latest_record.detail_ids:
            desc = detail.ledger_description
            if desc not in grouped_data:
                grouped_data[desc] = {
                    'ledger_description': desc,
                    'description': detail.description,
                    'total_qty': 0.0,
                    'uom_code': detail.uom_code  # assuming consistent uom_code per desc
                }
            grouped_data[desc]['total_qty'] += detail.quantity
        
        for data in list(grouped_data.values()):
            #_logger.info("--data--- %s", str(data))

            existing_line = self.vj_po_product_detail_line_ids.filtered(lambda l: l.description == data['description'])

            if existing_line:
                #_logger.info("--existing_line.total_quantity--- %s", str(existing_line.total_quantity))
                total_quantity = existing_line.total_quantity
                new_pending_qty = existing_line.pending_quantity
                #_logger.info("--new_pending_qty--- %s", str(new_pending_qty))
                #_logger.info("--total_quantitytotal_quantitytotal_quantity--- %s", str(total_quantity))
                #_logger.info("--data['total_qty']-- %s", str(data['total_qty']))

                if total_quantity != data['total_qty']:
                    new_pending_qty = data['total_qty'] - existing_line.submitted_quantity
                #_logger.info("--new_pending_qtynew_pending_qty--- %s", str(new_pending_qty))
                

                # Update the existing line
                existing_line.write({
                    'ledger_description': data['ledger_description'],
                    'total_quantity': data['total_qty'],
                    'uom_code': data['uom_code'],
                    'pending_quantity':new_pending_qty,
                })
            else:
                # Create new line
                self.vj_po_product_detail_line_ids = [(0, 0, {
                    'ledger_description': data['ledger_description'],
                    'description': data['description'],
                    'total_quantity': data['total_qty'],
                    'pending_quantity': data['total_qty'],
                    'uom_code': data['uom_code'],
                })]
        #_logger.info("--list(grouped_data.values())--- %s", str(list(grouped_data.values())))
        # Return as list of dictionaries
        return

class VjPoProductDetails(models.Model):
    _name = 'vj.po.product.details'

    poid = fields.Many2one('vj.purchase.order',"Purchase Order ID")
    ledger_description = fields.Char('Ledger Description')
    description = fields.Char('Description')
    uom_code = fields.Char('Uom Code')
    total_quantity = fields.Float(string="Total Quantity")
    pending_quantity = fields.Float(string="Pending Quantity")
    submitted_quantity = fields.Float(string="Submitted Quantity")
    
         
class PurchaseOrderLine(models.Model):
    _name = 'vj.purchase.order.line'

    poid = fields.Many2one('vj.purchase.order',"Purchase Order ID")
    supplier = fields.Char('Supplier')
    code = fields.Char('Code')
    description = fields.Char('Description')
    longDescription = fields.Char('LongDescription')
    uomCode = fields.Char('UomCode')
    quantity = fields.Float(string="Quantity")
    rate = fields.Float(string="Rate")
    amount = fields.Float(string="Amount")
    subProject = fields.Char('SubProject')
    budgetHead = fields.Char('BudgetHead')
    serialNo = fields.Char('SerialNo')
    ItemId = fields.Integer('ItemId')


    @api.model
    def update_record(self, record_id, ledger_description, submitted_qty):
        record = self.env['amendment.items'].browse(record_id)
        if not record:
            return

        relevant_details = record.detail_ids.filtered(lambda d: d.ledger_description == ledger_description)
        remaining_qty = submitted_qty

        for detail in relevant_details:
            if remaining_qty <= 0:
                break

            pending = detail.pending_qty
            if pending > 0:
                used = min(pending, remaining_qty)
                detail.submitted_qty += used
                detail.pending_qty -= used
                remaining_qty -= used
                detail.status = 'partial' if detail.pending_qty > 0 else 'completed'

    @api.model
    def get_latest_records(self, purchase_order_id):
        latest_record = self.env['amendment.items'].search([
            ('purchase_order_id', '=', purchase_order_id)
        ], order='document_date desc', limit=1)

        if not latest_record:
            return []

        grouped_data = defaultdict(lambda: {'actual_qty': 0, 'pending_qty': 0, 'submitted_qty': 0})
        #_logger.info("--grouped_data-- %s", str(grouped_data))
        for detail in latest_record.detail_ids:
            desc = detail.ledger_description
            grouped_data[desc]['actual_qty'] += detail.quantity
            grouped_data[desc]['pending_qty'] += detail.pending_qty
            grouped_data[desc]['submitted_qty'] += detail.submitted_qty

        result = []
        for desc, data in grouped_data.items():
            result.append({
                'record_id': latest_record.id,
                'ledger_description': desc,
                'actual_qty': data['actual_qty'],
                'pending_qty': data['pending_qty'],
                'submitted_qty': data['submitted_qty'],
            })
        #_logger.info("---result---- %s", str(result))
        return result

    def get_po_line_material_desc(self, po_ids):
        vjpo_obj = self.env['vj.purchase.order']
        product_data = []
        #_logger.info("--product_data-po_idspo_idspo_ids-. (data: %s)", po_ids)
        vjpo_ids = vjpo_obj.browse(po_ids)
        #_logger.info("--product_data--. (data: %s)", vjpo_ids)
        if not vjpo_ids:
            _logger.error("--missing vjpo_ids--.")
            return {}
        vjpo_ids.get_product_details()
        for product_line in vjpo_ids.vj_po_product_detail_line_ids:
            product_data.append({
            'description': product_line.description,
            'ledger_description': product_line.ledger_description,
            'quantity': product_line.total_quantity,#actual Qty
            'pending_qty': product_line.pending_quantity,#Pending Qty
            'submitted_qty': product_line.submitted_quantity,#Submitted Qty#enter qty
            'uom_code': product_line.uom_code,
            'line_id': product_line.id,
            'amendment_items_id': 123,  # Assuming it's a Many2one
        })
       
        _logger.info("--product_data--. (data: %s)", product_data)
        return product_data
    
    # no more required
    def get_qty(self,item_id,po_ids):
        po_lines = self.search([('ItemId','=',item_id),('poid','in',po_ids)])
        poline_qty = 0
        for line in  po_lines:
            poline_qty += line.quantity
        po_rec  = self.env['vj.purchase.order'].search([('id','in',po_ids)])
        amendment_rec = self.env['amendment.items'].search([('ItemId','=',item_id),('purchase_order_id','=',po_rec.pid)])
        for rec in amendment_rec:
            if rec.detail_ids:
                for line in rec.detail_ids:
                    poline_qty += line.quantity
        return {'qty':poline_qty,'pending_qty':poline_qty}
