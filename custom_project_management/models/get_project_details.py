from odoo import http
from odoo.http import request
import json
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class ProjectDetails(http.Controller):

# curl -X POST http://your_odoo_server.com/api/sale_orders \
# -H "Content-Type: application/json" \
# -d '{"from_date": "2024-03-01", "to_date": "2024-03-15"}'
    @http.route('/api/project_details', type='json', auth='public', methods=['POST'], csrf=False)
    def get_project_details(self, **kwargs):
        return {'status': 'success', 'message': 'API is working!'}

    @http.route('/api/project_details1', type='json', auth='public', methods=['POST'], csrf=False)
    def get_project_details1(self, **kwargs):
        print ("--------------get_project_details-------------------------------------")
        _logger.info("----get_project_details-------")
        try:
            # Get date parameters from request
            from_date = kwargs.get('from_date')
            to_date = kwargs.get('to_date')

            # Validate and parse dates
            domain = []
            if from_date and to_date:
                from_date = datetime.strptime(from_date, "%Y-%m-%d")
                to_date = datetime.strptime(to_date, "%Y-%m-%d")
                domain = [('completed_date', '>=', from_date),('completed_date', '<=', to_date),('state', '=', 'completed')]

            # Fetch sale orders based on the date range
            project_activity_rec = request.env['project.activity'].sudo().search(domain)
            _logger.info("--project_activity_rec-----,%s",project_activity_rec)

            # # Prepare response data
            # data = []
            # for order in sale_orders:
            #     data.append({
            #         'id': order.id,
            #         'name': order.name,
            #         'partner': order.partner_id.name,
            #         'amount_total': order.amount_total,
            #         'state': order.state,
            #         'date_order': order.date_order,
            #     })

            return {'status': 'success', 'project_details': project_activity_rec}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
