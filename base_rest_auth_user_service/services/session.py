import datetime
import time
from odoo import fields
from odoo.http import request, root
from odoo.service import security
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from werkzeug.exceptions import BadRequest
from datetime import datetime, timedelta
import math
import random
import logging
from odoo.http import request, route, Response
import json
from collections import Counter
from pytz import timezone
from odoo import http
import base64
import requests

_logger = logging.getLogger(__name__)

def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


class SessionAuthenticationService(Component):
    _inherit = "base.rest.service"
    _name = "session.authenticate.service"
    _usage = "auth"
    _collection = "session.rest.services"

    @restapi.method([(["/login"], "POST")], auth="public")
    def authenticate(self):
        params = request.params
        db_name = params.get("db")
        request.session.authenticate(
            db_name, params["login"], params["password"])
        result = request.env["ir.http"].session_info()
        # avoid to rotate the session outside of the scope of this method
        # to ensure that the session ID does not change after this method
        _rotate_session(request)
        request.session.rotate = False
        expiration = datetime.utcnow() + timedelta(days=90)
        result["session"] = {
            "sid": request.session.sid,
            "expires_at": fields.Datetime.to_string(expiration),
        }
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        base_url = base_url + \
            "/web/image?model=res.users&field=image_1920&id=" + \
            str(result['uid'])
        result['profile_image'] = base_url
        approver_group_id = self.env.ref(
            'custom_project_management.group_quality_approver')
        approver_group_id = self.env['res.groups'].sudo().browse(
            approver_group_id.id)
        checker_group_id = self.env.ref(
            'custom_project_management.group_quality_checker')
        checker_group_id = self.env['res.groups'].sudo().browse(
            checker_group_id.id)

        maker_group_id = self.env.ref(
            'custom_project_management.group_quality_maker')
        maker_group_id = self.env['res.groups'].sudo().browse(
            maker_group_id.id)

        ###
        hqi_maker_group_id = self.env.ref(
            'custom_project_management.group_maker_hqi')
        hqi_maker_group_id = self.env['res.groups'].sudo().browse(
            hqi_maker_group_id.id)
        
        hqi_checker_group_id = self.env.ref(
            'custom_project_management.group_checker_hqi')
        hqi_checker_group_id = self.env['res.groups'].sudo().browse(
            hqi_checker_group_id.id)
        
        hqi_approver_group_id = self.env.ref(
            'custom_project_management.group_approver_hqi')
        hqi_approver_group_id = self.env['res.groups'].sudo().browse(
            hqi_approver_group_id.id)
        ###

        del_activity_group_id = self.env.ref(
            'custom_project_management.group_delete_activity')
        del_activity_group_id = self.env['res.groups'].sudo().browse(
            del_activity_group_id.id)
        result['del_activity_users'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['del_activity_users'] = True

        result['group_button_submit_flat_hqi'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['group_button_submit_flat_hqi'] = True

        result['group_button_complete_flat_hqi'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['group_button_complete_flat_hqi'] = True

        result['group_button_generate_hqi_pdf'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['group_button_generate_hqi_pdf'] = True

        result['user_type'] = []

        if result['uid'] in approver_group_id.users.ids:
            result['user_type'].append('approver')
        if result['uid'] in checker_group_id.users.ids:
            result['user_type'].append('checker')
        if result['uid'] in maker_group_id.users.ids:
            result['user_type'].append('maker')
        if result['uid'] in hqi_maker_group_id.users.ids:
            result['user_type'].append('hqi_maker')
        if result['uid'] in hqi_checker_group_id.users.ids:
            result['user_type'].append('hqi_checker')
        if result['uid'] in hqi_approver_group_id.users.ids:
            result['user_type'].append('hqi_approver')

        # Default fallback if no group matched
        if not result['user_type']:
            result['user_type'] = ['employee']

        
        # if result['uid'] in approver_group_id.users.ids:
        #     result['user_type'] = 'approver'
        # elif result['uid'] in checker_group_id.users.ids:
        #     result['user_type'] = 'checker'
        # elif result['uid'] in maker_group_id.users.ids:
        #     result['user_type'] = 'maker'
        # elif result['uid'] in hqi_maker_group_id.users.ids:
        #     result['user_type'] = 'hqi_maker'
        # elif result['uid'] in hqi_checker_group_id.users.ids:
        #     result['user_type'] = 'hqi_checker'
        # elif result['uid'] in hqi_approver_group_id.users.ids:
        #     result['user_type'] = 'hqi_approver'
        # else:
        #     result['user_type'] = 'employee'

        return result

    @restapi.method([(["/signup"], "POST")], auth="public")
    def signup(self):
        params = request.params
        user_id = self.env['res.users'].sudo().search(
            [('login', '=', params["email"])], limit=1)
        if user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'User already exists', }),
                            content_type='application/json;charset=utf-8', status=200)

        data = {
            'name': params["name"],
            'login': params["email"],
            'password': params["password"]
        }
        if params.get('lat'):
            data.update({
                'lat': params.get('lat')
            })
        if params.get('long'):
            data.update({
                'longi': params.get('long')
            })

        user_id = self.env["res.users"].sudo().create(data)
        user_id.sudo()._change_password(params["password"])
        if params.get('maker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_maker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('checker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_checker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('approver'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_approver')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'User Signup Done', }),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/signout"], "POST")], auth="user")
    def get_partner(self):
        partner_id = self.env['res.partner'].sudo().search([])

        return {
            'partner_id': str(partner_id.ids)
        }

    @restapi.method([(["/logout"], "POST")], auth="user")
    def logout(self):
        request.session.logout(keep_db=True)
        return {"message": "Successful logout"}

    @restapi.method([(["/get/assigned/projects"], "POST")], auth="user")
    def get_assigned_projects(self):

        project_ids = self.env['project.info'].sudo().search(
            [('visibility', '=', False), ('assigned_to_ids', 'in', self.env.user.id)])
        data_dict = [] 
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        for project in project_ids:
            url = base_url+"/web/image?model=project.info&field=image&id=" + \
                str(project.id)
            # print ("--base_url----",base_url)
            data_dict.append({
                'name': project.name,
                'image': url,
                'project_id': project.id,
                'progress': project.project_progress_bar or 0.0,
                'bu_id':project.bu_id or '',
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data_dict}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/nc"], "POST")], auth="user")
    def get_project_nc(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_data = self.env['project.info'].sudo(
        ).get_project_nc_data(params.get('project_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/tower_floor/nc"], "POST")], auth="user")
    def get_project_tower_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/floor/nc"], "POST")], auth="user")
    def get_project_tower_floor_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_floor_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('floor_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity/nc"], "POST")], auth="user")
    def get_floor_activity_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('floor_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity_type/nc"], "POST")], auth="user")
    def get_floor_activity_type_nc(self):

        params = request.params

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity, Type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_type_nc(
            params.get('activity_id'), params.get('type_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/checklist/nc"], "POST")], auth="user")
    def get_floor_checklist_nc(self):

        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_floor_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For Flat Start

    @restapi.method([(["/get/project/tower_flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_towerflat_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_flat_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('flat_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity/nc"], "POST")], auth="user")
    def get_flat_activity_nc(self):
        #_logger.info("--get_flat_activity_nc----")

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('flat_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity_type/nc"], "POST")], auth="user")
    def get_flat_activity_type_nc(self):

        params = request.params
        if not params.get('activity_id') and not params.get('type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity and Type Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_type_nc(
            params.get('type_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/checklist/nc"], "POST")], auth="user")
    def get_flat_checklist_nc(self):
        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_flat_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For  Flats End

    @restapi.method([(["/get/project_info"], "POST")], auth="user")
    def get_project_info(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_id = self.env['project.info'].sudo().browse(
            int(params.get('project_id')))
        if not project_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        project_image_url = base_url + \
            "/web/image?model=project.info&field=image&id="+str(project_id.id)
        data = {
            'project_name': project_id.name,
            'image_url': project_image_url,
        }
        #_logger.info("-project --data------,%s",str(data))
        list_data = []
        for project_info in project_id.project_details_line:
            line_url = base_url+"/web/image?model=project.details&field=image&id=" + \
                str(project_info.id)
            list_data.append({
                'name': project_info.name,
                'image': line_url,
                'checklist_id': project_info.id,
            })
        data['checklist_data'] = list_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/checklist/tower"], "POST")], auth="user")
    def get_checklist_tower(self):
        params = request.params
        user_id = False
        list_data = []
        progress = 0.0
        if params.get('user_id'):
            user_id = params.get('user_id')
        line_id = int(params.get('checklist_id'))
        if not line_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Line ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        detail_rec = self.env['project.details'].sudo().browse(line_id)
        if not detail_rec:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Line ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        checklist_image_url = base_url + \
            "/web/image?model=project.details&field=image&id=" + \
            str(detail_rec.id)

        data = {
            'checklist_name': detail_rec.name,
            'image_url': checklist_image_url,
            'checklist_id': detail_rec.id,
            # 'progress':checklist_id.project_id.project_progress_bar or 0.0,
        }

        for tower in detail_rec.tower_id:
            progress = tower.project_id.project_progress_bar or 0.0
            # _logger.info("---------6666------")
            user_ids = list(tower.assigned_to_ids.ids)
            if int(user_id) in user_ids:
                list_data.append({
                    'name': tower.name,
                    'tower_id': tower.id,
                    'progress': tower.tower_progress_percentage,  # prject overall progress

                })
        data.update({'progress': progress})
        data['tower_data'] = list_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/checklist/count"], "POST")], auth="user")
    def get_tower_checklist_count(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        tower_id = self.env['project.tower'].sudo().browse(
            int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        data = {
            'tower_name': tower_id.name,
            'tower_id': tower_id.id
        }
        floor_data = []
        for floor in tower_id.tower_floor_line_id:
            submit_count = checked_count = approve_count = 0

            for activity in floor.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

            floor_data.append({
                'name': floor.name,
                'floor_id': floor.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,

            })
        data['floor_data'] = floor_data
        flat_data = []
        for flat in tower_id.tower_flat_line_id:
            submit_count = checked_count = approve_count = 0
            for activity in flat.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

            flat_data.append({
                'name': flat.name,
                # this should be flat_id
                'floor_id': flat.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,
            })

        data['flat_data'] = flat_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/get/flat/floor"], "POST")], auth="user")
    def get_flat_floor_by_tower_test(self):
        def compute_counts(lines, progress_field,type=False):
            total_maker = total_checker = total_approver = total_checklist = 0
            data_list = []

            if type == 'flat' or type == 'floor':
                value = 'floor_id'
                if type == 'flat':
                    value = 'flat_id'

                for line in lines.sorted('sequence'):
                    submit = checked = approved = total = 0
                    for activity in line.activity_ids:
                        for act_type in activity.activity_type_ids:
                            total += 1
                            if act_type.status == 'submit':
                                submit += 1
                            if act_type.status == 'checked':
                                checked += 1
                            if act_type.status == 'approve':
                                approved += 1

                    maker = submit + checked + approved
                    checker = checked + approved

                    total_maker += maker
                    total_checker += checker
                    total_approver += approved
                    total_checklist += total

                    data_list.append({
                        "name": line.name,
                        value : line.id,
                        #"{}_id".format(line._name.split('.')[-1]): line.id,  # dynamic key: flat_id or floor_id
                        "progress": getattr(line, progress_field, 0.0) or 0.0,
                        "total_count": total,
                        "maker_count": maker,
                        "checker_count": checker,
                        "approver_count": approved,
                    })
            else:
                if type == 'development':
                    value = 'dev_act_id'

                    for line in lines:
                        submit = checked = approved = total = 0
                        for activity in line.development_activity_ids:
                            for act_type in activity.activity_type_ids:
                                total += 1
                                if act_type.status == 'submit':
                                    submit += 1
                                if act_type.status == 'checked':
                                    checked += 1
                                if act_type.status == 'approve':
                                    approved += 1

                        maker = submit + checked + approved
                        checker = checked + approved

                        total_maker += maker
                        total_checker += checker
                        total_approver += approved
                        total_checklist += total

                        data_list.append({
                            "name": line.name,
                            value : line.id,
                            #"{}_id".format(line._name.split('.')[-1]): line.id,  # dynamic key: flat_id or floor_id
                            "progress": getattr(line, progress_field, 0.0) or 0.0,
                            "total_count": total,
                            "maker_count": maker,
                            "checker_count": checker,
                            "approver_count": approved,
                        })
                if type == 'common':
                    value = 'common_act_id'
                    for line in lines:
                        submit = checked = approved = total = 0
                        for activity in line.activity_ids:
                            for act_type in activity.activity_type_ids:
                                total += 1
                                if act_type.status == 'submit':
                                    submit += 1
                                if act_type.status == 'checked':
                                    checked += 1
                                if act_type.status == 'approve':
                                    approved += 1

                        maker = submit + checked + approved
                        checker = checked + approved

                        total_maker += maker
                        total_checker += checker
                        total_approver += approved
                        total_checklist += total

                        data_list.append({
                            "name": line.name,
                            value : line.id,
                            #"{}_id".format(line._name.split('.')[-1]): line.id,  # dynamic key: flat_id or floor_id
                            "progress": getattr(line, progress_field, 0.0) or 0.0,
                            "total_count": total,
                            "maker_count": maker,
                            "checker_count": checker,
                            "approver_count": approved,
                        })

            #_logger.info("-data_listdata_list---,%s",str(data_list))
            
            return total_checklist, total_maker, total_checker, total_approver, data_list

        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower_id = self.env['project.tower'].sudo().browse(int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        # Compute floor and flat details
        floor_total, floor_maker, floor_checker, floor_approver, floor_data = compute_counts(
            tower_id.tower_floor_line_id, 'floor_progress_percentage','floor'
        )
        flat_total, flat_maker, flat_checker, flat_approver, flat_data = compute_counts(
            tower_id.tower_flat_line_id, 'flats_progress_percentage','flat'
        )
        com_total, com_maker, com_checker, com_approver, com_data = compute_counts(
            tower_id, 'progress_percentage','common'
        )
        dev_total, dev_maker, dev_checker, dev_approver, dev_data = compute_counts(
            tower_id, 'progress_percentage','development'
        )
        # _logger.info("---tower_total_count-----,%s",str(data['tower_total_count']))


        data = {
            "tower_name": tower_id.name,
            "tower_id": tower_id.id,
            "progress": tower_id.tower_progress_percentage,
            "tower_total_count": flat_total + floor_total,
            "tower_maker_count": flat_maker + floor_maker,
            "tower_checker_count": flat_checker + floor_checker,
            "tower_approver_count": flat_approver + floor_approver,
            "flat_total_count": flat_total,
            "flat_maker_count": flat_maker,
            "flat_checker_count": flat_checker,
            "flat_approver_count": flat_approver,
            "floor_total_count": floor_total,
            "floor_maker_count": floor_maker,
            "floor_checker_count": floor_checker,
            "floor_approver_count": floor_approver,
            "list_flat_data": flat_data,
            "list_floor_data": floor_data,
            "com_total": com_total,
            "com_maker": com_maker,
            "com_checker": com_checker,
            "com_approver": com_approver,
            "com_data": com_data,
            "dev_total": dev_total,
            "dev_maker": dev_maker,
            "dev_checker": dev_checker,
            "dev_approver": dev_approver,
            "dev_data": dev_data,
        }    
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    

    # @restapi.method([(["/get/flat/floor"], "POST")], auth="user")
    # def get_flat_floor_by_tower_test(self):
    #     params = request.params
    #     if not params.get('tower_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     tower_id = self.env['project.tower'].sudo().browse(
    #         int(params.get('tower_id')))
    #     if not tower_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     get_param = self.env['ir.config_parameter'].sudo().get_param
    #     # = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')

    #     data = {
    #         "tower_name": tower_id.name,
    #         "tower_id": tower_id.id,
    #         "progress": tower_id.tower_progress_percentage,  # tower progress
    #     }

    #     flat_maker = flat_checker = flat_approver = flat_checklist = 0
    #     floor_maker = floor_checker = floor_approver = floor_checklist = 0

    #     floor_data = []
    #     for floor in tower_id.tower_floor_line_id.sorted('sequence'):
    #         submit_count = checked_count = approve_count = total_checklist_count = 0

    #         for activity in floor.activity_ids:
    #             for act_type in activity.activity_type_ids:
    #                 status = act_type.status
    #                 total_checklist_count += 1
    #                 if status == 'submit':
    #                     submit_count += 1
    #                 if status == 'checked':
    #                     checked_count += 1
    #                 if status == 'approve':
    #                     approve_count += 1

    #         floor_maker += submit_count+checked_count+approve_count
    #         floor_checker += checked_count+approve_count
    #         floor_approver += approve_count
    #         floor_checklist += total_checklist_count

    #         floor_data.append({
    #             "name": floor.name,
    #             "floor_id": floor.id,
    #             "progress": floor.floor_progress_percentage or 0.0,
    #             "total_count": total_checklist_count,
    #             "maker_count": submit_count+checked_count+approve_count,
    #             "checker_count": checked_count+approve_count,
    #             "approver_count": approve_count,
    #         })

    #     floor_total = floor_checklist
    #     flat_data = []
    #     for flat in tower_id.tower_flat_line_id.sorted('sequence'):
    #         submit_count = checked_count = approve_count = total_checklist_count = 0
    #         for activity in flat.activity_ids:
    #             for act_type in activity.activity_type_ids:
    #                 status = act_type.status
    #                 total_checklist_count += 1
    #                 if status == 'submit':
    #                     submit_count += 1
    #                 if status == 'checked':
    #                     checked_count += 1
    #                 if status == 'approve':
    #                     approve_count += 1

    #         flat_maker += submit_count+checked_count+approve_count
    #         flat_checker += checked_count+approve_count
    #         flat_approver += approve_count
    #         flat_checklist += total_checklist_count
    #         flat_data.append({
    #             "name": flat.name,
    #             "flat_id": flat.id,
    #             "progress": flat.flats_progress_percentage or 0.0,
    #             "total_count": total_checklist_count,
    #             "maker_count": submit_count+checked_count+approve_count,
    #             "checker_count": checked_count+approve_count,
    #             "approver_count": approve_count,
    #         })

    #     flat_total = flat_checklist
    #     data["tower_total_count"] = flat_total+floor_total
    #     data["tower_maker_count"] = flat_maker+floor_maker
    #     data["tower_checker_count"] = flat_checker+floor_checker
    #     data["tower_approver_count"] = flat_approver+floor_approver
    #     data["flat_total_count"] = flat_total
    #     data["flat_maker_count"] = flat_maker
    #     data["flat_checker_count"] = flat_checker
    #     data["flat_approver_count"] = flat_approver
    #     data["floor_total_count"] = floor_total
    #     data["floor_maker_count"] = floor_maker
    #     data["floor_checker_count"] = floor_checker
    #     data["floor_approver_count"] = floor_approver
    #     data['list_flat_data'] = flat_data
    #     data['list_floor_data'] = floor_data

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)

    # @restapi.method([(["/get/flat/activites"], "POST")], auth="user")
    # def get_flat_activites(self):
    #     params = request.params
    #     #_logger.info("-get_flat_activites--params-----,%s",params)

    #     flat_id = params.get('flat_id')

    #     # Check if flat_id is missing, empty, or not a valid integer
    #     if not flat_id or flat_id in ['null', 'None']:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     try:
    #         flat_id = int(flat_id)
    #     except (ValueError, TypeError):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     flat_id = self.env['project.flats'].sudo().browse(
    #         int(params.get('flat_id')))
    #     if not flat_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Flat ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     data = {
    #         'flat_name': flat_id.name,
    #         'flat_id': flat_id.id
    #     }

    #     list_flat_data = []
    #     total_count = 0
    #     for activity in flat_id.activity_ids:
    #         count = draft = checked = approve = 0
    #         color = 'yellow'
    #         activity_type_status = False
    #         for act_type in activity.activity_type_ids:
    #             status = act_type.status
    #             count += 1
    #             if status == 'draft':
    #                 draft += 1
    #             if status == 'checked':
    #                 checked += 1
    #             if status == 'approve':
    #                 approve += 1

    #         total_count += count
    #         if draft and not checked and not approve:
    #             color = 'red'
    #         if approve and not draft and not checked:
    #             color = 'green'
    #             activity_type_status = True

    #         list_flat_data.append({
    #             'name': activity.name,
    #             'desc': '',
    #             'activity_id': activity.id,
    #             'write_date': str(activity.write_date),
    #             'activity_type_status': activity_type_status,
    #             'progress': activity.progress_percentage or 0.0,
    #             'color': color,
    #         })
    #     data['list_flat_data'] = list_flat_data
    #     data['total_count'] = total_count

    #     # _logger.info("-----data------,%s",data)

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)

    # @restapi.method([(["/get/floor/activites"], "POST")], auth="user")
    # def get_floor_activites(self):
    #     params = request.params
    #     #_logger.info("-get_floor_activites--params-----,%s",params)
    #     ###
    #     floor_id = params.get('floor_id')
    #     # Check if flat_id is missing, empty, or not a valid integer
    #     if not floor_id or floor_id in ['null', 'None']:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     try:
    #         floor_id = int(floor_id)
    #     except (ValueError, TypeError):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     ###
    #     floor_id = self.env['project.floors'].sudo().browse(
    #         int(params.get('floor_id')))
    #     if not floor_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Floor ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     data = {
    #         'floor_name': floor_id.name,
    #         'floor_id': floor_id.id
    #     }
    #     list_floor_data = []
    #     total_count = 0
    #     for activity in floor_id.activity_ids:
    #         count = draft = checked = approve = 0
    #         color = 'yellow'
    #         activity_type_status = False

    #         for act_type in activity.activity_type_ids:
    #             status = act_type.status
    #             count += 1
    #             if status == 'draft':
    #                 draft += 1
    #             if status == 'checked':
    #                 checked += 1
    #             if status == 'approve':
    #                 approve += 1

    #         total_count += count
    #         if draft and not checked and not approve:
    #             color = 'red'
    #         if approve and not draft and not checked:
    #             color = 'green'
    #             activity_type_status = True

    #         list_floor_data.append({
    #             'name': activity.name,
    #             'desc': '',
    #             'activity_id': activity.id,
    #             'write_date': str(activity.write_date),
    #             'activity_type_status': activity_type_status,
    #             'progress': activity.progress_percentage or 0.0,
    #             'color': color,
    #         })
    #     data['list_floor_data'] = list_floor_data
    #     data['total_count'] = total_count

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)


#change by swami for last updated time 
    def _get_activity_last_update(self, activity):
        """
        Return the most recent write_date (as a string) among:
        - the activity
        - its activity_type_ids
        The returned string is converted to the requesting user's timezone if possible.
        Returns '' when no date found.
        """
        # Collect write_date strings
        dates = []
        if activity.write_date:
            dates.append(activity.write_date)
        # mapped returns list of strings (may include falsy values)
        dates += activity.mapped('activity_type_ids.write_date') or []
        # keep only truthy values
        dates = [d for d in dates if d]
        if not dates:
            return ''

        # Convert to datetime objects (UTC)
        try:
            dt_objs = [fields.Datetime.from_string(d) for d in dates]
        except Exception:
            # fallback: return the max string (rare)
            return max(dates)

        last_dt = max(dt_objs)  # this is a naive UTC datetime (Odoo stores UTC)

        # Convert to user's timezone if possible
        try:
            user = request.env.user
            local_dt = fields.Datetime.context_timestamp(user, last_dt)
            return fields.Datetime.to_string(local_dt)
        except Exception:
            # if timezone conversion fails, return UTC string
            return fields.Datetime.to_string(last_dt)


    @restapi.method([(["/get/flat/activites"], "POST")], auth="user")
    def get_flat_activites(self):
        params = request.params
        flat_id = params.get('flat_id')
        if not flat_id or flat_id in ['null', 'None']:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        try:
            flat_int = int(flat_id)
        except (ValueError, TypeError):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        flat = self.env['project.flats'].sudo().browse(flat_int)
        if not flat.exists():
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = {'flat_name': flat.name, 'flat_id': flat.id}
        list_flat_data = []
        total_count = 0

        # iterate activities
        for activity in flat.activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                elif status == 'checked':
                    checked += 1
                elif status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            last_update = self._get_activity_last_update(activity)

            list_flat_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': last_update or '',
                'activity_type_status': activity_type_status,
                'progress': float(activity.progress_percentage or 0.0),
                'color': color,
            })

        data['list_flat_data'] = list_flat_data
        data['total_count'] = total_count

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/get/floor/activites"], "POST")], auth="user")
    def get_floor_activites(self):
        params = request.params
        floor_id = params.get('floor_id')
        if not floor_id or floor_id in ['null', 'None']:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        try:
            floor_int = int(floor_id)
        except (ValueError, TypeError):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        floor = self.env['project.floors'].sudo().browse(floor_int)
        if not floor.exists():
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Floor ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = {'floor_name': floor.name, 'floor_id': floor.id}
        list_floor_data = []
        total_count = 0

        for activity in floor.activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                elif status == 'checked':
                    checked += 1
                elif status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            last_update = self._get_activity_last_update(activity)

            list_floor_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': last_update or '',
                'activity_type_status': activity_type_status,
                'progress': float(activity.progress_percentage or 0.0),
                'color': color,
            })

        data['list_floor_data'] = list_floor_data
        data['total_count'] = total_count

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)


    # color coding
    # 2
    # @restapi.method([(["/get/checklist"], "POST")], auth="user")
    # def get_checklist_by_activity(self):
    #     params = request.params
    #     user_id = ''
    #     role = ''

    #     get_param = self.env['ir.config_parameter'].sudo().get_param
    #     base_url = get_param(
    #         'web.base.url', default='http://www.odoo.com?NoBaseUrl')

    #     # if not params.get('user_id'):
    #     #     return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User Id'}),
    #     #             content_type='application/json;charset=utf-8', status=201)
    #     # user_id = params.get('user_id')
    #     # user_record = self.env['res.users'].browse(user_id)
    #     if not params.get('activity_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     activity_id = self.env['project.activity'].sudo().browse(
    #         int(params.get('activity_id')))
    #     if not activity_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     data = {
    #         'activity_name': activity_id.name,
    #         'activity_id': activity_id.id,
    #         'activity_progress': activity_id.progress_percentage,
    #         'project_id': activity_id.project_id.id,
    #         'project_name': activity_id.project_id.name,
    #         'tower_id': activity_id.tower_id.id,
    #         'tower_name': activity_id.tower_id.name,
    #         'floor_id': activity_id.floor_id.id or False,
    #         'floor_name': activity_id.floor_id.name or False,
    #     }

    #     list_checklist_data = []

    #     # pre,during,post
    #     total_count = 0

    #     for activity in activity_id.activity_type_ids:
    #         count = draft = checked = approve = 0
    #         color = 'yellow'
    #         reject = ''
    #         if activity.type_status:
    #             if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
    #                 reject = activity.type_status

    #         # status = activity.status
    #         # count += 1
    #         # if status == 'draft':
    #         #     draft += 1
    #         # if status == 'checked':
    #         #     checked += 1
    #         # if status == 'approve':
    #         #     approve += 1

    #         # total_count += count
    #         # if draft and not checked and not approve:
    #         #     color = 'red'
    #         # if approve and not draft and not checked:
    #         #     color = 'green'

    #         status = activity.status
    #         color = 'yellow'  # Default color
    #         if status in ['draft', 'submit', 'checker_reject']:
    #             color = 'red'
    #         elif status == 'checked':
    #             color = 'yellow'
    #         elif status == 'approve':
    #             color = 'green'

    #         line_data = []
    #         # logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
    #         for checklist_line in activity.checklist_ids:
    #             history = []
    #             log_lines = self.env['project.checklist.line.log'].search(
    #                 [('line_id', '=', checklist_line.id)])

    #             for line in log_lines:
    #                 image_link = []
    #                 for url in line.checklist_line_log_line:
    #                     # _logger.info("-url------,%s",str(url))
    #                     image_link.append(url.url)
    #                 history.append({
    #                     'id': line.id,
    #                     'name': line.checklist_template_id.name,
    #                     'reason': line.reason,
    #                     'is_pass': line.is_pass,
    #                     'name': line.checklist_template_id.name,
    #                     'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
    #                     'update_time': str(line.datetime),
    #                     'image_url': image_link,
    #                     'submitted': 'false',
    #                 })

    #             image_link = []
    #             for image_line in checklist_line.image_ids:
    #                 checklist_image_url = str(
    #                     base_url)+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
    #                 image_link.append(checklist_image_url)

    #             line_data.append({
    #                 'name': checklist_line.checklist_template_id.name,
    #                 'reason': checklist_line.reason,
    #                 'is_pass': checklist_line.is_pass,
    #                 'name': checklist_line.checklist_template_id.name,
    #                 'image_url': image_link,
    #                 'line_id': checklist_line.id,
    #                 'history': history
    #                 # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
    #                 # 'update_time':datetime.datetime.now(),
    #             })

    #         # activity_status = activity.status
    #         # if activity.status == 'approver_reject':
    #         #     activity_status = 'submit'
    #         # if activity.status == 'checker_reject':
    #         #     activity_status = 'draft'

    #         activity_status = activity.type_status
    #         _logger.info("-------activity_status-----,%s", activity_status)

    #         try:
    #             image_urls = []
    #             if activity.activity_type_img_ids:
    #                 for img in activity.activity_type_img_ids:
    #                     if img.img_type == 'pat':
    #                         checklist_image_url = str(
    #                             base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
    #                         image_urls.append(str(checklist_image_url))
    #         except Exception as e:
    #             _logger.info(
    #                 "-get_project_activity_details--exception- overall_images-----,%s", str(e))
    #             pass
    #         # _logger.info("-------color-----,%s",str(color))

    #         list_checklist_data.append({
    #             'name': activity.name,
    #             'activity_type_id': activity.id,
    #             'activity_status': activity_status,
    #             'activity_type_progress': activity.progress_percentage,
    #             'project_id': activity.project_id.id,
    #             'project_name': activity.project_id.name,
    #             'flat': activity.flat_id.id or False,
    #             'flat_name': activity.flat_id.name or False,
    #             'tower_id': activity.tower_id.id,
    #             'tower_name': activity.tower_id.name,
    #             'floor_id': activity.floor_id.id or False,
    #             'floor_name': activity.floor_id.name or False,
    #             'overall_remarks': activity.overall_remarks or '',
    #             'overall_images': image_urls,
    #             'line_data': line_data,
    #             'color': color,
    #             'wi_status': reject,
    #         })

    #     data['list_checklist_data'] = list_checklist_data
    #     # _logger.info("-gimage_urlsimage_urls----,%s",str(data))

    #     # data['color'] = color

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist info Fetch', 'checklist_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/checklist"], "POST")], auth="user")
    def get_checklist_by_activity(self):
        params = request.params
        user_id = ''
        role = ''

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        # if not params.get('user_id'):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User Id'}),
        #             content_type='application/json;charset=utf-8', status=201)
        # user_id = params.get('user_id')
        # user_record = self.env['res.users'].browse(user_id)
        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_id = self.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = {
            'activity_name': activity_id.name,
            'activity_id': activity_id.id,
            'activity_progress': activity_id.progress_percentage,
            'project_id': activity_id.project_id.id,
            'project_name': activity_id.project_id.name,
            'tower_id': activity_id.tower_id.id,
            'tower_name': activity_id.tower_id.name,
            'floor_id': activity_id.floor_id.id or False,
            'floor_name': activity_id.floor_id.name or False,
        }

        list_checklist_data = []

        # pre,during,post
        total_count = 0

        for activity in activity_id.activity_type_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            reject = ''
            if activity.type_status:
                if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
                    reject = activity.type_status
                    _logger.info("=================activity.type_status=============,%s", reject)

            # status = activity.status
            # count += 1
            # if status == 'draft':
            #     draft += 1
            # if status == 'checked':
            #     checked += 1
            # if status == 'approve':
            #     approve += 1

            # total_count += count
            # if draft and not checked and not approve:
            #     color = 'red'
            # if approve and not draft and not checked:
            #     color = 'green'

            # for color by Swami
            status = activity.status
            color = 'yellow'  # Default color
            if status in ['draft', 'submit', 'checker_reject']:
                color = 'red'
            elif status == 'checked':
                color = 'yellow'
            elif status == 'approve':
                color = 'green'

            line_data = []
            # logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
            for checklist_line in activity.checklist_ids:
                history = []
                log_lines = self.env['project.checklist.line.log'].search(
                    [('line_id', '=', checklist_line.id)])

                for line in log_lines:
                    image_link = []
                    for url in line.checklist_line_log_line:
                        # _logger.info("-url------,%s",str(url))
                        image_link.append(url.url)
                    history.append({
                        'id': line.id,
                        'name': line.checklist_template_id.name,
                        'reason': line.reason,
                        'is_pass': line.is_pass,
                        'name': line.checklist_template_id.name,
                        'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                        'update_time': str(line.datetime),
                        'image_url': image_link,
                        'submitted': 'false',
                    })

                image_link = []
                for image_line in checklist_line.image_ids:
                    checklist_image_url = str(
                        base_url)+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
                    image_link.append(checklist_image_url)

                line_data.append({
                    'name': checklist_line.checklist_template_id.name,
                    'reason': checklist_line.reason,
                    'is_pass': checklist_line.is_pass,
                    'name': checklist_line.checklist_template_id.name,
                    'image_url': image_link,
                    'line_id': checklist_line.id,
                    'history': history
                    # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
                    # 'update_time':datetime.datetime.now(),
                })

            activity_status = activity.status
            if activity.status == 'approver_reject':
                activity_status = 'submit'
            if activity.status == 'checker_reject':
                activity_status = 'draft'

            try:
                image_urls = []
                if activity.activity_type_img_ids:
                    for img in activity.activity_type_img_ids:
                        if img.img_type == 'pat':
                            checklist_image_url = str(
                                base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
                            image_urls.append(str(checklist_image_url))
            except Exception as e:
                _logger.info(
                    "-get_project_activity_details--exception- overall_images-----,%s", str(e))
                pass
            # _logger.info("-------color-----,%s",str(color))

            list_checklist_data.append({
                'name': activity.name,
                'activity_type_id': activity.id,
                'activity_status': activity_status,
                'activity_type_progress': activity.progress_percentage,
                'project_id': activity.project_id.id,
                'project_name': activity.project_id.name,
                'flat': activity.flat_id.id or False,
                'flat_name': activity.flat_id.name or False,
                'tower_id': activity.tower_id.id,
                'tower_name': activity.tower_id.name,
                'floor_id': activity.floor_id.id or False,
                'floor_name': activity.floor_id.name or False,
                'overall_remarks': activity.overall_remarks or '',
                'overall_images': image_urls,
                'line_data': line_data,
                'color': color,
                'wi_status': reject,
            })

        data['list_checklist_data'] = list_checklist_data
        # _logger.info("-gimage_urlsimage_urls----,%s",str(data))

        # data['color'] = color

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist info Fetch', 'checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    # AAAAAA overall remark - 2 images -
    @restapi.method([(["/maker/checklist/update"], "POST")], auth="user")
    def update_checklist_maker(self):
        pr_act_ty_img_obj = self.env['project.activity.type.image']
        # maker will update the checklist and click on submit button notification should sent to res. checker
        seq_no = 0
        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        # _logger.info("---------update_checklist_maker---------,%s", params)
        # user_id = False
        # send_notification = False
        user_id = params.get('user_id', False)
        send_notification = str(params.get('is_draft', 'yes')) == 'no'
        if params.get('is_draft'):
            # _logger.info("---------params--------,%s", params)
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        seq_no = activity_type_id.seq_no

        try:
            if params.get('overall_images'):
                images = params.get('overall_images')
                data = []
                for img in images:
                    temp = {'activity_type_id': activity_type_id.id,
                            'overall_img': img, 'img_type': 'pat'}
                    data.append(temp)
                if data:
                    pr_act_ty_img_obj.create(data)
        except Exception as e:
            _logger.info("---exception- overall_images-----,%s", str(e))
            pass

        if activity_type_id and user_id:
            activity_type_id.user_maker = user_id

        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})

                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                # print ("--image_datas---",image_datas)
                # _logger.info("----- No -------,%s",send_notification)

                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'maker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    # _logger.info("----- image datas -------,%s",len(image_datas))

                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    # _logger.info("----- image_urls -------,%s",len(image_urls))

                    for url in image_urls:
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        if send_notification:
            activity_type_id.sudo().button_submit(seq_no, user_id)
        # Maintining Log Details
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_reject_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # user_id = int(params.get('user_id')) or False
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no
        activity_type_id.is_calculated = False

        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    # seq_no = checklist_id.activity_type_id.seq_no
                    # _logger.info("-----seq_no-------,%s",seq_no)

                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false','first_time_check':False,'is_calculated':False})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)

                data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'), 'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks}
                pcl_log = self.env['project.checklist.line.log'].create(data)
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                for url in image_urls:
                    #_logger.info("-----url checker reject------,%s", url)
                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        activity_type_id.sudo().button_set_to_maker(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/update"], "POST")], auth="user")
    def update_checklist_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params
        seq_no = False
        user_id = False
        send_notification = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id
            activity_type_id.is_calculated = False

        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no
        # if activity_type_id.activity_id and user_id:
        #     activity_type_id.activity_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                # print('-------overall_remarks-----\n\n\n\n\n', checklist_id)
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false','first_time_check':False,'is_calculated':False})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                # if line.get('overall_remarks'):
                #     checklist_id.write({'overall_remarks':line.get('overall_remarks')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)

                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # user_id = int(params.get('user_id')) or False
        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_checking_done(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'Maker'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
        # _logger.info("---------update_checklist_reject---------,%s", params)
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id
        seq_no = activity_type_id.seq_no
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)

                data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'approver', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'), 'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks}
                pcl_log = self.env['project.checklist.line.log'].create(data)
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                #_logger.info(
                    # "----checker-update--image_urls----,%s", image_urls)

                for url in image_urls:
                    #_logger.info("----checker-update------,%s", url)

                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        activity_type_id.sudo().button_set_to_checker(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)
    ###f9afbbab36250d7c75a9da244734e950b6563975
    # @restapi.method([(["/test/func"], "POST")], auth="public")
    # def test_func(self):
    #     params = request.params
    #     _logger.info("---------test_func---------,%s", params)
    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Test Func','tower_data': {"hi":"hello"}}),
    #                     content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/checklist/update"], "POST")], auth="user")
    def update_checklist_approver(self):
        # approver will update the checklist and notification to admin
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        seq_no = False
        params = request.params
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no

        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id

        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'approver', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        #_logger.info("----approver-update------,%s", url)
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_approve(seq_no, user_id)
           #_logger.info("---activity_type_id--9999--,%s", activity_type_id)

            try:
                if activity_type_id.activity_id and activity_type_id.activity_id.state == 'completed':
                    act_obj = activity_type_id.activity_id
                    only_floor = bool(act_obj.floor_id and not act_obj.flat_id)

                    def get_activity_groups(group_ids):
                        return [
                            {"id": act.id, "activity_group_id": act.activity_group_id,
                                "name": act.name}
                            for act in (group_ids or [])
                        ]

                    con_act_list = get_activity_groups(
                        act_obj.project_activity_name_id.construction_activity_group_ids)
                    common_act_list = get_activity_groups(
                        act_obj.project_activity_name_id.common_activity_group_ids)
                    dev_act_list = get_activity_groups(
                        act_obj.project_activity_name_id.development_activity_group_ids)

                    tower = act_obj.tower_id
                    sub_id = tower.sub_business_unit_id.subId if tower and tower.sub_business_unit_id else ''
                    hierarchy_id = tower.vjd_pro_hie_id.hierarchyId if tower and tower.vjd_pro_hie_id else ''
                    project_hierarchy_bu_id = tower.vjd_pro_hie_id.buId if tower and tower.vjd_pro_hie_id else ''
                    business_unit = getattr(tower, 'businessUnit', None)

                    data = {
                        "project_info": {
                            "project_id": act_obj.project_id.id if act_obj.project_id else '',
                            "project_name": act_obj.project_id.name if act_obj.project_id else '',
                            "tower_id": tower.id if tower else '',
                            "sub_id": sub_id,
                            "hierarchy_id": hierarchy_id,
                            "project_hierarchy_bu_id": project_hierarchy_bu_id,
                            "tower_name": tower.name if tower else '',
                            "activity_type_id": activity_type_id.id,
                            "activity_type_name": activity_type_id.name,
                            "activity_id": act_obj.id,
                            "activity_name": act_obj.name,
                            "business_unit_name": business_unit.description if business_unit else '',
                            "bu_id": business_unit.buId if business_unit else '',
                            "construction_activity_groups": con_act_list,
                            "common_activity_groups": common_act_list,
                            "development_activity_groups": dev_act_list,
                        },
                        "floor_info": {},
                        "flat_info": {},
                        "scpl_info": {}
                    }

                    if only_floor and act_obj.floor_id:
                        floor = act_obj.floor_id
                        data["floor_info"].update({
                            #"floor_id": floor.id,
                            "floorId": floor.vj_floor_id,
                            "floor_name": floor.name,
                            #"status": floor.vjd_inventory_id.status if floor.vjd_inventory_id else ''
                        })
                    elif act_obj.flat_id:
                        flat = act_obj.flat_id
                        flat_inventory = getattr(
                            flat, 'vjd_inventory_id', None)
                        data["flat_info"].update({
                            "floorId": flat_inventory.floorId if flat_inventory else '',
                            "floor_name": flat_inventory.floorDesc if flat_inventory else '',
                            "flat_id": flat.id,
                            "unit_id": flat_inventory.unitId if flat_inventory else '',
                            "unit_no": flat_inventory.unitNo if flat_inventory else '',
                            "flat_name": flat.name,
                            "status": flat_inventory.status if flat_inventory else ''
                        })

                        data["floor_info"].update({
                            "floorId": flat_inventory.floorId if flat_inventory else '',
                            "floor_name": flat_inventory.floorDesc if flat_inventory else '',
                        })

                    if tower and tower.vjd_bu_hie_id:
                        scpl_obj = tower.vjd_bu_hie_id
                        data["scpl_info"].update({
                            "segment_id": scpl_obj.segmentId,
                            "segment_name": scpl_obj.segName,
                            "bu_code": scpl_obj.buCode,
                            "parent_id": scpl_obj.parentId,
                            "scpl_buid": scpl_obj.scplBuId
                        })
                    #_logger.info("---data----,%s", data)

                    act_obj.data = str(data)

                    #response = self.env['project.activity'].sudo(
                    #).submit_checklist(data)
                    #if response.get('status') != 'success':
                    #    act_obj.status_code = 400
                    #else:
                    #    act_obj.status_code = 200
                    #act_obj.response = json.dumps(response)

                    #{'project_info': {'project_id': 167, 'project_name': 'VJ - ETERNITEE', 'tower_id': 319, 'sub_id': 97, 'hierarchy_id': 499, 'project_hierarchy_bu_id': 130, 'tower_name': 'B BUILDING', 'activity_type_id': 2301620, 'activity_type_name': 'Post', 'activity_id': 786812, 'activity_name': 'Brickwork', 'business_unit_name': 'VJ - ETERNITEE', 'bu_id': 11, 'construction_activity_groups': [{'id': 4, 'activity_group_id': 4, 'name': 'BLOCKWORK AND PLASTER'}], 'common_activity_groups': [], 'development_activity_groups': []}, 'floor_info': {}, 'flat_info': {'floorId': 243, 'floor_name': 'FLOOR 1', 'flat_id': 16379, 'unit_id': 10383469, 'unit_no': '101', 'flat_name': '101', 'status': 'Booked'}, 'scpl_info': {'segment_id': 4, 'segment_name': 'RERA', 'bu_code': 'EY', 'parent_id': 56, 'scpl_buid': '11'}}

            except Exception as e:
                #_logger.exception("--Exception--e-9999- %s", str(e))
                act_obj.error = str(e)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/user/location"], "POST")], auth="user")
    def update_location_user(self):
        params = request.params
        if not params.get('lat'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send latitude'}),
                            content_type='application/json;charset=utf-8', status=201)
        if not params.get('long'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send longitude'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env.user.sudo().write({
            'lat': params.get('lat'),
            'longi': params.get('long'),

        })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Location Update'}),
                        content_type='application/json;charset=utf-8', status=200)
    # API FOR OFFLINE

    @restapi.method([(["/get/projects/offline"], "POST")], auth="user")
    def get_project_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        projects = self.env['project.info'].sudo().search(
            [('visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not projects:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Projects Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)

        data = []
        for project in projects:
            image = ''
            if project.image:
                image = base64.b64encode(project.image).decode('utf-8')
            pdata = {'id': project.id, 'name': project.name, 'image': image}
            detail_line = []
            for line in project.project_details_line:
                image = ''
                if line.image:
                    image = base64.b64encode(line.image).decode('utf-8')
                detail_line.append(
                    {'id': line.id, 'name': line.name, 'image': image})
            pdata['details_line'] = detail_line
            data.append(pdata)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Data Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/offline"], "POST")], auth="user")
    def get_tower_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Towers Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                tdata = {'id': tower.id, 'name': tower.name,
                         'project_id': project_id}
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    tdata['details_line_ids'] = detail_lines[0]
                    data.append(tdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/offline"], "POST")], auth="user")
    def get_floors_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        fdata = {'id': floor.id, 'name': floor.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}

                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Floors Data Fetch', 'floor_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/offline"], "POST")], auth="user")
    def get_flats_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        fdata = {'id': flat.id, 'name': flat.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}
                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flats Data Fetch', 'flat_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/offline"], "POST")], auth="user")
    def get_floors_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/offline"], "POST")], auth="user")
    def get_flats_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/types/offline"], "POST")], auth="user")
    def get_floors_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'floors_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/types/offline"], "POST")], auth="user")
    def get_flats_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Activity Data Fetch', 'flats_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/checklist/offline"], "POST")], auth="user")
    def get_flats_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flats Checklist Data Fetch', 'flats_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/checklist/offline"], "POST")], auth="user")
    def get_floors_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Checklist Data Fetch', 'floors_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/activity"], "POST")], auth="user")
    def delete_activities(self):
        params = request.params
        # _logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)

        actvity = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        actvity.activity_type_ids.unlink()
        actvity.unlink()

        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': ' Activity(s) Deleted'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/duplicate/activities/create"], "POST")], auth="user")
    def create_duplicate_activities(self):
        params = request.params

        # _logger.info("--create_duplicate_activities--params-1233333444-",params)

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)
        activity_id = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity ID does not exist'}),
                            content_type='application/json;charset=utf-8', status=400)
        # Get the base name of the activity
        base_name = activity_id.name
        count = activity_id.count

        # _logger.info("--FLAT-121212-",activity_id.flat_id.name)
        # _logger.info("--FLOOR-1212121-",activity_id.floor_id.name)
        f_name = ''
        if activity_id.flat_id:
            for activity in activity_id.flat_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.flat_id.name
                building_name = activity_id.flat_id.tower_id.name
                project = activity_id.flat_id.project_id.name

        if activity_id.floor_id:
            for activity in activity_id.floor_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.floor_id.name
                building_name = activity_id.floor_id.tower_id.name
                project = activity_id.floor_id.project_id.name

        # Find the next available number suffix
        # duplicate_activities = request.env['project.activity'].sudo().search([('name', 'ilike', base_name)])
        # suffix = len(duplicate_activities)
        # Generate the name for the duplicate activity
        duplicate_name = f"{base_name}_{count}"
        vals = {
            "name": duplicate_name,
            "tower_id": activity_id.tower_id.id if activity_id.tower_id else False,
            "flat_id": activity_id.flat_id.id or False,
            "project_id": activity_id.project_id.id,
            "floor_id": activity_id.floor_id.id or False,
            "project_activity_name_id": activity_id.project_activity_name_id.id,
            "project_activity_id": activity_id.project_activity_id.id,
            "description": activity_id.description,
            # "progress_percentage": activity_id.progress_percentage,
            # "activity_type_ids": [(6, 0, activity_id.activity_type_ids.ids)]
        }
        # activity_type_re = project_activity_type_obj.create(project_activity_type_data)

        duplicate_activity_id = request.env['project.activity'].sudo().create(
            vals)

        for type_data in activity_id.activity_type_ids:
            data = {'activity_id': duplicate_activity_id.id, 'project_actn_id': type_data.project_actn_id.id, 'name': type_data.name, 'project_id': activity_id.project_id.id,
                    'tower_id': activity_id.tower_id.id or False, 'flat_id': activity_id.flat_id.id or False, 'floor_id': activity_id.floor_id.id or False}
            pat_rec = self.env['project.activity.type'].sudo().create(data)
            for checklist in type_data.checklist_ids:
                self.env['project.checklist.line'].sudo().create(
                    {'activity_type_id': pat_rec.id, 'checklist_template_id': checklist.checklist_template_id.id})

        ###
        activity_seq = '001'
        if duplicate_activity_id.name:
            # activity_name = duplicate_activity_id.name[:4].strip()
            activity_name = duplicate_activity_id.name

            duplicate_activity_id.index_no = activity_seq
            new_number = int(activity_seq) + 1
            # activity_seq = '{:03d}'.format(new_number)
            activity_type_seq = '001'
            for activity_type in duplicate_activity_id.activity_type_ids:
                no = 1 + 1
                temp = activity_type_seq
                activity_type.index_no = activity_type_seq
                new_number = int(activity_type_seq) + 1
                activity_type_seq = '{:03d}'.format(new_number)
                activity_type.seq_no = "PLANEDGE"+"/" + str(project) + "/" + str(
                    building_name) + "/" + str(f_name) + "/" + str(activity_name) + "/" + str(temp)

        activity_id.count = count + 1
        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': f'Duplicate Activity ID {duplicate_activity_id.id} Created'}),
            content_type='application/json;charset=utf-8', status=200)


    # @restapi.method([(["/create/replicate/activitie/common/development"], "POST")], auth="user")
    # def create_common_development_replicate_activities(self):
    #     params = request.params
    #     if not params.get('activity_id') and not params.get('type'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id and Type Not Found!'}),
    #                         content_type='application/json;charset=utf-8', status=400)
    #     activity_id = request.env['project.activity'].sudo().browse(
    #         int(params.get('activity_id')))
    #     if not activity_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Activity ID does not exist'}),
    #                         content_type='application/json;charset=utf-8', status=400)
    #     type = params.get('type')
    #     # accidentally added project_tower_id and tower_id which is pointing to same model
    #     # workaround to fix this so common and development activity can see under the respective tower
    #     if type == 'common':
    #         tower_id = 'project_tower_id'
    #     else:
    #         tower_id = 'tower_id'
    #     # Get the base name of the activity
    #     base_name = activity_id.name
    #     count = activity_id.count or 0
    #     area = ''
    #     if params.get('area'):
    #         area = params.get('area')
    #     # Generate the name for the duplicate activity
    #     duplicate_name = f"{base_name}_{count}"
    #     vals = {
    #         "name": duplicate_name,
    #         tower_id: activity_id.tower_id.id if activity_id.tower_id else False,
    #         "project_id": activity_id.project_id.id,
    #         "project_activity_name_id": activity_id.project_activity_name_id.id,
    #         "project_activity_id": activity_id.project_activity_id.id,
    #         "description": activity_id.description,
    #     }
    #     duplicate_activity_id = request.env['project.activity'].sudo().create(
    #         vals)
    #     #_logger.info("----duplicate_activity_id----- %s", str(duplicate_activity_id))

    #     for type_data in activity_id.activity_type_ids:
    #         data = {'activity_id': duplicate_activity_id.id, 'project_actn_id': type_data.project_actn_id.id, 'name': type_data.name, 'project_id': activity_id.project_id.id,
    #                 'tower_id': activity_id.tower_id.id or False, }
    #         pat_rec = self.env['project.activity.type'].sudo().create(data)
    #         for checklist in type_data.checklist_ids:
    #             self.env['project.checklist.line'].sudo().create(
    #                 {'activity_type_id': pat_rec.id, 'checklist_template_id': checklist.checklist_template_id.id})

    #     ###
    #     activity_seq = '001'
    #     if duplicate_activity_id.name:
    #         # activity_name = duplicate_activity_id.name[:4].strip()
    #         activity_name = duplicate_activity_id.name

    #         duplicate_activity_id.index_no = activity_seq
    #         new_number = int(activity_seq) + 1
    #         # activity_seq = '{:03d}'.format(new_number)
    #         activity_type_seq = '001'
    #         for activity_type in duplicate_activity_id.activity_type_ids:
    #             no = 1 + 1
    #             temp = activity_type_seq
    #             activity_type.index_no = activity_type_seq
    #             new_number = int(activity_type_seq) + 1
    #             activity_type_seq = '{:03d}'.format(new_number)
    #             activity_type.seq_no = "VJ"+"/" + str(activity_id.project_id.name) + "/" + str(
    #                 activity_id.tower_id.name) + "/" + str(area) + "/" + str(activity_name) + "/" + str(temp)

    #     activity_id.count = count + 1
    #     return Response(
    #         json.dumps(
    #             {'status': 'SUCCESS', 'message': f'Replicate Activity ID {duplicate_activity_id.id} Created'}),
    #         content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/replicate/activitie/common/development"], "POST")], auth="user")
    def create_common_development_replicate_activities(self):
        params = request.params or {}

        if not params.get('activity_id') or not params.get('type'):
            return Response(
                json.dumps({'status': 'FAILED', 'message': 'Activity Id and Type Not Found!'}),
                content_type='application/json;charset=utf-8', status=400
            )

        activity_id = request.env['project.activity'].sudo().browse(int(params.get('activity_id')))
        if not activity_id.exists():
            return Response(
                json.dumps({'status': 'FAILED', 'message': 'Activity ID does not exist'}),
                content_type='application/json;charset=utf-8', status=400
            )

        req_type = params.get('type')
        area = params.get('area', '')
        
        # ✅ Define variables that were missing
        base = activity_id.name or 'Activity'
        count = int(activity_id.count or 0)
        duplicate_name = f"{base}_{count + 1}"

        # ✅ Common field for tower
        if req_type == 'common':
            target_tower_field = 'project_tower_id'
        else:
            target_tower_field = 'tower_id'

        # ✅ Create duplicate activity record
        duplicate_activity = request.env['project.activity'].sudo().create({
            'name': duplicate_name,
            'project_id': activity_id.project_id.id or False,
            'project_activity_name_id': activity_id.project_activity_name_id.id or False,
            'project_activity_id': activity_id.project_activity_id.id or False,
            'description': activity_id.description or False,
            # ✅ ensure tower hierarchy copied
            'tower_id': activity_id.tower_id.id or False,
            'floor_id': activity_id.floor_id.id or False,
            'flat_id': activity_id.flat_id.id or False,
            target_tower_field: activity_id.tower_id.id if activity_id.tower_id else False,
        })

        # ✅ Copy activity types and checklist lines
        for type_data in activity_id.activity_type_ids:
            new_type = request.env['project.activity.type'].sudo().create({
                'activity_id': duplicate_activity.id,
                'project_actn_id': type_data.project_actn_id.id or False,
                'name': type_data.name,
                'project_id': activity_id.project_id.id or False,
                'tower_id': activity_id.tower_id.id or False,
            })
            for checklist in type_data.checklist_ids:
                request.env['project.checklist.line'].sudo().create({
                    'activity_type_id': new_type.id,
                    'checklist_template_id': checklist.checklist_template_id.id or False
                })

        # ✅ Generate seq_no (keep variable names intact)
        try:
            seq = 1
            for activity_type in duplicate_activity.activity_type_ids:
                temp_seq = '{:03d}'.format(seq)
                project_name = activity_id.project_id.name or ''
                tower_name = activity_id.tower_id.name or ''
                activity_type.seq_no = f"PLANEDGE/{project_name}/{tower_name}/{area}/{duplicate_activity.name}/{temp_seq}"
                seq += 1
        except Exception as e:
            _logger.error("Error assigning sequence numbers: %s", str(e))

        # ✅ Update count
        activity_id.sudo().write({'count': count + 1})

        return Response(
            json.dumps({
                'status': 'SUCCESS',
                'message': f'Replicate Activity ID {duplicate_activity.id} Created',
                'activity_name': duplicate_activity.name,
                'tower_name': duplicate_activity.tower_id.name or 'N/A'
            }),
            content_type='application/json;charset=utf-8', status=200
    )


### Material Inspection APIs ######################
  
    @restapi.method([(["/get/po/docno"], "POST")], auth="public")
    def get_po_docno(self):
        params = request.params
        #_logger.info("-----get_po_docno----- %s", str(params))

        if not params.get('po_ids'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Po Ids'}),
                            content_type='application/json;charset=utf-8', status=201)
        vj_po = self.env['vj.purchase.order'].sudo().search(
            [('id', 'in', params.get('po_ids'))])  # Fetch all records
        vj_po_list = [{"po_id": po.id, "doc_no": po.documentNo}
                      for po in vj_po]
        #_logger.info("-----get_po_docno---vj_po_list-- %s", str(vj_po_list))


        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Documnet No Fetch', 'po_data': vj_po_list}),
                        content_type='application/json;charset=utf-8', status=200)
    
    # SupplierName 1 api
    @restapi.method([(["/get/ledger/description"], "POST")], auth="public")
    def get_ledger_description(self):
        params = request.params
        #_logger.info("-----get_ledger_description----- %s", str(params))

        if not params.get('bu_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Bu Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        
        vj_po_list = self.env['vj.purchase.order'].sudo().get_ledger_description(params.get('bu_id'))

        #_logger.info("-----get_ledger_description-vj_po_list---- %s", str(vj_po_list))


        return Response(json.dumps({'status': 'SUCCESS', 'message': 'PO Data Fetch', 'po_data': vj_po_list}),
                        content_type='application/json;charset=utf-8', status=200)

    # ledgerDescription
    @restapi.method([(["/get/poline/material/description"], "POST")], auth="public")
    def get_po_line_material_dec(self):
        params = request.params
        # _logger.info("-----get_po_line_material_dec----- %s", str(params))

        if not params.get('ledger_id') and not params.get('po_ids'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send ledger Id and PO Id(s)'}),
                            content_type='application/json;charset=utf-8', status=201)

        vj_poline_list = self.env['vj.purchase.order.line'].sudo().get_po_line_material_desc(params.get('po_ids'))
        #_logger.info("-----get_po_line_material_dec--vj_poline_list--- %s", str(vj_poline_list))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Supplier Name Fetched', 'poline_data': vj_poline_list}),
                        content_type='application/json;charset=utf-8', status=200)

    # # materialDescription
    # @restapi.method([(["/get/poline/description"], "POST")], auth="public")
    # def get_poline_description(self):
        
    #     params = request.params
    #     _logger.info("-------/get/poline/description--------- %s", str(params))

    #     if not params.get('item_id') and not params.get('po_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Item and PoId'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     vj_po_line = self.env['vj.purchase.order.line'].sudo().search(
    #         [('id', '=', params.get('po_id')),('ItemId', '=', params.get('item_id'))])
    #     vj_poline_list = [{"item_id": po.ItemId, "po_id": po.poid.id,
    #                        "description": po.description} for po in vj_po_line]
        
    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Description Fetched', 'poline_data': vj_poline_list}),
    #                     content_type='application/json;charset=utf-8', status=200)

    # Qty as per challen invoice
    @restapi.method([(["/get/poline/qty"], "POST")], auth="public")
    def get_poline_qty(self):
        #_logger.info("---------get poline qty----------- %s", str())

        params = request.params
        #_logger.info("---------get poline qty-params---------- %s", str(params))
        
        if not params.get('item_id') and not params.get('po_ids'):

            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Item and Po Ids'}),
                            content_type='application/json;charset=utf-8', status=201)

        vj_poline_list = self.env['vj.purchase.order.line'].sudo().get_qty(params.get('item_id'), params.get('po_ids'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Quantity Fetched', 'poline_data':vj_poline_list}),
                        content_type='application/json;charset=utf-8', status=200)

    # SubDescription
    # @restapi.method([(["/get/poline/subdescription"], "POST")], auth="public")
    # def get_poline_subdescription(self):
    #     params = request.params
    #     if not params.get('po_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send PO Id'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     vj_po_line = self.env['vj.purchase.order.line'].sudo().search(
    #         [('poid', '=', params.get('po_id'))])
    #     vj_poline_list = [{"line_id": po.id, "po_id": po.poid.id,
    #                        "sub_description": po.subProject} for po in vj_po_line]

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Sub Project Fetched', 'poline_data': vj_poline_list}),
    #                     content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/poline/uomcode"], "POST")], auth="public")
    def get_poline_uomcode(self):
        params = request.params
        if not params.get('po_ids'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send PO Ids'}),
                            content_type='application/json;charset=utf-8', status=201)

        vj_po_line = self.env['vj.purchase.order.line'].sudo().search(
            [('poid', 'in', params.get('po_ids'))])
        vj_poline_list = [{"item_id": po.ItemId, "po_id": po.poid.id,
                           "uom_code": po.uomCode or ''} for po in vj_po_line]

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Uom Code Fetched', 'poline_data': vj_poline_list}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/maker/mi/update"], "POST")], auth="user")
    def update_mi_maker(self):
        # maker will update the checklist and click on submit button notification should sent to res. checker
        params = request.params
    
        if not params.get('mi_id') and not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].update_mi_maker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/reject"], "POST")], auth="user")
    def reject_mi_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params

        #_logger.info("---------reject_mi_checker---------,%s", params)

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].sudo().reject_mi_checker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/update"], "POST")], auth="user")
    def update_mi_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        self.env['material.inspection'].sudo().update_mi_checker(params)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'success'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/reject"], "POST")], auth="user")
    def reject_mi_approver(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
 
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().reject_mi_approver(params)

        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/update"], "POST")], auth="user")
    def update_mi_approver(self):
        # approver will update the checklist and notification to admin
        params = request.params
        # _logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().update_mi_approver(params)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/material/inspection"], "POST")], auth="user")
    def get_material_inspection(self):
        # if params contain checked_by(id) will send realted MI data otherwise all MI data.
        response = {}
        params = request.params
        mi_data = self.env['material.inspection'].sudo().get_material_inspection(
            params.get('tower_id'), params.get('mi_id'))
        response['material_inspection'] = mi_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Data Fetch', 'mi_data': response}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/material/inspection"], "POST")], auth="user")
    def create_material_inspection(self):
        params = request.params
        #_logger.info("--params-1233333444-",params)
        if not params.get('project_info_id') and not params.get('tower_id') and not params.get('checked_by'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send project, tower id and Checked By(User) Id'}),
                            content_type='application/json;charset=utf-8', status=400)
        self.env['material.inspection'].sudo(
        ).create_material_inspection(params)
        #_logger.info("=======================================api called for material inspection")
        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': 'Material Inspection Created'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/towers"], "POST")], auth="user")
    def get_project_towers(self):
        params = request.params
        if not params.get('project_info_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        towers = self.env['project.tower'].sudo().get_project_towers(
            int(params.get('project_info_id')))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'towers': towers}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/mi/checklist"], "POST")], auth="user")
    def get_mi_checklist(self):
        checklist = self.env['mi.checklist'].sudo().get_mi_checklist()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'MI Checklist Fetched', 'mi_checklist': checklist}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/mi"], "POST")], auth="user")
    def delete_mi(self):
        params = request.params
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        mi_rec = self.env['material.inspection'].browse(
            int(params.get('mi_id'))).unlink()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection form deleted'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/mi"], "POST")], auth="user")
    def update_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].update_mi(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Updated Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/replicate/mi"], "POST")], auth="user")
    def replicate_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        mi_id = params.get('mi_id')
        self.env['material.inspection'].replicate(int(mi_id))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Replicate Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    # ForGot Password
    @restapi.method([(["/change_password"], "POST")], auth="user")
    def change_password(self):
        params = request.params

        if not params.get('user_id') and not params.get('old_password') and not params.get('new_password'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send User Id, Old Password and New password'}),
                            content_type='application/json;charset=utf-8', status=201)
        user_id = params.get('user_id')
        old_password = params.get('old_password')
        new_password = params.get('new_password')

        user = self.env['res.users'].sudo().browse(int(user_id))
        # if not user.check_password(old_password):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Old password in incorrect'}),
        #             content_type='application/json;charset=utf-8', status=200)
        try:
            user.password = new_password
            return Response(json.dumps({'status': 'SUCCESS', 'message': 'password chnaged successfully'}),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as e:
            #_logger.info("--change_password --e--", str(e))

            return Response(json.dumps({'status': 'FAILED', 'message': 'Can not change the password'}),
                            content_type='application/json;charset=utf-8', status=200)

    ### Training Report ###

    @restapi.method([(["/get/training/report"], "POST")], auth="user")
    def get_training_report_details(self):

        params = request.params
        response = {}
        traning_report = self.env['training.report'].sudo(
        ).get_training_report_details(params)
        # response['training_data'] = traning_report
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': traning_report}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/training/report"], "POST")], auth="user")
    def create_training_report(self):

        params = request.params
        self.env['training.report'].sudo().create_training_report(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Training Report Created'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/training/report"], "POST")], auth="user")
    def update_training_report(self):
        params = request.params
        if not params.get('training_report_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Training ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['training.report'].sudo().update_training_report(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Training Report Comleted.'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/towers"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):
        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower_records = self.env['project.tower'].sudo().search(
            [('project_id.visibility', '=', False), ('project_id', '=', params.get('project_id'))])
        tower_data = [{'tower_id': tower.id, 'name': tower.name,
                       } for tower in tower_records]
        
        #_logger.info("---tower_datatower_datatower_data------,%s",str(tower_data))


        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': tower_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/activities"], "POST")], auth="public")
    def get_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @restapi.method([(["/activity/type_names"], "POST")], auth="public")
    def get_activity_type_names(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklines associated to activity and its types

    @restapi.method([(["/activity/checklist"], "POST")], auth="public")
    def get_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_type_name.exists():
                _logger.warning(
                    "Activity Type Name not found for ID: %s", patn_id)
                return {'status': 'FAILED', 'message': 'Activity Type Name not found'}

            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', patn_id)])
            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            _logger.info("Successfully fetched checklist items: %s",
                         checklist_items)
            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}



#  for set flag manually
# for projects

    @restapi.method([(["/api/project/info"], "POST")], auth="user")
    def get_project_infolist(self):
        _logger.info("Fetching all projects")

        # try:
        #     projects = request.env['project.info'].sudo().search([])
        #     project_data = [{'project_id': project.id,
        #                      'project_name': project.name} for project in projects]

        #     _logger.info("-----projects------%s", project_data)
        #     return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'projects': project_data}

        # except Exception as e:
        #     _logger.exception("Error fetching activities: %s", str(e))
        #     return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

        project_ids = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', self.env.user.id)])
        project_data = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        for project in project_ids:
            project_data.append({
                'project_name': project.name,
                'project_id': project.id,
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'projects': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # @restapi.method([(["/api/tower/info"], "POST")], auth="public")
    # def get_tower_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         project_id = data.get('project_id')

    #         # Validate project_id
    #         if not project_id:
    #             _logger.warning("Project ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Project ID'}

    #         # Fetch tower records based on project_id
    #         tower_records = request.env['project.tower'].sudo().search(
    #             [('project_id', '=', project_id)])
    #         tower_data = [{'tower_id': tower.id, 'tower_name': tower.name}
    #                       for tower in tower_records]

    #         # Log fetched data
    #         # _logger.info("Fetched tower data: %s", tower_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'towers': tower_data}

    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/tower/info"], "POST")], auth="public")
    def get_tower_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            project_id = data.get('project_id')

            # Validate project_id
            if not project_id:
                _logger.warning("Project ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Project ID'}

            # ✅ Fetch tower records from project_info_tower_line_temp
            tower_records = request.env['project.info.tower.line.temp'].sudo().search(
                [('project_id', '=', project_id)]
            )

            # Prepare tower data
            tower_data = [
                {
                    'tower_id': tower.id,
                    'tower_name': tower.name or ''
                }
                for tower in tower_records
            ]

            # Return success response
            return {
                'status': 'SUCCESS',
                'message': 'Tower Data Fetched',
                'towers': tower_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }
    
    @restapi.method([(["/api/floor/info"], "POST")], auth="public")
    def get_floor_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            tower_temp_id = data.get('tower_id')

            if not tower_temp_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # ✅ Find the temp tower
            temp_tower = request.env['project.info.tower.line.temp'].sudo().browse(tower_temp_id)
            if not temp_tower.exists():
                return {'status': 'FAILED', 'message': 'Invalid Temporary Tower ID'}

            # ✅ Find matching tower in main project.tower model
            real_tower = request.env['project.tower'].sudo().search(
                [('name', '=', temp_tower.name)], limit=1
            )

            if not real_tower:
                return {'status': 'FAILED', 'message': 'Matching Tower not found in main tower list'}

            # ✅ Fetch all floors of that real tower
            floor_records = request.env['project.floors'].sudo().search(
                [('tower_id', '=', real_tower.id)]
            )

            floor_data = [
                {'floor_id': floor.id, 'floor_name': floor.name or ''}
                for floor in floor_records
            ]

            return {
                'status': 'SUCCESS',
                'message': 'Floor Data Fetched',
                'floors': floor_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }

    
 
    # @restapi.method([(["/api/floor/info"], "POST")], auth="public")
    # def get_floor_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         tower_id = data.get('tower_id')

    #         # Validate project_id
    #         if not tower_id:
    #             _logger.warning("Tower ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Tower ID'}

    #         # Fetch tower records based on project_id
    #         floor_records = request.env['project.floors'].sudo().search(
    #             [('tower_id', '=', tower_id)])
    #         floor_data = [{'floor_id': floor.id, 'floor_name': floor.name}
    #                       for floor in floor_records]

    #         # Log fetched data
    #         # _logger.info("Fetched Floor data: %s", floor_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'floors': floor_data}
    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    # @restapi.method([(["/api/flat/info"], "POST")], auth="public")
    # def get_flat_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         tower_id = data.get('tower_id')

    #         # Validate project_id
    #         if not tower_id:
    #             _logger.warning("Tower ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Tower ID'}

    #         # Fetch tower records based on project_id
    #         flat_records = request.env['project.flats'].sudo().search(
    #             [('tower_id', '=', tower_id)])
    #         flat_data = [{'flat_id': flat.id, 'flat_name': flat.name}
    #                      for flat in flat_records]

    #         # Log fetched data
    #         _logger.info("Fetched Flat data: %s", flat_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'flats': flat_data}
    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/flat/info"], "POST")], auth="public")
    def get_flat_info(self):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            tower_temp_id = data.get('tower_id')

            if not tower_temp_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # ✅ Find the temp tower
            temp_tower = request.env['project.info.tower.line.temp'].sudo().browse(tower_temp_id)
            if not temp_tower.exists():
                return {'status': 'FAILED', 'message': 'Invalid Temporary Tower ID'}

            # ✅ Find matching tower in project.tower model
            real_tower = request.env['project.tower'].sudo().search(
                [('name', '=', temp_tower.name)], limit=1
            )

            if not real_tower:
                return {'status': 'FAILED', 'message': 'Matching Tower not found in main tower list'}

            # ✅ Fetch flats linked to that real tower
            flat_records = request.env['project.flats'].sudo().search(
                [('tower_id', '=', real_tower.id)]
            )

            flat_data = [
                {
                    'flat_id': flat.id,
                    'flat_name': flat.name or '',
                    'floor_id': flat.floor_id.id if flat.floor_id else '',
                    'floor_name': flat.floor_id.name if flat.floor_id else ''
                }
                for flat in flat_records
            ]

            return {
                'status': 'SUCCESS',
                'message': 'Flat Data Fetched',
                'flats': flat_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }



    @restapi.method([(["/api/users/list"], "POST")], auth="public")
    def get_project_responsibles(self):
        try:
            group = request.env.ref(
            "custom_project_management.group_quality_maker")
            # Fetch all partners
            partners = request.env['res.users'].sudo().search([
            ('groups_id', 'in', group.id)
        ])
            # Prepare the partner data for response
            partner_data = [
                {'id': partner.id, 'name': partner.name, }
                for partner in partners
            ]

            # _logger.info("Fetched project responsible users: %s", partner_data)

            # Return the response
            return {
                'status': 'SUCCESS',
                'message': 'Project responsibles fetched successfully',
                'responsibles': partner_data   
            }

        except Exception as e:
            _logger.exception(
                "Error fetching project responsibles: %s", str(e))
            return {
                'status': 'FAILED',
                'message': 'An error occurred while fetching project responsibles',
                'error': str(e)
            }

    @restapi.method([(["/api/activities/info"], "POST")], auth="public")
    def get_nc_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    @restapi.method([(["/api/activity/type/info"], "POST")], auth="public")
    def get_nc_activity_type_names(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    @restapi.method([(["/api/activity/checklist/info"], "POST")], auth="public")
    def get_nc_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_type_name.exists():
                _logger.warning(
                    "Activity Type Name not found for ID: %s", patn_id)
                return {'status': 'FAILED', 'message': 'Activity Type Name not found'}

            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', patn_id)])
            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            _logger.info("Successfully fetched checklist items: %s",
                         checklist_items)
            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}

    #checker create nc to maker
    @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    def create_nc(self):
        try:
            data = json.loads(request.httprequest.data)
          
            _logger.info("Received JSON request: %s", data)
           

            _logger.info("POST API for NC creation called")
            # _logger.info("=" * 80)
            # _logger.info("FULL REQUEST DATA:")
            # _logger.info(f"Images in request: {len(data.get('images', []))}")
            _logger.info(f"Rectified images in request: {len(data.get('rectified_images', []))}")

            
            # Log the actual structure of the first image if exists
            if data.get('image'):
                first_img = data.get('images')[0]
                _logger.info(f"First image type: {type(first_img)}")
                if isinstance(first_img, dict):
                    _logger.info(f"First image keys: {first_img.keys()}")
                    _logger.info(f"First image has 'data': {'data' in first_img}")
                    _logger.info(f"First image has 'filename': {'filename' in first_img}")
                else:
                    _logger.info(f"First image is string, length: {len(first_img) if isinstance(first_img, str) else 'N/A'}")
            
            if data.get('rectified_image'):
                first_rect = data.get('rectified_image')[0]
                _logger.info(f"First rectified image type: {type(first_rect)}")
                if isinstance(first_rect, dict):
                    _logger.info(f"First rectified image keys: {first_rect.keys()}")
                else:
                    _logger.info(f"First rectified image is string, length: {len(first_rect) if isinstance(first_rect, str) else 'N/A'}")
            _logger.info("=" * 80)

            # Extract incoming IDs (some may come from temp models)
            project_info_id = int(data.get('project_id')) if data.get('project_id') else None
            temp_tower_id = int(data.get('tower_id')) if data.get('tower_id') else None
            project_floor_id = int(data.get('floor_id')) if data.get('floor_id') else None
            project_flats_id = int(data.get('flat_id')) if data.get('flat_id') else None
            project_activity_id = int(data.get('activity_id')) if data.get('activity_id') else None
            project_act_type = int(data.get('activity_type_id')) if data.get('activity_type_id') else None
            project_check_line = int(data.get('id')) if data.get('id') else None
            project_responsible = int(data.get('project_responsible_id')) if data.get('project_responsible_id') else None

            # -------------------------------------------
            # 🔍 Resolve actual Tower ID from temp model
            # -------------------------------------------
            project_tower_id = None
            if temp_tower_id:
                tower_temp = request.env['project.info.tower.line.temp'].sudo().browse(temp_tower_id)
                if tower_temp and tower_temp.tower_id:
                    project_tower_id = tower_temp.tower_id.id
                    _logger.info(f"Resolved real Tower ID: {project_tower_id} from temp ID: {temp_tower_id}")
                else:
                    _logger.warning(f"No matching project.tower found for temp tower ID: {temp_tower_id}")
            else:
                _logger.warning("tower_id not provided or invalid in payload")

            # -------------------------------------------
            # Lookup checklist & activity type records
            # -------------------------------------------
            checklist_template_id = int(project_check_line) if project_check_line else None
            project_check_line_record = request.env['project.activity.type.name.line'].sudo().search([
                ('checklist_id', '=', checklist_template_id)
            ], limit=1)
            project_check_line_id = project_check_line_record.id if project_check_line_record else None

            activity_type_record = request.env['project.activity.name.line'].sudo().search([
                ('patn_id', '=', project_act_type)
            ], limit=1)
            project_act_type_id = activity_type_record.id if activity_type_record else None

            # Extract main data
            custom_checklist_item = data.get('custom_checklist_item')
            description = data.get('description')
            flag_category = data.get('flag_category')
            project_create_date = data.get('project_create_date')
            status = data.get('status')

            # -------------------------------------------
            # Prepare NC record
            # -------------------------------------------
            nc_values = {
                'project_info_id': project_info_id,
                'project_tower_id': project_tower_id,
                'project_floor_id': project_floor_id,
                'project_flats_id': project_flats_id,
                'project_activity_id': project_activity_id,
                'project_act_type_id': project_act_type_id,
                'project_check_line_id': project_check_line_id,
                'description': description,
                'flag_category': flag_category,
                'project_create_date': project_create_date,
                'project_responsible': project_responsible,
                'status': status,
            }

            if custom_checklist_item:
                nc_values['custom_checklist_item'] = custom_checklist_item

            nc_values['seq_number'] = request.env['ir.sequence'].sudo().next_by_code('manually.set.flag') or 'New'

            # Create NC record
            nc = request.env['manually.set.flag'].sudo().create(nc_values)
            _logger.info(f"NC created successfully with ID: {nc.id}")
            
            # notification_status = self.send_notification(nc)
            # _logger.info("Notification status: %s", notification_status)

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple normal images
            # -------------------------------------------
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []
            
            _logger.info(f"Processing {len(image_list)} normal images for NC ID: {nc.id}")
            
            if image_list and len(image_list) > 0:
                for idx, img in enumerate(image_list[:5]):  # Limit to 5 images
                    try:
                        # Handle both object format {"data": "...", "filename": "..."} 
                        # and string format "base64string"
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            # If it's a string, treat it as base64 data directly
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        # Validate base64 data exists
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        # Ensure filename has proper extension
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        # Clean base64 string - remove data URI prefix if present
                        if isinstance(base64_str, str):
                            # Remove 'data:image/...;base64,' prefix
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            # Remove any whitespace and newlines
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        # Create image record
                        img_record = request.env['manually.set.flag.images'].sudo().create({
                            'flag_id': nc.id,
                            'image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Image record created successfully with ID: {img_record.id}")
                        
                        # Generate URL for the image
                        image_url = f"/web/image/manually.set.flag.images/{img_record.id}/image"
                        image_urls.append({
                            'id': img_record.id,
                            'url': image_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for image {idx+1}:")
                        image_errors.append(error_msg)
            
            _logger.info(f"Images processed: {len(image_urls)} successful, {len(image_errors)} failed")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple rectified images
            # -------------------------------------------
            rectified_list = data.get('rectified_image', [])
            rectified_urls = []
            rectified_errors = []
            
            _logger.info(f"Processing {len(rectified_list)} rectified images for NC ID: {nc.id}")
            
            if rectified_list and len(rectified_list) > 0:
                for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
                    try:
                        # Handle both object format {"data": "...", "filename": "..."} 
                        # and string format "base64string"
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            # If it's a string, treat it as base64 data directly
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Validate base64 data exists
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Ensure filename has proper extension
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        # Clean base64 string - remove data URI prefix if present
                        if isinstance(base64_str, str):
                            # Remove 'data:image/...;base64,' prefix
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            # Remove any whitespace and newlines
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        # Create rectified image record
                        rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
                            'flag_id': nc.id,
                            'rectified_image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                        
                        # Generate URL for the rectified image
                        rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
                        rectified_urls.append({
                            'id': rect_record.id,
                            'url': rectified_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Rectified image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for rectified image {idx+1}:")
                        rectified_errors.append(error_msg)
            
            _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")

            # -------------------------------------------
            # Prepare Response   
            # -------------------------------------------
            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC generated successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': project_tower_id,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,  # ✅ Convert datetime to ISO string
                    'custom_checklist': nc.custom_checklist_item,
                    # 'notification_status': notification_status,
                    'images': image_urls,  # ✅ Returns array of objects with id, url, filename
                    'rectified_images': rectified_urls,  # ✅ Returns array of objects with id, url, filename
                },
                'images_processed': {
                    'normal': {
                        'total_sent': len(image_list),
                        'successfully_stored': len(image_urls),
                        'failed': len(image_errors)
                    },
                    'rectified': {
                        'total_sent': len(rectified_list),
                        'successfully_stored': len(rectified_urls),
                        'failed': len(rectified_errors)
                    }
                }
            }
            
            # Add error details if any images failed
            if image_errors:
                response_data['image_errors'] = image_errors
            if rectified_errors:
                response_data['rectified_image_errors'] = rectified_errors

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    # def send_notification(self, nc):
    #     """ Sends push notification to the responsible person """
    #     if not nc.project_responsible:
    #         return {'error': 'No responsible person assigned'}

    #     project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
    #     tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
    #     flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
    #     flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
    #     floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

    #     # Conditional address logic
    #     if flat_name:
    #         location_detail = f"Flat/{flat_name}"
    #     elif floor_name:
    #         location_detail = f"Floor/{floor_name}"
    #     else:
    #         location_detail = ""

    #     seq_no = nc.seq_number
    #     # Get current user's name
    #     current_user_name = request.env.user.name if request.env.user else 'Unknown User'

    #     # Update the message
    #     message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}"
    #     if location_detail:
    #         message += f"/{location_detail}"
    #         message += "."
    #     title = message

    #     # Get Push Notification ID
    #     player_id, user_r = request.env['res.users'].sudo(
    #     ).get_player_id(nc.project_responsible.id)
    #     player_ids = [player_id] if player_id else []

    #     if not player_ids:
    #         return {'error': 'No push notification ID found for the responsible person'}

    #     # OneSignal API credentials
    #     app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
    #     rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

    #     # Data to send in the notification
    #     data = {
    #         "app_id": app_id,
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     # Convert data to JSON
    #     data_json = json.dumps(data)

    #     # URL for OneSignal REST API
    #     url = "https://onesignal.com/api/v1/notifications"

    #     # Headers for the request
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {rest_api_key}"
    #     }

    #     # Send the notification
    #     response = requests.post(url, data=data_json, headers=headers)

    #     # Log Notification Status
    #     status = 'sent' if response.status_code == 200 else 'failed'
    #     request.env['app.notification.log'].sudo().create({
    #         'title': title if status == 'sent' else f"{title} (Failed)",
    #         'message': message,
    #         'res_user_id': nc.project_responsible.id,
    #         'player_id': player_id,
    #         'seq_no': seq_no,
    #         'status': status,
    #         'table_id': nc.id,
    #         'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
    #         'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
    #     })

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    def send_notification(self, nc):
        """ Sends push notification to the responsible person """
        if not nc.project_responsible:
            return {'error': 'No responsible person assigned'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number
        # Get current user's name
        current_user_name = request.env.user.name if request.env.user else 'Unknown User'

        # Update the message
        message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
            message += "."
        title = message

        # Get Push Notification ID
        player_id, user_r = request.env['res.users'].sudo(
        ).get_player_id(nc.project_responsible.id)
        player_ids = [player_id] if player_id else []

        if not player_ids:
            return {'error': 'No push notification ID found for the responsible person'}

        # OneSignal API credentials
        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        # Data to send in the notification
        data = {
            "app_id": app_id,
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        # Convert data to JSON
        data_json = json.dumps(data)

        # URL for OneSignal REST API
        url = "https://onesignal.com/api/v1/notifications"

        # Headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {rest_api_key}"
        }

        # Send the notification
        response = requests.post(url, data=data_json, headers=headers)

        # Log Notification Status
        status = 'sent' if response.status_code == 200 else 'failed'
        request.env['app.notification.log'].sudo().create({
            'title': title if status == 'sent' else f"{title} (Failed)",
            'message': message,
            'res_user_id': nc.project_responsible.id,
            'player_id': player_id,
            'seq_no': seq_no,
            'status': status,
            'table_id': nc.id,
            'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
            'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
        })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}
    
    @restapi.method([(["/api/nc/submit"], 'POST')], auth="public")
    def close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called %s", data)

            nc_id = data.get('nc_id')
            status = data.get('status')
            # image = data.get('image')
            overall_remarks = data.get('overall_remarks')


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple normal images
            # -------------------------------------------
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []
            
            _logger.info(f"Processing {len(image_list)} normal images for NC ID: {nc.id}")
            
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []

            valid_images = [img for img in image_list if img and isinstance(img, (dict, str))]

            if valid_images:
                for idx, img in enumerate(valid_images[:5]):
                    try:
                        # Handle dict format
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')

                        # Handle string format
                        elif isinstance(img, str):
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'

                        # Reject blanks
                        if not base64_str or base64_str.strip() == "":
                            continue

                        # Remove prefix
                        if 'base64,' in base64_str:
                            base64_str = base64_str.split('base64,')[-1]

                        base64_str = base64_str.strip()

                        img_record = request.env['manually.set.flag.images'].sudo().create({
                            'flag_id': nc.id,
                            'image': base64_str,
                            'filename': filename
                        })

                        image_urls.append({
                            'id': img_record.id,
                            'url': f"/web/image/manually.set.flag.images/{img_record.id}/image",
                            'filename': filename
                        })

                    except Exception as e:
                        image_errors.append(str(e))

            _logger.info(f"Images processed: {len(image_urls)} successful, {len(image_errors)} failed")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple rectified images
            # -------------------------------------------
            # rectified_list = data.get('rectified_image', [])
            # rectified_urls = []
            # rectified_errors = []
            
            # _logger.info(f"Processing {len(rectified_list)} rectified images for NC ID: {nc.id}")
            
            # if rectified_list and len(rectified_list) > 0:
            #     for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
            #         try:
            #             # Handle both object format {"data": "...", "filename": "..."} 
            #             # and string format "base64string"
            #             if isinstance(img, dict):
            #                 base64_str = img.get('data')
            #                 filename = img.get('filename', f're_image_{idx+1}.jpg')
            #             elif isinstance(img, str):
            #                 # If it's a string, treat it as base64 data directly
            #                 base64_str = img
            #                 filename = f'image_{idx+1}.jpg'
            #             else:
            #                 error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
            #                 _logger.error(error_msg)
            #                 rectified_errors.append(error_msg)
            #                 continue
                        
            #             # Validate base64 data exists
            #             if not base64_str:
            #                 error_msg = f"Image {idx+1}: No data provided"
            #                 _logger.error(error_msg)
            #                 rectified_errors.append(error_msg)
            #                 continue
                        
            #             # Ensure filename has proper extension
            #             if not filename or filename.strip() == '':
            #                 filename = f'image_{idx+1}.jpg'
            #             elif '.' not in filename:
            #                 filename = f'{filename}.jpg'
                        
            #             # Clean base64 string - remove data URI prefix if present
            #             if isinstance(base64_str, str):
            #                 # Remove 'data:image/...;base64,' prefix
            #                 if 'base64,' in base64_str:
            #                     base64_str = base64_str.split('base64,')[-1]
            #                 # Remove any whitespace and newlines
            #                 base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
            #             _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
            #             # Create rectified image record
            #             rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
            #                 'flag_id': nc.id,
            #                 'rectified_image': base64_str,
            #                 'filename': filename
            #             })
                        
            #             _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                        
            #             # Generate URL for the rectified image
            #             rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
            #             rectified_urls.append({
            #                 'id': rect_record.id,
            #                 'url': rectified_url,
            #                 'filename': filename
            #             })
                        
            #         except Exception as e:
            #             error_msg = f"Rectified image {idx+1} error: {str(e)}"
            #             _logger.error(error_msg)
            #             _logger.exception(f"Full traceback for rectified image {idx+1}:")
            #             rectified_errors.append(error_msg)
            
            # _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # image_data = None
            # rimage_data = image

            # if rimage_data:
            #     try:
            #         image_data = rimage_data.split(',')[1]
            #         decoded_image = base64.b64decode(
            #             image_data)

            #         attachment = self.env['ir.attachment'].sudo().create({
            #             'name': 'image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")


            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            # image_data = None
            # if image:
            #     try:
            #         image_data = image.split(',')[1]
            #         decoded_image = base64.b64decode(image_data)

            #         request.env['ir.attachment'].sudo().create({
            #             'name': 'closed_nc_image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")

            # Update NC status
            nc.write({
                'status': 'submit',
                'overall_remarks': overall_remarks,
                # 'image': image_urls,
            })

            _logger.info("NC status updated to 'submit' with ID: %s", nc.id)

            # 🔥 REMOVE maker notification when maker submits NC
            if nc.project_responsible:
                request.env['app.notification.log'].sudo().search([
                    ('table_id', '=', nc.id),                 # same NC
                    ('res_user_id', '=', nc.project_responsible.id),  # maker
                    ('status', '=', 'sent')
                ]).unlink()
            # Send notification to project responsible
            # if nc.project_responsible:

            notification_status = self.send_close_notification(nc)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_number': nc.seq_number,
                    'project_create_date': nc.project_create_date,
                    'project_id': nc.project_info_id.id,
                    'tower_id': nc.project_tower_id.id,
                    'floor_id': nc.project_floor_id.id,
                    'flat_id': nc.project_flats_id.id,
                    'activity_id': nc.project_activity_id.id,
                    'activity_type_id': nc.project_act_type_id.id,
                    'id': nc.project_check_line_id.id,
                    'description': nc.description,
                    'overall_remarks': nc.overall_remarks,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'image': image_urls,
                },
                'notification_status': notification_status
            }
            _logger.info("response data: %s", response_data)

            return response_data, 200

        except Exception as e:
            _logger.error("Error submitting NC: %s", e)
            return {'status': 'error', 'message': f'Failed to submit NC: {str(e)}'}, 500

    def send_close_notification(self, nc):
        _logger.info("=== Sending Approver Notification for NC ID %s ===", nc.id)

        tower = nc.project_tower_id
        if not tower or not tower.assigned_to_ids:
            _logger.error("No assigned users found for tower. Cannot find approvers.")
            return {"error": "No approvers found"}

        approver_users = []

        # 🔍 EXACT SAME LOGIC AS button_checking_done (group.name == 'Approver')
        for user in tower.assigned_to_ids:
            for group in user.groups_id:
                if group.name == "Approver":
                    approver_users.append(user)

        _logger.info("Approvers Found: %s", [u.name for u in approver_users])

        if not approver_users:
            _logger.error("No Approver users assigned to this tower.")
            return {"error": "Approver not assigned to tower"}

        # Build Notification Message
        current_user = request.env.user
        seq_no = nc.seq_number
        
        project_name = nc.project_info_id.name or ''
        tower_name = nc.project_tower_id.name or ''
        floor_name = nc.project_floor_id.name or ''
        flat_name = nc.project_flats_id.name or ''
        category = nc.flag_category or ''

        # message = f"{current_user.name} has submitted the {category} for {project_name}/{tower_name}."
        # title = f"NC {seq_no} Submitted"
        location_text = f"{project_name}/{tower_name}/{floor_name}/{flat_name}"

        message = f"{current_user.name} has submitted the {category} for {location_text}."
        title = f"{current_user.name} has submitted the {category} for {location_text}."

        notification_obj = request.env['app.notification']
        log_obj = request.env['app.notification.log']

        sent = False
        failed_users = []

        # 🔔 Send to all approvers
        for approver in approver_users:
            player_id, _ = request.env['res.users'].sudo().get_player_id(approver.id)

            if player_id:
                try:
                    notification_obj.send_push_notification(
                        title,
                        [player_id],
                        message,
                        [approver.id],
                        seq_no,
                        'close_nc',
                        nc
                    )
                    sent = True

                    log_obj.sudo().create({
                        'title': title,
                        'message': message,
                        'res_user_id': approver.id,
                        'status': "sent",
                        'seq_no': seq_no,
                        'table_id': nc.id,
                        'project_info_id': nc.project_info_id.id,
                        'tower_id': nc.project_tower_id.id
                    })
                except Exception as e:
                    _logger.error("Failed sending to %s: %s", approver.name, e)
                    failed_users.append(approver.name)
            else:
                failed_users.append(approver.name)

        if not sent:
            return {"error": f"No notifications sent. Failed for {failed_users}"}

        return {"success": True, "message": "Notifications sent to approver(s)"}


    @restapi.method([(["/api/approver/nc/close"], "POST")], auth="public")
    def approver_close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')
            approver_remark = data.get('approver_remark')
            approver_close_images = data.get('approver_close_images', [])
            
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)
            notification_status = self.send_close_nc_notification(nc)

            if not nc_id:
                return {'status': 'error', 'message': 'NC ID missing'}, 400

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            if nc.status != 'submit':
                return {'status': 'error', 'message': 'NC status must be submit'}, 400
                        
            nc.write({
                'status': 'close',
                'approver_remark': approver_remark
            })
            # 🔥 REMOVE maker notification when maker submits NC
            if nc.project_responsible:
                request.env['app.notification.log'].sudo().search([
                    ('table_id', '=', nc.id),                 # same NC
                    ('res_user_id', '=', nc.project_responsible.id),  # maker
                    ('status', '=', 'sent')
                ]).unlink()

            for idx, img in enumerate(approver_close_images[:5]):
                try:
                    if isinstance(img, dict):
                        base64_str = img.get('data') or img.get('approver_close_img')
                        filename = img.get('filename', f'close_{idx+1}.jpg')

                    elif isinstance(img, str):
                        base64_str = img
                        filename = f'close_{idx+1}.jpg'

                    if not base64_str:
                        continue

                    if 'base64,' in base64_str:
                        base64_str = base64_str.split('base64,')[-1]

                    request.env['manually.set.flag.approver.close.images'].sudo().create({
                        'flag_id': nc.id,
                        'approver_close_img': base64_str,   
                        'filename': filename,
                    })

                except Exception as e:
                    _logger.error("Approver Close image error: %s", e)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'custom_checklist': nc.custom_checklist_item,
                    'approver_remark': nc.approver_remark,
                    'notification_status': notification_status,
                    # 'images': nc.image_urls, 
                    # 'rectified_images': nc.rectified_urls, 
                },
                
            }            

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_close_nc_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    # def send_close_nc_notification(self, nc):
    #     """ Sends push notification to NC creator & project responsible """

    #     project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
    #     tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
    #     flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
    #     flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
    #     floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

    #     current_user = request.env.user
    #     current_user_name = current_user.name if current_user else 'Unknown User'

    #     # Conditional address logic
    #     if flat_name:
    #         location_detail = f"Flat/{flat_name}"
    #     elif floor_name:
    #         location_detail = f"Floor/{floor_name}"
    #     else:
    #         location_detail = ""

    #     seq_no = nc.seq_number

    #     # 💡 User who created the NC
    #     creator_user = nc.create_uid
    #     # creator_name = creator_user.name if creator_user else "Unknown User"

    #     # 📝 Notification Message
    #     message = f"{current_user_name} has closed a {flag_category} for {project_name}/{tower_name}"
    #     if location_detail:
    #         message += f"/{location_detail}"
    #     message += "."
    #     title = message

    #     # 🎯 Target users
    #     player_ids = []

    #     # Project Responsible
    #     if nc.project_responsible:
    #         pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
    #         if pr_player:
    #             player_ids.append(pr_player)

    #     # NC Creator
    #     if creator_user:
    #         creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
    #         if creator_player:
    #             player_ids.append(creator_player)

    #     if not player_ids:
    #         return {'error': 'No push notification IDs found for recipients'}

    #     # OneSignal Push
    #     data = {
    #         "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
    #     }

    #     response = requests.post("https://onesignal.com/api/v1/notifications",
    #                             data=json.dumps(data),
    #                             headers=headers)

    #     status = 'sent' if response.status_code == 200 else 'failed'

    #     # Logging notification for both NC creator & project responsible
    #     for user in [creator_user, nc.project_responsible]:
    #         if user:
    #             request.env['app.notification.log'].sudo().create({
    #                 'title': title if status == 'sent' else f"{title} (Failed)",
    #                 'message': message,
    #                 'res_user_id': user.id,
    #                 'status': status,
    #                 'seq_no': seq_no,
    #                 'table_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
    #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
    #             })

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    def send_close_nc_notification(self, nc):
        """ Sends push notification to NC creator & project responsible """

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        current_user = request.env.user
        current_user_name = current_user.name if current_user else 'Unknown User'

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number

        # 💡 User who created the NC
        creator_user = nc.create_uid
        # creator_name = creator_user.name if creator_user else "Unknown User"

        # 📝 Notification Message
        message = f"{current_user_name} has closed a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
        message += "."
        title = message

        # 🎯 Target users
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
            if pr_player:
                player_ids.append(pr_player)

        # NC Creator
        if creator_user:
            creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
            if creator_player:
                player_ids.append(creator_player)

        if not player_ids:
            return {'error': 'No push notification IDs found for recipients'}

        # OneSignal Push
        data = {
            "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
        }

        response = requests.post("https://onesignal.com/api/v1/notifications",
                                data=json.dumps(data),
                                headers=headers)

        status = 'sent' if response.status_code == 200 else 'failed'

        # Logging notification for both NC creator & project responsible
        for user in [creator_user, nc.project_responsible]:
            if user:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user.id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}


    @restapi.method([(["/api/approver/nc/reject"], "POST")], auth="public")
    def approver_reject_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC (approver_reject) called")

            nc_id = data.get('nc_id')
            approver_remark = data.get('approver_remark')
            close_images = data.get('close_images', [])

            
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            if not nc_id:
                return {'status': 'error', 'message': 'NC ID missing'}, 400

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            if nc.status != 'submit':
                return {'status': 'error', 'message': 'NC status must be submit'}, 400
                        
            nc.write({
                'status': 'approver_reject',
                'approver_remark': approver_remark
            })
            # 🔥 REMOVE approver notification when approver reject NC
            request.env['app.notification.log'].sudo().search([
                ('table_id', '=', nc.id),          # Same NC
                ('res_user_id', '=', request.env.user.id),  # Current approver
                ('status', '=', 'sent')
            ]).unlink()
            # valid_images = [img for img in close_images if img and isinstance(img, (dict, str))]

            for idx, img in enumerate(close_images[:5]):
                try:
                    if isinstance(img, dict):
                        base64_str = img.get('data') or img.get('approver_image')
                        filename = img.get('filename', f'close_{idx+1}.jpg')

                    elif isinstance(img, str):
                        base64_str = img
                        filename = f'close_{idx+1}.jpg'

                    if not base64_str:
                        continue

                    # ✅ remove base64 prefix
                    if 'base64,' in base64_str:
                        base64_str = base64_str.split('base64,')[-1]

                    request.env['manually.set.flag.close.images'].sudo().create({
                        'flag_id': nc.id,
                        'approver_image': base64_str,   # ✅ CORRECT
                        'filename': filename,
                    })

                except Exception as e:
                    _logger.error("Close image error: %s", e)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'approver rejected the Nc changes.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'custom_checklist': nc.custom_checklist_item,
                    'approver_remark': nc.approver_remark
                    # 'images': nc.image_urls, 
                    # 'rectified_images': nc.rectified_urls, 
                },
                
            }            

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_reject_nc_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    def send_reject_nc_notification(self, nc):
        """ Sends push notification to NC creator & project responsible """

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        current_user = request.env.user
        current_user_name = current_user.name if current_user else 'Unknown User'

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number

        # 💡 User who created the NC
        creator_user = nc.create_uid
        # creator_name = creator_user.name if creator_user else "Unknown User"

        # 📝 Notification Message
        message = f"{current_user_name} has rejected a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
        message += "."
        title = message

        # 🎯 Target users
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
            if pr_player:
                player_ids.append(pr_player)

        # # NC Creator
        # if creator_user:
        #     creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
        #     if creator_player:
        #         player_ids.append(creator_player)

        # if not player_ids:
        #     return {'error': 'No push notification IDs found for recipients'}

        # OneSignal Push
        data = {
            "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
        }

        response = requests.post("https://onesignal.com/api/v1/notifications",
                                data=json.dumps(data),
                                headers=headers)

        status = 'sent' if response.status_code == 200 else 'failed'

        # Logging notification for both NC creator & project responsible
        for user in [nc.project_responsible]:
            if user:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user.id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}



#######################old flow for sending notification
    # def send_close_notification(self, nc):
        
    #     if not nc.project_responsible and not request.env.user:
    #         return {'error': 'No recipient found for notification'}

    #     project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
    #     tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
    #     flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
    #     seq_no = nc.seq_number
    #     current_user = request.env.user  # Get the user who is closing the NC
    #     current_user_name = current_user.name if current_user else 'Unknown User'
    #     flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
    #     floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

    #     # Conditional address logic
    #     if flat_name:
    #         location_detail = f"Flat/{flat_name}"
    #     elif floor_name:
    #         location_detail = f"Floor/{floor_name}"
    #     else:
    #         location_detail = ""

    #     message = f"{current_user_name} has closed the {flag_category} for {project_name}/{tower_name}"
    #     if location_detail:
    #         message += f"/{location_detail}"
    #         message += "."
    #     title = message

    #     # Get player IDs for both project responsible & closing user
    #     player_ids = []

    #     # Project Responsible
    #     if nc.project_responsible:
    #         project_responsible_player, _ = request.env['res.users'].sudo(
    #         ).get_player_id(nc.project_responsible.id)
    #         if project_responsible_player:
    #             player_ids.append(project_responsible_player)

    #     # User who closed the NC
    #     if current_user:
    #         closing_user_player, _ = request.env['res.users'].sudo(
    #         ).get_player_id(current_user.id)
    #         if closing_user_player:
    #             player_ids.append(closing_user_player)

    #     if not player_ids:
    #         return {'error': 'No push notification IDs found for recipients'}

    #     app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
    #     rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

    #     data = {
    #         "app_id": app_id,
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     data_json = json.dumps(data)
    #     url = "https://onesignal.com/api/v1/notifications"
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {rest_api_key}"
    #     }

    #     response = requests.post(url, data=data_json, headers=headers)
    #     status = 'sent' if response.status_code == 200 else 'failed'
 
    #     # Log notification for both users
    #     for user_id in [nc.project_responsible.id, current_user.id]:
    #         if user_id:
    #             request.env['app.notification.log'].sudo().create({
    #                 'title': title if status == 'sent' else f"{title} (Failed)",
    #                 'message': message,
    #                 'res_user_id': user_id,
    #                 'status': status,
    #                 'seq_no': seq_no,
    #                 'table_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
    #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
    #             })

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

  
  
  
  #########################################################
    # @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    # def fetch_all_nc(self):
    #     try:
    #         _logger.info("POST API for fetching all NC called")
    #         _logger.info("Received request at /api/nc/fetch_all")

    #         # Fetch all tasks
    #         ncs = request.env['manually.set.flag'].sudo().search([])

    #         # Prepare response data for all tasks
    #         nc_data = []
    #         for nc in ncs:
    #             _logger.debug("Processing nc ID: %s", nc.id)
    #             nc_data.append({
    #                 'seq_number': nc.seq_number,
    #                 'nc_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id,
    #                 'project_info_name': nc.project_info_id.name,
    #                 'project_tower_id': nc.project_tower_id.id,
    #                 'project_tower_name': nc.project_tower_id.name,
    #                 'project_floor_id': nc.project_floor_id.id,
    #                 'project_floor_name': nc.project_floor_id.name,
    #                 'project_flats_id': nc.project_flats_id.id,
    #                 'project_flats_name': nc.project_flats_id.name,

    #                 'project_activity_id': nc.project_activity_id.id,
    #                 'project_activity_name': nc.project_activity_id.name,

    #                 # # 'project_activity_name': nc.project_activity_id.name,
    #                 # 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
    #                 # 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id.exists() else '',
    #                 'project_act_type_id': nc.project_act_type_id.id,
    #                 # 'project_act_type_name': nc.project_act_type_id.patn_id.name,
    #                 'project_act_type_name': nc.project_act_type_id.name,


    #                 'project_check_line_id': nc.project_check_line_id.id,
    #                 # 'project_check_line_name': nc.project_check_line_id,
    #                 'project_check_line_name': nc.project_check_line_id.checklist_id.name,
    #                 # 'project_check_line_name': nc.project_check_line_id.checklist_template_id.name,
    #                 'custom_checklist_item': nc.custom_checklist_item,

    #                 'project_create_date': nc.project_create_date,
    #                 'project_responsible': nc.project_responsible.name,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'rectified_image': nc.rectified_image,
    #             })

    #         _logger.info("Total ncs fetched: %s", len(ncs))

    #         return {
    #             'status': 'success',
    #             'ncs': nc_data
    #         }, 200

    #     except Exception as e:
    #         _logger.error("Error fetching ncs: %s", e, exc_info=True)
    #         return {
    #             'status': 'error',
    #             'message': 'Failed to fetch ncs.',
    #             'error_details': str(e)
    #         }, 500


#  working
    # @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    # def fetch_all_nc(self):
    #     try:
    #         _logger.info("POST API for fetching all NC called")
    #         _logger.info("Received request at /api/nc/fetch_all")

    #         # Fetch all NCs
    #         ncs = request.env['manually.set.flag'].sudo().search([])

    #         # Prepare response data for all NCs
    #         nc_data = []
    #         for nc in ncs:
    #             _logger.debug("Processing nc ID: %s", nc.id)
                
    #             # Fetch all images for this NC
    #             image_urls = []
    #             for img in nc.image_ids:
    #                 image_urls.append({
    #                     'id': img.id,
    #                     'url': f"/web/image/manually.set.flag.images/{img.id}/image",
    #                     'filename': img.filename or 'image.jpg'
    #                 })
                
    #             # Fetch all rectified images for this NC
    #             rectified_image_urls = []
    #             for img in nc.rectified_image_ids:
    #                 rectified_image_urls.append({
    #                     'id': img.id,
    #                     'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
    #                     'filename': img.filename or 'rectified_image.jpg'
    #                 })
                
    #             nc_data.append({
    #                 'seq_number': nc.seq_number,
    #                 'nc_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
    #                 'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
    #                 'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
    #                 'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
    #                 'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
    #                 'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
    #                 'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
    #                 'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
    #                 'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
    #                 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
    #                 'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
    #                 'project_act_type_name': nc.project_act_type_id.name if nc.project_act_type_id else '',
    #                 'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
    #                 'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
    #                 'custom_checklist_item': nc.custom_checklist_item or '',
    #                 'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
    #                 'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
    #                 'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
    #                 'description': nc.description or '',
    #                 'flag_category': nc.flag_category or '',
    #                 'status': nc.status or '',
    #                 'images': image_urls,  # ✅ Array of image objects
    #                 'rectified_images': rectified_image_urls,  # ✅ Array of rectified image objects
    #             })

    #         _logger.info("Total ncs fetched: %s", len(ncs))

    #         return {
    #             'status': 'success',
    #             'ncs': nc_data
    #         }, 200

    #     except Exception as e:
    #         _logger.error("Error fetching ncs: %s", e, exc_info=True)
    #         return {
    #             'status': 'error',
    #             'message': 'Failed to fetch ncs.',
    #             'error_details': str(e)
    #         }, 500



    @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    def fetch_all_nc(self):
        try:
            _logger.info("POST API for fetching all NC called")
            _logger.info("Received request at /api/nc/fetch_all")

            # Fetch all NCs
            ncs = request.env['manually.set.flag'].sudo().search([])

            # Prepare response data for all NCs
            nc_data = []
            for nc in ncs:
                _logger.debug("Processing nc ID: %s", nc.id)
                
                # Fetch all images for this NC - Fixed to return proper structure
                image_urls = []
                for img in nc.image_ids:
                    image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.images/{img.id}/image",
                        'filename': img.filename or 'image.jpg'
                    })
                
                # Fetch all rectified images for this NC - Fixed to return proper structure
                rectified_image_urls = []
                for img in nc.rectified_image_ids:
                    rectified_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
                        'filename': img.filename or 'rectified_image.jpg'
                    })

                approver_image_urls = []
                for img in nc.approver_image_ids:   
                    approver_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.close.images/{img.id}/approver_image",
                        'filename': img.filename or 'approver_image.jpg'
                    })

                approver_close_image_urls = []
                for img in nc.approver_close_image_ids:   
                    approver_close_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.approver.close.images/{img.id}/approver_image",
                        'filename': img.filename or 'approver_close_img.jpg'
                    })
                
                nc_data.append({
                    'seq_number': nc.seq_number,
                    'nc_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
                    'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
                    'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
                    'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
                    'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
                    'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
                    'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_act_type_name': nc.project_act_type_id.patn_id.name if nc.project_act_type_id else '',
                    'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
                    'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
                    'custom_checklist_item': nc.custom_checklist_item or '',
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
                    'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
                    'description': nc.description or '',
                    'overall_remarks': nc.overall_remarks or '',
                    # 'approver_reject': nc.approver_reject or '',
                    'approver_remark': nc.approver_remark or '',
                    'flag_category': nc.flag_category or '',
                    'status': nc.status or '',
                    'images': image_urls,  
                    'rectified_images': rectified_image_urls, 
                    'image_count': len(image_urls),  
                    'rectified_image_count': len(rectified_image_urls), 
                    'approver_reject_image': approver_image_urls,
                    'reject_image_count': len(approver_image_urls),
                    'approver_close_img': approver_close_image_urls,
                    'approver_close_img_count': len(approver_close_image_urls),
                    'close_image': image_urls,
#                     'rectified_image': (
#     f"/web/image/manually.set.flag/{nc.id}/image"
#     if nc.image else None
# ),
                })

            _logger.info(f"✅ Total NCs fetched: {len(ncs)}")

            return {
                'status': 'success',
                'total_count': len(ncs),
                'ncs': nc_data
            }, 200

        except Exception as e:
            _logger.error("❌ Error fetching NCs: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch NCs.',
                'error_details': str(e)
            }, 500



    @restapi.method([(["/api/nc/fetch"], "POST")], auth="public")
    def fetch_nc_details(self):
        try:
            _logger.info("POST API for fetching NC details called")
            _logger.info("Received request at /api/nc/fetch")

            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called %s", data)
            nc_id = data.get('nc_id')

            if not nc_id:
                return {
                    'status': 'error',
                    'message': 'NC ID is required.'
                }, 400

            # Fetch the NC record by nc.id
            nc = request.env['manually.set.flag'].sudo().search([('id', '=', nc_id)], limit=1)

            if not nc:
                return {
                    'status': 'error',
                    'message': 'NC not found.'
                }, 404

            image_urls = []
            for img in nc.image_ids:
                image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.images/{img.id}/image",
                    'filename': img.filename or 'image.jpg'
                })
            
            # Fetch all rectified images for this NC - Fixed to return proper structure
            rectified_image_urls = []
            for img in nc.rectified_image_ids:
                rectified_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
                    'filename': img.filename or 'rectified_image.jpg'
                })

            approver_image_urls = []
            for img in nc.approver_image_ids:   
                approver_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.close.images/{img.id}/approver_image",
                    'filename': img.filename or 'approver_image.jpg'
                })

            approver_close_image_urls = []
            for img in nc.approver_close_image_ids:   
                approver_close_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.approver.close.images/{img.id}/approver_image",
                    'filename': img.filename or 'approver_close_img.jpg'
                })

                
            # Prepare the response data
            nc_data ={
                    'seq_number': nc.seq_number,
                    'nc_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
                    'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
                    'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
                    'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
                    'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
                    'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
                    'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_act_type_name': nc.project_act_type_id.patn_id.name if nc.project_act_type_id else '',
                    'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
                    'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
                    'custom_checklist_item': nc.custom_checklist_item or '',
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
                    'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
                    'description': nc.description or '',
                    'overall_remarks': nc.overall_remarks or '',
                    # 'approver_reject': nc.approver_reject or '',
                    'approver_remark': nc.approver_remark or '',
                    'flag_category': nc.flag_category or '',
                    'status': nc.status or '',
                    'images': image_urls,  
                    'rectified_images': rectified_image_urls, 
                    'image_count': len(image_urls),  
                    'rectified_image_count': len(rectified_image_urls), 
                    'close_image': image_urls,
                    'approver_reject_image': approver_image_urls,
                    'reject_image_count': len(approver_image_urls),
                    'approver_close_img': approver_close_image_urls,
                    'approver_close_img_count': len(approver_close_image_urls),
#                     'rectified_image': (
#     f"/web/image/manually.set.flag/{nc.id}/image"
#     if nc.image else None
# ),
                }

            _logger.info("NC details fetched: %s", nc_data)

            return {
                'status': 'success',
                'nc': nc_data
            }, 200

        except Exception as e:
            _logger.error("Error fetching NC details: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch NC details.',
                'error_details': str(e)
            }, 500














    @restapi.method([(["/get/activity/common"], "POST")], auth="user")
    def get_checklist_for_common(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower = self.env['project.tower'].sudo().browse(int(params.get('tower_id')))
        if not tower.exists():
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = {'tower_name': tower.name, 'tower_id': tower.id}
        list_flat_data = []
        total_count = 0

        for activity in tower.activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                elif status == 'checked':
                    checked += 1
                elif status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            elif approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            last_update = self._get_activity_last_update(activity)

            list_flat_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': last_update or '',
                'activity_type_status': activity_type_status,
                'progress': float(activity.progress_percentage or 0.0),
                'color': color,
            })

        data['list_flat_data'] = list_flat_data
        data['total_count'] = total_count

        return Response(json.dumps({
            'status': 'SUCCESS',
            'message': 'Activity info Fetch',
            'activity_data': data
        }), content_type='application/json;charset=utf-8', status=200)


    # @restapi.method([(["/get/activity/development"], "POST")], auth="user")
    # def get_checklist_for_development(self):
    #     params = request.params
    #     if not params.get('tower_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     tower_id = self.env['project.tower'].sudo().browse(
    #         int(params.get('tower_id')))
    #     if not tower_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     data = {
    #         'tower_name': tower_id.name,
    #         'tower_id': tower_id.id
    #     }

    #     list_flat_data = []
    #     total_count = 0
    #     for activity in tower_id.development_activity_ids:
    #         #_logger.info("-----act name-----,%s",activity.name)

    #         count = draft = checked = approve = 0
    #         color = 'yellow'
    #         activity_type_status = False
    #         for act_type in activity.activity_type_ids:
    #             status = act_type.status
    #             count += 1
    #             if status == 'draft':
    #                 draft += 1
    #             if status == 'checked':
    #                 checked += 1
    #             if status == 'approve':
    #                 approve += 1

    #         total_count += count
    #         if draft and not checked and not approve:
    #             color = 'red'
    #         if approve and not draft and not checked:
    #             color = 'green'
    #             activity_type_status = True

    #         list_flat_data.append({
    #             'name': activity.name,
    #             'desc': '',
    #             'activity_id': activity.id,
    #             'write_date': str(activity.write_date),
    #             'activity_type_status': activity_type_status,
    #             'progress': activity.progress_percentage or 0.0,
    #             'color': color,
    #         })
    #     data['list_flat_data'] = list_flat_data
    #     data['total_count'] = total_count

    #     # _logger.info("-----data------,%s",data)

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/activity/development"], "POST")], auth="user")
    def get_checklist_for_development(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower = self.env['project.tower'].sudo().browse(int(params.get('tower_id')))
        if not tower.exists():
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = {'tower_name': tower.name, 'tower_id': tower.id}
        list_flat_data = []
        total_count = 0

        for activity in tower.development_activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                elif status == 'checked':
                    checked += 1
                elif status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            elif approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            last_update = self._get_activity_last_update(activity)

            list_flat_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': last_update or '',
                'activity_type_status': activity_type_status,
                'progress': float(activity.progress_percentage or 0.0),
                'color': color,
            })

        data['list_flat_data'] = list_flat_data
        data['total_count'] = total_count

        return Response(json.dumps({
            'status': 'SUCCESS',
            'message': 'Activity info Fetch',
            'activity_data': data
        }), content_type='application/json;charset=utf-8', status=200)

    

    ################### HIQ API's ###########################3
    @restapi.method([(["/get/issue/category"], "POST")], auth="user")
    def get_issue_category(self):
        records = self.env['issue.category'].sudo().search([])
        data = [
            {
                'issue_category_id': rec.id,
                'name': rec.name,
                'sequence': rec.sequence,
            }
            for rec in records
        ]
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Issue Category','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/get/issue/type"], "POST")], auth="user")
    def get_issue_type(self):
        params = request.params
        if not params.get('issue_category_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Categor Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        records = self.env['issue.type'].sudo().search([('issue_category_id','=',int(params.get('issue_category_id')))])
        data = [
            {
                'issue_type_id': rec.id,
                'name': rec.name,
                'sequence': rec.sequence,
                'issue_category_id':rec.issue_category_id.id or False,
            }
            for rec in records
        ]
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Issue Type(s)','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/get/hqi/towers"], "POST")], auth="user")
    def get_hqi_towers(self):
        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param

        project_id = params.get('project_id')
        user_id = int(params.get('user_id'))

        if not project_id and not user_id:
            return Response(
                json.dumps({'status': 'FAILED', 'message': 'Please send Project ID and User ID'}),
                content_type='application/json;charset=utf-8', status=400
            )

        try:
            project_id = int(project_id)
        except ValueError:
            return Response(
                json.dumps({'status': 'FAILED', 'message': 'Invalid Project ID'}),
                content_type='application/json;charset=utf-8', status=400
            )

        # Get towers with HQI in progress or completed
        towers = self.env['project.tower'].sudo().search([
            ('project_id', '=', project_id),
            ('hqi_state', 'in', ['progress', 'completed']),
            ('hqi_user_ids', 'in', user_id),

        ])

        tower_data = [{
            'tower_id': tower.id,
            'name': tower.name,
            'progress': 0.00,  # Placeholder, update if needed
        } for tower in towers]

        # Get project details line with name "Home Inspection"
        project = self.env['project.info'].sudo().browse(project_id)
        line = project.project_details_line.filtered(lambda l: l.name == "Home Inspection")
        checklist_image_url = ''
        if line:
            line_id = line[0].id
            base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
            checklist_image_url = f"{base_url}/web/image?model=project.details&field=image&id={line_id}"

        master_data = {
            'checklist_name': "Home Inspection",
            'image_url': checklist_image_url,
            'tower_data': tower_data
        }

        return Response(
            json.dumps({'status': 'SUCCESS', 'message': 'HQI eligible Towers', 'data': master_data}),
            content_type='application/json;charset=utf-8',
            status=200
        )

    
    # @restapi.method([(["/get/hqi/towers"], "POST")], auth="user")
    # def get_hqi_towers(self):
    #     params = request.params
    #     get_param = self.env['ir.config_parameter'].sudo().get_param
        
    #     project_id = int(params.get('project_id'))
    #     if not project_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
   
    #     project_towers = self.env['project.tower'].sudo().search([('project_id','=',project_id),('hqi_state','in',['progress','completed'])])
    #     data = [
    #         {
    #             'tower_id': rec.id,
    #             'name': rec.name,
    #             'progress': 0.00,              
    #         }
    #         for rec in project_towers
    #     ]
    #     line_id = False
    #     project_rec = self.env['project.info'].sudo().browse(project_id)
    #     for line in project_rec.project_details_line:
    #         if "Home Inspection"  == line.name:
    #             line_id = line.id

    #     base_url = get_param(
    #         'web.base.url', default='http://www.odoo.com?NoBaseUrl')
    #     checklist_image_url = base_url + \
    #         "/web/image?model=project.details&field=image&id=" + \
    #         str(line_id)
                

    #     master_data = {'checklist_name':"Home Inspection",'image_url':checklist_image_url,'tower_data':data}

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'HQI eligible Towers','data': master_data}),
    #                     content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/submit/hqi/flat"], "POST")], auth="user")
    def submit_hqi_flat(self):
        params = request.params
        flat_id = int(params.get('flat_id'))
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        flat_rec = self.env['project.flats'].sudo().browse(flat_id)
        
        value = self.env['flat.site.visit'].create_first_site_visit(flat_id)
        _logger.info("--value------submit_hqi_flat----------,%s",value)

        if value == 100:
            return Response(json.dumps({'status': 'Failed', 'message': 'Visit Exists'}),
                        content_type='application/json;charset=utf-8', status=200)
        if value == 300:
            return Response(json.dumps({'status': 'Failed', 'message': 'Unit Locations does not exists'}),
                        content_type='application/json;charset=utf-8', status=200)
        flat_rec.hqi_state = 'progress'
        flat_rec.tower_id.hqi_state = 'progress'
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'HQI set to progress'}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/complete/hqi/flats"], "POST")], auth="user")
    def complete_flat_hqi(self):
        params = request.params
        flat_id = int(params.get('flat_id'))
       
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['project.flats'].sudo().complete_flat_hqi(flat_id)
       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat HQI Completed'}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/get/hqi/flats"], "POST")], auth="user")
    def get_hqi_flats(self):
        params = request.params
        project_id = int(params.get('project_id'))
        tower_id = int(params.get('tower_id'))
        if not project_id and not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project and Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = self.env['project.flats'].sudo().get_hqi_flats(project_id,tower_id)
       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'HQI eligible flats','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/get/flat/visits"], "POST")], auth="user")
    def get_flat_visits(self):
        params = request.params
        project_id = int(params.get('project_id'))
        tower_id = int(params.get('tower_id'))
        flat_id = int(params.get('flat_id'))
        user_id = int(params.get('user_id'))

        if not project_id and not tower_id and not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project, Tower and Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = self.env['project.flats'].sudo().get_flat_visits(project_id, tower_id,flat_id,user_id)   
        #_logger.info("--DATA---------------,%s",data)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat Visits','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/get/flat/sv/location/obseration"], "POST")], auth="user")
    def get_flat_sv_location_observation(self):
        #_logger.info("--get_flat_sv_location_observationget_flat_sv_location_observation--,%s",params)

        params = request.params
        #_logger.info("--get_flat_sv_location_observationget_flat_sv_location_observation--,%s",params)

        location_id = int(params.get('location_id'))
        
        if not location_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Locarion ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = self.env['site.visit.locations'].sudo().get_flat_sv_location_observation(location_id)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat Visits','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/flat/observation/return-to-maker"], "POST")], auth="user")
    def flat_observation_return_to_maker_by_checker(self):
        params = request.params
        #_logger.info("-------flat_observation_return_to_maker_by_checker--,%s",params)
    
        location_id = params.get('location_id')
        user_id = params.get('user_id')

        if not location_id and not user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Location and User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        
        try:
            user_id = int(user_id)
            location_id = int(location_id)

        except ValueError:
            _logger.info("------INVALID userid or location id--")

            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid user_id or Location ID'}),
                            content_type='application/json;charset=utf-8', status=400)

        self.env['site.visit.location.observation'].sudo().flat_observation_return_to_maker_by_checker(params)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Observation to maker'}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/flat/observation/completed"], "POST")], auth="user")
    def flat_observation_completed(self):
        params = request.params
        #_logger.info("------flat_observation_completed--,%s",params)

        observation_id = params.get('observation_id')
        user_id = params.get('user_id')

        
        if not observation_id and not user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Observation and User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        
        try:
            user_id = int(user_id)
            observation_id = int(observation_id)

        except ValueError:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid user_id or Observation ID'}),
                            content_type='application/json;charset=utf-8', status=400)

        self.env['site.visit.location.observation'].sudo().flat_observation_completed(params)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker cleared the obervation'}),
                        content_type='application/json;charset=utf-8', status=200)
    
    
    
    @restapi.method([(["/flat/observation/resubmit-to-checker"], "POST")], auth="user")
    def flat_observation_resubmit_to_checker(self):
        params = request.params
        #_logger.info("-----flat_observation_resubmit_to_checker---,%s",params)

        observation_id = params.get('observation_id')
        user_id = params.get('user_id')

        
        if not observation_id and not user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Observation and User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        
        try:
            user_id = int(user_id)
            observation_id = int(observation_id)

        except ValueError:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid User  or Observation ID'}),
                            content_type='application/json;charset=utf-8', status=400)

        data = self.env['site.visit.location.observation'].sudo().flat_observation_resubmit_to_checker(params)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Resubmit By Checker','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/get/hqi/observation/history"], "POST")], auth="user")
    def get_hqi_observation_history(self):
        params = request.params
        observation_id = int(params.get('observation_id'))
       
        if not observation_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = self.env['site.visit.location.observation'].sudo().get_hqi_observation_history(observation_id)
        
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Observation History','data': data}),
                        content_type='application/json;charset=utf-8', status=200)
    
    @restapi.method([(["/replicate/hqi/observation"], "POST")], auth="user")
    def replicate_hqi_observation_history(self):
        params = request.params
        observation_id = int(params.get('observation_id'))
        user_id = int(params.get('user_id'))

        if not observation_id and not user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Observation and User Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        
        try:
            user_id = int(user_id)
            observation_id = int(observation_id)

        except ValueError:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid User or Observation ID'}),
                            content_type='application/json;charset=utf-8', status=400)
        data = self.env['site.visit.location.observation'].sudo().replicate_hqi_observation_history(observation_id,user_id)
       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Replicate Observation Successfully','data':data}),
                        content_type='application/json;charset=utf-8', status=200)
    


    @restapi.method([(["/get/site/visit/pdf"], "POST")], auth="user")
    def get_site_visit_pdf(self):
        params = request.params
        visit_id = int(params.get('visit_id', 0))
        if not visit_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please provide Visit ID'}),
                            content_type='application/json;charset=utf-8', status=400)

        pdf_data = self.env['flat.site.visit'].sudo().get_site_visit_pdf(visit_id)
      
        if not pdf_data:
            return Response(json.dumps({'status': 'FAILED', 'message': 'PDF generation failed'}),
                            content_type='application/json;charset=utf-8', status=500)

        return Response(json.dumps({
            'status': 'SUCCESS',
            'message': 'PDF Generated',
            'pdf_base64': pdf_data
        }), content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/get/flat/hqi/pdf"], "POST")], auth="user")
    def get_flat_hqi_pdf(self):
        params = request.params
        flat_id = int(params.get('flat_id', 0))
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Provide Flat ID'}),
                            content_type='application/json;charset=utf-8', status=400)

        pdf_data = self.env['project.flats'].sudo().get_flat_hqi_pdf(flat_id)
      
        if not pdf_data:
            return Response(json.dumps({'status': 'FAILED', 'message': 'PDF generation failed'}),
                            content_type='application/json;charset=utf-8', status=500)

        return Response(json.dumps({
            'status': 'SUCCESS',
            'message': 'PDF Generated',
            'pdf_base64': pdf_data
        }), content_type='application/json;charset=utf-8', status=200)

    #### Offline APi ##
    @restapi.method([(["/get/hqi/flats/offline"], "POST")], auth="user")
    def get_flat_hqi_offline(self):
        params = request.params
        flat_id = int(params.get('flat_id'))
        user_id = int(params.get('user_id'))


        if not flat_id and not user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat and User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = self.env['project.flats'].sudo().get_flat_hqi_offline(flat_id,user_id)
       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat Data','data': data}),
                        content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/get/flat/sv/location/observation/offline"], "POST")], auth="user")
    def get_flat_sv_location_observation_offline(self):
        #_logger.info("--get_flat_sv_location_observationget_flat_sv_location_observation--,%s",params)

        params = request.params
        _logger.info("--get_flat_sv_location_observationget_flat_sv_location_observation--,%s",params)

        location_id = int(params.get('location_id'))
        
        if not location_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Locarion ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = self.env['site.visit.locations'].sudo().get_flat_sv_location_observation(location_id)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat Visits','data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/hqi/observation/history/offline"], "POST")], auth="user")
    def get_hqi_observation_history_offline(self):
        params = request.params
        observation_id = int(params.get('observation_id'))
       
        if not observation_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = self.env['site.visit.location.observation'].sudo().get_hqi_observation_history(observation_id)
       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Observation History','data': data}),
                        content_type='application/json;charset=utf-8', status=200)

def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'phone', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang'}


def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(4):
        OTP += digits[int(math.floor(random.random() * 10))]
    return OTP
