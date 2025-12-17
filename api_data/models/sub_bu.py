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
subBusinessUnit = config.get('settings', 'subBusinessUnit', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)


class SubBuUnit(models.Model):
    _name = 'sub.business.unit'
    _inherit = ['mail.thread']  # Add mail.thread for chatter

    _rec_name = "buId"
    #_order = 'notification_dt desc, id desc'
    _description = "SubBuUnit"

    description = fields.Char("Description")
    type = fields.Char("Type")
    tower_type = fields.Selection(
    [('development', 'Development'),('other', 'Other'), ('residential', 'Residential')],
    default='residential',
    string="Tower Type",
    readonly=False)
    parentId = fields.Integer("Parent Id")
    segmentId = fields.Integer("Segment Id")
    subDescription = fields.Char("Sub Description")
    subId = fields.Integer("Sub Id")
    buId = fields.Integer("Bu Id")
    vjd_bu_hie_id = fields.Many2one('vjd.bu.hierarchy', 'Bu Hierarchy',domain="[('scplBuId', '=', buId)]",tracking=True)
    vjd_pro_hie_id = fields.Many2one('vjd.project.hierarchy', 'Project Hierarchy',domain="[('bu_hie_id', '=', vjd_bu_hie_id)]",tracking=True)
    project_state = fields.Selection(selection=[('draft', 'Draft'), ('created', 'Created')],default='draft',string="Project State",readonly=True,store=True,tracking=True)
    tower_state = fields.Selection(selection=[('draft', 'Draft'),('created', 'Created')],default='draft',string="Tower State",readonly=True,store=True,tracking=True)
    ff_state = fields.Selection(selection=[('draft', 'Draft'),('created', 'Created')],default='draft',string="Flat/Floor State",readonly=True,store=True,tracking=True)
    project_info_id = fields.Many2one('project.info', 'Project',readonly=True,store=True,tracking=True)
    tower_id = fields.Many2one('project.tower', 'Tower',readonly=True,store=True,tracking=True)
    
    api.onchange('vjd_bu_hie_id')
    def _onchange_field1(self):
        self.vjd_pro_hie_id = False
    
    
    def fields_get(self, allfields=None, attributes=None):
        res = super(SubBuUnit, self).fields_get(allfields, attributes=attributes or [])
        
        # List of fields that should NOT be readonly
        editable_fields = ['vjd_bu_hie_id', 'vjd_pro_hie_id','subDescription']  # Add the field names you want to keep editable
        
        for field in res:
            if field not in editable_fields:
                res[field]['readonly'] = True  # Make all other fields readonly
        return res
    @api.model
    def action_sub_business_unit(self, timestamp):
        _logger.info("--- action_sub_business_unit --- (%s)", timestamp)
        ist = pytz.timezone('Asia/Kolkata')
        aware_dt = datetime.now(ist)                      # Aware datetime in IST
        utc_naive_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)
        api_log_obj = self.env['api.log']
        log_vals = {
            'name': f'SubBusinessUnit Sync - {timestamp}',
            'api_name': 'sub_bu',
            'create_datetime': utc_naive_dt,
        }

        headers = {
            "Authorization": Authorization,  # Replace with your token
            "Content-Type": ContentType,
        }

        try:
            response = requests.get(subBusinessUnit, headers=headers)

            if response.status_code == 200:
                data = response.json()
                records_to_create = []

                try:
                    for key, values in data.items():
                        if key and values:
                            for value in values:
                                records_to_create.append({
                                    'description': key or '',
                                    'type': value.get('Type', ''),
                                    'parentId': value.get('ParentId', 0),
                                    'segmentId': value.get('SegmentId', 0),
                                    'subDescription': value.get('SubDescription', ''),
                                    'subId': value.get('SubId', 0),
                                    'buId': value.get('BuId', 0),
                                })
                except Exception as e:
                    _logger.error("Error processing lines: %s", e)

                _logger.info("--- Records fetched for creation: %s", len(records_to_create))

                master_data = []
                for record in records_to_create:
                    domain = [
                        ('description', '=', record.get('description')),
                        ('type', '=', record.get('type')),
                        ('parentId', '=', record.get('parentId')),
                        ('segmentId', '=', record.get('segmentId')),
                        ('subDescription', '=', record.get('subDescription')),
                        ('subId', '=', record.get('subId')),
                        ('buId', '=', record.get('buId'))
                    ]
                    if not self.search(domain):
                        master_data.append(record)

                if master_data:
                    self.create(master_data)
                    message = f"action_sub_business_unit ---success--- records created: {len(master_data)}"
                    log_vals.update({'state': 'done', 'message': message})
                    api_log_obj.sudo().create(log_vals)
                    return {'status': 'success', 'message': message}

                message = "action_sub_business_unit ---success--- no new records to create"
                log_vals.update({'state': 'done', 'message': message})
                api_log_obj.sudo().create(log_vals)
                return {'status': 'success', 'message': message}

            else:
                error_msg = f"API response error. Status code: {response.status_code}, Response: {response.text}"
                _logger.error(error_msg)
                log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Failed to fetch subBusinessUnit data'})
                api_log_obj.sudo().create(log_vals)
                return {'status': 'failed', 'message': 'Data not received'}

        except Exception as e:
            error_msg = f"Exception during subBusinessUnit sync: {str(e)}"
            _logger.exception(error_msg)
            log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Exception during subBusinessUnit API call'})
            api_log_obj.sudo().create(log_vals)
            return {'status': 'failed', 'message': 'Exception occurred during sync'}

    # @api.model
    # def action_sub_business_unit(self, timestamp):
    #     _logger.info("---action_sub_business_unit-------. ""(%s)", timestamp)
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # Make the GET request
    #     response = requests.get(subBusinessUnit, headers=headers)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         records_to_create = []
    #         # for line in data:
    #         try:
    #             for key, values in data.items():
    #                 if key and values:
    #                     for value in values:
    #                         # value.update({'description':key})
    #                         records_to_create.append({
    #                             'description': key or '',
    #                             'type': value['Type'] or '',
    #                             'parentId': value['ParentId'] or 0,
    #                             'segmentId': value['SegmentId'] or 0,  # Adjust key names as per actual structure
    #                             'subDescription': value['SubDescription'] or '',
    #                             'subId': value['SubId'] or 0,
    #                             'buId': value['BuId'] or 0,
    #                     })
            
    #         except Exception as e:
    #             _logger.error("Error processing line:. Error: %s", e)
                  
    #         # Create all new records in one batch
    #         _logger.info("-action_sub_business_unit--records_to_create-. ""(service name: %s)", len(records_to_create))

    #         master_data = []
    #         if records_to_create:
    #             for record in records_to_create:
    #                 #_logger.info("--record-. ""(record: %s)", (record))

    #                 domain = [('description','=',record.get('description')),('type','=',record.get('type')),('parentId','=',record.get('parentId')),('segmentId','=',record.get('segmentId')),('subDescription','=',record.get('subDescription')),('subId','=',record.get('subId')),('buId','=',record.get('buId'))]
    #                 #_logger.info("-SubBusinessUnit---domain--. ""(service name: %s)", (domain))
                    
    #                 if not self.search(domain):
    #                     #_logger.info("-getting record--. ""(record: %s)", len(record))
    #                     master_data.append(record)
    #             #_logger.info("-SubBusinessUnit---master_data--. ""(service name: %s)", len(master_data))
                
    #             if master_data:
    #                 self.create(master_data)
    #                 #_logger.info("-SubBusinessUnit-Data retrieved from API---. ""(service name: %s)", master_data)
    #                 return {'status': 'sucess', 'message': 'SubBusinessUnit Data Created Sucessfully'}
    #         return {'status': 'sucess', 'message': 'SubBusinessUnit No Records Found to Create '}
            
    #     else:
    #         _logger.info("-SubBusinessUnit-Failed to retrieve data. Status code:-. ""(service name: %s)", response.status_code)
    #         _logger.info("-SubBusinessUnit-Error message--. ""(service name: %s)", response.text)
    #         return {'status': 'failed', 'message': 'SubBusinessUnit data not reeived'}
    
    def create_project_towers(self):
        _logger.info("-ccreate_project_towers----------------")    
        vals_main = []
        project_info_obj = self.env['project.info']
        project_tower_obj = self.env['project.tower']
        bu_obj = self.env['business.unit']
        bu_id = self.buId
        description = self.description
        bu_rec = bu_obj.search([('buId', '=', bu_id)])
        if not bu_rec and not bu_id:
            return
        
        # Search or create project based on BU ID
        project = project_info_obj.search([('bu_id', '=', bu_id)])
        if not project:
            project = project_info_obj.create({'bu_id': bu_id, 'businessUnit':bu_rec.id or '','name': description})
        self.project_state = 'created'
        self.project_info_id = project.id
                                           
        if not self.vjd_pro_hie_id and not self.tower_type == 'development':
            raise UserError("Please select the project Hierarchy .")
        
        tower = self.subDescription
        tower_rec  = project_tower_obj.search([('name', '=', tower),('project_id', '=', project.id)])
        if not tower_rec:
            tower_rec = project_tower_obj.create({
                        'name': tower,
                        'project_id': project.id or '',
                        'businessUnit':bu_rec.id,
                        'vjd_bu_hie_id':self.vjd_pro_hie_id.bu_hie_id.id,
                        'vjd_pro_hie_id':self.vjd_pro_hie_id.id,
                        'tower_type':self.tower_type,
                        'sub_business_unit_id':self.id,
                    })
        self.tower_id = tower_rec.id    
        self.tower_state = 'created'
        tower_rec.sub_business_unit_id = self.id,

    def extract_floor_number(self,floor_desc):
        # Extracts the first number from the string
        match = re.search(r'\d+', floor_desc)
        return int(match.group()) if match else -1

    def create_flats_floors(self):

        """
        Creates flat and floor records based on inventory data for a specific hierarchy and business unit.
        """
        #print("------create_flat_floors------------")
        vjd_inventory_obj = self.env['vjd.inventory']
        flats_obj = self.env['project.flats']
        floors_obj = self.env['project.floors']

        if not self.project_info_id and self.tower_id:
            return

        # Fetch inventory records with a single search
        flats_recs = vjd_inventory_obj.search([
            ('hirerchyParent', '=', self.vjd_pro_hie_id.hierarchyId),
            ('buid', '=', self.vjd_pro_hie_id.buId),
            ('unitType', '=', 'Unit'),
            #('unitSubType', '=', 'Flat'),
            #('unitTypeId', '!=', False),
            #('state', '=', 'draft'),
        ],order='unitNo asc')

        #_logger.info("-----------flats_recs---: %s", len(flats_recs))
        floors_recs = vjd_inventory_obj.search([
            ('hirerchyParent', '=', self.vjd_pro_hie_id.hierarchyId),
            ('buid', '=', self.vjd_pro_hie_id.buId),
            #('unitSubType', '=', 'Flat'),
            ('floorDesc', '!=', False), 
            ('floorId', '!=', False),
            #('state', '=', 'draft'),
        ],order='id asc')

        flat_data = []
        floor_data = []
        flooridlst = []

        # Sort floors_recs based on the numeric part of floorDesc in descending order
        #sorted_floors_recs = sorted(floors_recs, key=lambda rec: int(rec.floorDesc.split()[-1]), reverse=False)
        sorted_floors_recs = sorted(floors_recs, key=lambda rec: self.extract_floor_number(rec.floorDesc))
        for rec in sorted_floors_recs:
            floor_value = floors_obj.search([('project_id','=',self.project_info_id.id),('tower_id','=',self.tower_id.id),('vj_floor_id','=',rec.floorId),('name','=',rec.floorDesc)])
            if not floor_value:
                if rec.floorId not in flooridlst:
                    floor = {
                        'vj_floor_id': rec.floorId,
                        'name': rec.floorDesc,
                        'tower_id': self.tower_id.id,
                        'project_id': self.project_info_id.id,
                        'vjd_inventory_id': rec.id,
                    }
                    floor_data.append(floor)
                flooridlst.append(rec.floorId)

        flat_data = []
        # Sort flats_recs based on the numeric value of floorId (ascending order)
        sorted_flats_recs = sorted(flats_recs, key=lambda rec: int(rec.floorId), reverse=False)
        #sorted_flats_recs = sorted(flats_recs, key=lambda rec: self.extract_floor_number(rec.floorDesc))

        for rec in sorted_flats_recs:
            flat_value = flats_obj.search([('name','=',rec.unitNo),('project_id','=',self.project_info_id.id),('tower_id','=',self.tower_id.id),('unit_type_id','=',rec.unitTypeId),('vj_floor_id','=',rec.floorId)])
            if not flat_value:
                flat = {
                    # 'floor_id': rec.floor_id,
                    'unit_type_id': rec.unitTypeId,  # flat ID
                    'name': rec.unitNo,
                    'vj_floor_id': rec.floorId,  # Sorting based on this
                    'tower_id': self.tower_id.id,
                    'project_id': self.project_info_id.id,
                    'vjd_inventory_id': rec.id,
                }
                flat_data.append(flat)
        # for data in flat_data:
        #     _logger.info("--flat_data--: %s", (data['name']))

        flats_obj.create(flat_data)
        floors_obj.create(floor_data)
        #floors_recs.state = 'created'
        #flats_recs.state = 'created'
        self.ff_state = 'created'


    # def create_flats_floors(self):

    #     """
    #     Creates flat and floor records based on inventory data for a specific hierarchy and business unit.
    #     """
    #     #print("------create_flat_floors------------")
    #     vjd_inventory_obj = self.env['vjd.inventory']
    #     flats_obj = self.env['project.flats']
    #     floors_obj = self.env['project.floors']

    #     if not self.project_info_id and self.tower_id:
    #         return

    #     # Fetch inventory records with a single search
    #     flats_recs = vjd_inventory_obj.search([
    #         ('hirerchyParent', '=', self.vjd_pro_hie_id.hierarchyId),
    #         ('buid', '=', self.vjd_pro_hie_id.buId),
    #         ('unitSubType', '=', 'Flat'),
    #         ('unitTypeId', '!=', False),
    #         ('state', '=', 'draft'),
    #     ],order='unitNo asc')

    #     #_logger.info("-----------flats_recs---: %s", len(flats_recs))
    #     floors_recs = vjd_inventory_obj.search([
    #         ('hirerchyParent', '=', self.vjd_pro_hie_id.hierarchyId),
    #         ('buid', '=', self.vjd_pro_hie_id.buId),
    #         ('unitSubType', '=', 'Flat'),
    #         ('floorDesc', '!=', False), 
    #         ('floorId', '!=', False),
    #         ('state', '=', 'draft'),
    #     ],order='id asc')
    #     flat_data = []
    #     floor_data = []
    #     flooridlst = []

    #     # Sort floors_recs based on the numeric part of floorDesc in descending order
    #     sorted_floors_recs = sorted(floors_recs, key=lambda rec: int(rec.floorDesc.split()[-1]), reverse=False)

    #     for rec in sorted_floors_recs:
    #         if rec.floorId not in flooridlst:
    #             floor = {
    #                 'vj_floor_id': rec.floorId,
    #                 'name': rec.floorDesc,
    #                 'tower_id': self.tower_id.id,
    #                 'project_id': self.project_info_id.id,
    #                 'vjd_inventory_id': rec.id,
    #             }
    #             floor_data.append(floor)
    #         flooridlst.append(rec.floorId)

    #     flat_data = []
    #     # Sort flats_recs based on the numeric value of floorId (ascending order)
    #     sorted_flats_recs = sorted(flats_recs, key=lambda rec: int(rec.floorId), reverse=False)

    #     for rec in sorted_flats_recs:
    #         flat = {
    #             # 'floor_id': rec.floor_id,
    #             'unit_type_id': rec.unitTypeId,  # flat ID
    #             'name': rec.unitNo,
    #             'vj_floor_id': rec.floorId,  # Sorting based on this
    #             'tower_id': self.tower_id.id,
    #             'project_id': self.project_info_id.id,
    #             'vjd_inventory_id': rec.id,
    #         }
    #         flat_data.append(flat)
    #     for data in flat_data:
    #         _logger.info("--flat_data--: %s", (data['name']))

    #     flats_obj.create(flat_data)
    #     floors_obj.create(floor_data)
    #     floors_recs.state = 'created'
    #     flats_recs.state = 'created'
    #     self.ff_state = 'created'
