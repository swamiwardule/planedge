from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ProjectTowers(models.Model):
    _inherit = 'project.tower'
    #_order = 'notification_dt desc, id desc'
    _description = "Project Tower"

    businessUnit = fields.Many2one('business.unit','Business Unit')
    subDescription = fields.Char('Sub Description')

    def create_floor_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        vjd_inventory_obj = self.env['vjd.inventory']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        construction_activity_group_obj = self.env['construction.activity.group']
        act_list = []
        if self.tower_floor_line_id:
            for floor in self.tower_floor_line_id[0]:
                if floor.vj_floor_id and floor.name:
                    floor_inv_records = vjd_inventory_obj.search([('floorId', '=', floor.vj_floor_id),('floorDesc','=',floor.name),('floor_activity_group_ids','!=',False)])
                    if floor_inv_records:
                        for record in floor_inv_records:
                            for groups in record.floor_activity_group_ids:
                                for group in groups:
                                    act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', construction_activity_group_obj.search([('id','=',group.id),('type_1','=','floor')]).ids)])
                                    # if construction_activity_group_obj.search([('id','=',group.id),('type_1','=','floor')]):
                                    #     act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', group.id)])
                                    #     if act_records:
                                    #         #_logger.info("---act_records----. "": %s)", act_records)
                                    act_list+=act_records
                #_logger.info("---act_list----. "": %s)", set(act_list))
                act_list = list(set(act_list))
                #print ("-FLOOR--act_list----",act_list)
                _logger.info("-FLOOR--act_list----. "": %s)", set(act_list))

                for act in act_list:
                    activity_rec = project_activity_obj.create({'project_activity_name_id':act.id,'name':act.name,'floor_id':floor.id,'tower_id':floor.tower_id.id,'project_id':floor.project_id.id})
                    for activity_type in act.panl_ids:
                        project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':floor.project_id.id,'tower_id':floor.tower_id.id,'floor_id':floor.id}
                        activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                        checklist_data = []
                        for chk in activity_type.patn_id.patnl_ids:
                            checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                        project_checklist_line_obj.create(checklist_data)
                                    
    def create_flat_activity(self):
        project_act_name_obj = self.env['project.activity.name']
        vjd_inventory_obj = self.env['vjd.inventory']
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        construction_activity_group_obj = self.env['construction.activity.group']
        if self.tower_flat_line_id:
            for flat in self.tower_flat_line_id[0]:
                act_list = []
                if flat.vj_floor_id and flat.name:
                    flat_inv_records = vjd_inventory_obj.search([('floorId', '=', flat.vj_floor_id),('unitNo','=',flat.name),('flat_activity_group_ids','!=',False)])
                    if flat_inv_records:
                        for record in flat_inv_records:
                            for groups in record.flat_activity_group_ids:
                                for group in groups:
                                    act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', construction_activity_group_obj.search([('id','=',group.id),('type_1','=','flat')]))])

                                    #checklist_allocation_line_obj.search([('floor_id','=',floor.id),('chk_flat_id','=', self.id)])   
                                    # if construction_activity_group_obj.search([('id','=',group.id),('type_1','=','flat')]):
                                    #     act_records = project_act_name_obj.search([('construction_activity_group_ids', 'in', group.id)])
                                    #     if act_records:
                                    #         #_logger.info("---act_records----. "": %s)", act_records)
                                    act_list+=act_records
                #_logger.info("---act_list----. "": %s)", set(act_list))
                act_list = list(set(act_list))
                _logger.info("-FLAT--act_list----. "": %s)",(act_list))
                for act in act_list:
                    activity_rec = project_activity_obj.create({'project_activity_name_id':act.id,'name':act.name,'flat_id':flat.id,'tower_id':flat.tower_id.id,'project_id':flat.project_id.id})
                    for activity_type in act.panl_ids:
                        project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':flat.project_id.id,'tower_id':flat.tower_id.id,'flat_id':flat.id}
                        activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                        checklist_data = []
                        for chk in activity_type.patn_id.patnl_ids:
                            checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                        project_checklist_line_obj.create(checklist_data)
                     
        return