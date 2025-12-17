import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class TestAPI(http.Controller):

    @http.route('/api/test/data/new', type='json', auth="public", methods=['POST'], csrf=False)
    def test_api(self, **kwargs):
        
        """ API that returns sample data """
        
        # Log request data
        _logger.info("Received API request with params: %s", kwargs)

        # Sample response data
        response_data = {
            "status": "SUCCESS",
            "message": "API is working!",
            "data": {
                "id": 1,
                "name": "Test User",
                "email": "test@example.com"
            }
        }

        return response_data  # Automatically returns JSON response
