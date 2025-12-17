# from odoo import http
# from odoo.http import request

# class OdooAPIController(http.Controller):

#     @http.route('/api/get_customers', type='json', auth="public", methods=['POST'], csrf=False)
#     def get_customers(self, **kwargs):
#         """ API to fetch customer data from Odoo with API Key Authentication """

#         # Get API Key from Headers
#         api_key = request.httprequest.headers.get("Authorization")
#         if not api_key or not api_key.startswith("Bearer "):
#             return {"error": "Unauthorized", "message": "API Key is missing"}, 401

#         # # Extract the key and validate it
#         # api_key = api_key.replace("Bearer ", "").strip()
#         # user = request.env["res.users"].sudo().search([("api_key", "=", api_key)], limit=1)
#         # if not user:
#         #     return {"error": "Unauthorized", "message": "Invalid API Key"}, 401

#         # # Get customers
#         # customers = request.env['res.partner'].sudo().search([('customer_rank', '>', 0)])
#         # customer_data = [{"id": c.id, "name": c.name, "email": c.email} for c in customers]

#         return {"status": "SUCCESS", "message": "Data retrieved", "data": {"customer_data": "customer_data"}}


from odoo import http
from odoo.http import request

class MyAPIController(http.Controller):
    @http.route('/api/test', type='json', auth="user", methods=['POST'])
    def test_api(self):
        user = request.env.user  # Odoo will authenticate the API key
        return {
            "status": "SUCCESS",
            "message": "Authenticated API Request",
            "user": user.name
        }
