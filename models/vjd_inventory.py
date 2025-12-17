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
VjdInventory = config.get('settings', 'VJDInventory', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)

class VJDInventory(models.Model):
    _name = 'vjd.inventory'
    _rec_name = "unitId"
    #_order = 'notification_dt desc, id desc'
    _description = "VJD Inventory"

    unitId = fields.Integer("Unit Id")
    unitNo = fields.Char("Unit No")
    businessUnit = fields.Char("BusinessUnit")
    hierarchyLebel = fields.Char("Hierarchy Lebel")
    level4 = fields.Char("Level4")
    level3 = fields.Char("Level3")
    level2 = fields.Char("Level2")
    level1 = fields.Char("Level1")
    hierarchyID = fields.Integer("Hierarchy ID")
    hirerchyParent = fields.Integer("Hirerchy Parent")
    floorId = fields.Integer("Floor Id")
    floorDesc = fields.Char("Floor Desc")
    typologyId = fields.Integer("Typology Id")
    typology = fields.Char("Typology")
    unitSubType = fields.Char("UnitSub Type")
    unitTypeId = fields.Integer("UnitType Id")
    unitType = fields.Char("Unit Type")
    area1 = fields.Float("Area1")
    uom1 = fields.Char("UOM1")
    area2 = fields.Float("Area2")
    uom2 = fields.Char("UOM2")
    area3 = fields.Float("Area3")
    uom3 = fields.Char("UOM3")
    area4 = fields.Float("Area4")
    uom4 = fields.Char("UOM4")
    status = fields.Char("Status")
    buid = fields.Integer("Buid")

    # activity_group_ids = fields.Many2many(
    #     'construction.activity.group',    # The target model
    #     'vjd_inventory_activity_group_rel',  # The relationship table name
    #     'inventory_id',                    # Foreign key in the relation table pointing to vjd.inventory
    #     'activity_group_id',               # Foreign key in the relation table pointing to construction.activity.group
    #     string='Flat Activity Groups'           # The label for the field
    # )


    flat_activity_group_ids = fields.Many2many(
        'construction.activity.group',    # The target model
        'vjd_inventory_flat_activity_group_rel',  # The relationship table name
        'inventory_id',                    # Foreign key in the relation table pointing to vjd.inventory
        'activity_group_id',               # Foreign key in the relation table pointing to construction.activity.group
        string='Flat Activity Groups'           # The label for the field
    )
    floor_activity_group_ids = fields.Many2many(
        'construction.activity.group',    # The target model
        'vjd_inventory_floor_activity_group_rel',  # The relationship table name
        'inventory_id',                    # Foreign key in the relation table pointing to vjd.inventory
        'activity_group_id',               # Foreign key in the relation table pointing to construction.activity.group
        string='Floor Activity Groups'           # The label for the field
    )
    state = fields.Selection([('draft', 'Draft'),('created', 'created')],default='draft',string="state")
    type = fields.Selection([('flat_wise', 'Flat'),('floor_wise', 'Floor'),('common_area', 'Common Area'),('development', 'Development')],default='',string="Type")
    
    def fields_get(self, allfields=None, attributes=None):
        res = super(VJDInventory, self).fields_get(allfields, attributes=attributes or [])
        
        # List of fields that should NOT be readonly
        #editable_fields = ['vjd_bu_hie_id', 'vjd_pro_hie_id']  # Add the field names you want to keep editable
        
        for field in res:
            res[field]['readonly'] = True  # Make all other fields readonly
        return res
    
    @api.model
    def action_get_all_vjd_inventory(self, timestamp):
        _logger.info("-----action_get_all_vjd_inventory-------. (time: %s)", timestamp)

        api_log_obj = self.env['api.log']
        log_vals = {
            'name': f'VJD Inventory Sync - {timestamp}',
            'api_name': 'vjd_inventory',
            'create_datetime': datetime.now(),
        }

        headers = {
            "Authorization": Authorization,
            "Content-Type": ContentType,
        }

        try:
            response = requests.get(VjdInventory, headers=headers)
            if response.status_code == 200:
                response = response.json()
                data = response.get('data', [])
                existing_ids = set(self.search([]).mapped('unitId'))

                records_to_create = []
                created_count = 0
                error_count = 0

                for line in data:
                    try:
                        if isinstance(line, str):
                            line = ast.literal_eval(line)

                        if isinstance(line, dict):
                            if int(line.get('UnitId', 0)) not in existing_ids:
                                records_to_create.append({
                                    'unitId': line.get('UnitId', 0),
                                    'unitNo': line.get('UnitNo', ''),
                                    'businessUnit': line.get('BusinessUnit', ''),
                                    'hierarchyLebel': line.get('HierarchyLebel', ''),
                                    'level4': line.get('Level4', ''),
                                    'level3': line.get('Level3', ''),
                                    'level2': line.get('Level2', ''),
                                    'level1': line.get('Level1', ''),
                                    'hierarchyID': line.get('HierarchyID', 0),
                                    'hirerchyParent': line.get('HirerchyParent', 0),
                                    'floorId': line.get('FloorId', 0),
                                    'floorDesc': line.get('FloorDesc', ''),
                                    'typologyId': line.get('TypologyId', 0),
                                    'typology': line.get('Typology', ''),
                                    'unitSubType': line.get('UnitSubType', ''),
                                    'unitTypeId': line.get('UnitTypeId', 0),
                                    'unitType': line.get('UnitType', ''),
                                    'area1': line.get('Area1', 0.0),
                                    'uom1': line.get('Uom1', ''),
                                    'area2': line.get('Area2', 0.0),
                                    'uom2': line.get('Uom2', ''),
                                    'area3': line.get('Area3', 0.0),
                                    'uom3': line.get('Uom3', ''),
                                    'area4': line.get('Area4', 0.0),
                                    'uom4': line.get('Uom4', ''),
                                    'status': line.get('Status', ''),
                                    'buid': line.get('Buid', ''),
                                    'state': 'draft',
                                })
                        else:
                            _logger.warning("Skipping non-dict line: %s", line)

                    except Exception as e:
                        _logger.error("Error processing line: %s. Error: %s", line, e)
                        error_count += 1

                if records_to_create:
                    self.create(records_to_create)
                    created_count = len(records_to_create)
                    _logger.info("Created %s new inventory records.", created_count)

                log_vals.update({
                    'state': 'done' if error_count == 0 else 'partial',
                    'message': f'action_get_all_vjd_inventory completed. Records created: {created_count}, Errors: {error_count}',
                })

                api_log_obj.sudo().create(log_vals)
                return {'status': 'success', 'message': f'Data sync complete. Created: {created_count}, Errors: {error_count}'}
            else:
                log_vals.update({
                    'state': 'failed',
                    'message': f'Failed to retrieve data. Status code: {response.status_code}. Error: {response.text}',
                })
                api_log_obj.sudo().create(log_vals)
                return {'status': 'failed', 'message': 'Data not received'}

        except Exception as e:
            _logger.error("API call failed. Error: %s", e)
            log_vals.update({
                'state': 'failed',
                'message': f'Exception during API call: {e}',
            })
            api_log_obj.sudo().create(log_vals)
            return {'status': 'failed', 'message': 'Exception during data fetch'}



    # @api.model
    # def action_get_all_vjd_inventory(self, timestamp):
    #     _logger.info("-----action_get_all_vjd_inventory-------. ""(time: %s)", timestamp)
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # Make the GET request
    #     response = requests.get(VjdInventory, headers=headers)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         response = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('unitId'))
         
    #         #_logger.info("-existing_ids--. ""(service name: %s)", existing_ids)
    #         # Prepare records to create
    #         records_to_create = []
    #         data = response['data']
    #         #_logger.info("----data------. ""(line: %s)", data)
    #         for line in data:
    #             #_logger.info("-line--. ""(line: %s)", line)
    #             try:
    #                 # Convert line to dictionary if it is a string
    #                 if isinstance(line, str):
    #                     line = ast.literal_eval(line)  # Convert to dictionary

    #                 # Proceed if the line is now a dictionary
    #                 if isinstance(line, dict):
    #                     if int(line['UnitId']) not in existing_ids:
    #                         records_to_create.append(
    #                                 {
    #                                     'unitId': line.get('UnitId',0),
    #                                     'unitNo': line.get('UnitNo',''),
    #                                     'businessUnit': line.get('BusinessUnit',''),
    #                                     'hierarchyLebel': line.get('HierarchyLebel',''),
    #                                     'level4': line.get('Level4',''),
    #                                     'level3': line.get('Level3',''),
    #                                     'level2': line.get('Level2',''),
    #                                     'level1': line.get('Level1',''),
    #                                     'hierarchyID': line.get('HierarchyID',0),
    #                                     'hirerchyParent': line.get('HirerchyParent',0),
    #                                     'floorId': line.get('FloorId',0),
    #                                     'floorDesc': line.get('FloorDesc',''),
    #                                     'typologyId': line.get('TypologyId',0),
    #                                     'typology': line.get('Typology',''),
    #                                     'unitSubType': line.get('UnitSubType',''),
    #                                     'unitTypeId': line.get('UnitTypeId',0),
    #                                     'unitType': line.get('UnitType',''),
    #                                     'area1': line.get('Area1',0.0),
    #                                     'uom1': line.get('Uom1',''),
    #                                     'area2': line.get('Area2',0.0),
    #                                     'uom2': line.get('Uom2',''),
    #                                     'area3': line.get('Area3',0.0),
    #                                     'uom3': line.get('Uom3',''),
    #                                     'area4': line.get('Area4',0.0),
    #                                     'uom4': line.get('Uom4',''),
    #                                     'status': line.get('Status',''),
    #                                     'buid': line.get('Buid',''),
    #                                     'state': 'draft',
    #                                 },)

    #                 else:
    #                     _logger.warning("action_get_all_vjd_inventory Skipping non-dictionary line: %s", line)
    #             except Exception as e:
    #                 _logger.error("Error processing line: %s. Error: %s", line, e)
                  
    #         # Create all new records in one batch
    #         _logger.info("--action_get_all_vjd_inventory-records_to_create--. ""(%s)", len(records_to_create))

    #         if records_to_create:
    #             self.create(records_to_create)
    #             _logger.info("-action_get_all_vjd_inventory-Data retrieved from API---. "": %s)", data[0])
    #             return {'status': 'sucess', 'message': 'Data Created Sucessfully'}
    #         return {'status': 'sucess', 'message': 'No Records Found to Create '}
            
    #     else:
    #         _logger.info("-action_get_all_vjd_inventory-Failed to retrieve data. Status code:-. ""(service name: %s)", response.status_code)
    #         _logger.info("-action_get_all_vjd_inventory -Error message- -. "": %s)", response.text)
    #         return {'status': 'failed', 'message': 'data not reeived'}