from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger("__name__")

try:
    from cachetools import LRUCache, cachedmethod
except ImportError:
    _logger.debug("Cannot import 'cachetools'.")

class MyController(http.Controller):


    @http.route('/get/activity/details', auth='public', methods=['POST'], csrf=False)
    def get_activity_details(self):
        #_logger.info("---------get_activity_details--------")
        data = json.loads(request.httprequest.data)
        #_logger.info("--------data--------",data)
        #_logger.info("---------projects--------,%s",(data))
        env = request.env    
        activity_type_id = int(data['id'])           
        activity_data = env['project.activity.type'].sudo().get_project_activity_details(activity_type_id)
        #_logger.info("---------Activity Data--------,%s",len(activity_data))
        return json.dumps({"status": "SUCCESS","message": "Activity Data Fetch","activity_data":activity_data})
    

    @http.route('/get/user/notifications', auth='public', methods=['POST'], csrf=False)
    def get_users_notification(self):
        #_logger.info("---------get_users_notificaton--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        user_id = int(data['id'])
        Notifications = env['app.notification.log'].sudo().get_users_notification_details(user_id)
        #_logger.info("---------Notifications--------,%s",len(Notifications))
        return json.dumps({"status": "SUCCESS","message": "Notification Fetch","notification_data":Notifications})
    
    @http.route('/get/all/projects', auth='public', methods=['POST'], csrf=False)
    def get_all_projects(self):
        #_logger.info("---------get_all_projects--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        #_logger.info((env))
        #_logger.info((data['id']))
        user_id = int(data['id'])
        projects = env['project.info'].sudo().get_all_projects_details(user_id)
        #_logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS","message": "Project Fetch","project_data":projects})
    
    @http.route('/get/all/projects/towers/checklist', auth='public', methods=['POST'], csrf=False)
    def get_all_projects_towers_checklist(self):
        data = json.loads(request.httprequest.data)
        env = request.env
        #_logger.info((env))
        #_logger.info((data['id']))
        user_id = int(data['id'])
        #_logger.info("---------get_all_projects_towers_checklist--------")
        projects = env['project.info'].sudo().get_all_projects_towers_checklist_details(user_id)
        #_logger.info("-------get_all_projects_towers_checklist--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS","message": "Project Fetch","tower_info":projects})
    
    
    @http.route('/get/all/projects/flats/floors', auth='public', methods=['POST'], csrf=False)
    
    def get_all_projects_all_flats_floors(self):
        #_logger.info("---------get_all_projects_all_flats_floors--------")

        env = request.env
        data = json.loads(request.httprequest.data)
        env = request.env
        #_logger.info((env))
        #_logger.info((data['id']))
        user_id = int(data['id'])
        
        projects = env['project.info'].sudo().get_all_projects_all_flats_floors_details(user_id)
        #_logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS","message": "Tower info Fetch","flat_floor_info":projects})

    ##### Need to shift all the above apis to session.py######



    @http.route('/onesignal/my_endpoint', auth='public', methods=['POST'], csrf=False)
    def my_endpoint(self, **kwargs):
        try:
            # Access POST data
            data = json.loads(request.httprequest.data)
            env = request.env
            _logger.info((env))
            _logger.info((data['id']))

            _logger.info((data['token']))
            _logger.info((data['player_id']))
            user_record = env['res.users'].sudo().browse(int(data['id']))
            if user_record:
                child_records = [(0, 0, {'player_id': data['player_id']})]
                user_record.sudo().write({'player_line_ids': child_records})
            #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
            
            # Process data (you can customize this part)
            result = {"success": True, "message": "Data received successfully"}
        except Exception as e:
            _logger.info(str(e))

            result = {"success": False, "message": str(e)}

        # Return the response as JSON
        return json.dumps(result)





    @http.route('/material_inspection/pending_report_counts', type='http', auth='public', methods=['POST'], csrf=False)
    def get_pending_report_counts(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            project_id = data.get('project_id')
            tower = data.get('tower')

            # Ensure proper model call
            result = request.env['material.inspection'].sudo().get_pending_report_counts(
                project_id=project_id,
                tower=tower
            )

            response = {
                'status': 'success',
                'data': result
            }
        except Exception as e:
            response = {
                'status': 'error',
                'message': str(e)
            }

        return request.make_response(
            json.dumps(response),
            headers=[('Content-Type', 'application/json')]
        )


    @http.route('/material/role_wise_report_counts', type='json', auth='public')
    def get_role_wise_report_counts_api(self, **kwargs):
        """
        API to get role-wise report counts filtered by project_id and tower_id
        """
        project_id = kwargs.get('project_id')
        tower_id = kwargs.get('tower_id')

        domain = []
        if project_id:
            domain.append(('project_info_id', '=', int(project_id)))
            _logger.info("====found====")
        if tower_id:
            domain.append(('tower_id', '=', int(tower_id)))
        

        result = {
            'maker': {'completed': 0, 'pending': 0},
            'checker': {'completed': 0, 'pending': 0},
            'approver': {'completed': 0, 'pending': 0},
        }

        status_counts = request.env['material.inspection'].sudo().read_group(
            domain=domain,
            fields=['status'],
            groupby=['status'],
            lazy=False
        )

        for rec in status_counts:
            status = rec['status']
            count = rec['__count']

            if status == 'draft':
                result['maker']['pending'] += count
            elif status == 'submit':
                result['maker']['completed'] += count
                result['checker']['pending'] += count
            elif status == 'checked':
                result['checker']['completed'] += count
                result['approver']['pending'] += count
            elif status == 'approve':
                result['approver']['completed'] += count
            elif status == 'checker_rejected':
                result['checker']['pending'] += count
            elif status == 'approver_rejected':
                result['approver']['pending'] += count

        _logger.info("Role-wise filtered report counts: %s", result)
        return result


    @http.route('/session/auth/material/completed_report_counts', type='json', auth='public')
    def get_completed_report_counts_api(self):

        data = json.loads(request.httprequest.data)
        project_id = data.get('project_id')
        tower_id = data.get('tower_id')


        _logger.info("recieved data: %s",project_id)
        _logger.info("recieved data: %s", tower_id)

        domain = []
        if project_id:
            domain.append(('project_info_id', '=', int(project_id)))
        if tower_id:
            domain.append(('tower_id', '=', int(tower_id)))
        _logger.info("=======================%s", domain)

        result = {
            "maker_pending": 0,
            "maker_completed": 0,
            "checker_pending": 0,
            "checker_completed": 0,
            "approver_pending": 0,
            "approver_completed": 0
        }

        status_counts = request.env['material.inspection'].sudo().read_group(
            domain=domain,
            fields=['status'],
            groupby=['status'],
            lazy=False
        )

        for rec in status_counts:
            stat = rec['status']
            count = rec['__count']

            if stat == 'submit':
                result["maker_completed"] += count
            elif stat == 'checked':
                result["checker_completed"] += count
            elif stat == 'approve':
                result["approver_completed"] += count

        return result