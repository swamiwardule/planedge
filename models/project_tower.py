from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ProjectTowers(models.Model):
    _inherit = 'project.tower'
    #_order = 'notification_dt desc, id desc'
    _description = "Project Tower"

    businessUnit = fields.Many2one('business.unit','Business Unit',tracking=True,readonly=True)
    subDescription = fields.Char('Sub Description',tracking=True,readonly=True)
    vjd_bu_hie_id = fields.Many2one('vjd.bu.hierarchy','VJD BU Hierarchy',tracking=True,readonly=True)
    vjd_pro_hie_id = fields.Many2one('vjd.project.hierarchy', 'Project Hierarchy',tracking=True,readonly=True)
    sub_business_unit_id = fields.Many2one('sub.business.unit', 'Sub Business Unit',tracking=True,readonly=True)
    # tower_type = fields.Selection(
    # [('development', 'Development'),('other', 'Other'), ('residential', 'Residential')],
    # default='residential',
    # string="Tower Type",
    # readonly=False)

    def create_floor_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        flag = False
        
        if self.tower_floor_line_id:
            floor_records = self.tower_floor_line_id.filtered(lambda r: r.activity_state == 'draft')[:100]

            for floor in floor_records:
                act_list = []
                if floor.vjd_inventory_id:

                    for groups in floor.vjd_inventory_id.floor_activity_group_ids:
                        for group in groups:
                            act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', group.id),('type','=','floor')])
                            act_list+=act_records
                act_list = list(set(act_list))
                for act in act_list:
                    activity_rec = project_activity_obj.create({'project_activity_name_id':act.id,'name':act.name,'floor_id':floor.id,'tower_id':floor.tower_id.id,'project_id':floor.project_id.id})
                    for activity_type in act.panl_ids:
                        project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':floor.project_id.id,'tower_id':floor.tower_id.id,'floor_id':floor.id}
                        activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                        checklist_data = []
                        for chk in activity_type.patn_id.patnl_ids:
                            checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                        project_checklist_line_obj.create(checklist_data)
                        flag = True
                if flag:
                    floor.activity_state = 'created'
                                    
    def create_flat_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']

        if self.tower_flat_line_id:
            _logger.info("---self.tower_flat_line_id---. "": %s)",len(self.tower_flat_line_id))
            flat_records = self.tower_flat_line_id.filtered(lambda r: r.activity_state == 'draft')[:50]
            _logger.info("---flat_records.flat_records---. "": %s)",len(flat_records))
            for flat in flat_records:
                act_list = []
                flag = False
                if flat.vjd_inventory_id:
                    for groups in flat.vjd_inventory_id.flat_activity_group_ids:
                        for group in groups:
                            act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', group.id),('type','=','flat')])
                            act_list+=act_records
                    act_list = list(set(act_list))
                    for act in act_list:
                        activity_rec = project_activity_obj.create({'project_activity_name_id':act.id,'name':act.name,'flat_id':flat.id,'tower_id':flat.tower_id.id,'project_id':flat.project_id.id})
                        for activity_type in act.panl_ids:
                            project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':flat.project_id.id,'tower_id':flat.tower_id.id,'flat_id':flat.id}
                            activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                            checklist_data = []
                            for chk in activity_type.patn_id.patnl_ids:
                                checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                            project_checklist_line_obj.create(checklist_data)
                            flag = True
                    if flag:
                        flat.activity_state = 'created'
        return

    def create_common_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        
        # Search for records in 'project.activity.name' where 'common_activity_group_ids' is set (non-empty)
        activities_with_groups = self.env['project.activity.name'].search([
            ('common_activity_group_ids', '!=', False)
        ])
        
        # Get the IDs of those records
        activity_ids = activities_with_groups.ids
        _logger.info("---activity_ids---: %s", activity_ids)

        # Loop through the activities to create the project activity records
        created_activity_ids = []  # To store the IDs of created project activities

        for activity in activity_ids:
            pan_rec = project_act_name_obj.browse(activity)
            _logger.info("--activity_rec--: %s", pan_rec)

            # Check if activity already exists for the project tower
            act_created = project_activity_obj.search([
                ('project_id', '=', self.project_id.id),
                ('tower_id', '=', self.id),
                ('act_type', '=', 'common'),
                ('project_activity_name_id', '=', activity)
            ])
            
            _logger.info("--activity_rec--: %s", act_created)

            if not act_created:
                # Create a new project activity record
                project_activity_data = {
                    'project_activity_name_id': pan_rec.id,
                    'description': pan_rec.description,
                    'name': pan_rec.name,
                    'tower_id': self.id,
                    'project_id': self.project_id.id,
                    'act_type':'common',
                }
                activity_rec = project_activity_obj.create(project_activity_data)
                created_activity_ids.append(activity_rec.id)  # Store created activity ID

                # Create associated project activity types and checklist lines
                for activity_type in pan_rec.panl_ids:
                    project_activity_type_data = {
                        'activity_id': activity_rec.id,
                        'project_actn_id': activity_type.patn_id.id,
                        'name': activity_type.patn_id.name,
                        'project_id': self.project_id.id,
                        'tower_id': self.id
                    }
                    activity_type_re = project_activity_type_obj.create(project_activity_type_data)

                    checklist_data = []
                    for chk in activity_type.patn_id.patnl_ids:
                        checklist_data.append({
                            'activity_type_id': activity_type_re.id,
                            'checklist_template_id': chk.checklist_id.id
                        })
                    project_checklist_line_obj.create(checklist_data)

        # Now, update the `activity_ids` field in the project.tower model
        if created_activity_ids:
            self.write({
                'activity_ids': [(4, activity_id) for activity_id in created_activity_ids]
            })
            _logger.info("Appended new activity_ids to project tower: %s", created_activity_ids)
    # this button on hold
    def create_development_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        
        # Search for records in 'project.activity.name' where 'common_activity_group_ids' is set (non-empty)
        activities_with_groups = self.env['project.activity.name'].search([
            ('development_activity_group_ids', '!=', False)
        ])
        
        # Get the IDs of those records
        activity_ids = activities_with_groups.ids
        _logger.info("---activity_ids---: %s", activity_ids)

        # Loop through the activities to create the project activity records
        created_activity_ids = []  # To store the IDs of created project activities

        for activity in activity_ids:
            pan_rec = project_act_name_obj.browse(activity)
            _logger.info("--activity_rec--: %s", pan_rec)

            # Check if activity already exists for the project tower
            act_created = project_activity_obj.search([
                ('project_id', '=', self.project_id.id),
                ('tower_id', '=', self.id),
                ('act_type', '=', 'development'),
                ('project_activity_name_id', '=', activity)
            ])
            
            _logger.info("--activity_rec--: %s", act_created)

            if not act_created:
                # Create a new project activity record
                project_activity_data = {
                    'project_activity_name_id': pan_rec.id,
                    'description': pan_rec.description,
                    'name': pan_rec.name,
                    'tower_id': self.id,
                    'project_id': self.project_id.id,
                    'act_type':'development',
                }
                activity_rec = project_activity_obj.create(project_activity_data)
                created_activity_ids.append(activity_rec.id)  # Store created activity ID

                # Create associated project activity types and checklist lines
                for activity_type in pan_rec.panl_ids:
                    project_activity_type_data = {
                        'activity_id': activity_rec.id,
                        'project_actn_id': activity_type.patn_id.id,
                        'name': activity_type.patn_id.name,
                        'project_id': self.project_id.id,
                        'tower_id': self.id
                    }
                    activity_type_re = project_activity_type_obj.create(project_activity_type_data)

                    checklist_data = []
                    for chk in activity_type.patn_id.patnl_ids:
                        checklist_data.append({
                            'activity_type_id': activity_type_re.id,
                            'checklist_template_id': chk.checklist_id.id
                        })
                    project_checklist_line_obj.create(checklist_data)

        # Now, update the `activity_ids` field in the project.tower model
        if created_activity_ids:
            self.write({
                'development_activity_ids': [(4, activity_id) for activity_id in created_activity_ids]
            })
            _logger.info("Appended new activity_ids to project tower: %s", created_activity_ids)

    
    
    # def create_common_activity(self):
    #     project_act_name_obj = self.env['project.activity.name']
    #     project_activity_obj = self.env['project.activity']
    #     project_activity_type_obj = self.env['project.activity.type']
    #     project_checklist_line_obj = self.env['project.checklist.line']
    #     # Search for records in 'project.activity.name' where 'common_activity_group_ids' is set (non-empty)
    #     activities_with_groups = self.env['project.activity.name'].search([
    #     ('common_activity_group_ids', '!=', False)
    #     ])
    #     # Get the IDs of those records
    #     activity_ids = activities_with_groups.ids

    #     # Now, activity_ids contains the IDs of all activities that have 'common_activity_group_ids' set
    #     print("---activity_ids-----",activity_ids)
    #     _logger.info("---activity_idsactivity_ids--. "": %s)",(activity_ids))

    #     for activity in activity_ids:
    #         pan_rec = project_act_name_obj.browse(activity)
    #         _logger.info("--activity_rec--. "": %s)",(pan_rec))

    #         act_created = project_activity_obj.search([('project_id','=',self.project_id.id),('tower_id','=',self.id),('project_activity_name_id','=',activity)])
    #         _logger.info("--activity_rec--. "": %s)",(act_created))
            
    #         if not act_created:
              
    #             project_activity_data = {'project_activity_name_id':pan_rec.id,'description':pan_rec.description,'name':pan_rec.name,'tower_id':self.id,'project_id':self.project_id.id}
    #             activity_rec = project_activity_obj.create(project_activity_data)
    #             #allocation_line.is`_created = 'yes'
    #             for activity_type in pan_rec.panl_ids:
    #                 project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':self.project_id.id,'tower_id':self.id}
    #                 activity_type_re = project_activity_type_obj.create(project_activity_type_data)
    #                 checklist_data = []
    #                 for chk in activity_type.patn_id.patnl_ids:
    #                     checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
    #                 project_checklist_line_obj.create(checklist_data)

class ProjectFlats(models.Model):
    _inherit = 'project.flats'
    _description = "Project Flats"

    vjd_inventory_id = fields.Many2one('vjd.inventory','VJD Inventory',tracking=True,readonly=True)

class ProjectFloors(models.Model):
    _inherit = 'project.floors'
    _description = "Project Floor"

    vjd_inventory_id = fields.Many2one('vjd.inventory','VJD Inventory',tracking=True,readonly=True)