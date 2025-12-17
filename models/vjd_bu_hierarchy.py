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
VjdBuHierarchy = config.get('settings', 'VJDBuAndHierarchy', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)


class VJDBuHierarchy(models.Model):
    _name = 'vjd.bu.hierarchy'
    _description = 'VJD BU and Hierarchy'
    _rec_name = 'buName'


    businessUnit = fields.Many2one('business.unit','Business Unit')
    vjBuId = fields.Integer(string='VJ Buid')
    buName = fields.Char(string='BU Name')
    buCode = fields.Char(string='BU Code')
    parentId = fields.Integer(string='Parent Id')
    segmentId = fields.Integer(string='Segment Id')
    segName = fields.Char(string='Segment Name')
    scplBuId = fields.Char(string='SCPL Buid')
    project_hierarchy_ids = fields.One2many('vjd.project.hierarchy', 'bu_hie_id', string='Project Hierarchy')
    state = fields.Selection([('draft', 'Draft'),('created', 'Created')],default='draft',string="state")
    
    _sql_constraints = [
        ('unique_vjBuId', 'UNIQUE(vjBuId)', 'The vjBuId must be unique!')
    ]

    def fields_get(self, allfields=None, attributes=None):
        res = super(VJDBuHierarchy, self).fields_get(allfields, attributes=attributes or [])
        
        # List of fields that should NOT be readonly
        #editable_fields = ['vjd_bu_hie_id', 'vjd_pro_hie_id']  # Add the field names you want to keep editable
        
        for field in res:
            res[field]['readonly'] = True  # Make all other fields readonly
        return res
    
    @api.model
    def action_get_vjd_bu_hierarchy(self, timestamp):
        _logger.info("-----action_get_vjd_bu_hierarchy-------. (time: %s)", timestamp)

        api_log_obj = self.env['api.log']
        log_vals = {
            'name': f'VJD BU Hierarchy Sync - {timestamp}',
            'api_name': 'bu_hierarchy',
            'create_datetime': datetime.now(),
        }

        headers = {
            "Authorization": Authorization,
            "Content-Type": ContentType,
        }

        bu_rec = self.env['business.unit'].search([])
        vjd_project_hir_obj = self.env['vjd.project.hierarchy']
        created_count = 0
        error_count = 0

        for bu in bu_rec:
            _logger.info("---bu_id-------. (buId: %s)", bu.buId)
            payload = {"scplBuid": str(bu.buId)}
            _logger.info("---payload------. (payload: %s)", payload)

            try:
                response = requests.get(VjdBuHierarchy, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json().get('combinedResult', [])
                    if not data:
                        _logger.info("No data received from API for buId: %s", bu.buId)
                        continue

                    for unit in data:
                        try:
                            if isinstance(unit, dict) and not self.search([('vjBuId', '=', int(unit.get('VJBuid', 0)))]):
                                bu_vals = {
                                    'businessUnit': bu.id,
                                    'vjBuId': unit.get('VJBuid', 0),
                                    'buName': unit.get('BuName'),
                                    'buCode': unit.get('BuCode'),
                                    'parentId': unit.get('ParentId'),
                                    'segmentId': unit.get('SegmentId'),
                                    'segName': unit.get('SegName'),
                                    'scplBuId': unit.get('SCPLBuid'),
                                }
                                bu_record = self.create(bu_vals)
                                created_count += 1

                                line_data = []
                                for hierarchy in unit.get('projectHierarchy', []):
                                    hierarchy_vals = {
                                        'bu_hie_id': bu_record.id,
                                        'buId': hierarchy.get('Buid'),
                                        'hierarchyId': hierarchy.get('HierarchyId'),
                                        'hierarchyTypeId': hierarchy.get('HierarchyTypeId'),
                                        'parentId': hierarchy.get('ParentId'),
                                        'hierarchyName': hierarchy.get('HierarchyName'),
                                        'hierarchyLebel': hierarchy.get('HierarchyLebel'),
                                    }
                                    line_data.append(hierarchy_vals)

                                if line_data:
                                    vjd_project_hir_obj.create(line_data)

                        except Exception as e:
                            _logger.error("Error processing unit: %s. Error: %s", unit, e)
                            error_count += 1

                else:
                    _logger.error("Failed to retrieve data for buId: %s. Status code: %s. Error: %s",
                                bu.buId, response.status_code, response.text)
                    error_count += 1

            except Exception as e:
                _logger.error("Error during API call for buId: %s. Error: %s", bu.buId, e)
                error_count += 1

        log_vals.update({
            'state': 'done' if error_count == 0 else 'partial',
            'message': f'action_get_vjd_bu_hierarchy completed. Records created: {created_count}, Errors: {error_count}',
        })
        api_log_obj.sudo().create(log_vals)

        return {'status': 'success', 'message': 'Process completed'}


    # @api.model
    # def action_get_vjd_bu_hierarchy(self, timestamp):
    #     _logger.info("-----action_get_vjd_bu_hierarchy-------. (time: %s)", timestamp)

    #     headers = {
    #         "Authorization": Authorization,  # Ensure this variable is properly defined
    #         "Content-Type": ContentType,     # Ensure this variable is properly defined
    #     }

    #     #scplBuid_list = self.env['business.unit'].search([]).mapped('buId')
    #     bu_rec = self.env['business.unit'].search([])
    #     for bu in bu_rec:
    #         _logger.info("---bu_id-------. (time: %s)", bu.buId)
    #         payload = {"scplBuid": str(bu.buId)}   
    #         _logger.info("---payload------. (payload: %s)", payload)
                   
    #         try:
    #             # Make the GET request
    #             response = requests.get(VjdBuHierarchy, headers=headers, json=payload)

    #             if response.status_code == 200:
    #                 data = response.json().get('combinedResult', [])
    #                 if not data:
    #                     _logger.info("No data received from API for buId: %s", bu.buId)
    #                     continue  # Continue to the next bu_id

    #                 vjd_project_hir_obj = self.env['vjd.project.hierarchy']

    #                 for unit in data:
    #                     try:
                            
    #                         if isinstance(unit, dict) and not self.search([('vjBuId', '=', int(unit.get('VJBuid', 0)))]):
    #                         #if isinstance(unit, dict):
    #                             # Prepare business unit values
    #                             bu_vals = {
    #                                 'businessUnit':bu.id,
    #                                 'vjBuId': unit.get('VJBuid', 0),
    #                                 'buName': unit.get('BuName'),
    #                                 'buCode': unit.get('BuCode'),
    #                                 'parentId': unit.get('ParentId'),
    #                                 'segmentId': unit.get('SegmentId'),
    #                                 'segName': unit.get('SegName'),
    #                                 'scplBuId': unit.get('SCPLBuid'),
    #                             }
    #                             bu_record = self.create(bu_vals)

    #                             # Prepare hierarchy values
    #                             line_data = []
    #                             for hierarchy in unit.get('projectHierarchy', []):
    #                                 hierarchy_vals = {
    #                                     'bu_hie_id': bu_record.id,
    #                                     'buId': hierarchy.get('Buid'),
    #                                     'hierarchyId': hierarchy.get('HierarchyId'),
    #                                     'hierarchyTypeId': hierarchy.get('HierarchyTypeId'),
    #                                     'parentId': hierarchy.get('ParentId'),
    #                                     'hierarchyName': hierarchy.get('HierarchyName'),
    #                                     'hierarchyLebel': hierarchy.get('HierarchyLebel'),
    #                                 }
    #                                 line_data.append(hierarchy_vals)

    #                             if line_data:
    #                                 vjd_project_hir_obj.create(line_data)

    #                     except Exception as e:
    #                         _logger.error("Error processing unit: %s. Error: %s", unit, e)
    #                         pass

    #             else:
    #                 _logger.error("Failed to retrieve data for buId: %s. Status code: %s. Error message: %s", 
    #                             bu.buId, response.status_code, response.text)
                    
                    
            
    #         except Exception as e:
    #             _logger.error("Error during API call for buId: %s. Error: %s", bu.buId, e)
    #         #return {'status': 'Failed', 'message': 'Failed'}
            
    #     return {'status': 'success', 'message': 'Process completed'}

    def create_project_towers(self):
        _logger.info("-ccreate_project_towers----------------")
        #rec = self.env['project.floors'].search([('vj_floor_id','>',0)],limit=150).unlink()
        #rec = self.env['project.flats'].search([('vj_floor_id','>',0)]).unlink()
        # rec = self.env['project.tower'].search([('hierarchy_id','>',0)],limit=40).unlink()
        # rec = self.env['project.info'].search([('bu_id','>',0)],limit=40).unlink()
        # rec = self.env['vjd.inventory'].search([],limit=40).unlink()
        # rec = self.env['business.unit'].search([],limit=40).unlink()
        # rec = self.env['sub.business.unit'].search([],limit=40).unlink()
        # rec = self.env['activity.master'].search([],limit=40).unlink()
        # rec = self.env['item.master'].search([],limit=40).unlink()
        # rec = self.env['vj.purchase.order'].search([],limit=40).unlink()
        # rec = self.env['amendment.items'].search([],limit=40).unlink()
        # rec = self.env['vj.work.order'].search([],limit=40).unlink()
        # rec = self.env['work.order.amendment'].search([],limit=40).unlink()
        # rec = self.env['vjd.inventory'].search([],limit=40).unlink()
        # rec = self.env['vjd.bu.hierarchy'].search([],limit=40).unlink()
    
        vals_main = []
        project_info_obj = self.env['project.info']
        project_tower_obj = self.env['project.tower']
        vjBuId = self.vjBuId
        if not vjBuId:
            return  # Exit early if no BU ID is provided
        
        # Search or create project based on BU ID
        project = project_info_obj.search([('bu_id', '=', vjBuId)], limit=1)
        if not project:
            project = project_info_obj.create({'bu_id': vjBuId, 'businessUnit':self.businessUnit.id or '','name': self.buName})
            self.state = 'created'
                                           
        if not self.project_hierarchy_ids:
            return  # Exit early if no hierarchy lines are provided
        draft_records = self.project_hierarchy_ids.filtered(lambda record: record.state == 'draft')
        _logger.info("-create_towers--draft_records. (%s)", len(draft_records))
        
        for line in draft_records:
            #if vjBuId == line.buId and line.hierarchyId not in existing_hierarchy_ids:
            sub_business_unit = self.env['sub.business.unit'].search([('buId','=',self.scplBuId),('vjd_bu_hie_id','=',self.id),('vjd_pro_hie_id','=',line.hierarchyName)],limit=1)
            if sub_business_unit:
                vals_main.append({
                    'name': line.hierarchyName,
                    'hierarchy_id': line.hierarchyId,
                    'project_id': project.id or '',
                    'businessUnit':self.businessUnit.id or '',
                    'subDescription':sub_business_unit.subDescription or ','
                })
                line.tower = 'created'
        if vals_main:
            _logger.info("-create_towers--. (%s)", vals_main)
            project_tower_obj.create(vals_main)
            #self.state = 'tower_created'

    # def create_towers(self):
    #     vals_main = []
    #     project_info_obj = self.env['project.info']
    #     project_tower_obj = self.env['project.tower']

    #     vjBuId = self.vjBuId
    #     if vjBuId:
    #         project = project_info_obj.search([('bu_id','=',vjBuId)])
    #         if not project:
    #             project = project_info_obj.create({'bu_id':vjBuId,'name':self.buName})
    #         if self.project_hierarchy_ids:
    #             for line in self.project_hierarchy_ids:
    #                 _logger.info("-vjBuId--. ""(%s)", (vjBuId))
    #                 _logger.info("-line.buId--. ""(%s)", (line.buId))

    #                 if vjBuId == line.buId:
    #                     if not project_tower_obj.search([('project_id','=',project.id),('hierarchy_id','=',line.hierarchyId)]):
    #                         _logger.info("-----------------. ")
    #                         vals_main.append({'name':line.hierarchyName,'hierarchy_id':line.hierarchyId,'project_id':project.id})
    #         if vals_main and vjBuId:
    #             _logger.info("-create_towers--. ""(%s)", (vals_main))

    #             project_tower_obj.create(vals_main)

class VJDProjectHierarchy(models.Model):
    _name = 'vjd.project.hierarchy'
    _description = 'VJD Project Hierarchy'
    _rec_name = 'hierarchyName'

    hierarchyId = fields.Integer(string='Hierarchy Id')
    buId = fields.Integer(string='Bu Id')
    bu_hie_id = fields.Many2one('vjd.bu.hierarchy', string='BU')
    hierarchyTypeId = fields.Integer(string='Hierarchy Type Id')
    parentId = fields.Integer(string='Parent Id')
    hierarchyName = fields.Char(string='Hierarchy Name')
    hierarchyLebel = fields.Char(string='Hierarchy Lable')
    tower = fields.Selection([('draft', 'Draft'),('created','Created')],default='draft',string="Tower")
    state = fields.Selection([('draft', 'Draft'),('created','Created')],default='draft',string="Flat/Floor")
 

    def fields_get(self, allfields=None, attributes=None):
        res = super(VJDProjectHierarchy, self).fields_get(allfields, attributes=attributes or [])
        
        # List of fields that should NOT be readonly
        #editable_fields = ['vjd_bu_hie_id', 'vjd_pro_hie_id']  # Add the field names you want to keep editable
        
        for field in res:
            res[field]['readonly'] = True  # Make all other fields readonly
        return res

    # No Use
    def create_flat_floors(self):
        return

        """
        Creates flat and floor records based on inventory data for a specific hierarchy and business unit.
        """
        print("------create_flat_floors------------")
        vjd_inventory_obj = self.env['vjd.inventory']
        flats_obj = self.env['project.flats']
        floors_obj = self.env['project.floors']

        tower = self.env['project.tower'].search([
            ('hierarchy_id', '=', self.hierarchyId),
            ('project_id.bu_id', '=', self.buId)
        ], limit=1)

        if not tower:
            _logger.info("No tower found for hierarchy ID: %s and BU ID: %s", self.hierarchyId, self.buId)
            return

        _logger.info("Tower found: %s", tower.name)

        # Fetch inventory records with a single search
        flats_recs = vjd_inventory_obj.search([
            ('hirerchyParent', '=', self.hierarchyId),
            ('buid', '=', self.buId),
            ('unitSubType', '=', 'Flat'),
            ('unitTypeId', '!=', False),
            ('state', '=', 'draft'),
        ],order='unitNo asc')
        _logger.info("-----------flats_recs---: %s", len(flats_recs))
        floors_recs = vjd_inventory_obj.search([
            ('hirerchyParent', '=', self.hierarchyId),
            ('buid', '=', self.buId),
            ('unitSubType', '=', 'Flat'),
            ('floorDesc', '!=', False), 
            ('floorId', '!=', False),
            ('state', '=', 'draft'),
        ],order='unitNo asc')
        flat_data = []
        floor_data = []
        _logger.info("-----------floors_recs---: %s", len(floors_recs))
        flooridlst = []
        for rec in floors_recs:
            if rec.floorId not in flooridlst:
                floor = {
                    'vj_floor_id': rec.floorId,
                    'name': rec.floorDesc,
                    'tower_id': tower.id,
                    'project_id': tower.project_id.id,
                    'vjd_inventory_id':rec.id,
                }
                floor_data.append(floor)
            flooridlst.append(rec.floorId)

        _logger.info("--floor_data--: %s", len(floor_data))
        _logger.info("--flat_data--: %s", len(flat_data))

        for rec in flats_recs:
            flat = {
                    #'floor_id': rec.floor_id,
                    'unit_type_id': rec.unitTypeId,#flatid
                    'name': rec.unitNo,
                    'vj_floor_id': rec.floorId,
                    'tower_id': tower.id,
                    'project_id': tower.project_id.id,
                    'vjd_inventory_id':rec.id,
                }
            flat_data.append(flat)

        flats_obj.create(flat_data)
        floors_obj.create(floor_data)
        floors_recs.state = 'created'
        flats_recs.state = 'created'

    # def create_flat_floors(self):
    #     """
    #     Creates flat and floor records based on inventory data for a specific hierarchy and business unit.
    #     """
    #     print("------create_flat_floors------------")
    #     vjd_inventory_obj = self.env['vjd.inventory']
    #     flats_obj = self.env['project.flats']
    #     floors_obj = self.env['project.floors']

    #     tower = self.env['project.tower'].search([
    #         ('hierarchy_id', '=', self.hierarchyId),
    #         ('project_id.bu_id', '=', self.buId)
    #     ], limit=1)

    #     if not tower:
    #         _logger.info("No tower found for hierarchy ID: %s and BU ID: %s", self.hierarchyId, self.buId)
    #         return

    #     _logger.info("Tower found: %s", tower.name)

    #     # Fetch inventory records with a single search
    #     inv_recs = vjd_inventory_obj.search([
    #         ('hirerchyParent', '=', self.hierarchyId),
    #         ('buid', '=', self.buId),
    #         ('unitSubType', '=', 'Flat')
    #     ],order='unitNo asc')

    #     _logger.info("Number of inventory records fetched: %s", len(inv_recs))

    #     flat_data = []
    #     floor_cache = {}

    #     for rec in inv_recs:
    #         floor_id = floor_cache.get(rec.floorId)

    #         if not floor_id and rec.floorDesc and rec.floorId:
    #             # Check if the floor already exists
    #             existing_floor = floors_obj.search([
    #                 ('vj_floor_id', '=', rec.floorId),
    #                 ('name', '=', rec.floorDesc),
    #                 ('tower_id', '=', tower.id),
    #                 ('project_id', '=', tower.project_id.id)
    #             ], limit=1)

    #             if not existing_floor:
    #                 # Create a new floor record
    #                 floor = {
    #                     'vj_floor_id': rec.floorId,
    #                     'name': rec.floorDesc,
    #                     'tower_id': tower.id,
    #                     'project_id': tower.project_id.id
    #                 }
    #                 floor_record = floors_obj.create(floor)
    #                 floor_id = floor_record.id
    #             else:
    #                 floor_id = existing_floor.id

    #             # Cache the floor_id for future use
    #             floor_cache[rec.floorId] = floor_id

    #         # Check if the flat already exists
    #         if not flats_obj.search([
    #             ('floor_id', '=', floor_id),
    #             ('name', '=', rec.unitNo),
    #             'unit_type_id','=',rec.unitTypeId,
    #             ('tower_id', '=', tower.id),
    #             ('project_id', '=', tower.project_id.id)
    #         ], limit=1):
    #             flat_data.append({
    #                 'floor_id': floor_id,
    #                 'unit_type_id': rec.unitTypeId,
    #                 'name': rec.unitNo,
    #                 'vj_floor_id': rec.floorId,
    #                 'tower_id': tower.id,
    #                 'project_id': tower.project_id.id
    #             })

    #     _logger.info("Number of flats to create: %s", len(flat_data))

    #     # Bulk create flat records
    #     if flat_data:
    #         flats_obj.create(flat_data)

         
